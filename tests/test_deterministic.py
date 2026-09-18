"""Unit tests for the deterministic core (no browser, no model)."""
from backend.agent import completion, memory, safety
from backend.agent.goal import compile_goal
from backend.agent.planner import _coerce
from backend.events import EventBus, load_events
from backend.runtime.accessibility import risk_score
from backend.runtime.fingerprint import canonical_route, state_fingerprint
from backend.schemas import (
    ActionType, AxeViolation, BrowserAction, ExecutionStep, ModelDecision, ModelFact, Observation, ObservedElement, PageFact,
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


def test_fingerprint_keeps_origins_and_task_state_distinct():
    """F14: identical routes on different sites, or a changed selected filter, are separate states."""
    base = state_fingerprint("https://one.example/results", "Results", "", ["combobox|Size||M|None|True|visible|False"], "Shoes")
    other_origin = state_fingerprint("https://two.example/results", "Results", "", ["combobox|Size||M|None|True|visible|False"], "Shoes")
    changed_filter = state_fingerprint("https://one.example/results", "Results", "", ["combobox|Size||L|None|True|visible|False"], "Shoes")
    assert base != other_origin and base != changed_filter


def test_action_requires_action_specific_fields():
    """F13: incomplete actions must be rejected before they reach the browser adapter."""
    import pytest
    with pytest.raises(Exception):
        BrowserAction(observation_id="o", action=ActionType.SCROLL)
    with pytest.raises(Exception):
        BrowserAction(observation_id="o", action=ActionType.PRESS)
    with pytest.raises(Exception):
        BrowserAction(observation_id="o", action=ActionType.SELECT, element_id=1)
    with pytest.raises(Exception):
        BrowserAction(observation_id="o", action=ActionType.HOVER)
    assert BrowserAction(observation_id="o", action=ActionType.SELECT, element_id=1, text="Blue").text == "Blue"


def test_extract_json_rejects_non_object_model_output():
    from backend.agent.llm import extract_json
    import pytest
    with pytest.raises(ValueError):
        extract_json("[]")


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


def test_completion_rejects_empty_cart_even_if_url_matches():
    g = compile_goal("Search for earphones, add one to the cart, and open the cart.", success_url=["cart"])
    assert not completion.verify(g, obs("Your Amazon Cart is empty", route="/cart")).completed
    assert completion.verify(g, obs("Subtotal (1 item): ₹299", route="/cart")).completed


def test_completion_rejects_over_budget_price():
    """F01/F03: an item priced above the goal's max_price must not verify as complete, even once the
    checkout route, an email field and the cart sighting are all otherwise satisfied."""
    g = compile_goal("Find the Nova headphones under ₹3,000, add them to cart, and reach checkout.")
    email = ObservedElement(element_id=0, role="textbox", input_type="email")
    o = obs("Nova Headphones ₹3,499", route="/#/checkout", elements=[email])
    over_budget = [_pf(3499, 3, "checkout", "checkout")]
    assert not completion.verify(g, o, over_budget, cart_product_seen=True).completed
    within_budget = [_pf(2799, 3, "checkout", "checkout")]
    assert completion.verify(g, o, within_budget, cart_product_seen=True).completed
    # No grounded price at all: unknown must not silently block completion of the other criteria.
    assert completion.verify(g, o, [], cart_product_seen=True).completed


def test_completion_cart_presence_is_not_a_sticky_historical_flag():
    """F01: removing the item after it was seen in the cart must invalidate a prior cart-success sighting."""
    g = compile_goal("Search for earphones, add one to the cart, and open the cart.", success_url=["cart"])
    had_item = obs("Nova Earbuds x1 Subtotal: ₹1,299", route="/cart")
    now_empty = obs("Your cart is empty.", route="/cart")
    assert completion.verify(g, had_item).completed
    assert not completion.verify(g, now_empty).completed


def test_completion_login_form_presence_does_not_prove_login():
    """F01: a visible password field proves a login FORM is showing, never that the user is logged in."""
    g = compile_goal("log in to the account")
    password = ObservedElement(element_id=0, role="textbox", input_type="password")
    on_login_page = obs(route="/#/login", elements=[password])
    assert not completion.verify(g, on_login_page).completed
    logged_in = obs(route="/#/account", elements=[])
    assert completion.verify(g, logged_in).completed


def test_completion_query_param_does_not_fake_a_destination():
    """F01: "/search?q=checkout" must not satisfy a url_contains=["checkout"] destination check, while a
    real checkout route with an unrelated query string still must."""
    g = compile_goal("reach checkout")
    email = ObservedElement(element_id=0, role="textbox", input_type="email")
    assert not completion.verify(g, obs(route="/#/search?q=checkout", elements=[email])).completed
    assert completion.verify(g, obs(route="/#/checkout?ref=email", elements=[email])).completed


def test_price_grounding_does_not_round_decimal_to_visible_integer():
    """F03: a proposed 29.99 must not be accepted just because the page shows a rounded 30."""
    o = obs("Widget 30")
    bad = ModelFact(kind="product_price", entity="Widget", value=29.99)
    assert not memory.is_grounded(bad, o)
    exact = obs("Widget 29.99")
    assert memory.is_grounded(bad, exact)


def test_no_price_conflict_across_currency_change():
    """F03: a currency change fully explains a numeric difference; it must not be reported as a defect."""
    facts = [PageFact(kind="product_price", entity="Nova", value=29.99, currency="USD", context="product_page",
                       step_number=1, url="/product"),
             PageFact(kind="product_price", entity="Nova", value=2499, currency="INR", context="cart",
                       step_number=2, url="/cart")]
    assert memory.detect_price_conflicts(facts, set()) == []


def test_expected_dialog_is_not_an_interruption():
    """F04: opening a Filters panel is normal UI, not friction - unlike a promo modal over Checkout."""
    from backend.agent import critic
    from backend.schemas import AgentState, ExecutionStep, GoalSpec

    st = AgentState(goal=GoalSpec(raw="x"), target_url="http://x")
    prev = obs("Results", "/results", dialog=False, fp="a")
    after_filter = obs("[DIALOG] Filter by size", "/results", dialog=True, fp="b")
    step = BrowserAction(observation_id="o", action=ActionType.CLICK, element_id=0, display_label="Filters")
    xstep = ExecutionStep(step_number=1, url_before="x", action=step, outcome="success",
                           state_before="a")
    after_filter.dialog_name = "Filter by size"
    rep = critic.analyse_transition(st, prev, after_filter, xstep)
    assert st.friction.interruptions == 0
    assert not any(f.category == "friction" for f in rep.findings)

    prev2 = obs("Cart", "/cart", dialog=False, fp="c")
    promo = obs("[DIALOG] Join Nova+", "/cart", dialog=True, fp="d")
    promo.dialog_name = "Join Nova+ and save 10%"
    step2 = BrowserAction(observation_id="o", action=ActionType.CLICK, element_id=0, display_label="Checkout")
    xstep2 = ExecutionStep(step_number=2, url_before="x", action=step2, outcome="success", state_before="c")
    rep2 = critic.analyse_transition(st, prev2, promo, xstep2)
    assert st.friction.interruptions == 1
    assert any(f.category == "friction" and f.severity == "high" for f in rep2.findings)


def test_required_field_message_is_not_a_defect_finding():
    """F04: a bare "required" validation message on an empty field is expected behaviour, not an app defect."""
    from backend.agent import critic
    from backend.schemas import AgentState, GoalSpec

    st = AgentState(goal=GoalSpec(raw="x"), target_url="http://x")
    prev = obs("Checkout form", "/checkout", fp="a")
    after = obs("Checkout form Last Name is required", "/checkout", fp="a")
    act = BrowserAction(observation_id="o", action=ActionType.CLICK, element_id=0, display_label="Continue")
    step = ExecutionStep(step_number=1, url_before="x", action=act, outcome="success", state_before="a")
    rep = critic.analyse_transition(st, prev, after, step)
    assert not any("required" in f.title.lower() or "required" in f.evidence.lower() for f in rep.findings)
    assert st.friction.validation_errors == 0

    after_invalid = obs("Checkout form Invalid card number", "/checkout", fp="a")
    step2 = ExecutionStep(step_number=2, url_before="x", action=act, outcome="success", state_before="a")
    rep2 = critic.analyse_transition(st, prev, after_invalid, step2)
    assert any("Invalid card number" in f.evidence for f in rep2.findings)


def test_recovery_counters_do_not_combine_across_states_and_reset_on_progress():
    """F07: different "Continue" controls on different screens must not share one failure count, and a
    successful state change must forgive that control's past failures."""
    from backend.agent import critic
    from backend.schemas import AgentState, GoalSpec

    st = AgentState(goal=GoalSpec(raw="x"), target_url="http://x")
    act = BrowserAction(observation_id="o", action=ActionType.CLICK, element_id=0, display_label="Continue")
    same = obs("Step 1", "/wizard/1", fp="s1")
    for _ in range(2):
        step = ExecutionStep(step_number=1, url_before="x", action=act, outcome="success", state_before="s1")
        critic.analyse_transition(st, same, same, step)  # no state change: repeated no-op click
    other_screen = obs("Step 2", "/wizard/2", fp="s2")
    step_elsewhere = ExecutionStep(step_number=1, url_before="x", action=act, outcome="success", state_before="s2")
    critic.analyse_transition(st, other_screen, other_screen, step_elsewhere)
    assert st.blocked_reason is None  # different "Continue" on a different screen: independent budget

    progressed = obs("Step 1 done", "/wizard/1b", fp="s1b")
    step_progress = ExecutionStep(step_number=2, url_before="x", action=act, outcome="success", state_before="s1")
    critic.analyse_transition(st, same, progressed, step_progress)
    assert st.attempt_failures.get("s1:click:Continue") is None  # forgiven after real progress


def test_safety_gate_consumes_forbidden_actions_and_gates_enter_submission():
    """F06: GoalSpec.forbidden_actions must actually be enforced, and pressing Enter on a payment-labelled
    control must be judged the same way as clicking it."""
    act = BrowserAction(observation_id="o", action=ActionType.CLICK, element_id=0, display_label="Switch region")
    el = ObservedElement(element_id=0, role="button", name="Switch region")
    assert safety.check(act, el, False, "", ["switch region"]) is not None
    assert safety.check(act, el, False, "", ["export data"]) is None

    enter = BrowserAction(observation_id="o", action=ActionType.PRESS, key="Enter", display_label="Pay now")
    assert safety.check(enter, None, False) is not None
    harmless_enter = BrowserAction(observation_id="o", action=ActionType.PRESS, key="Enter", display_label="Search")
    assert safety.check(harmless_enter, None, False) is None


def test_replay_name_path_confinement():
    """F16: a caller-supplied replay name must never be able to traverse or escape replay_dir."""
    from backend.api.app import _replay_path
    import pytest as _pytest
    from fastapi import HTTPException

    with _pytest.raises(HTTPException):
        _replay_path("../../etc/passwd")
    with _pytest.raises(HTTPException):
        _replay_path("/etc/passwd")
    with _pytest.raises(HTTPException):
        _replay_path("golden/../../secrets")
    assert _replay_path("golden").name == "golden"


def test_safety_blocks_invented_identity_data():
    typ = BrowserAction(observation_id="o", action=ActionType.TYPE, element_id=0, text="testuser@example.com")
    email = ObservedElement(element_id=0, role="textbox", name="Enter mobile number or email")
    assert safety.check(typ, email, False, "add earphones to cart") is not None
    user = BrowserAction(observation_id="o", action=ActionType.TYPE, element_id=0, text="standard_user")
    assert safety.check(user, ObservedElement(element_id=0, role="textbox", name="Username"), False, "log in as standard_user") is None
