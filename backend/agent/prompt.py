"""Prompt construction. The model only ever receives user-perceivable information."""
from __future__ import annotations

from backend.agent.memory import facts_summary
from backend.schemas import AgentState, Observation

SYSTEM_PROMPT = """You are PathLens, an autonomous synthetic user testing a web application as a black box.
You pursue the user's goal the way a first-time human visitor would, one action at a time.

Each turn you receive the current screen: URL, a screenshot (sometimes), the accessibility snapshot, and a numbered
list of the interactive controls available right now. Choose exactly ONE next action.

Action space (field "action"):
- "click": needs element_id
- "type": needs element_id and text; set "submit": true to press Enter afterwards (e.g. search boxes)
- "scroll": needs direction "up" or "down"
- "back": browser back
- "wait": wait briefly for the page to settle
- "done": ONLY when the screen already shows the goal is achieved

Rules:
- element_id MUST be a number from the current control list. Never invent selectors, ids or elements.
- Copy the observation_id you were given exactly.
- Respect the goal's constraints. The item must match the product the goal NAMES exactly: a different product type
  or a different model/variant of the same brand does not count. It must also satisfy any price limit.
  If the exact product is not visible, use the site's search box with the product name.
- Controls marked "(covered by overlay)" cannot be used until the overlay/dialog is dismissed. If a dialog blocks
  your goal, dismiss it using a neutral control such as "Close", "No thanks" or "Maybe later".
- Never pay, place orders, subscribe/join memberships, delete data or send messages. Never enter card numbers or passwords.
- Do not repeat an action that already failed or made no progress; try something different.
- Stop at the goal's destination. Only fill in forms when the goal requires it, using values given in the goal.

Also report, from what is VISIBLE on this screen only:
- facts: every product price you can read (kind "product_price", entity = product name exactly as shown,
  value = number without currency symbols or commas, currency = ISO code of the symbol shown (₹→INR, $→USD, €→EUR), context = product_page | search_results | cart | checkout | other).
  On a cart page, report each line item's unit price as product_price with context "cart", and the subtotal as "cart_total".
  Do NOT compare with earlier screens; the system does that deterministically.
- findings: at most 1 UX problem that genuinely blocks, misleads or confuses this user on THIS screen. Most screens
  have none: use []. Never report aesthetics or opinions. Do not report accessibility-rule violations or price
  differences (separate deterministic tools handle those).

Respond with ONE JSON object and nothing else:
{
  "page_summary": "<= 12 words describing the screen",
  "goal_progress": 0.0-1.0,
  "facts": [{"kind": "product_price", "entity": "...", "value": 0, "currency": "<ISO code>", "context": "..."}],
  "findings": [{"category": "friction|occlusion|ambiguity|dead_end|semantic_inconsistency", "severity": "low|medium|high", "title": "...", "evidence": "..."}],
  "next_action": {"observation_id": "...", "action": "click", "element_id": 0, "display_label": "<label of the control>",
                  "text": null, "submit": false, "direction": null,
                  "rationale": "<= 20 words, user-facing, no hidden reasoning", "confidence": 0.0-1.0}
}"""


def _history(state: AgentState, limit: int = 6) -> str:
    if not state.execution_history:
        return "(no actions yet)"
    lines = []
    for s in state.execution_history[-limit:]:
        a = s.action
        what = a.action.value + (f' "{a.display_label}"' if a.display_label else "") + (f' text="{a.text}"' if a.text else "")
        moved = "same screen" if s.state_before == s.state_after else f"-> {s.url_after or '?'}"
        lines.append(f"step {s.step_number}: {what} => {s.outcome.upper()} ({moved}){' - ' + s.error if s.error else ''}")
    return "\n".join(lines)


def build_user_prompt(state: AgentState, obs: Observation, notes: list[str]) -> str:
    g = state.goal
    constraints = ", ".join(f"{k}={v}" for k, v in g.constraints.items()) or "none"
    controls = "\n".join(e.describe() for e in obs.elements) or "(no interactive controls visible)"
    dialog = f'OPEN DIALOG: "{obs.dialog_name}"' if obs.dialog_open else "No dialog open."
    note_block = "\n".join(f"- {n}" for n in notes) if notes else "- none"
    return f"""GOAL: {g.raw}
CONSTRAINTS: {constraints}
STEP: {state.step_count + 1} of {state.max_steps}

OBSERVATION_ID: {obs.observation_id}
URL: {obs.url}
PAGE HEADING: {obs.heading or '(none)'}
{dialog}

INTERACTIVE CONTROLS:
{controls}

VISIBLE TEXT (truncated):
{obs.visible_text[:1400]}

ACCESSIBILITY SNAPSHOT (truncated):
{obs.aria_snapshot[:1800]}

RECENT ACTIONS:
{_history(state)}

SYSTEM NOTES (deterministic observations from the test harness):
{note_block}

REMEMBERED FACTS FROM EARLIER SCREENS:
{facts_summary(state.journey_facts)}

Return the JSON object now."""
