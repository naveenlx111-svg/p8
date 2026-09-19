"""Safety gate: every proposed action is checked BEFORE it reaches the browser."""
from __future__ import annotations

import re

from backend.schemas import ActionType, BrowserAction, ObservedElement

IRREVERSIBLE = re.compile(
    r"\b(pay|place (?:your )?order|buy now|purchase|confirm (?:order|payment)|complete (?:order|purchase)|"
    r"delete|remove account|close account|deactivate|unsubscribe|subscribe|join|send|transfer|"
    r"report emergency|call emergency(?: services)?|contact emergency(?: services)?|trigger emergency|sos)\b", re.I)
SENSITIVE_FIELD = re.compile(r"\b(card|cvv|cvc|password|passcode|otp|pin|ssn|aadhaar|iban|account number)\b", re.I)
# Identity fields: the agent must never invent an email/phone/username to get past a login or signup wall.
IDENTITY_FIELD = re.compile(r"\b(e-?mail|mobile|phone|username|user name|login|user id)\b", re.I)


def check(action: BrowserAction, element: ObservedElement | None, allow_irreversible: bool, goal_text: str = "",
          forbidden_actions: list[str] | None = None) -> str | None:
    """Returns a rejection reason, or None if the action is allowed."""
    if allow_irreversible:
        return None
    label = " ".join(filter(None, [
        element.name if element else None, element.placeholder if element else None,
        " ".join(element.form_submit_labels) if element else None, action.display_label or "",
    ]))
    for phrase in forbidden_actions or []:
        if phrase and phrase.lower() in label.lower():
            return f'"{label}" matches an action the goal explicitly forbids: "{phrase}"'
    if element is None:
        # No resolved element (e.g. a page-level PRESS or a TYPE whose target could not be re-resolved).
        # A focused-control activation (PRESS Enter) can submit a form exactly like a click, so the same
        # irreversible-label check must apply even though there is no element to inspect further.
        if action.action == ActionType.PRESS and action.key == "Enter" and IRREVERSIBLE.search(action.display_label or ""):
            return f'"{action.display_label}" looks like an irreversible or financial action; pressing Enter to submit it is not allowed'
        return None
    if action.action == ActionType.CLICK and IRREVERSIBLE.search(element.name or ""):
        return f'"{element.name}" looks like an irreversible or financial action (payment, order, subscription, deletion or message)'
    if action.action == ActionType.PRESS and action.key == "Enter" and IRREVERSIBLE.search(label):
        return f'pressing Enter from "{element.name or element.role}" may activate "{label}", an irreversible or financial action'
    if action.action == ActionType.TYPE and (element.input_type == "password" or SENSITIVE_FIELD.search(label)):
        # A value the tester wrote into the goal (e.g. test credentials) is authorised; anything invented is not.
        if action.text and len(action.text) >= 3 and action.text in goal_text:
            return None
        return f'typing into a sensitive field ("{element.name or element.input_type}") is not allowed unless the value is given in the goal'
    if action.action == ActionType.TYPE and (element.input_type in ("email", "tel") or IDENTITY_FIELD.search(label)):
        if not (action.text and action.text in goal_text):
            return (f'identity data may only be typed if the goal provides it ("{action.text}" is not in the goal); '
                    'if a sign-in wall blocks the goal, report it instead of inventing credentials')
    if action.action == ActionType.TYPE and action.submit and IRREVERSIBLE.search(label):
        return f'"{label}" looks like an irreversible action and pressing Enter after typing would submit it'
    return None


def is_sensitive_target(element: ObservedElement | None) -> bool:
    """True if this element's value should never appear verbatim in events, state or reports."""
    if element is None:
        return False
    if element.input_type == "password":
        return True
    label = " ".join(filter(None, [element.name, element.placeholder]))
    return bool(SENSITIVE_FIELD.search(label))


def masked_text(text: str | None, element: ObservedElement | None) -> str | None:
    if text and is_sensitive_target(element):
        return "•" * 6
    return text
