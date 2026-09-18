"""Deterministic goal-completion verification. The model saying DONE is never sufficient on its own."""
from __future__ import annotations

from dataclasses import dataclass

from backend.agent.memory import normalize_entity
from backend.schemas import GoalSpec, Observation, PageFact


@dataclass
class Verdict:
    completed: bool
    evidence: list[str]
    missing: list[str]


def _norm(text: str) -> str:
    return " ".join("".join(c if c.isalnum() else " " for c in text.lower()).split())


def _path_only(route: str) -> str:
    """The route without its query string, so a query PARAMETER VALUE (e.g. "?q=checkout") cannot
    masquerade as having reached a destination route."""
    return route.split("?", 1)[0]


def cart_shows(obs: Observation, product: str) -> bool:
    """Deterministic: the product name is visible on a cart screen (plain text match, no model involved)."""
    return "cart" in obs.route.lower() and _norm(product) in _norm(obs.visible_text)


def update_cart_seen(current: bool, obs: Observation, product: str) -> bool:
    """Reflects the MOST RECENT cart-route observation, never a historical "ever seen" flag: if the item
    is later removed and the cart is revisited, that must invalidate a prior sighting."""
    if obs.dialog_open or "cart" not in obs.route.lower():
        return current  # not a cart observation right now: carry the last known cart state forward
    return cart_shows(obs, product)


def _price_verdict(max_price: float, entity: str, facts: list[PageFact]) -> tuple[str | None, str | None]:
    """Returns (evidence, missing). Neither is set (both None) when there is no evidence either way: an
    unmet price constraint we cannot check yet must not silently pass, but it must not fail either."""
    matching = [f for f in facts if f.kind == "product_price" and normalize_entity(f.entity) == normalize_entity(entity)]
    if not matching:
        return None, None  # unknown: no grounded price for this product has been observed yet
    latest = max(matching, key=lambda f: f.step_number)
    if latest.value > max_price + 1e-9:
        return None, f"{entity} price {latest.value:g} (step {latest.step_number}) exceeds the limit {max_price:g}"
    return f"{entity} price {latest.value:g} is within the limit {max_price:g}", None


def verify(goal: GoalSpec, obs: Observation, facts: list[PageFact] | None = None, cart_product_seen: bool = False) -> Verdict:
    crit = goal.success
    facts = facts or []
    evidence, missing = [], []
    has_positive = crit.url_contains or crit.visible_input_types or crit.visible_text_any
    has_negative = crit.forbid_url_contains or crit.forbid_visible_input_types
    if not (has_positive or has_negative):  # forbid-text-only is not enough on its own
        return Verdict(False, [], ["goal has no deterministic success criteria"])

    route = _path_only(obs.route.lower())
    if crit.url_contains:
        hit = next((u for u in crit.url_contains if u in route), None)
        (evidence if hit else missing).append(f'route contains "{hit or "|".join(crit.url_contains)}"')

    if crit.forbid_url_contains:
        hit = next((u for u in crit.forbid_url_contains if u in route), None)
        if hit:
            missing.append(f'route still contains "{hit}"')
        else:
            evidence.append(f'route no longer contains "{"|".join(crit.forbid_url_contains)}"')

    if crit.visible_input_types:
        usable = [e for e in obs.elements if not e.covered and not e.disabled and e.input_type]
        hit = next((e for e in usable if e.input_type in crit.visible_input_types), None)
        if hit:
            evidence.append(f"visible {hit.input_type} input ({hit.name or 'unlabelled'})")
        else:
            missing.append(f"visible input of type {'/'.join(crit.visible_input_types)}")

    if crit.forbid_visible_input_types:
        usable = [e for e in obs.elements if not e.covered and e.input_type]
        hit = next((e for e in usable if e.input_type in crit.forbid_visible_input_types), None)
        if hit:
            missing.append(f"a {hit.input_type} input is still visible ({hit.name or 'unlabelled'})")
        else:
            evidence.append(f"no visible input of type {'/'.join(crit.forbid_visible_input_types)}")

    if crit.visible_text_any:
        text = obs.visible_text.lower()
        hit = next((t for t in crit.visible_text_any if t.lower() in text), None)
        (evidence if hit else missing).append(f'visible text "{hit or "|".join(crit.visible_text_any)}"')

    if crit.cart_contains:
        if cart_product_seen:
            evidence.append(f'"{crit.cart_contains}" was shown in the cart')
        else:
            missing.append(f'"{crit.cart_contains}" never appeared in the cart')

    if crit.max_price is not None and crit.price_entity:
        ok, bad = _price_verdict(crit.max_price, crit.price_entity, facts)
        if ok:
            evidence.append(ok)
        elif bad:
            missing.append(bad)
        # else: unknown - neither blocks nor proves completion

    text_now = obs.visible_text.lower()
    contradiction = next((t for t in crit.forbid_text_any if t in text_now), None)
    if contradiction:
        missing.append(f'page says "{contradiction}"')

    if obs.dialog_open:
        missing.append("no blocking dialog")
    return Verdict(not missing, evidence, missing)
