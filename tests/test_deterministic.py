"""Unit tests for the deterministic core (no browser, no model)."""
from backend.agent import completion, memory, safety
from backend.agent.goal import compile_goal
from backend.agent.planner import _coerce
from backend.events import EventBus, load_events
from backend.runtime.accessibility import risk_score
from backend.runtime.fingerprint import canonical_route, state_fingerprint
from backend.schemas import (
    ActionType, AxeViolation, BrowserAction, ModelDecision, ModelFact, Observation, ObservedElement, PageFact,
)


def obs(text="", route="/#/cart", elements=(), dialog=False, fp="s1"):
    return Observation(observation_id="o1", url="http://x" + route, route=route, visible_text=text,
                       elements=list(elements), dialog_open=dialog, fingerprint=fp)


def test_entity_normalization():
    assert memory.normalize_entity("  Nova   Headphones ") == memory.normalize_entity("nova headphones")
    assert memory.normalize_entity("Nova-Headphones!") == "nova headphones"
    assert memory.normalize_entity("Nova+ Pro") != memory.normalize_entity("Nova Pro")


def test_fact_grounding_rejects_hallucinated_prices():
    o = obs("Nova Headphones 1 ₹2,799 Subtotal: ₹2,799")
    good = ModelFact(kind="product_price", entity="Nova Headphones", value=2799, context="cart")
    bad = ModelFact(kind="product_price", entity="Nova Headphones", value=2499, context="cart")
    facts: list[PageFact] = []
    accepted, rejected = memory.absorb_facts(facts, [good, bad], o, 4, "cart")
    assert [f.value for f in accepted] == [2799] and rejected == [bad]


def test_indian_grouping_grounding():
    o = obs("Price ₹1,24,999")
    f = ModelFact(kind="product_price", entity="TV", value=124999)
    assert memory.is_grounded(f, o)


def _pf(value, step, state, ctx):
    return PageFact(kind="product_price", entity="Nova Headphones", value=value, step_number=step, url="/", state_id=state, context=ctx)


def test_price_conflict_detection_and_dedup():
    facts = [_pf(2499, 2, "results", "search_results"), _pf(2499, 3, "product", "product_page"), _pf(2799, 4, "cart", "cart")]
    reported: set[str] = set()
    found = memory.detect_price_conflicts(facts, reported)
    assert len(found) == 1
    f = found[0]
    assert f.severity == "high" and f.verified and f.data["difference"] == 300 and f.data["percent"] == 12.0
    assert f.data["before_context"] == "product_page"
    assert memory.detect_price_conflicts(facts, reported) == []  # not re-reported


def test_no_conflict_when_prices_match():
    assert memory.detect_price_conflicts([_pf(2499, 2, "a", "search_results"), _pf(2499, 3, "b", "product_page")], set()) == []


def test_accessibility_score_counts_unique_rules():
    v = lambda i, imp: AxeViolation(id=i, impact=imp, description="d", help="h")
    assert risk_score([]) == 100
    assert risk_score([v("color-contrast", "serious"), v("label", "critical")]) == 61
    assert risk_score([v("label", "critical"), v("label", "critical")]) == 75
    assert risk_score([v(f"r{i}", "critical") for i in range(9)]) == 0


def test_fingerprint_stable_under_noise_and_modal_sensitive():
    a = state_fingerprint("http://x/#/cart?utm_source=a", "Your cart", "", ["button:Checkout"], "Total 2,799 at 10:31:02")
    b = state_fingerprint("http://x/#/cart", "Your cart", "", ["button:Checkout"], "Total 2,799 at 11:02:45")
    c = state_fingerprint("http://x/#/cart", "Your cart", "Join Nova+", ["button:Close"], "Total 2,799")
    assert a == b and a != c
    assert canonical_route("http://x/#/results?q=nova&fbclid=1") == "/#/results?q=nova"


def test_goal_compilation():
    g = compile_goal("Find the Nova headphones under ₹3,000, add them to cart, and reach checkout.")
    assert g.objective == "reach_checkout"
    assert g.constraints == {"max_price": 3000.0, "product": "Nova headphones"}
    assert g.success.url_contains == ["checkout"]


def test_completion_requires_deterministic_evidence():
    g = compile_goal("reach checkout")
    email = ObservedElement(element_id=0, role="textbox", input_type="email")
    assert completion.verify(g, obs(route="/#/checkout", elements=[email])).completed
    assert not completion.verify(g, obs(route="/#/cart", elements=[email])).completed
    assert not completion.verify(g, obs(route="/#/checkout", elements=[])).completed
    assert not completion.verify(g, obs(route="/#/checkout", elements=[email], dialog=True)).completed
    covered = email.model_copy(update={"covered": True})
    assert not completion.verify(g, obs(route="/#/checkout", elements=[covered])).completed


def test_safety_gate():
    act = BrowserAction(observation_id="o", action=ActionType.CLICK, element_id=0)
    el = lambda name, **kw: ObservedElement(element_id=0, role="button", name=name, **kw)
    assert safety.check(act, el("Pay ₹2,799"), False)
    assert safety.check(act, el("Join Nova+"), False)
    assert safety.check(act, el("Place order"), False)
    assert safety.check(act, el("Checkout"), False) is None
    assert safety.check(act, el("Close"), False) is None
    assert safety.check(act, el("Pay ₹2,799"), True) is None
    typ = act.model_copy(update={"action": ActionType.TYPE, "text": "x"})
    assert safety.check(typ, ObservedElement(element_id=0, role="textbox", input_type="password"), False)
    assert safety.check(typ, ObservedElement(element_id=0, role="textbox", name="Card number"), False)


def test_action_schema_validation_and_coercion():
    raw = {"page_summary": "cart", "goal_progress": 0.6,
           "facts": [{"kind": "product_price", "entity": "Nova", "value": "2,799", "context": "cart"}],
           "findings": [], "next_action": {"observation_id": "WRONG", "action": "CLICK", "element_id": 3,
                                           "rationale": "go", "confidence": 0.9}}
    d = ModelDecision.model_validate(_coerce(raw, obs()))
    assert d.next_action.observation_id == "o1" and d.next_action.action == ActionType.CLICK
    assert d.facts[0].value == 2799
    import pytest
    with pytest.raises(Exception):
        ModelDecision.model_validate({"page_summary": "x", "goal_progress": 2, "next_action": {}})


def test_event_serialization_roundtrip(tmp_path):
    bus = EventBus("r1", tmp_path)
    bus.emit("run_started", {"mode": "live"})
    bus.emit("finding", {"title": "t", "severity": "high"})
    bus.close()
    evs = load_events(tmp_path / "events.jsonl")
    assert [e.sequence for e in evs] == [1, 2] and evs[1].type == "finding" and evs[1].run_id == "r1"


def test_readback_detects_field_that_rejects_input_and_side_effects():
    from backend.agent import critic
    from backend.schemas import AgentState, ExecutionStep, GoalSpec, TargetDescriptor
    first = ObservedElement(element_id=0, role="textbox", name="First Name", input_type="text", value="Asha")
    last = ObservedElement(element_id=1, role="textbox", name="Last Name", input_type="text", value=None)
    prev = obs("Checkout", "/checkout", [first, last], fp="a")
    after = obs("Checkout", "/checkout", [first.model_copy(update={"value": "Rao"}), last], fp="a")
    st = AgentState(goal=GoalSpec(raw="x"), target_url="http://x")
    step = ExecutionStep(step_number=1, url_before="x", action=BrowserAction(observation_id="o", action=ActionType.TYPE, element_id=1, display_label="Last Name", text="Rao"),
                         target=TargetDescriptor(role="textbox", name="Last Name", input_type="text"), outcome="success")
    rep = critic.analyse_transition(st, prev, after, step)
    f = next(f for f in rep.findings if "does not keep typed input" in f.title)
    assert f.severity == "high" and "First Name" in f.evidence


def test_new_error_message_detection():
    from backend.agent.critic import new_error_messages
    msgs = new_error_messages(obs("Checkout form"), obs("Checkout form Error: Last Name is required"))
    assert msgs and "Last Name is required" in msgs[0]
    assert new_error_messages(obs("Error: x is required"), obs("Error: x is required")) == []


def test_currency_detected_from_page_not_model():
    o = obs("Sauce Labs Backpack $29.99 Add to cart")
    f = ModelFact(kind="product_price", entity="Sauce Labs Backpack", value=29.99, currency="INR")
    accepted, _ = memory.absorb_facts([], [f], o, 1, "s")
    assert accepted[0].currency == "USD"
    assert memory.money(29.99, "USD") == "$29.99" and memory.money(2499, "INR") == "₹2,499"


def test_safety_allows_credentials_given_in_goal_only():
    typ = BrowserAction(observation_id="o", action=ActionType.TYPE, element_id=0, text="secret_sauce")
    pw = ObservedElement(element_id=0, role="textbox", input_type="password")
    assert safety.check(typ, pw, False, "log in with password secret_sauce") is None
    assert safety.check(typ, pw, False, "log in") is not None
