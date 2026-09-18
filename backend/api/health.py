"""Pre-demo health check. Every value should be true before presenting."""
from __future__ import annotations

import os

import httpx
from playwright.async_api import async_playwright

from backend.config import model_name, settings

KEY_ENV = {"gemini": ("GOOGLE_API_KEY", "GEMINI_API_KEY"), "anthropic": ("ANTHROPIC_API_KEY",),
           "openai": ("OPENAI_API_KEY",), "ollama": (), "scripted": ()}


async def _browser_ok() -> tuple[bool, str]:
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(headless=True)
            v = b.version
            await b.close()
            return True, v
    except Exception as exc:
        return False, str(exc)[:200]


async def _target_ok() -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(settings.target_url)
            return r.status_code == 200, f"HTTP {r.status_code}"
    except Exception as exc:
        return False, type(exc).__name__


async def _model_ok(deep: bool) -> tuple[bool, str]:
    if settings.provider == "scripted":
        return False, "scripted OFFLINE TEST DOUBLE configured (not AI)"
    keys = KEY_ENV[settings.provider]
    if keys and not any(os.environ.get(k) for k in keys):
        return False, f"missing {' or '.join(keys)}"
    if not deep:
        return True, f"{settings.provider}/{model_name()} (key present; use ?deep=true to ping)"
    from backend.agent.llm import build_model
    try:
        text, ms = await build_model().complete("Reply with JSON only.", 'Return {"ok": true}')
        return '"ok"' in text, f"{settings.provider}/{model_name()} {ms}ms"
    except Exception as exc:
        return False, str(exc)[:200]


async def health_report(deep: bool = False) -> dict:
    browser, target, model = await _browser_ok(), await _target_ok(), await _model_ok(deep)
    axe = settings.axe_path.exists() and settings.axe_path.stat().st_size > 100_000
    replay = (settings.replay_dir / "golden" / "events.jsonl").exists()
    checks = {
        "backend": (True, "ok"), "browser": browser, "target_app": (target[0], f"{settings.target_url} {target[1]}"),
        "axe": (axe, str(settings.axe_path.name)), "model": model, "websocket": (True, "/ws/runs/{run_id}"),
        "replay": (replay, "golden" if replay else "no golden replay saved yet"),
    }
    return {**{k: v[0] for k, v in checks.items()}, "details": {k: v[1] for k, v in checks.items()},
            "all_green": all(v[0] for v in checks.values())}
