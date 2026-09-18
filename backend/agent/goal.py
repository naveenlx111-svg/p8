"""Deterministic GoalSpec compilation from the natural-language goal.

Success signals are generic user-observable conventions (route words, standard input types), never
selectors or knowledge of the target's source. Callers may also pass an explicit GoalSpec.
"""
from __future__ import annotations

import re

from backend.schemas import GoalSpec, SuccessCriteria

_PRICE = re.compile(r"(?:under|below|less than|max(?:imum)?|within)\s*(?:₹|rs\.?|inr|\$)?\s*([\d,]+)", re.I)
_PRODUCT = re.compile(r"\b(?:find|search for|buy|get|locate|add)\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:\s+(?:to|under|below|for|less than|within)\b|,|$)", re.I)

# Destination phrases -> (objective, success criteria). Order matters: most specific first.
_DESTINATIONS = [
    (re.compile(r"\bcheckout\b", re.I), "reach_checkout",
     SuccessCriteria(url_contains=["checkout"], visible_input_types=["email", "text"])),
    (re.compile(r"\bcart\b", re.I), "reach_cart", SuccessCriteria(url_contains=["cart"])),
    (re.compile(r"\b(sign ?up|register)\b", re.I), "reach_signup",
     SuccessCriteria(url_contains=["signup", "register"], visible_input_types=["email", "password"])),
    (re.compile(r"\b(log ?in|sign ?in)\b", re.I), "reach_login",
     SuccessCriteria(url_contains=["login", "signin"], visible_input_types=["password"])),
]


def compile_goal(raw: str, success_url: list[str] | None = None, success_text: list[str] | None = None) -> GoalSpec:
    """success_url / success_text: optional acceptance criteria supplied by the tester (override the defaults)."""
    constraints: dict = {}
    if m := _PRICE.search(raw):
        constraints["max_price"] = float(m.group(1).replace(",", ""))
    if m := _PRODUCT.search(raw):
        constraints["product"] = m.group(1).strip().rstrip(".")
    objective, success = "explore", SuccessCriteria()
    # Pick the destination that appears LAST in the sentence: "add to cart, and reach checkout" -> checkout.
    best = -1
    for pattern, obj, crit in _DESTINATIONS:
        for m in pattern.finditer(raw):
            if m.start() > best:
                best, objective, success = m.start(), obj, crit.model_copy(deep=True)
    if objective in ("reach_checkout", "reach_cart") and constraints.get("product"):
        success.cart_contains = constraints["product"]
    if success_url or success_text:
        objective = objective if objective != "explore" else "custom"
        success.url_contains = list(success_url or [])
        success.visible_text_any = list(success_text or [])
        success.visible_input_types = []
    return GoalSpec(raw=raw, objective=objective, constraints=constraints, success=success)
