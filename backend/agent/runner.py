"""Runs one live mission end-to-end and always terminates with run_completed or run_failed."""
from __future__ import annotations

import asyncio

from backend.agent.goal import compile_goal, focus_words
from backend.agent.graph import RunContext, build_graph, save_state, summarize
from backend.agent.llm import build_model
from backend.config import model_name, settings
from backend.events import EventBus
from backend.runtime.android import AndroidSession
from backend.runtime.browser import BrowserSession
from backend.schemas import AgentState, GoalSpec, RunStatus, short_id


def new_state(goal: str | GoalSpec, target_url: str | None = None, run_id: str | None = None,
              success_url: list[str] | None = None, success_text: list[str] | None = None,
              max_steps: int | None = None, platform: str = "web", device_serial: str | None = None,
              android_package: str | None = None, android_activity: str | None = None,
              apk_path: str | None = None, record_video: bool = True) -> AgentState:
    spec = goal if isinstance(goal, GoalSpec) else compile_goal(goal, success_url, success_text)
    destination = target_url or settings.target_url
    if platform == "android":
        destination = f"android://{device_serial or 'auto'}/{android_package or 'uploaded-app'}"
    return AgentState(run_id=run_id or short_id(), goal=spec, target_url=destination,
                      platform=platform, device_serial=device_serial, android_package=android_package,
                      android_activity=android_activity, apk_path=apk_path, record_video=record_video,
                      provider=settings.provider, model=model_name(), max_steps=max(1, min(max_steps or settings.max_steps, 300)),
                      stall_limit=settings.stall_limit,
                      max_recovery_attempts=settings.max_recoveries)


async def run_live(state: AgentState, bus: EventBus) -> AgentState:
    run_dir = settings.artifacts_dir / f"run_{state.run_id}"
    bus.emit("run_started", {
        "mode": "live", "goal": state.goal.model_dump(), "target_url": state.target_url,
        "provider": state.provider, "model": state.model, "offline_test_double": state.provider == "scripted",
        "vision_mode": settings.vision_mode, "max_steps": state.max_steps,
        "platform": state.platform, "device_serial": state.device_serial,
        "android_package": state.android_package, "record_video": state.record_video,
        "artifact_base": f"/artifacts/run_{state.run_id}/",
    })
    if state.platform == "android":
        session = AndroidSession(
            run_dir, state.device_serial, state.android_package or "", state.apk_path,
            state.android_activity, state.record_video, settings.max_elements,
        )
    else:
        session = BrowserSession(run_dir, focus_words(state.goal.raw), state.record_video)
    try:
        model = build_model()
        await session.start(state.target_url)
        ctx = RunContext(state=state, session=session, model=model, bus=bus, run_dir=run_dir)
        await build_graph(ctx).ainvoke({"state": state}, {"recursion_limit": 8 * state.max_steps + 20})
    except asyncio.CancelledError:
        state.status = RunStatus.FAILED
        state.run_error = "run cancelled by user"
    except Exception as exc:  # any crash becomes an explicit, recorded run_failed
        state.status = RunStatus.FAILED
        state.run_error = f"{type(exc).__name__}: {exc}"
    finally:
        await session.close()
        state.video_path = session.video_name

        # Finalization is part of cleanup: cancellation must still produce a closed
        # browser, state.json, report and a terminal event.
        run_dir.mkdir(parents=True, exist_ok=True)
        save_state(state, run_dir)
        summary = summarize(state)
        if state.video_path:
            summary["video_url"] = f"/artifacts/run_{state.run_id}/{state.video_path}"
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
