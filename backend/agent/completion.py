"""Deterministic goal-completion verification. The model saying DONE is never sufficient on its own."""
from __future__ import annotations

from dataclasses import dataclass

from backend.schemas import GoalSpec, Observation


@dataclass
class Verdict:
    completed: bool
    evidence: list[str]
    missing: list[str]


def _norm(text: str) -> str:
    return " ".join("".join(c if c.isalnum() else " " for c in text.lower()).split())


def cart_shows(obs: Observation, product: str) -> bool:
    """Deterministic: the product name is visible on a cart screen (plain text match, no model involved)."""
    return "cart" in obs.route.lower() and _norm(product) in _norm(obs.visible_text)


def verify(goal: GoalSpec, obs: Observation, cart_product_seen: bool = False) -> Verdict:
    crit = goal.success
    evidence, missing = [], []
    if not (crit.url_contains or crit.visible_input_types or crit.visible_text_any):  # forbid-only is not enough
        return Verdict(False, [], ["goal has no deterministic success criteria"])

    route = obs.route.lower()
    if crit.url_contains:
        hit = next((u for u in crit.url_contains if u in route), None)
        (evidence if hit else missing).append(f'route contains "{hit or "|".join(crit.url_contains)}"')

    if crit.visible_input_types:
        usable = [e for e in obs.elements if not e.covered and not e.disabled and e.input_type]
        hit = next((e for e in usable if e.input_type in crit.visible_input_types), None)
        if hit:
            evidence.append(f"visible {hit.input_type} input ({hit.name or 'unlabelled'})")
        else:
            missing.append(f"visible input of type {'/'.join(crit.visible_input_types)}")

    if crit.visible_text_any:
        text = obs.visible_text.lower()
        hit = next((t for t in crit.visible_text_any if t.lower() in text), None)
        (evidence if hit else missing).append(f'visible text "{hit or "|".join(crit.visible_text_any)}"')

    if crit.cart_contains:
        if cart_product_seen:
            evidence.append(f'"{crit.cart_contains}" was shown in the cart')
        else:
            missing.append(f'"{crit.cart_contains}" never appeared in the cart')

    text_now = obs.visible_text.lower()
    contradiction = next((t for t in crit.forbid_text_any if t in text_now), None)
    if contradiction:
        missing.append(f'page says "{contradiction}"')

    if obs.dialog_open:
        missing.append("no blocking dialog")
    return Verdict(not missing, evidence, missing)
