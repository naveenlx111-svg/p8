"""FastAPI transport: REST + WebSocket. Live and replay runs emit the same event contract.

    uvicorn backend.api.app:app --port 8000
"""
from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.agent.runner import new_state, run_live
from backend.api.health import health_report
from backend.api.comparison import compare_runs
from backend.api.report import render_report
from backend.config import ROOT, settings
from backend.events import EventBus, load_events
from backend.runtime.android import AndroidError, apk_package, list_devices
from backend.schemas import AgentState, short_id

app = FastAPI(title="PathLens")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
settings.replay_dir.mkdir(parents=True, exist_ok=True)
settings.upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=settings.artifacts_dir), name="artifacts")
app.mount("/replay_runs", StaticFiles(directory=settings.replay_dir), name="replay_runs")

BUSES: dict[str, EventBus] = {}
TASKS: dict[str, asyncio.Task] = {}

_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _replay_path(name: str) -> Path:
    """Confines a caller-supplied replay name to a single path segment directly under replay_dir.
    Rejects anything that could traverse or escape it (absolute paths, "..", separators) before any
    filesystem read/write/delete touches it."""
    if not _SAFE_NAME.match(name):
        raise HTTPException(400, "replay name must match ^[A-Za-z0-9_-]{1,64}$")
    base = settings.replay_dir.resolve()
    target = (base / name).resolve()
    if target.parent != base:
        raise HTTPException(400, "invalid replay name")
    return target


class RunRequest(BaseModel):
    goal: str = "Find the Nova headphones under ₹3,000, add them to cart, and reach checkout."
    target_url: str | None = None
    mode: str = "live"  # live | replay
    replay: str = "golden"
    speed: float = 1.0
    success_url: list[str] | None = None
    success_text: list[str] | None = None
    max_steps: int | None = None
    platform: str = "web"
    device_serial: str | None = None
    android_package: str | None = None
    android_activity: str | None = None
    apk_id: str | None = None
    record_video: bool = True


class CompareRequest(BaseModel):
    baseline_run: str
    candidate_run: str


def _spawn(run_id: str, coro) -> None:
    task = asyncio.create_task(coro)
    TASKS[run_id] = task
    task.add_done_callback(lambda _task: TASKS.pop(run_id, None))


def _apk_path(apk_id: str) -> Path:
    if not _SAFE_NAME.match(apk_id):
        raise HTTPException(400, "invalid apk_id")
    base = settings.upload_dir.resolve()
    path = (base / f"{apk_id}.apk").resolve()
    if path.parent != base or not path.is_file():
        raise HTTPException(404, "uploaded APK not found")
    return path


@app.get("/api/android/devices")
async def android_devices() -> dict:
    try:
        devices = await list_devices()
    except AndroidError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"devices": [device.model_dump() for device in devices],
            "ready": any(device.status == "device" for device in devices)}


@app.post("/api/android/apks")
async def upload_apk(file: UploadFile = File(...)) -> dict:
    if not (file.filename or "").lower().endswith(".apk"):
        raise HTTPException(400, "choose an .apk file")
    apk_id = short_id()
    destination = settings.upload_dir / f"{apk_id}.apk"
    size = 0
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 250 * 1024 * 1024:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(413, "APK exceeds the 250 MB demo limit")
            output.write(chunk)
    try:
        with destination.open("rb") as uploaded:
            signature = uploaded.read(2)
        if signature != b"PK":
            raise AndroidError("the upload is not an APK/ZIP file")
        package = await apk_package(destination)
    except AndroidError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(400, str(exc)) from exc
    return {"apk_id": apk_id, "filename": file.filename, "package": package, "size": size}


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
        if not (_replay_path(req.replay) / "events.jsonl").exists():
            raise HTTPException(404, f"replay '{req.replay}' not found")
        run_id = "replay_" + short_id()
        bus = EventBus(run_id, settings.artifacts_dir, record=False)
        BUSES[run_id] = bus
        _spawn(run_id, _replay(bus, req.replay, req.speed))
        return {"run_id": run_id, "mode": "replay"}
    if req.platform not in ("web", "android"):
        raise HTTPException(400, "platform must be web or android")
    if req.platform == "web" and req.target_url and not req.target_url.lower().startswith(("http://", "https://")):
        raise HTTPException(400, "target_url must start with http:// or https://")
    if not req.goal.strip():
        raise HTTPException(400, "goal must not be empty")
    apk_path = None
    android_package = req.android_package
    if req.platform == "android":
        if req.apk_id:
            apk_path = _apk_path(req.apk_id)
            if not android_package:
                try:
                    android_package = await apk_package(apk_path)
                except AndroidError as exc:
                    raise HTTPException(400, str(exc)) from exc
        if not android_package:
            raise HTTPException(400, "Android runs need an uploaded APK or installed package name")
        if not req.success_text or not any(text.strip() for text in req.success_text):
            raise HTTPException(400, "Android runs need deterministic 'Done when screen shows' text")
    state = new_state(req.goal, req.target_url, success_url=req.success_url, success_text=req.success_text,
                      max_steps=req.max_steps, platform=req.platform, device_serial=req.device_serial,
                      android_package=android_package, android_activity=req.android_activity,
                      apk_path=str(apk_path) if apk_path else None, record_video=req.record_video)
    bus = EventBus(state.run_id, settings.artifacts_dir / f"run_{state.run_id}")
    BUSES[state.run_id] = bus
    _spawn(state.run_id, run_live(state, bus))
    return {"run_id": state.run_id, "mode": "live"}


def _run_dir(run_id: str) -> Path:
    d = settings.artifacts_dir / f"run_{run_id}"
    if not d.is_dir():
        raise HTTPException(404, "run not found")
    return d


def _load_completed_state(run_id: str) -> AgentState:
    state_path = _run_dir(run_id) / "state.json"
    if not state_path.exists():
        raise HTTPException(409, f"run {run_id} is still in progress")
    return AgentState.model_validate_json(state_path.read_text(encoding="utf-8"))


@app.get("/api/runs")
def list_runs() -> list[dict]:
    out = []
    for d in sorted(settings.artifacts_dir.glob("run_*"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
        st = d / "state.json"
        if st.exists():
            data = json.loads(st.read_text())
            out.append({"run_id": data["run_id"], "goal": data["goal"]["raw"], "status": data["status"],
                        "steps": data["step_count"], "provider": data["provider"], "model": data["model"],
                        "platform": data.get("platform", "web"),
                        "target_url": data.get("target_url"),
                        "goal_completed": data.get("goal_completed", False),
                        "accessibility_score": data.get("accessibility_score", 100),
                        "experience_score": (data.get("experience_score") or {}).get("overall"),
                        "runtime_s": data.get("runtime_s"),
                        "updated_at": data.get("updated_at") or data.get("finished_at")})
    return out


@app.post("/api/compare")
def compare(req: CompareRequest) -> dict:
    if req.baseline_run == req.candidate_run:
        raise HTTPException(400, "baseline and candidate must be different runs")
    return compare_runs(_load_completed_state(req.baseline_run), _load_completed_state(req.candidate_run))


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
        state_path = d / "state.json"
        if not state_path.exists():
            raise HTTPException(409, "run is still in progress; report will be available after finalization")
        state = AgentState.model_validate_json(state_path.read_text(encoding="utf-8"))
        path.write_text(render_report(state, d), encoding="utf-8")
    if download:
        return FileResponse(path, filename=f"audit-{run_id}.html", media_type="text/html")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.delete("/api/runs/{run_id}")
async def cancel_run(run_id: str) -> dict:
    task = TASKS.get(run_id)
    if task is None:
        if (settings.artifacts_dir / f"run_{run_id}" / "state.json").exists():
            raise HTTPException(409, "run has already finished")
        raise HTTPException(404, "active run not found")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        # Defensive only: run_live currently consumes cancellation after recording final artifacts.
        pass
    return {"run_id": run_id, "cancelled": True}


@app.post("/api/runs/{run_id}/save-replay")
def save_replay(run_id: str, name: str = "golden") -> dict:
    src = _run_dir(run_id)
    if not (src / "state.json").exists():
        raise HTTPException(409, "run has not finished")
    dst = _replay_path(name)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return {"saved": name, "from": run_id}


@app.get("/api/replays")
def list_replays() -> list[str]:
    return sorted(p.parent.name for p in settings.replay_dir.glob("*/events.jsonl"))


@app.get("/api/replays/{name}/report", response_class=HTMLResponse)
def replay_report(name: str):
    path = _replay_path(name) / "report.html"
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
