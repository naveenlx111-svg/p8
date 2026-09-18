# PathLens — Complete Pragyaan 2.0 Winning Plan

> **Problem Statement:** P8 — Autonomous Agentic Black-Box UI/UX & Accessibility Testing Framework  
> **Working Project Name:** **PathLens**  
> **Tagline:** *Give it a goal. Watch it experience your product like a user.*  
> **Hackathon Objective:** Build the strongest possible, honest, demo-ready proof of concept with a clear technical moat, measurable outputs, and architecture that can absorb the surprise checkpoint feature quickly.

---

# 0. Executive Decision

## Why we are choosing P8

PathLens targets a very specific gap between traditional automated testing and real user experience testing.

Traditional tools such as Selenium, Playwright, Cypress, and Appium are excellent when developers already know:

- what page they are testing,
- which selectors to interact with,
- which sequence of steps to execute,
- and what exact assertion should pass.

They are much weaker when the question becomes:

> “Can a first-time user accomplish this goal, what paths can they take, where will they get confused, and did the experience become worse after a UI change?”

That is the gap PathLens attacks.

Instead of a developer writing a rigid test such as:

```text
click("#search")
type("blue shoes")
click("#first-result")
click("#add-to-cart")
```

they provide only a user intent:

```text
"Find blue running shoes under ₹5,000 and reach guest checkout."
```

The system must autonomously:

1. inspect the current interface,
2. decide what action seems useful,
3. execute it,
4. observe what changed,
5. remember visited states,
6. recover from failed or misleading actions,
7. explore alternative paths,
8. validate whether the goal was actually reached,
9. detect friction/accessibility issues,
10. generate evidence-backed findings.

That makes the project genuinely agentic rather than “LLM + predefined automation”.

---

# 1. One-Sentence Product Definition

**PathLens is an autonomous black-box UX testing agent that takes a natural-language user goal, explores an unfamiliar application without source-code access or predefined test steps, builds a journey graph, detects friction and accessibility problems, verifies its findings, and produces replayable evidence.**

---

# 2. Core Winning Thesis

Our project should NOT be presented as:

> “AI that generates Playwright tests.”

That is too generic.

It should be presented as:

> **An intent-driven UX exploration engine that treats the application as an unknown environment and discovers how a real user can or cannot accomplish a goal.**

The technical differentiator is the combination of:

- **goal-conditioned navigation**
- **state/journey graph construction**
- **multi-path exploration**
- **deterministic friction metrics**
- **accessibility-aware interaction**
- **self-verification of suspected issues**
- **version-to-version UX regression comparison**
- **replayable evidence**

This makes the system a UX intelligence layer above raw browser/device automation.

---

# 3. Hackathon Scope

## 3.1 What we MUST build

The minimum winning build should support:

### A. Natural-language task input

Example:

```text
"Find a wireless keyboard under ₹3,000 and proceed to checkout as a guest."
```

### B. Black-box navigation

The agent operates through browser-visible UI and accessibility information.

No source code.
No hard-coded selectors for the target website.
No hidden application test hooks.

### C. Autonomous decision loop

The system repeatedly performs:

```text
Observe → Understand → Choose Action → Execute → Verify → Update State → Continue
```

### D. Journey graph

Every meaningful application state becomes a node.

Every user action becomes an edge.

This allows:

- loop detection,
- dead-end detection,
- backtracking,
- alternate path discovery,
- shortest valid path calculation.

### E. Friction detection

The system should detect and quantify at least:

- unnecessary extra steps,
- repeated states,
- backtracking,
- failed clicks,
- dead ends,
- confusing or non-responsive controls,
- accessibility violations.

### F. Accessibility audit

At minimum:

- missing labels,
- inaccessible interactive elements,
- focus-order problems where detectable,
- keyboard navigation issues,
- basic automated accessibility scan.

### G. Evidence trail

For every important finding:

- screenshot,
- step number,
- action attempted,
- state before/after,
- reason for flagging,
- replay sequence.

### H. Final report/dashboard

The result should contain:

- goal success/failure,
- journey graph,
- discovered paths,
- friction score,
- accessibility findings,
- dead ends,
- final recommendations.

---

## 3.2 High-value feature if time allows

### Differential UX Regression Mode

Input:

```text
Version A: http://localhost:3000
Version B: http://localhost:3001
Goal: "Complete guest checkout."
```

Output:

| Metric | Version A | Version B |
|---|---:|---:|
| Goal reached | Yes | Yes |
| Shortest valid path | 6 steps | 10 steps |
| Failed interactions | 0 | 2 |
| Dead ends | 0 | 1 |
| Accessibility issues | 1 | 4 |
| Friction score | 18 | 47 |

Then:

> “Version B still allows checkout, but introduces a modal that adds 4 interactions, creates one keyboard focus trap, and makes the guest path less discoverable.”

This is an extremely powerful demo.

---

# 4. What We Deliberately Do NOT Build

To avoid scope death:

- full iOS support,
- full Android support,
- browser-extension packaging,
- CI/CD integrations,
- production-grade distributed crawling,
- enterprise authentication workflows,
- full WCAG certification,
- reinforcement-learning training,
- multi-user cloud deployment,
- automatic code fixes.

The PoC will focus on **web applications first**.

The architecture will use adapters so mobile support can be added later.

---

# 5. User Personas

## Primary

### QA Engineer
Needs to validate complete flows but does not want to manually write brittle scripts for every UI change.

### Frontend Developer
Wants to know whether a UI refactor changed the experience even if functional tests still pass.

### Product/UX Team
Wants evidence of where a first-time user experiences unnecessary friction.

### Accessibility Engineer
Wants both automated accessibility checks and goal-oriented interaction traces.

---

# 6. User Experience

## Main Screen

The interface should be extremely simple.

### Inputs

- Target URL
- User goal
- Optional persona
- Exploration budget
- Optional comparison URL

Example:

```text
Target URL:
http://localhost:3000

Goal:
Find a blue running shoe under ₹5,000 and reach guest checkout.

Persona:
First-time user

Exploration budget:
25 actions
```

### Buttons

- Start Exploration
- Stop
- Replay
- Compare Version
- Export Report

---

# 7. Live Demo Layout

A strong demo should show three areas simultaneously.

```text
┌──────────────────────────┬─────────────────────────────────┐
│                          │ Current Goal                    │
│       Live Browser       │ "Reach guest checkout"         │
│                          │                                 │
│                          │ Current Agent Reasoning         │
│                          │ "Cart is visible; checkout..."  │
├──────────────────────────┼─────────────────────────────────┤
│ Journey Graph            │ Metrics / Findings              │
│                          │                                 │
│ Home → Search → Product  │ Goal: In Progress              │
│   └→ Category → Product  │ Steps: 8                       │
│                          │ Failed Actions: 1               │
│                          │ Friction: 26                    │
└──────────────────────────┴─────────────────────────────────┘
```

Do NOT expose chain-of-thought.

Instead display concise decision summaries:

```text
Observation: Search results contain 5 products.
Decision: Open result matching color and price constraints.
Action: Click "AeroRun Blue".
Outcome: Product page opened.
```

---

# 8. System Architecture

```text
                            ┌────────────────────┐
                            │      Web UI        │
                            │ Goal / URL / Report│
                            └─────────┬──────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │   Exploration Controller │
                         │   Session + budget loop  │
                         └───────┬───────────┬──────┘
                                 │           │
                       ┌─────────▼───┐   ┌──▼──────────┐
                       │ Perception  │   │ Goal Planner│
                       │ Engine      │   │             │
                       └──────┬──────┘   └────┬────────┘
                              │               │
                              └───────┬───────┘
                                      ▼
                           ┌────────────────────┐
                           │ Explorer Agent     │
                           │ Chooses next action│
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │ Browser Adapter    │
                           │ Playwright / CDP   │
                           └─────────┬──────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │ Target App       │
                            │ True Black Box   │
                            └────────┬─────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │ State Extractor    │
                           └────┬─────────┬─────┘
                                │         │
                     ┌──────────▼──┐  ┌──▼────────────┐
                     │ Journey Graph│  │ Accessibility │
                     │ + Memory     │  │ Analyzer      │
                     └──────┬───────┘  └──────┬────────┘
                            │                  │
                            └─────────┬────────┘
                                      ▼
                           ┌────────────────────┐
                           │ Issue Verifier     │
                           │ Reproduce findings │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │ Metrics + Reporter │
                           └────────────────────┘
```

---

# 9. Agent Design

Avoid fake “20-agent architecture”.

Use only agents where reasoning is genuinely required.

## 9.1 Goal Planner

### Input

Natural-language goal.

### Output

Structured success criteria.

Example:

Input:

```text
"Find blue running shoes under ₹5,000 and reach guest checkout."
```

Output:

```json
{
  "objective": "reach_guest_checkout",
  "constraints": {
    "category": "running shoes",
    "color": "blue",
    "max_price": 5000
  },
  "success_signals": [
    "checkout page visible",
    "guest checkout option visible"
  ],
  "forbidden_actions": [
    "submit payment",
    "place order"
  ]
}
```

### Why agentic?

Goals are open-ended and cannot reliably be converted to fixed scripts.

---

## 9.2 Explorer Agent

This is the main reasoning agent.

Inputs:

- structured goal,
- current screen representation,
- current journey history,
- visited states,
- exploration budget,
- prior failed actions.

Outputs:

```json
{
  "action": "click",
  "target": {
    "text": "Shop Now",
    "role": "button"
  },
  "reason": "Likely entry point to product catalogue",
  "confidence": 0.83
}
```

Possible actions:

```text
click
type
select
scroll
press
back
open
wait
stop_success
stop_failure
```

---

## 9.3 Issue Verifier

Its job is NOT to discover everything.

Its job is to challenge suspected findings.

Example:

Explorer reports:

> “Checkout appears to be a dead end.”

Verifier tries:

1. alternative clickable element,
2. keyboard path,
3. browser back and alternate route,
4. second attempt from clean state.

Only after reproduction does the issue become confirmed.

Possible result:

```json
{
  "status": "confirmed",
  "reproducibility": 2,
  "severity": "high",
  "evidence_steps": [7, 8, 9]
}
```

---

# 10. Non-Agent Components

## Browser Adapter

Recommended:

**Playwright**

Responsibilities:

- navigate,
- click,
- type,
- scroll,
- keyboard actions,
- screenshots,
- DOM/accessibility extraction,
- console/network metadata if useful.

The target remains a black box because we use browser-observable information, not target source code.

---

## Accessibility Analyzer

Use:

- axe-core where practical,
- ARIA role/name inspection,
- focus inspection,
- keyboard traversal.

Important positioning:

PathLens does NOT claim full WCAG certification.

Instead:

> “PathLens combines deterministic accessibility checks with goal-driven interaction traces.”

---

## Journey Graph Store

For hackathon:

- in-memory NetworkX or custom adjacency map,
- optionally persist to SQLite/JSON.

Node:

```json
{
  "id": "state_12",
  "url": "/cart",
  "title": "Cart",
  "visual_hash": "...",
  "semantic_hash": "...",
  "timestamp": "...",
  "goal_progress": 0.68
}
```

Edge:

```json
{
  "from": "state_10",
  "to": "state_12",
  "action": "click",
  "target": "Add to cart",
  "success": true,
  "duration_ms": 830
}
```

---

# 11. State Representation

A key technical problem is determining whether two UI states are effectively the same.

Use a combined state fingerprint.

## 11.1 URL Component

Canonicalized URL.

Ignore irrelevant:

- tracking parameters,
- session IDs,
- timestamps.

---

## 11.2 Semantic Component

Extract visible interactive elements:

```text
button: Search
link: Men
link: Running Shoes
textbox: Search products
button: Cart (1)
```

Normalize and hash.

---

## 11.3 Visual Component

Use screenshot perceptual hash if time allows.

This helps detect:

- same URL but different modal,
- popup,
- layout shift,
- changed cart state.

---

## 11.4 State Fingerprint

Conceptually:

\[
S = H(U, A, V)
\]

Where:

- \(U\) = normalized URL
- \(A\) = accessibility/semantic representation
- \(V\) = visual fingerprint

For MVP:

\[
S = H(U, A)
\]

is enough.

---

# 12. Journey Graph

Use:

\[
G = (V, E)
\]

where:

- \(V\) = discovered UI states
- \(E\) = observed user actions.

Every action adds:

```text
Current State → Action → New State
```

Example:

```text
             Search
            /      \
           v        v
Home → Products → Product → Cart → Checkout
   \                    \
    → Categories → Product
                       \
                        → Login Wall [dead end]
```

This graph enables:

- shortest path,
- alternate paths,
- cycle detection,
- dead-end discovery,
- branch coverage,
- regression comparison.

---

# 13. Exploration Strategy

A purely greedy agent may find only one path.

We need controlled exploration.

## Phase 1 — Goal Seeking

Prioritize actions likely to make progress.

Action score:

\[
Q(a) =
w_gG(a) +
w_nN(a) +
w_cC(a)
-
w_rR(a)
-
w_fF(a)
\]

Where:

- \(G(a)\) = predicted goal progress,
- \(N(a)\) = novelty,
- \(C(a)\) = model confidence,
- \(R(a)\) = repetition penalty,
- \(F(a)\) = failure penalty.

Example weights:

```text
goal progress: +0.45
novelty:       +0.25
confidence:    +0.20
repetition:    -0.30
failure:       -0.40
```

Exact weights can remain heuristic for the PoC.

---

## Phase 2 — Alternate Path Discovery

Once one successful trajectory exists:

1. find branch points,
2. return to earlier states,
3. try unused high-value actions,
4. search for another valid trajectory.

Stop after:

- max paths reached,
- action budget exhausted,
- no useful unexplored actions remain.

---

# 14. Loop Detection

If an action returns the system to an already visited state:

```text
A → B → C → A
```

increment repetition count.

Potential loop:

\[
loop = visited(S_t) \land distance(t, previous(S_t)) < k
\]

If repeated multiple times, flag:

> “Navigation loop detected.”

Explorer then penalizes those actions.

---

# 15. Dead-End Detection

A state can be considered a probable dead end if:

- goal not achieved,
- no new meaningful actions remain,
- all available actions return to known states,
- or progression requires violating goal constraints.

Dead end should initially be **suspected**, not immediately reported.

Verifier rechecks it.

---

# 16. Goal Progress Estimation

Represent progress as:

\[
P_t \in [0,1]
\]

Example:

Goal:

> Find blue shoes under ₹5,000 and reach checkout.

Progress:

```text
Home                 0.00
Product catalogue    0.20
Blue filter applied  0.35
Valid product found  0.55
Added to cart        0.70
Checkout opened      0.90
Guest flow visible   1.00
```

The planner can generate subgoals:

```json
[
  "locate product catalogue",
  "identify valid product",
  "open product",
  "add to cart",
  "open checkout",
  "locate guest checkout"
]
```

---

# 17. Friction Scoring

This is one of PathLens' most important differentiators.

We should avoid:

> “The LLM says UX score = 6/10.”

Instead compute score from measurable events.

## Candidate formula

\[
F =
w_s S +
w_b B +
w_r R +
w_e E +
w_d D +
w_a A +
w_l L
\]

Where:

- \(S\) = excess step count,
- \(B\) = backtracks,
- \(R\) = repeated states,
- \(E\) = failed interactions,
- \(D\) = dead ends,
- \(A\) = accessibility penalties,
- \(L\) = latency/wait penalties.

Normalize to:

\[
F_{norm} = \min(100, F)
\]

---

## Suggested PoC weights

```text
Each unnecessary step:      +2
Backtrack:                   +5
Repeated state:              +6
Failed interaction:          +8
Dead end:                   +15
Critical accessibility bug: +15
Major accessibility bug:    +8
Minor accessibility bug:    +3
Long wait/timeout:           +5
```

These are heuristic.

Be honest:

> “The score is a transparent heuristic intended for relative comparison, not an industry standard.”

That honesty helps.

---

# 18. Path Efficiency

Given successful paths:

\[
P = \{p_1, p_2, ..., p_n\}
\]

Shortest discovered path:

\[
p^* = \arg\min_{p \in P}|p|
\]

For another path \(p\):

\[
ExcessSteps(p) = |p| - |p^*|
\]

This gives us objective evidence:

> “Category navigation required 4 more interactions than search.”

---

# 19. Accessibility Strategy

Accessibility has two layers.

## Layer A — Deterministic

Check:

- missing accessible names,
- missing labels,
- invalid ARIA,
- poor contrast where tool-supported,
- role violations,
- focusability,
- duplicate IDs,
- malformed headings.

---

## Layer B — Experiential

Run goal execution in restricted modes.

Examples:

### Keyboard-only mode

Allowed actions:

```text
Tab
Shift+Tab
Enter
Space
Arrow keys
Escape
typing
```

No mouse click.

Detect:

- unreachable controls,
- focus traps,
- illogical focus order,
- lost focus.

### Reduced-vision persona — future

Could reason from semantic labels and possibly altered visual conditions.

Do not overclaim.

---

# 20. Issue Verification Workflow

Every suspicious issue follows:

```text
Detect → Hypothesize → Reproduce → Challenge → Confirm → Report
```

Example:

### Detection

Button appears clickable but action produces no change.

### Hypothesis

“Continue button is non-responsive.”

### Verification

Retry once.

Then use keyboard Enter.

Then attempt same from clean state.

### Confirmed Issue

Only if failure is reproduced.

---

# 21. Evidence Model

Every action should generate a trace.

```json
{
  "step": 8,
  "timestamp": "2026-09-18T12:20:01",
  "state_id": "S7",
  "observation": "Cart contains one item",
  "decision": "Proceed to checkout",
  "action": {
    "type": "click",
    "target": "Checkout"
  },
  "result": {
    "success": true,
    "new_state": "S8"
  },
  "screenshot": "step_008.png"
}
```

This makes findings reproducible.

---

# 22. Replay

A confirmed path can be replayed through recorded semantic actions:

```text
1. Click "Shop"
2. Click "Running Shoes"
3. Click "AeroRun Blue"
4. Click "Add to cart"
5. Click "Checkout"
```

Avoid storing brittle CSS selectors as the main representation.

Store semantic target descriptors:

```json
{
  "role": "button",
  "name": "Checkout",
  "text": "Checkout"
}
```

If needed, use locators only as low-level execution details.

---

# 23. Regression Comparison

Given:

\[
G_A = (V_A,E_A)
\]

and

\[
G_B = (V_B,E_B)
\]

for the same goal.

Compare:

- goal completion,
- path length,
- friction score,
- failed actions,
- dead ends,
- accessibility findings,
- major state changes.

Regression delta:

\[
\Delta F = F_B - F_A
\]

If:

\[
\Delta F > T
\]

flag meaningful UX regression.

We do not need sophisticated graph matching for the hackathon.

Simple metric comparison is sufficient.

---

# 24. Suggested Technical Stack

## Frontend

Recommended:

```text
Next.js + React + Tailwind CSS
```

Why:

- fast UI iteration,
- easy dashboards,
- graph visualization libraries,
- polished live demo.

Alternative:

```text
Vite + React
```

if speed is more important.

---

## Backend

Recommended:

```text
Python + FastAPI
```

Why:

- excellent AI ecosystem,
- Playwright support,
- fast agent orchestration,
- clean WebSocket/SSE updates.

---

## Agent Orchestration

Recommended:

### Option A — Custom state machine

Best for hackathon control.

```text
planner()
observe()
choose_action()
execute()
verify()
update_graph()
```

This avoids unnecessary framework complexity.

### Option B — LangGraph

Use only if the team is already fast with it.

Graph:

```text
PLAN
 ↓
OBSERVE
 ↓
DECIDE
 ↓
ACT
 ↓
VERIFY
 ├── goal reached → REPORT
 ├── recoverable → OBSERVE
 └── issue → VERIFY_ISSUE
```

My recommendation:

> **Use a lightweight custom orchestrator unless LangGraph clearly saves time.**

---

## LLM

Pick one reliable model API already available to the team.

Requirements:

- strong structured output,
- good tool/action selection,
- reasonable visual reasoning if screenshots are supplied,
- fast latency.

Do not make the project's value depend on the brand name of the model.

Implement model wrapper:

```python
class ReasoningModel:
    def plan(...)
    def choose_action(...)
    def verify_goal(...)
```

This allows easy substitution.

---

## Browser

```text
Playwright Chromium
```

Optional:

```text
Chrome DevTools Protocol
```

---

## Accessibility

```text
axe-core / browser accessibility data
```

---

## Storage

MVP:

```text
SQLite + JSON trace files
```

or purely:

```text
JSON files
```

Session folder:

```text
runs/
  run_001/
    config.json
    graph.json
    trace.json
    screenshots/
    report.json
```

---

## Graph Visualization

Options:

- React Flow
- Cytoscape.js
- D3
- vis-network

Recommendation:

**React Flow** if the team already knows React.

---

## Live Updates

Use:

```text
Server-Sent Events
```

or WebSockets.

SSE is enough because most updates are backend → UI.

Events:

```text
run_started
state_discovered
action_started
action_completed
issue_found
graph_updated
metrics_updated
run_finished
```

---

# 25. Backend Modules

```text
backend/
│
├── api/
│   ├── runs.py
│   ├── reports.py
│   └── replay.py
│
├── agent/
│   ├── planner.py
│   ├── explorer.py
│   ├── verifier.py
│   └── prompts.py
│
├── browser/
│   ├── adapter.py
│   ├── observer.py
│   ├── action_executor.py
│   └── accessibility.py
│
├── exploration/
│   ├── controller.py
│   ├── state.py
│   ├── graph.py
│   ├── scoring.py
│   └── pathfinder.py
│
├── reporting/
│   ├── metrics.py
│   ├── findings.py
│   └── exporter.py
│
├── models/
│   └── schemas.py
│
└── main.py
```

---

# 26. Frontend Structure

```text
frontend/
│
├── app/
├── components/
│   ├── GoalForm.tsx
│   ├── BrowserPreview.tsx
│   ├── JourneyGraph.tsx
│   ├── LiveTrace.tsx
│   ├── MetricsPanel.tsx
│   ├── FindingCard.tsx
│   ├── ComparisonView.tsx
│   └── ReplayPanel.tsx
│
└── lib/
    ├── api.ts
    └── events.ts
```

---

# 27. Core Data Schemas

## Goal

```json
{
  "raw_text": "",
  "objective": "",
  "constraints": {},
  "success_signals": [],
  "forbidden_actions": []
}
```

## UI Element

```json
{
  "id": "e12",
  "role": "button",
  "name": "Add to cart",
  "text": "Add to cart",
  "visible": true,
  "enabled": true
}
```

## State

```json
{
  "id": "S4",
  "url": "",
  "title": "",
  "elements": [],
  "fingerprint": "",
  "screenshot": "",
  "goal_progress": 0.5
}
```

## Action

```json
{
  "type": "click",
  "target": {},
  "confidence": 0.82
}
```

## Finding

```json
{
  "id": "F3",
  "type": "dead_end",
  "severity": "high",
  "title": "",
  "description": "",
  "confirmed": true,
  "evidence_steps": []
}
```

---

# 28. API Endpoints

## Create run

```http
POST /api/runs
```

Request:

```json
{
  "url": "http://localhost:3000",
  "goal": "Reach guest checkout",
  "max_actions": 25
}
```

Response:

```json
{
  "run_id": "run_001"
}
```

---

## Run status

```http
GET /api/runs/{id}
```

---

## Live events

```http
GET /api/runs/{id}/events
```

SSE stream.

---

## Final report

```http
GET /api/runs/{id}/report
```

---

## Replay

```http
POST /api/runs/{id}/replay
```

---

## Compare

```http
POST /api/compare
```

---

# 29. Prompt Design

## Planner Prompt Concept

```text
You are converting a user-facing task into machine-checkable progress criteria.

Return:
- objective
- constraints
- ordered subgoals
- observable success signals
- forbidden actions

Never assume access to source code.
Do not create CSS selectors.
Use only things that could be observed through the interface.
```

---

## Explorer Prompt Concept

Input:

- goal,
- recent history,
- current state,
- available interactive elements,
- previously failed actions.

Instruction:

```text
Choose exactly one next action.

Prioritize:
1. progressing toward the goal,
2. novel unexplored states,
3. safe interactions,
4. avoiding repeated failed actions.

Return structured JSON only.
```

---

## Verifier Prompt Concept

```text
A suspected usability issue was detected.

Your task is to attempt to disprove it.

Suggest one safe alternative interaction that could make progress.

If no plausible alternative remains after the allowed retries,
mark the issue reproducible.
```

---

# 30. Guardrails

This is important because the agent interacts with real interfaces.

Never allow, without explicit permission:

- purchase completion,
- financial transaction,
- destructive deletion,
- account closure,
- sending messages,
- form submission with sensitive information.

Goal Planner creates forbidden actions.

Action Executor checks every proposed action.

```text
Agent Action
    ↓
Safety Gate
    ├── allowed → execute
    └── blocked → report + replan
```

For hackathon demos use safe local/mock websites.

---

# 31. Test Application Strategy

Do NOT rely entirely on a random public website.

Prepare one local test website intentionally containing known UX problems.

This makes the live demo reliable.

## Demo app scenario

Simple e-commerce app.

Pages:

```text
Home
Products
Product Details
Cart
Checkout
```

Intentional Version A:

- clean guest checkout,
- logical navigation,
- correct labels.

Intentional Version B:

- modal appears before checkout,
- ambiguous “Continue” button,
- one broken/hidden guest link,
- keyboard focus trap,
- extra navigation path,
- missing accessible label.

PathLens should discover these differences.

This gives us a deterministic demo while still allowing a second test on an unfamiliar external/local app.

---

# 32. Demo App Requirements

Version A:

```text
Home → Products → Product → Cart → Checkout → Guest
```

Version B:

```text
Home → Products → Product → Cart
                             ↓
                      Promotional Modal
                             ↓
                         Login Page
                           /     \
                    Hidden guest   Sign in
```

Add at least:

- one dead-end branch,
- one redundant path,
- one missing label,
- one focus issue,
- one failed interaction.

---

# 33. Success Metrics

The hackathon PoC should demonstrate:

### Functional

- agent completes goal autonomously,
- no predefined step sequence,
- at least one recovery/replanning event.

### Exploration

- at least 2 paths discovered,
- at least 1 repeated state or alternate branch identified.

### UX

- friction score produced from trace events.

### Accessibility

- at least 2 accessibility findings.

### Verification

- at least 1 finding replayed/confirmed.

### Reporting

- screenshot-backed final report.

### Regression

Ideal:

- clear metric difference between v1 and v2.

---

# 34. Suggested Demo Story

This should be rehearsed word-for-word.

## Opening — 15 seconds

> “Traditional E2E testing checks whether a scripted path works. But users are not scripts. PathLens receives only a human goal and explores the application as a first-time user.”

---

## Step 1

Goal:

```text
Find a blue running shoe under ₹5,000 and reach guest checkout.
```

Click:

**Start Exploration**

---

## Step 2

The browser begins moving.

The dashboard displays:

```text
State S1 discovered
Action: Open Products
Reason: likely route toward product search
```

Journey graph grows live.

---

## Step 3

Agent tries a path that reaches a dead end.

Show:

```text
Suspected dead end
Verifier running...
```

Verifier retries.

Then:

```text
Dead end confirmed
```

---

## Step 4

Agent backtracks and reaches checkout.

Result:

```text
GOAL ACHIEVED
```

Show:

- path length,
- screenshots,
- friction score,
- issue list.

---

## Step 5 — killer moment

Click:

**Compare with Version B**

Run same intent.

Output:

```text
Version A friction: 18
Version B friction: 47

+4 interactions
+1 dead end
+2 failed actions
+3 accessibility issues
```

Then explain:

> “Both versions technically pass a normal functional requirement. PathLens reveals that the user experience regressed.”

That is the core punchline.

---

# 35. Judge Questions We Must Be Ready For

## “Is this just Playwright?”

Answer:

> Playwright is our execution layer. It gives the agent hands. PathLens provides the reasoning, state representation, multi-path exploration, friction metrics, verification, and regression intelligence.

---

## “Why do you need an LLM?”

Answer:

> A fixed script already knows the exact path. Our system receives only the intent and an unfamiliar UI. The model must interpret the interface, decide which action is relevant, recover when assumptions fail, and explore alternatives.

---

## “How is this different from generated test cases?”

Answer:

> Generated tests generally convert a specification into a deterministic script. PathLens explores an unknown state space first, discovers paths and friction, and only then can produce replayable traces.

---

## “How do you avoid hallucinated bugs?”

Answer:

> The model can propose a suspected issue, but reports are evidence-based. We record state transitions and screenshots, and important findings go through a verifier that attempts to reproduce or disprove them.

---

## “How is friction calculated?”

Answer:

> We use transparent trace-derived penalties such as excess steps, backtracking, repeated states, failed interactions, dead ends, waits, and accessibility violations. The score is heuristic but deterministic and comparable across versions.

---

## “Does this replace accessibility experts?”

Answer:

> No. It automates repeatable checks and goal-oriented interaction traces. It is an assistive testing tool, not a claim of complete accessibility certification.

---

## “Is it truly black box?”

Answer:

> The agent does not require application source code, custom SDKs, or internal test hooks. It interacts through standard browser-visible and accessibility information.

---

## “Would this work on mobile?”

Answer:

> The core is platform-agnostic. The browser adapter can later be replaced with native drivers such as Android/iOS automation adapters while reusing the planner, exploration graph, verifier, metrics, and reporting layers.

---

# 36. Risks and Mitigations

## Risk 1 — Agent gets lost

Mitigation:

- action budget,
- visited-state memory,
- repeated-action penalty,
- backtracking,
- max retries.

---

## Risk 2 — Model returns invalid action

Mitigation:

- structured JSON schema,
- validate action,
- retry with error context.

---

## Risk 3 — Dynamic websites break state comparison

Mitigation:

Ignore:

- ads,
- timestamps,
- random IDs,
- animated values.

Fingerprint stable semantic structure.

---

## Risk 4 — Live model/API latency

Mitigation:

- compact semantic page representation,
- send screenshot only when necessary,
- cache state analysis,
- stream progress.

---

## Risk 5 — Demo internet failure

Mitigation:

- local target app,
- local screenshots/traces from prior runs,
- cached report available as fallback.

Prefer an online LLM only if network is stable.

---

## Risk 6 — Too much frontend polish too early

Mitigation:

Do backend exploration first.

Milestone:

```text
CLI can autonomously complete one goal.
```

Only then build dashboard.

---

# 37. Priority Ladder

## P0 — absolutely required

- Goal → plan
- Browser observation
- Agent chooses actions
- Playwright executes actions
- State memory
- Goal detection
- Basic trace
- Final result

Without this there is no project.

---

## P1 — required for strong judging

- Journey graph
- friction scoring
- screenshots
- accessibility scan
- one verifier loop
- polished dashboard

---

## P2 — podium differentiator

- multi-path exploration
- version comparison
- replay
- keyboard-only mode

---

## P3 — only if everything else works

- automatic exported Playwright test
- mobile adapter
- persona simulation
- CI integration
- LLM-generated recommendations.

---

# 38. Development Order

## Phase 1 — prove autonomous navigation

Build CLI.

Hard target:

```text
python run.py \
  --url http://localhost:3000 \
  --goal "Reach guest checkout"
```

Success means agent reaches target without predefined path.

---

## Phase 2 — state tracking

Add:

- state fingerprints,
- visited-state set,
- action log,
- loop detection.

---

## Phase 3 — journey graph

Persist:

```text
nodes
edges
successful paths
```

---

## Phase 4 — metrics

Implement:

- step count,
- failed actions,
- repeats,
- backtracks,
- dead ends,
- friction score.

---

## Phase 5 — accessibility

Integrate automated checks.

Add keyboard-only experiment if feasible.

---

## Phase 6 — frontend

Build:

- input screen,
- run status,
- live trace,
- graph,
- result cards.

---

## Phase 7 — regression mode

Run goal against A and B.

Compare metrics.

---

## Phase 8 — polish

- animations,
- screenshots,
- icons,
- final report,
- demo flow,
- fallback data.

---

# 39. Today / Tomorrow Execution Plan

The hackathon instructions mean the initial design is submitted in advance, while the checkpoint requires development of a new feature tomorrow before lunch.

Therefore the architecture must stay modular.

## TODAY — Design + Core Preparation

### Hour 1

Lock:

- project name,
- architecture,
- feature scope,
- team responsibilities,
- repo structure.

### Hour 2–3

Build target demo app Version A and Version B.

### Hour 2–5 in parallel

Backend team:

- Playwright observation,
- semantic element extraction,
- action executor.

### Hour 4–6

Agent:

- planner,
- explorer loop,
- structured output.

### Hour 5–7

State graph + logging.

### Hour 6–8

Frontend dashboard skeleton.

### End of day

Must have:

```text
Goal → autonomous navigation → evidence trace
```

Even if UI is ugly.

---

## TOMORROW MORNING

### First priority

Make the supplied checkpoint feature work.

Do not sacrifice the entire system to over-polish our planned extras.

### Parallel team split

Person A:
checkpoint feature

Person B:
stabilize agent/browser loop

Person C:
dashboard/report

Person D:
demo/test/backup/presentation

---

# 40. Checkpoint-Proof Architecture

Tomorrow they may ask for a new feature.

Likely categories:

## “Support keyboard-only navigation”

Add new action adapter.

No architecture rewrite.

---

## “Support mobile”

Add:

```text
BrowserAdapter
MobileAdapter
```

same exploration engine.

---

## “Generate test scripts”

Convert successful replay trace → Playwright script.

---

## “Support personas”

Planner receives persona config.

Example:

```json
{
  "technical_skill": "low",
  "interaction_mode": "keyboard"
}
```

---

## “Add comparison”

Already planned.

---

## “Export issue reports”

Reporter converts findings to JSON/Markdown.

---

## “Add another accessibility metric”

Accessibility Analyzer module.

---

# 41. Team Role Split

Adjust based on actual team.

## Person 1 — Agent/Backend Lead

Own:

- planner,
- explorer,
- verifier,
- orchestration.

## Person 2 — Browser/Systems Lead

Own:

- Playwright,
- UI observation,
- action execution,
- state extraction,
- accessibility.

## Person 3 — Frontend Lead

Own:

- dashboard,
- graph,
- live trace,
- metrics,
- report UI.

## Person 4 — Product/Integration Lead

Own:

- demo app,
- testing,
- integration,
- documentation,
- submission,
- presentation.

If 3 people:

combine Person 1 + Person 2 strategically.

---

# 42. Git Strategy

Branches:

```text
main
agent-core
browser-engine
frontend
demo-app
```

Do NOT let everybody edit same files.

Merge frequently.

Commit milestones:

```text
feat: browser observation
feat: goal planner
feat: autonomous action loop
feat: journey graph
feat: friction score
feat: live dashboard
feat: regression comparison
```

---

# 43. README Story

README should immediately contain:

1. problem,
2. what PathLens does,
3. architecture diagram,
4. 30-second demo GIF,
5. quick start,
6. example report,
7. limitations.

Avoid a huge framework-logo wall.

---

# 44. UI Style

Professional developer-tool aesthetic.

Recommended:

- clean white/dark neutral UI,
- 1 main accent color,
- status colors only for severity,
- monospaced traces,
- modern but restrained cards.

Core screens:

```text
New Run
Live Exploration
Run Report
Version Comparison
Replay
```

---

# 45. Report Structure

Example:

```text
PathLens Audit Report
─────────────────────

Goal
Find a blue running shoe under ₹5,000 and reach guest checkout.

Result
✓ Goal achieved

Exploration
States discovered: 14
Actions executed: 19
Successful paths: 2
Dead ends: 1

UX
Shortest path: 7 actions
Alternative path: 11 actions
Backtracks: 2
Failed actions: 1
Friction score: 36/100

Accessibility
High: 1
Medium: 2
Low: 3

Confirmed Findings
1. Guest checkout link is difficult to discover.
2. Promotional modal traps keyboard focus.
3. Category path requires 4 unnecessary actions.
```

---

# 46. Severity Classification

Simple deterministic severity mapping.

## Critical

Goal impossible.

Examples:

- checkout cannot be reached,
- keyboard user fully blocked.

## High

Major workflow obstruction.

Example:

- dead-end navigation branch,
- inaccessible primary control.

## Medium

Significant extra friction.

Example:

- unnecessary steps,
- unclear navigation.

## Low

Minor usability/accessibility issue.

---

# 47. Honest Limitations

State these if asked.

- UX quality is partly subjective.
- Friction score is our heuristic, not an accepted standard.
- semantic state fingerprinting can struggle with highly dynamic pages.
- model navigation is slower than deterministic test scripts.
- accessibility automation cannot replace expert/manual assessment.
- current PoC focuses on browser applications.
- very complex authentication/payment flows are outside demo scope.

These limitations make us sound credible, not weaker.

---

# 48. What We Want Judges to Remember

Not:

> “They used Playwright.”

Not:

> “They used an LLM.”

Not:

> “They had five agents.”

They should remember:

> **“That team gave an AI only a user goal, and it autonomously mapped different paths through an app and proved the new version was harder to use.”**

That is the mental hook.

---

# 49. Optional Killer Feature — Automatic Test Generation

After discovering a successful path:

```text
User intent
    ↓
Agent exploration
    ↓
Validated semantic trajectory
    ↓
Generate deterministic regression test
```

Example output:

```ts
test('guest checkout flow', async ({ page }) => {
  await page.goto('...');
  await page.getByRole('link', { name: 'Products' }).click();
  await page.getByText('AeroRun Blue').click();
  await page.getByRole('button', { name: 'Add to cart' }).click();
  await page.getByRole('button', { name: 'Checkout' }).click();
  await expect(page.getByText('Guest Checkout')).toBeVisible();
});
```

This creates a beautiful story:

> The agent explores once.  
> Then it can convert a discovered path into a stable automated regression test.

Only implement if core system is solid.

---

# 50. Optional Killer Feature — Persona Testing

Provide persona:

```text
First-time user
Keyboard-only user
Low-technical-confidence user
Power user
```

Persona affects:

- allowed actions,
- exploration preference,
- friction sensitivity.

Do not claim simulation perfectly represents actual humans.

---

# 51. Potential Project Names

Preferred:

## PathLens

Strong because:

- path exploration,
- inspection,
- developer-tool feel,
- short and memorable.

Alternatives:

- FlowScout
- TraceUX
- JourneyLens
- UXProbe
- PathProbe
- FlowLens
- AgentUX
- BlackPath

My choice remains:

# PathLens

---

# 52. Tagline Options

Best:

> **Give it a goal. Watch it experience your product like a user.**

Alternatives:

> **Test journeys, not selectors.**

> **Your users don't follow scripts. Neither should your tester.**

> **Autonomous UX exploration for real user journeys.**

For presentation:

## **PathLens — Test journeys, not selectors.**

is extremely strong.

---

# 53. Submission Positioning

When filling the official `.md`, emphasize:

### Problem

Traditional testing validates known paths, not how users discover and experience them.

### Agentic Need

Unknown UI + unknown route + failures + alternative exploration requires continuous planning.

### Current Build

Be exact.

Do not claim mobile if only web works.

### Future Scope

Choose checkpoint-friendly features:

1. Native mobile adapter
2. CI-generated replay tests
3. Persona/accessibility modes

---

# 54. Architecture Narrative for Judges

Use this explanation:

> “We separate reasoning from execution. Playwright is only the actuator. The agent sees a semantic representation of the visible application, chooses an action from available controls, executes it, and checks whether the world actually changed. Every state and action enters a journey graph. That graph lets us detect repetition, alternate paths and dead ends. Findings are measured from trace events and verified before reporting.”

This is short, technical, and defensible.

---

# 55. Why This Can Place Top 3

PathLens combines several properties that are unusually strong together:

### Clear problem

Everyone understands brittle testing and confusing UI.

### Visible autonomy

Judges can literally watch the agent act.

### Technical depth

There is non-trivial:

- planning,
- state representation,
- graph exploration,
- scoring,
- accessibility,
- verification.

### Objective metrics

Not just “AI said this page is bad.”

### Great demo theatre

Browser + graph + live trace + regression comparison.

### Honest scope

A small web PoC can already demonstrate the full idea.

### Extensible architecture

Good for the checkpoint surprise.

---

# 56. Failure Recovery Logic

Pseudo-flow:

```python
while steps < budget:

    state = observe()

    if goal_reached(state):
        mark_success()
        break

    if seen_many_times(state):
        action = choose_backtrack_or_branch()
    else:
        action = explorer.choose_action(
            state=state,
            goal=goal,
            history=history,
            unexplored=unexplored_actions
        )

    if unsafe(action):
        block(action)
        continue

    result = execute(action)

    if not result.success:
        record_failure(action)
        penalize(action)
        continue

    new_state = observe()

    update_graph(state, action, new_state)
    update_metrics()

    if suspected_issue():
        queue_for_verification()
```

---

# 57. Multi-Path Algorithm

After first success:

```python
success_path = shortest_success_path()

branch_points = states_with_untried_actions(success_path)

for branch in branch_points:
    restore_or_replay_to(branch)
    try_best_unexplored_action(branch)

    continue_exploration_until:
        goal reached
        or dead end
        or budget exhausted
```

For PoC, replay from home to branch point is easier than arbitrary state restoration.

---

# 58. Screenshot Strategy

Capture screenshot:

- before each action if cheap,
- after meaningful state transition,
- on every failure,
- on every reported issue.

File naming:

```text
run_001/
screenshots/
  001_home.png
  002_products.png
  003_product.png
  004_failed_checkout.png
```

---

# 59. Model Cost/Latency Strategy

Do not send full raw DOM.

Instead send compact representation:

```text
URL: /products
Title: Products

Visible controls:
[1] textbox "Search products"
[2] button "Search"
[3] link "Running Shoes"
[4] link "Casual Shoes"
[5] button "Cart (0)"
```

This improves:

- cost,
- latency,
- reliability.

Screenshot can be used only when semantic information is insufficient.

---

# 60. Action Targeting Strategy

Priority:

1. role + accessible name
2. visible text
3. stable DOM semantics
4. coordinates as fallback.

Example:

```python
page.get_by_role("button", name="Checkout")
```

preferred over:

```python
page.locator("#checkout-btn-v2")
```

because semantic targeting fits the black-box philosophy.

---

# 61. Goal Verification

Never trust the explorer's own claim alone.

Use a separate goal check.

Input:

- target goal criteria,
- current page semantic representation.

Return:

```json
{
  "achieved": true,
  "confidence": 0.93,
  "matched_signals": [
    "Guest checkout visible",
    "Checkout page active"
  ]
}
```

For reliable demos, add deterministic rules where possible.

---

# 62. Production Vision

At production scale PathLens could run in CI:

```text
New pull request
      ↓
Deploy preview
      ↓
PathLens executes critical user intents
      ↓
Compare against baseline
      ↓
UX regression found?
      ├─ No → pass
      └─ Yes → attach report to PR
```

Example report:

```text
PR #1842 introduces:
+3 checkout interactions
1 new keyboard focus trap
1 previously valid path now blocked
```

That is the enterprise/dev-tool story.

---

# 63. Future Scope

## Native mobile exploration

Adapters:

```text
Android → ADB / accessibility
iOS → simulator accessibility
```

Reuse:

- planner,
- graph,
- scoring,
- verifier,
- reporter.

---

## CI integration

GitHub/GitLab PR analysis.

---

## Crowd-derived baselines

Compare friction against historical runs.

---

## Learning from repeated runs

Identify recurring high-friction states.

---

## Automatic bug ticket generation

Produce Jira/GitHub issue with:

- evidence,
- severity,
- replay sequence,
- screenshots.

---

# 64. Presentation Slide Plan

If presentation is required:

## Slide 1 — Problem

**Users don't follow scripts. Testing tools do.**

Visual:

```text
Traditional Test:
A → B → C → D

Real User:
A → C → B → ? → E → A → D
```

---

## Slide 2 — Solution

PathLens:

```text
Natural Language Goal
       ↓
Autonomous Exploration
       ↓
Journey Graph
       ↓
Friction + Accessibility
       ↓
Verified Report
```

---

## Slide 3 — Architecture

Use the architecture from Section 8.

---

## Slide 4 — Core Innovation

Three blocks:

- Intent-driven exploration
- Journey graph + friction metrics
- Verified UX regression detection

---

## Slide 5 — Demo / Results

Version comparison table.

---

# 65. Final Build Checklist

## Core

- [ ] Repository created
- [ ] Target demo app created
- [ ] Browser launches
- [ ] URL loads
- [ ] Semantic controls extracted
- [ ] Goal planner returns valid JSON
- [ ] Explorer chooses valid action
- [ ] Action executor works
- [ ] State changes detected
- [ ] Goal completion works
- [ ] Trace stored

## Journey Intelligence

- [ ] State fingerprint
- [ ] Graph nodes
- [ ] Graph edges
- [ ] Loop detection
- [ ] Dead-end detection
- [ ] Alternate path attempt
- [ ] Shortest path

## UX Metrics

- [ ] Failed actions
- [ ] Repeats
- [ ] Backtracks
- [ ] Dead ends
- [ ] Friction score

## Accessibility

- [ ] Automated scan
- [ ] Findings surfaced
- [ ] Keyboard check if possible

## Verification

- [ ] Suspected issue queue
- [ ] Retry/reproduce
- [ ] Evidence attached

## Frontend

- [ ] Goal input
- [ ] Live browser preview or screenshots
- [ ] Trace
- [ ] Journey graph
- [ ] Metrics
- [ ] Findings cards
- [ ] Final report
- [ ] Compare screen

## Demo Safety

- [ ] Local demo runs offline
- [ ] Backup screenshots
- [ ] Backup saved trace
- [ ] Backup recorded demo
- [ ] API key tested
- [ ] Internet contingency

## Submission

- [ ] Official `.md` filled
- [ ] Character limits checked
- [ ] No fake claims
- [ ] Repo link inserted
- [ ] Architecture link inserted
- [ ] Team details correct
- [ ] File name lowercase/no spaces

---

# 66. Definition of Done

We do NOT need every future feature.

The project is strong enough when a judge can watch this happen:

1. We enter an unfamiliar application URL.
2. We provide only a natural-language goal.
3. PathLens autonomously navigates.
4. It encounters at least one failure or alternate route.
5. It remembers and changes strategy.
6. It reaches the goal.
7. It displays the journey graph.
8. It reports measurable friction.
9. It identifies at least one accessibility issue.
10. It provides evidence.
11. Ideally, it compares two versions and proves a UX regression.

If those eleven points work smoothly, stop adding random features and polish the experience.

---

# 67. Final Winning Narrative

The entire project should be explainable in four sentences:

> Traditional UI testing verifies paths developers already know. PathLens starts with only a human intent and explores an unfamiliar interface as a user would, continuously deciding what to do next. It builds a graph of discovered journeys, measures friction and accessibility barriers, and verifies suspected problems with replayable evidence. By running the same intent against two application versions, it can show when software remains technically functional but becomes meaningfully harder to use.

That is the project.

---

# 68. Immediate Next Actions

## Do these now

1. **Lock the name: PathLens.**
2. Create a monorepo.
3. Create the simple Version A / Version B e-commerce test app.
4. Build Playwright semantic observation.
5. Build the planner + explorer JSON contract.
6. Make one complete autonomous run from goal → success.
7. Add graph state.
8. Add live dashboard.
9. Add friction metrics.
10. Add accessibility scan.
11. Add verifier.
12. Add version comparison.
13. Rehearse the exact demo.
14. Fill the official hackathon `.md` only with functionality that is actually working or explicitly marked planned.

---

# 69. Recommended Repository Layout

```text
pathlens/
├── README.md
├── docker-compose.yml
├── apps/
│   ├── dashboard/
│   ├── demo-v1/
│   └── demo-v2/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agent/
│   │   ├── browser/
│   │   ├── exploration/
│   │   ├── reporting/
│   │   └── models/
│   ├── tests/
│   └── requirements.txt
├── runs/
├── docs/
│   ├── architecture.md
│   ├── demo-script.md
│   └── submission.md
└── scripts/
```

---

# 70. One Final Rule

**Do not optimize for the largest architecture diagram. Optimize for the cleanest undeniable demo.**

A smaller PathLens that autonomously explores one application, discovers a real alternate path, proves one usability regression and explains the evidence is substantially stronger than a gigantic multi-platform architecture where half the components are mocked.

The goal is not to show how many AI buzzwords we know.

The goal is to make the judges think:

> **“Wait — normal automated testing doesn't do that.”**

That is the moment we are building for.
