"""Integration: fresh browser -> full autonomous loop against the local demo app.

Uses the offline test double by default so it runs without API keys or consuming a developer's configured model
quota (it validates runtime, orchestration, memory, critic, completion and axe). Set
PATHLENS_TEST_REAL_PROVIDER=1 to explicitly use the configured real provider.

The demo app is started in-process (a background HTTP server serving demo_app/) so this test runs
unattended in CI instead of silently skipping when nothing happens to be listening on PATHLENS_TARGET_URL.
"""
import asyncio
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from backend.agent.runner import new_state, run_live
from backend.config import settings
from backend.events import EventBus

if not os.environ.get("PATHLENS_TEST_REAL_PROVIDER"):
    settings.provider = "scripted"

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_app"


@pytest.fixture(scope="module")
def demo_app_url():
    handler = partial(SimpleHTTPRequestHandler, directory=str(DEMO_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        server.server_close()


def test_golden_journey_fresh_browser(tmp_path, demo_app_url):
    settings.artifacts_dir = tmp_path
    settings.target_url = demo_app_url
    state = new_state("Find the Nova headphones under ₹3,000, add them to cart, and reach checkout.")
    bus = EventBus(state.run_id, tmp_path / f"run_{state.run_id}")
    state = asyncio.run(run_live(state, bus))

    assert state.goal_completed, state.run_error
    cats = [f.category for f in state.critic_findings]
    assert "semantic_inconsistency" in cats
    assert "friction" in cats and "recovery" in cats
    rules = {v.id for v in state.axe_results}
    assert {"label", "color-contrast"} <= rules
    assert state.accessibility_score == 61
    assert state.step_count <= 12
    assert (tmp_path / f"run_{state.run_id}" / "report.html").exists()
    assert bus.history[-1].type == "run_completed"
