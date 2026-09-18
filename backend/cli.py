"""Terminal vertical slice:  python -m backend.cli "Find the Nova headphones under ₹3,000, add them to cart, and reach checkout."

Options: --url URL  --runs N (repeat for reliability measurement)
Provider/model via env: PATHLENS_PROVIDER=gemini|anthropic|openai|scripted, PATHLENS_MODEL=...
"""
from __future__ import annotations

import argparse
import asyncio
import json

from backend.agent.runner import new_state, run_live
from backend.config import settings
from backend.events import EventBus

C = {"red": "\033[31m", "grn": "\033[32m", "yel": "\033[33m", "blu": "\033[34m", "dim": "\033[2m", "b": "\033[1m", "x": "\033[0m"}


def render(ev) -> str | None:
    p, t = ev.payload, ev.type
    if t == "run_started":
        tag = " [OFFLINE TEST DOUBLE - NOT AI]" if p["offline_test_double"] else ""
        return f"{C['b']}▶ {p['goal']['raw']}{C['x']}\n  target={p['target_url']} model={p['provider']}/{p['model']}{tag}"
    if t == "decision":
        facts = ", ".join(f"{f['entity']}=₹{f['value']:.0f}" for f in p["facts"])
        return (f"{C['blu']}◆ step {p['step']}{C['x']} observed: {p['observed']}"
                + (f"\n  facts: {facts}" if facts else "")
                + f"\n  → {p['action'].upper()} {p['label'] or ''}{(' ' + repr(p['text'])) if p['text'] else ''}"
                  f"  {C['dim']}({p['rationale']}; conf {p['confidence']:.0%}; {p['latency_ms']}ms{', vision' if p['vision'] else ''}){C['x']}")
    if t == "action_completed":
        col = C["grn"] if p["outcome"] == "success" else C["yel"]
        return f"  {col}{p['outcome']}{C['x']} {C['dim']}{p['duration_ms']}ms {p['error'] or ''}{C['x']}"
    if t == "finding":
        col = C["red"] if p["severity"] in ("high", "critical") else C["yel"]
        return f"  {col}⚠ {p['code']} [{p['severity'].upper()}] {p['title']}{C['x']}\n    {p['evidence']}"
    if t == "observation" and "verification" in p:
        return f"  {C['grn']}✓ completion verified: {', '.join(p['verification']['evidence'])}{C['x']}"
    if t in ("run_completed", "run_failed"):
        col = C["grn"] if t == "run_completed" else C["red"]
        return f"{col}{C['b']}■ {t.upper()}{C['x']}\n{json.dumps(p, indent=1, ensure_ascii=False)}"
    return None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("goal", nargs="?", default="Find the Nova headphones under ₹3,000, add them to cart, and reach checkout.")
    ap.add_argument("--url", default=settings.target_url)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--success-url", action="append", help="acceptance: URL must contain this (repeatable)")
    ap.add_argument("--success-text", action="append", help="acceptance: page must show this text (repeatable)")
    ap.add_argument("--max-steps", type=int, default=None)
    args = ap.parse_args()
    results = []
    for i in range(args.runs):
        if args.max_steps:
            settings.max_steps = args.max_steps
        state = new_state(args.goal, args.url, success_url=args.success_url, success_text=args.success_text)
        bus = EventBus(state.run_id, settings.artifacts_dir / f"run_{state.run_id}")
        q = bus.subscribe()

        async def printer():
            while (ev := await q.get()) is not None:
                if line := render(ev):
                    print(line, flush=True)

        pt = asyncio.create_task(printer())
        state = await run_live(state, bus)
        await pt
        results.append((state.run_id, state.status.value, state.step_count))
    if args.runs > 1:
        ok = sum(1 for r in results if r[1] == "completed")
        print(f"\n{C['b']}{ok}/{args.runs} runs completed{C['x']}: {results}")


if __name__ == "__main__":
    asyncio.run(main())
