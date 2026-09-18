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
    # A login/sign-in goal is met by LEAVING the login form, not by merely reaching a page that has one:
    # a password field being visible proves a login form is showing, never that the user is logged in.
    (re.compile(r"\b(log ?in|sign ?in)\b", re.I), "reach_login",
     SuccessCriteria(forbid_url_contains=["login", "signin"], forbid_visible_input_types=["password"])),
]


_STOP = {"the", "and", "for", "with", "under", "below", "into", "then", "its", "them", "it", "reach", "open",
         "find", "get", "go", "to", "a", "an", "of", "on", "in", "my", "your", "page", "enter", "name", "code",
         "log", "username", "password", "less", "than", "within", "search"}


def focus_words(raw: str) -> list[str]:
    """Goal vocabulary used to prioritise matching controls, the way a person scans a page for their task."""
    words = [w for w in re.findall(r"[a-z][a-z0-9+]{2,}", raw.lower()) if w not in _STOP]
    return list(dict.fromkeys(words + ["search", "cart", "checkout", "close"]))[:20]


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
    if constraints.get("max_price") and constraints.get("product"):
        success.max_price = constraints["max_price"]
        success.price_entity = constraints["product"]
    if success_url or success_text:
        objective = objective if objective != "explore" else "custom"
        success.url_contains = list(success_url or [])
        success.visible_text_any = list(success_text or [])
        success.visible_input_types = []
        success.cart_contains = None  # the tester's explicit acceptance criteria replace the defaults
        success.forbid_url_contains = []
        success.forbid_visible_input_types = []
    if re.search(r"\b(add|put)\b.*\b(cart|basket|bag)\b", raw, re.I):
        success.forbid_text_any = ["cart is empty", "basket is empty", "bag is empty", "0 items in cart",
                                   "no items in your cart", "your cart is currently empty"]
    return GoalSpec(raw=raw, objective=objective, constraints=constraints, success=success)
