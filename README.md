# PathLens: an autonomous synthetic user for UX intelligence

> Traditional QA tests whether software works. PathLens tests whether the experience works for a human.
> Give it a goal, not a test script.

PathLens takes a **target URL or Android APK/installed package and a plain-English goal**, then drives a real
Chromium browser, Android phone, or emulator one action at a time. It only gets what a user or screen reader would
get: visible text, the platform accessibility tree, the currently actionable controls, and (optionally) the screenshot.
While it works, it records the journey, remembers facts across screens, notices when an action
"worked" but the goal did not progress, recovers, verifies completion **in code**, audits accessibility with
axe-core, and streams everything to a live dashboard, an HTML audit and a replayable log.

The AI investigates the experience. Deterministic tooling verifies what should be deterministic.

## Quick start

```bash
scripts/setup.sh                 # venv + Chromium + frontend build (one time)
ollama pull qwen2.5:7b           # or set a cloud provider in .env
scripts/start.sh                 # demo shop :4173 + dashboard/API :8000; rebuilds UI if changed, checks model, prints health
scripts/stop.sh                  # stop both servers
```

Open http://127.0.0.1:8000, then press **Run live**, or **Replay golden run** to play a recorded run (clearly labelled REPLAY).

### Android app testing (real phone, emulator, or APK)

1. Install Android SDK Platform-Tools and verify the device is authorised with `adb devices -l`. For a physical
   phone, enable Developer options and USB debugging; an emulator appears through the same ADB interface.
2. In the dashboard select **Android · ADB**, press **↻ ADB**, and select the device.
3. Either upload an APK (PathLens verifies its package with `aapt`, installs it with `adb install -r`, then launches
   it) or enter an already-installed package such as `com.example.app`.
4. Supply the natural-language goal and deterministic **Done when screen shows** text, then run.

Android uses the same agent and evidence protocol as web. The adapter captures a fresh UIAutomator XML hierarchy,
builds observation-scoped semantic element IDs, executes taps/text/keys through ADB, captures PNG screenshots,
checks accessible names and 48dp touch targets, and records a native MP4 using `screenrecord`. Each dashboard state
links to the exact captured accessibility tree. The APK is never exposed as a static public artifact.

### 60-second differential-regression demo

1. Run the default **NovaMart demo shop** goal and click **Set current as baseline** when it finishes.
2. Choose **NovaMart candidate release (UX regression)** from Examples and run the same goal.
3. Click **Compare candidate**. PathLens reports the added Delivery milestone, +1 observed action, the new
   `button-name` accessibility defect and the accessibility-score delta.

The candidate is a controlled release fixture selected only by URL (`?release=candidate`). The navigator still
operates from rendered UI and accessibility semantics; the comparator uses saved deterministic evidence and never
asks an LLM to judge whether the release regressed.

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
   ┌─► OBSERVE  Playwright/ADB: route, visible text, ARIA/UIAutomator tree, controls → ephemeral registry, frame
   │      │     state fingerprint, journey node/edge, transition critic, platform a11y audit, completion verifier
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
- **LLM perceives, code verifies.** A product-price fact is kept only when its exact visible amount is associated
  with the named product in the same page region (no rounding). Contradictions are computed in Python and skipped
  when a currency change fully explains the
  difference. Completion checks the route, a visible email field, the goal product currently shown in the cart
  (not merely ever seen there), and any price limit against the latest grounded fact for that product. A model
  saying DONE is ignored unless the verifier agrees. Unverified AI observations are labelled as such and never
  counted as defects.
- **States are semantic fingerprints**, not URLs (canonical route + heading + dialog + controls + text). Closing
  the modal returns to the *same* Cart state, so the graph shows the detour as a loop.
- **Loops are action evidence, not log messages.** When a sequence returns to a prior semantic state, PathLens
  reports the exact action chain and currently visible, unattempted controls that offer alternative pathways.
- **Accessibility claims retain provenance.** Every state stores its ARIA snapshot or native UIAutomator XML;
  each finding names the method, evidence, and a concrete remediation. Automated results remain explicitly
  labelled as risk checks rather than WCAG certification.
- **Journey video is automatic.** Web runs save Playwright WebM; Android runs save the platform `screenrecord` MP4.
- **Replay** re-emits a recorded run's exact event stream (`contracts/websocket.md`) with the original timing.
- **Release intelligence is evidence-based.** `POST /api/compare` aligns semantic milestones and compares goal
  outcome, observed actions, runtime, friction counters, accessibility score and verified findings. Unverified AI
  observations never become regression evidence.
- **The experience score is smart without being self-certified.** A single 0–100 grade combines verified outcome,
  normalized interaction cost, accessibility findings, semantic consistency, recovery resilience and audit coverage.
  The dashboard exposes each dimension and an evidence-confidence indicator; the model may explain a screen, but it
  never gets to choose its own score.

## Repository layout

```
backend/
  schemas.py        frozen contracts (state, actions, findings, events)
  config.py         env config        events.py   event bus + JSONL recorder
  agent/            graph.py (LangGraph), planner.py, prompt.py, llm.py (providers), memory.py,
                    critic.py, completion.py, safety.py, journey.py, goal.py, runner.py, scripted.py
  runtime/          browser.py, android.py (ADB/UIAutomator), observer.py (registry), executor.py,
                    accessibility.py, keyboard.py, fingerprint.py
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
  `qwen2.5:7b` (6 actions, about 30 s), and a real SauceDemo run completed in 7 actions. Dashboard, journey graph,
  audit, replay, health check, cancellation, deterministic A/B comparison, video evidence, captured accessibility
  trees, semantic action-loop traces, experiential modal-focus checks, native Android ADB/UIAutomator execution,
  and 44 tests all work. The Android adapter was live-smoke-tested on an Android 36 emulator by launching Settings,
  resolving and tapping “Network & internet,” observing the destination screen, auditing it, and pulling the MP4.
  The golden-journey integration test starts its own demo-app
  server, so `pytest` does not silently skip it. In the controlled A/B rehearsal, both releases complete: baseline
  6 actions / a11y 61, candidate 7 actions / a11y 36, with a new `button-name` rule and Delivery milestone.
- **Limits:** Android APK installation requires local Android SDK `adb` and `aapt`; device permission dialogs and
  OS security boundaries still apply. Screen recordings use Android's three-minute `screenrecord` segment limit.
  Screenshots are evidence only with the local model: the local
  vision model (`qwen3-vl:8b`) took 30–70 s per step, and the cloud vision providers are implemented but not yet
  benchmarked. Goal parsing and success criteria are rule-based and cover checkout/cart/login-style goals. The
  friction score is our own transparent heuristic, and the accessibility score is not a WCAG certification.
- **Not built:** bounded multi-path frontier (the current agent records one route per run), a full keyboard-only
  journey persona, and responsive matrix. These remain intentionally separate from the implemented A/B
  comparison so the dashboard does not claim capabilities it cannot execute.
