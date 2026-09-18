"""OFFLINE TEST DOUBLE — not AI.

A keyword heuristic that reads the same black-box prompt the real model gets and answers in the same JSON contract.
It exists so the orchestration, runtime, memory, dashboard and replay pipeline can be tested without API keys.
It must never be presented as the autonomous agent in a demo; the UI labels runs using it.
"""
from __future__ import annotations

import json
import re

from backend.agent.llm import ReasoningModel

_CONTROL = re.compile(r'^\[(\d+)\] (\S+) (?:"([^"]*)"|\(no accessible name\))(.*)$', re.M)
_PRICE_PAIR = re.compile(r"((?:[A-Z][\w+]*)(?: [A-Z][\w+]*)*) (?:\d+ )?₹([\d,]+)")


def _section(prompt: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*\n(.*?)(?:\n\n[A-Z ]+:|\Z)", prompt, re.S | re.M)
    return m.group(1) if m else ""


class ScriptedModel(ReasoningModel):
    provider = "scripted"

    async def _complete(self, system: str, user: str, image: bytes | None) -> str:
        obs_id = re.search(r"^OBSERVATION_ID: (\S+)", user, re.M).group(1)
        url = re.search(r"^URL: (\S+)", user, re.M).group(1)
        product = (re.search(r"product=([^,\n]+)", user) or [None, ""])[1].strip()
        controls = [(int(i), role, name or "", rest) for i, role, name, rest in _CONTROL.findall(_section(user, "INTERACTIVE CONTROLS"))]
        usable = [c for c in controls if "covered by overlay" not in c[3]]
        text = _section(user, "VISIBLE TEXT \\(truncated\\)")

        context = ("cart" if "/cart" in url else "product_page" if "/product" in url
                   else "search_results" if "results" in url else "checkout" if "checkout" in url else "other")
        facts = [{"kind": "product_price", "entity": n.strip(), "value": float(p.replace(",", "")), "context": context}
                 for n, p in _PRICE_PAIR.findall(text) if "Subtotal" not in n and "Pay" not in n]

        def pick(pattern: str, role: str | None = None):
            return next((c for c in usable if re.search(pattern, c[2], re.I) and (role is None or c[1] == role)), None)

        choice, action, extra, why = None, "click", {}, ""
        if "OPEN DIALOG" in user:
            choice, why = pick(r"^(close|no thanks|maybe later|dismiss|×)$"), "Dismiss the dialog blocking the goal"
        elif "checkout" in url and "#/checkout" in url:
            action, why = "done", "Checkout page reached"
        elif c := pick(r"^checkout$"):
            choice, why = c, "Proceed to checkout"
        elif c := pick(r"^add to cart$"):
            choice, why = c, "Add the matching product to the cart"
        elif product and (c := pick(rf"^{re.escape(product)}$", "link")):
            choice, why = c, "Open the product matching the goal"
        elif (c := next((c for c in usable if c[1] in ("searchbox", "textbox") and "search" in c[2].lower()), None)):
            choice, action, why = c, "type", "Search for the requested product"
            extra = {"text": product.split()[0].lower() if product else "", "submit": True}
        else:
            action, extra, why = "scroll", {"direction": "down"}, "Look for more options"

        return json.dumps({
            "page_summary": text[:60], "goal_progress": 0.5, "facts": facts, "findings": [],
            "next_action": {"observation_id": obs_id, "action": action, "element_id": choice[0] if choice else None,
                            "display_label": choice[2] if choice else None, "rationale": why, "confidence": 0.9, **extra},
        })
