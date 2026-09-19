"""One reasoning call per loop: observation -> validated ModelDecision (one schema-correction retry)."""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from backend.agent.llm import ModelError, ReasoningModel, extract_json
from backend.agent.prompt import SYSTEM_PROMPT, build_user_prompt
from backend.config import settings
from backend.schemas import AgentState, ModelDecision, Observation


@dataclass
class PlanResult:
    decision: ModelDecision
    latency_ms: int
    attempts: int
    used_vision: bool


def _wants_vision(state: AgentState, obs: Observation) -> bool:
    if settings.vision_mode == "always":
        return True
    if settings.vision_mode == "off":
        return False
    # fallback: only when the structured view is likely insufficient
    return obs.dialog_open or not obs.elements or state.last_outcome not in (None, "success")


def _coerce(data: dict, obs: Observation) -> dict:
    """Light, meaning-preserving repairs. A stale observation is never silently rebound."""
    gp = data.get("goal_progress")
    if isinstance(gp, (int, float)) and 1 < gp <= 100:
        data["goal_progress"] = gp / 100  # some models answer in percent
    na = data.get("next_action")
    if isinstance(na, dict):
        claimed = na.get("observation_id")
        if claimed and claimed != obs.observation_id:
            raise ValueError(
                f"next_action referenced stale observation {claimed}; current observation is {obs.observation_id}"
            )
        na["observation_id"] = obs.observation_id
        if isinstance(na.get("action"), str):
            na["action"] = na["action"].lower().strip()
        if isinstance(na.get("rationale"), str):
            na["rationale"] = na["rationale"][:300]
        # Meaning-preserving repairs for fields small models leave empty (never a change of action type):
        if na.get("action") == "scroll" and na.get("direction") not in ("up", "down"):
            why = f"{na.get('rationale') or ''} {na.get('display_label') or ''}".lower()
            na["direction"] = "up" if " up" in f" {why}" or "top" in why else "down"
        if na.get("action") != "type" and na.get("submit"):
            na["submit"] = False
    for f in data.get("facts") or []:
        if isinstance(f, dict) and isinstance(f.get("value"), str):
            f["value"] = f["value"].replace(",", "").replace("₹", "").strip()
    return data


def _explain(exc: Exception) -> str:
    """Field-level reason ("next_action: scroll requires direction") so the correction retry can actually fix it."""
    if isinstance(exc, ValidationError):
        parts = [f"{'.'.join(str(x) for x in e['loc']) or 'reply'}: {e['msg']}" for e in exc.errors()[:4]]
        return "; ".join(parts)[:400]
    return (str(exc).splitlines()[0] if str(exc) else type(exc).__name__)[:300]


async def plan(model: ReasoningModel, state: AgentState, obs: Observation, notes: list[str], screenshot: bytes | None) -> PlanResult:
    user = build_user_prompt(state, obs, notes)
    image = screenshot if _wants_vision(state, obs) else None
    total_latency, error = 0, ""
    for attempt in (1, 2):
        prompt = user if attempt == 1 else (
            f"{user}\n\nYOUR PREVIOUS REPLY WAS INVALID: {error}\nReturn ONLY one JSON object matching the schema exactly.")
        text, latency = await model.complete(SYSTEM_PROMPT, prompt, image)
        total_latency += latency
        state.metrics.model_calls += 1
        state.metrics.model_latencies_ms.append(latency)
        try:
            decision = ModelDecision.model_validate(_coerce(extract_json(text), obs))
            return PlanResult(decision, total_latency, attempt, image is not None)
        except (ValueError, ValidationError) as exc:
            state.metrics.schema_failures += 1
            error = _explain(exc)
    raise ModelError(f"model output failed schema validation twice: {error}")
