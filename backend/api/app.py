"""FastAPI transport: REST + WebSocket. Live and replay runs emit the same event contract.

    uvicorn backend.api.app:app --port 8000
"""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.agent.runner import new_state, run_live
from backend.api.health import health_report
from backend.api.report import render_report
from backend.config import ROOT, settings
from backend.events import EventBus, load_events
from backend.schemas import AgentState, short_id

app = FastAPI(title="PathLens")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
settings.replay_dir.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=settings.artifacts_dir), name="artifacts")
app.mount("/replay_runs", StaticFiles(directory=settings.replay_dir), name="replay_runs")

BUSES: dict[str, EventBus] = {}
TASKS: set[asyncio.Task] = set()


class RunRequest(BaseModel):
    goal: str = "Find the Nova headphones under ₹3,000, add them to cart, and reach checkout."
    target_url: str | None = None
    mode: str = "live"  # live | replay
    replay: str = "golden"
    speed: float = 1.0
    success_url: list[str] | None = None
    success_text: list[str] | None = None


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    TASKS.add(task)
    task.add_done_callback(TASKS.discard)


async def _replay(bus: EventBus, name: str, speed: float) -> None:
    src = settings.replay_dir / name / "events.jsonl"
    events = load_events(src)
    prev = 0
    for ev in events:
        await asyncio.sleep(max(0, (ev.offset_ms - prev) / 1000 / max(speed, 0.1)))
        prev = ev.offset_ms
        payload = dict(ev.payload)
        if ev.type == "run_started":
            payload.update(mode="replay", replay_name=name, replay_of=ev.run_id,
                           artifact_base=f"/replay_runs/{name}/")
        if ev.type in ("run_completed", "run_failed") and "report_url" in payload:
            payload["report_url"] = f"/api/replays/{name}/report"
        bus.emit(ev.type, payload, offset_ms=ev.offset_ms)
    bus.close()


@app.post("/api/runs")
async def create_run(req: RunRequest) -> dict:
    if req.mode == "replay":
        if not (settings.replay_dir / req.replay / "events.jsonl").exists():
            raise HTTPException(404, f"replay '{req.replay}' not found")
        run_id = "replay_" + short_id()
        bus = EventBus(run_id, settings.artifacts_dir, record=False)
        BUSES[run_id] = bus
        _spawn(_replay(bus, req.replay, req.speed))
        return {"run_id": run_id, "mode": "replay"}
    if req.target_url and not req.target_url.lower().startswith(("http://", "https://")):
        raise HTTPException(400, "target_url must start with http:// or https://")
    if not req.goal.strip():
        raise HTTPException(400, "goal must not be empty")
    state = new_state(req.goal, req.target_url, success_url=req.success_url, success_text=req.success_text)
    bus = EventBus(state.run_id, settings.artifacts_dir / f"run_{state.run_id}")
    BUSES[state.run_id] = bus
    _spawn(run_live(state, bus))
    return {"run_id": state.run_id, "mode": "live"}


def _run_dir(run_id: str) -> Path:
    d = settings.artifacts_dir / f"run_{run_id}"
    if not d.is_dir():
        raise HTTPException(404, "run not found")
    return d


@app.get("/api/runs")
def list_runs() -> list[dict]:
    out = []
    for d in sorted(settings.artifacts_dir.glob("run_*"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
        st = d / "state.json"
        if st.exists():
            data = json.loads(st.read_text())
            out.append({"run_id": data["run_id"], "goal": data["goal"]["raw"], "status": data["status"],
                        "steps": data["step_count"], "provider": data["provider"], "model": data["model"]})
    return out


@app.get("/api/runs/{run_id}/events")
def run_events(run_id: str, after: int = 0) -> list[dict]:
    if run_id in BUSES:
        return [e.model_dump(mode="json") for e in BUSES[run_id].history if e.sequence > after]
    return [e.model_dump(mode="json") for e in load_events(_run_dir(run_id) / "events.jsonl") if e.sequence > after]


@app.get("/api/runs/{run_id}/report", response_class=HTMLResponse)
def run_report(run_id: str, download: bool = False):
    d = _run_dir(run_id)
    path = d / "report.html"
    if not path.exists():
        state = AgentState.model_validate_json((d / "state.json").read_text())
        path.write_text(render_report(state, d), encoding="utf-8")
    if download:
        return FileResponse(path, filename=f"audit-{run_id}.html", media_type="text/html")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.post("/api/runs/{run_id}/save-replay")
def save_replay(run_id: str, name: str = "golden") -> dict:
    src = _run_dir(run_id)
    if not (src / "state.json").exists():
        raise HTTPException(409, "run has not finished")
    dst = settings.replay_dir / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return {"saved": name, "from": run_id}


@app.get("/api/replays")
def list_replays() -> list[str]:
    return sorted(p.parent.name for p in settings.replay_dir.glob("*/events.jsonl"))


@app.get("/api/replays/{name}/report", response_class=HTMLResponse)
def replay_report(name: str):
    path = settings.replay_dir / name / "report.html"
    if not path.exists():
        raise HTTPException(404, "replay report not found")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/health")
async def health(deep: bool = False) -> dict:
    return await health_report(deep)


@app.websocket("/ws/runs/{run_id}")
async def run_socket(ws: WebSocket, run_id: str, after: int = 0):
    await ws.accept()
    bus = BUSES.get(run_id)
    try:
        if bus is None:  # finished run from disk (e.g. after a backend restart)
            path = settings.artifacts_dir / f"run_{run_id}" / "events.jsonl"
            if not path.exists():
                await ws.close(code=4404)
                return
            for ev in load_events(path):
                if ev.sequence > after:
                    await ws.send_text(ev.model_dump_json())
            await ws.close()
            return
        q = bus.subscribe()  # subscribe before replaying history so nothing is missed
        try:
            sent = after
            for ev in list(bus.history):
                if ev.sequence > sent:
                    await ws.send_text(ev.model_dump_json())
                    sent = ev.sequence
            if bus.closed and q.empty():
                await ws.close()
                return
            while (ev := await q.get()) is not None:
                if ev.sequence > sent:
                    await ws.send_text(ev.model_dump_json())
                    sent = ev.sequence
            await ws.close()
        finally:
            bus.unsubscribe(q)
    except WebSocketDisconnect:
        pass


_dist = ROOT / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
