"""Safety gate: every proposed action is checked BEFORE it reaches the browser."""
from __future__ import annotations

import re

from backend.schemas import ActionType, BrowserAction, ObservedElement

IRREVERSIBLE = re.compile(
    r"\b(pay|place (?:your )?order|buy now|purchase|confirm (?:order|payment)|complete (?:order|purchase)|"
    r"delete|remove account|close account|deactivate|unsubscribe|subscribe|join|send|transfer)\b", re.I)
SENSITIVE_FIELD = re.compile(r"\b(card|cvv|cvc|password|passcode|otp|pin|ssn|aadhaar|iban|account number)\b", re.I)


def check(action: BrowserAction, element: ObservedElement | None, allow_irreversible: bool, goal_text: str = "") -> str | None:
    """Returns a rejection reason, or None if the action is allowed."""
    if element is None or allow_irreversible:
        return None
    label = " ".join(filter(None, [element.name, element.placeholder, action.display_label or ""]))
    if action.action == ActionType.CLICK and IRREVERSIBLE.search(element.name or ""):
        return f'"{element.name}" looks like an irreversible or financial action (payment, order, subscription, deletion or message)'
    if action.action == ActionType.TYPE and (element.input_type == "password" or SENSITIVE_FIELD.search(label)):
        # A value the tester wrote into the goal (e.g. test credentials) is authorised; anything invented is not.
        if action.text and len(action.text) >= 3 and action.text in goal_text:
            return None
        return f'typing into a sensitive field ("{element.name or element.input_type}") is not allowed unless the value is given in the goal'
    return None
