# PathLens: an autonomous synthetic user for UX intelligence

> Traditional QA tests whether software works. PathLens tests whether the experience works for a human.
> Give it a goal, not a test script.

PathLens takes a **target URL and a plain-English goal**, then drives a real Chromium browser one action at a time.
It only gets what a user or screen reader would get: visible text, the accessibility tree, the currently visible
controls, and (optionally) the screenshot. While it works, it remembers facts across screens, notices when a click
"worked" but the goal did not progress, recovers, verifies completion **in code**, audits accessibility with
axe-core, and streams everything to a live dashboard, an HTML audit and a replayable log.

The AI investigates the experience. Deterministic tooling verifies what should be deterministic.

## Quick start

```bash
scripts/setup.sh                 # venv + Chromium + frontend build (one time)
ollama pull qwen2.5:7b           # or set a cloud provider in .env
scripts/start.sh                 # demo shop on :4173, dashboard + API on :8000
```

Open http://127.0.0.1:8000, then press **Run live**, or **Replay golden run** to play a recorded run (clearly labelled REPLAY).

Terminal only:

```bash
.venv/bin/python -m backend.cli "Find the Nova headphones under ₹3,000, add them to cart, and reach checkout."
.venv/bin/python -m backend.cli --runs 3      # reliability check: 3 fresh-browser runs
curl localhost:8000/health?deep=true          # pre-demo check: every value must be true
.venv/bin/python -m pytest                    # unit + golden-journey integration test
```

### Model providers (`.env`)

| `PATHLENS_PROVIDER` | Notes |
|---|---|
| `ollama` | Local. Default `qwen2.5:7b` with `PATHLENS_VISION_MODE=off` (~3–5 s/step on an 8 GB GPU). |
| `gemini` | `GOOGLE_API_KEY`, default `gemini-2.5-flash`, vision capable. |
| `anthropic` | `ANTHROPIC_API_KEY`, default `claude-opus-5`, vision capable. |
| `openai` | `OPENAI_API_KEY`, and optionally `PATHLENS_OPENAI_BASE_URL` for any OpenAI-compatible endpoint. |
| `scripted` | **Offline test double, not AI.** A keyword heuristic used only for tests. The UI labels it "TEST DOUBLE". |

`PATHLENS_MODEL` overrides the model. `PATHLENS_VISION_MODE` = `always` \| `fallback` \| `off`.

## How it works

```
goal ─► GoalSpec (product, max price, success signals)
          │
          ▼
   ┌─► OBSERVE  Playwright: URL, visible text, ARIA snapshot, visible controls → ephemeral registry, screenshot
   │      │     state fingerprint, journey node/edge, transition critic, axe (live rules), completion verifier
   │      ▼
   │   DECIDE   one LLM call → JSON: page summary, facts, findings, next action (element id from THIS observation)
   │      │     facts grounded against visible text → fact memory → price-conflict check (plain Python)
   │      ▼
   │   GATE     safety (no pay/order/subscribe/delete/sensitive typing), DONE only if verifier agrees
   │      ▼
   └── EXECUTE  click/type/scroll/back/wait → outcome: success | stale | blocked | failed | rejected
          │
      FINALIZE  full axe WCAG A/AA audit, scores, state.json, report.html, run_completed/run_failed
```

Key design decisions:

- **No selectors from the model.** Each observation lists the controls visible right now. The model picks an
  `element_id` that is valid only for that `observation_id`, and the registry expires on the next observation.
  Nothing is stamped into the target DOM.
- **"The click happened" ≠ "the goal progressed".** A click that keeps the URL and opens a dialog becomes a
  high-severity friction finding. A click that times out because something covers the control becomes **blocked**
  (UX evidence), not a crash.
- **LLM perceives, code verifies.** A price fact is kept only if its value is literally visible on the page.
  Contradictions are computed in Python. Completion needs the route, a visible email field, and the goal product
  having been shown in the cart. A model saying DONE is ignored unless the verifier agrees. Unverified AI
  observations are labelled as such and never counted as defects.
- **States are semantic fingerprints**, not URLs (canonical route + heading + dialog + controls + text). Closing
  the modal returns to the *same* Cart state, so the graph shows the detour as a loop.
- **Replay** re-emits a recorded run's exact event stream (`contracts/websocket.md`) with the original timing.

## Repository layout

```
backend/
  schemas.py        frozen contracts (state, actions, findings, events)
  config.py         env config        events.py   event bus + JSONL recorder
  agent/            graph.py (LangGraph), planner.py, prompt.py, llm.py (providers), memory.py,
                    critic.py, completion.py, safety.py, journey.py, goal.py, runner.py, scripted.py
  runtime/          browser.py, observer.py (registry), executor.py, accessibility.py, fingerprint.py
  api/              app.py (REST + WebSocket), report.py (HTML audit), health.py
  vendor/axe.min.js axe-core 4.10.3, vendored (no CDN at demo time)
  cli.py
frontend/           React + Tailwind + React Flow dashboard
demo_app/           NovaMart: deterministic local shop with planted defects
replay_runs/golden  recorded real-model run (qwen2.5:7b) used for fallback replay
contracts/          WebSocket event contract
tests/
```

## Demo target and planted defects

`demo_app/index.html`, routes `#/`, `#/results?q=`, `#/product/:id`, `#/cart`, `#/checkout`, `#/complete`.

1. **Price mismatch:** product page ₹2,499, cart ₹2,799.
2. **Checkout obstruction:** the first Checkout click opens a "Join Nova+" dialog (no timers); the second works.
3. **Accessibility:** the email input has visible text but no programmatic label (axe `label`, critical), and the
   Pay button has 1.33:1 contrast (axe `color-contrast`, serious). Risk score = 100 − 25 − 14 = **61**.
   (The original plan assumed 72; axe rates `label` as critical.)

The agent code contains no knowledge of these defects or of the app. `grep -ri nova backend/agent backend/runtime`
returns nothing.

## Honest status

- **Works:** the golden journey from goal text only passed 3/3 consecutive fresh-browser runs with local
  `qwen2.5:7b` (6 actions, about 30 s). Dashboard, journey graph, audit, replay, health check and 13 tests all work.
- **Limits:** tested only on our own demo shop so far. Screenshots are evidence only with the local model: the local
  vision model (`qwen3-vl:8b`) took 30–70 s per step, and the cloud vision providers are implemented but not yet
  benchmarked. Goal parsing and success criteria are rule-based and cover checkout/cart/login-style goals. The
  friction score is our own transparent heuristic, and the accessibility score is not a WCAG certification.
- **Not built:** multi-path exploration, version A/B regression, keyboard-only/focus-order mode, mobile.
