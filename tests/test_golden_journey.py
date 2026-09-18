"""Integration: fresh browser -> full autonomous loop against the local demo app.

Uses the offline test double by default so it runs without API keys (it validates runtime, orchestration,
memory, critic, completion and axe). Set PATHLENS_PROVIDER to a real provider to test the actual agent.
Requires the demo app on PATHLENS_TARGET_URL (scripts/demo_app.sh).
"""
import asyncio
import os

import httpx
import pytest

from backend.agent.runner import new_state, run_live
from backend.config import settings
from backend.events import EventBus

if not os.environ.get("PATHLENS_PROVIDER"):
    settings.provider = "scripted"


def _target_up() -> bool:
    try:
        return httpx.get(settings.target_url, timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(not _target_up(), reason="demo app not running")
def test_golden_journey_fresh_browser(tmp_path):
    settings.artifacts_dir = tmp_path
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
