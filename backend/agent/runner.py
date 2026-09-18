"""Runs one live mission end-to-end and always terminates with run_completed or run_failed."""
from __future__ import annotations

from backend.agent.goal import compile_goal
from backend.agent.graph import RunContext, build_graph, save_state, summarize
from backend.agent.llm import build_model
from backend.config import model_name, settings
from backend.events import EventBus
from backend.runtime.browser import BrowserSession
from backend.schemas import AgentState, GoalSpec, RunStatus, short_id


def new_state(goal: str | GoalSpec, target_url: str | None = None, run_id: str | None = None,
              success_url: list[str] | None = None, success_text: list[str] | None = None,
              max_steps: int | None = None) -> AgentState:
    spec = goal if isinstance(goal, GoalSpec) else compile_goal(goal, success_url, success_text)
    return AgentState(run_id=run_id or short_id(), goal=spec, target_url=target_url or settings.target_url,
                      provider=settings.provider, model=model_name(), max_steps=max(1, min(max_steps or settings.max_steps, 100)),
                      stall_limit=settings.stall_limit,
                      max_recovery_attempts=settings.max_recoveries)


async def run_live(state: AgentState, bus: EventBus) -> AgentState:
    run_dir = settings.artifacts_dir / f"run_{state.run_id}"
    bus.emit("run_started", {
        "mode": "live", "goal": state.goal.model_dump(), "target_url": state.target_url,
        "provider": state.provider, "model": state.model, "offline_test_double": state.provider == "scripted",
        "vision_mode": settings.vision_mode, "max_steps": state.max_steps,
        "artifact_base": f"/artifacts/run_{state.run_id}/",
    })
    session = BrowserSession(run_dir)
    try:
        model = build_model()
        await session.start(state.target_url)
        ctx = RunContext(state=state, session=session, model=model, bus=bus, run_dir=run_dir)
        await build_graph(ctx).ainvoke({"state": state}, {"recursion_limit": 8 * state.max_steps + 20})
    except Exception as exc:  # any crash becomes an explicit, recorded run_failed
        state.status = RunStatus.FAILED
        state.run_error = f"{type(exc).__name__}: {exc}"
    finally:
        await session.close()

    run_dir.mkdir(parents=True, exist_ok=True)
    save_state(state, run_dir)
    summary = summarize(state)
    try:
        from backend.api.report import write_report
        write_report(state, run_dir)
        summary["report_url"] = f"/api/runs/{state.run_id}/report"
    except Exception as exc:  # report failure must not hide the mission result
        summary["report_error"] = str(exc)
    if state.status == RunStatus.COMPLETED:
        bus.emit("run_completed", summary)
    else:
        bus.emit("run_failed", {**summary, "reason": state.run_error, "fallback_available": True})
    bus.close()
    return state
