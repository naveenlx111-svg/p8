"""Run event bus: every event is (1) kept in memory for late joiners, (2) fanned out to live subscribers,
(3) appended to <run_dir>/events.jsonl for replay. Live and replay emit the identical contract (schemas.Event)."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from backend.schemas import Event, EventType


class EventBus:
    def __init__(self, run_id: str, run_dir: Path, record: bool = True):
        self.run_id = run_id
        self.history: list[Event] = []
        self._subscribers: set[asyncio.Queue] = set()
        self._t0 = time.perf_counter()
        self._seq = 0
        self._file = None
        self.closed = False
        if record:
            run_dir.mkdir(parents=True, exist_ok=True)
            self._file = (run_dir / "events.jsonl").open("w", encoding="utf-8")

    def emit(self, type: EventType, payload: dict[str, Any], offset_ms: int | None = None) -> Event:
        self._seq += 1
        ev = Event(run_id=self.run_id, sequence=self._seq, type=type, payload=payload,
                   offset_ms=offset_ms if offset_ms is not None else int((time.perf_counter() - self._t0) * 1000))
        self.history.append(ev)
        if self._file:
            self._file.write(ev.model_dump_json() + "\n")
            self._file.flush()
        for q in list(self._subscribers):
            q.put_nowait(ev)
        return ev

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def close(self) -> None:
        self.closed = True
        if self._file:
            self._file.close()
            self._file = None
        for q in list(self._subscribers):
            q.put_nowait(None)  # sentinel: stream finished


def load_events(path: Path) -> list[Event]:
    with path.open(encoding="utf-8") as fh:
        return [Event.model_validate(json.loads(line)) for line in fh if line.strip()]
