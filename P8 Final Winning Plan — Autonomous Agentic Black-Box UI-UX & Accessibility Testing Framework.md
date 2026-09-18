    # P8 FINAL WINNING PLAN
## Autonomous Agentic Black-Box UI/UX & Accessibility Testing Framework

### Objective

Build a stage-reliable autonomous synthetic user that receives only a natural-language goal, explores a web application strictly as a black box, detects usability friction and accessibility defects, autonomously recovers from unexpected UI states, remembers facts across the user journey, identifies cross-screen inconsistencies, and produces an evidence-backed visual audit.

The project is NOT:

- an AI wrapper around Playwright;
- an axe-core dashboard;
- an LLM generating selectors;
- a scripted Selenium replacement;
- a generic website crawler.

The winning one-line pitch is:

> **Traditional QA tests whether software works. We test whether the experience works for a human.**

The core differentiator is:

> **Give the system a goal, not a test script.**

---

# 1. WINNING DEMO STORY

The golden demo uses one deterministic local e-commerce SPA.

User enters only:

> **“Find the Nova headphones under ₹3,000, add them to cart, and reach checkout.”**

The system then autonomously:

```text
Natural-language goal
        ↓
Observe screenshot + ARIA tree
        ↓
Discover available controls
        ↓
Search for Nova headphones
        ↓
Open product
        ↓
Observe price: ₹2,499
        ↓
Store structured journey fact
        ↓
Add product to cart
        ↓
Cart shows ₹2,799
        ↓
AI extracts price
        ↓
Python compares journey facts
        ↓
⚠ SEMANTIC INCONSISTENCY
Price changed ₹2,499 → ₹2,799
        ↓
Agent attempts Checkout
        ↓
Promotional modal unexpectedly opens
        ↓
⚠ UX FRICTION
Primary journey interrupted
        ↓
Agent closes modal autonomously
        ↓
Retries Checkout
        ↓
Reaches checkout
        ↓
Deterministic completion verifier confirms:
- URL = #/checkout
- email field visible
        ↓
axe-core audit
        ↓
⚠ Missing accessible label
⚠ Low-contrast primary CTA
        ↓
MISSION COMPLETE
        ↓
Journey Graph + Scorecard + Audit Report
```

This proves four separate layers of intelligence:

```text
Playwright
→ Can the system operate the product?

Vision / LLM
→ Can the system understand what a user sees?

Journey Memory
→ Can it reason across multiple UI states?

axe-core
→ Does the interface violate deterministic accessibility rules?
```

---

# 2. STRICT MVP

Build exactly four core capabilities.

## Core Feature 1 — Autonomous black-box navigation

Input:

```text
Find the Nova headphones under ₹3,000,
add them to cart,
and reach checkout.
```

Allowed browser actions:

```text
CLICK
TYPE
SCROLL
BACK
WAIT
DONE
```

The LLM NEVER writes CSS selectors.

The LLM NEVER receives application source code.

The LLM NEVER receives a pre-scripted action sequence.

Maximum live mission:

```text
12 steps
```

Ideal:

```text
6–9 reasoning loops
```

---

## Core Feature 2 — Autonomous friction detection + recovery

The Checkout flow intentionally produces an unexpected promotional modal.

Important:

The modal MUST NOT appear based on a timer.

It appears deterministically on the first Checkout action.

Flow:

```text
Cart visible
    ↓
Agent chooses Checkout
    ↓
Checkout action triggers promotional modal
    ↓
URL remains #/cart
    ↓
Goal has not progressed
    ↓
Agent observes blocking modal
    ↓
Critic classifies:
Primary-flow obstruction
    ↓
Agent closes modal
    ↓
Agent retries checkout
    ↓
Success
```

The key demo line:

> “The click technically worked, but the user's intended outcome didn't. The agent detected that difference and recovered.”

That is much stronger than deliberately causing a Playwright error.

---

## Core Feature 3 — Cross-screen semantic inconsistency

Product page:

```text
Nova Headphones
₹2,499
```

Cart:

```text
Nova Headphones
₹2,799
```

axe-core cannot detect this.

The LLM extracts structured facts from every screen:

```json
{
  "kind": "product_price",
  "entity": "Nova Headphones",
  "value": 2499,
  "currency": "INR"
}
```

Python stores and compares those facts.

Result:

```text
HIGH SEVERITY

Price inconsistency detected

Product:
Nova Headphones

Product page:
₹2,499

Cart:
₹2,799

Difference:
₹300
+12.0%
```

This is the strongest defense against:

> “Axe found everything. What exactly did the AI do?”

Answer:

> “Axe detects standards violations. The AI interprets user-visible information across screens, while deterministic journey logic verifies inconsistencies.”

---

## Core Feature 4 — Accessibility audit + evidence-backed journey graph

Final checkout contains:

1. Unlabelled email input.
2. Deliberately low-contrast Pay button.

axe-core reports both.

Dashboard shows:

```text
AUTOMATED ACCESSIBILITY RISK SCORE
72 / 100

2 serious findings
0 critical findings
```

Do NOT call this a WCAG compliance score.

Use:

> **Automated Accessibility Risk Score**

Include disclaimer:

> Automated heuristic based on detected accessibility violations; not a WCAG certification.

---

# 3. ANTI-GOALS

Do NOT build:

```text
✗ Android support
✗ iOS support
✗ Firefox
✗ Safari
✗ cross-browser testing
✗ full WCAG certification
✗ source-code repair
✗ GitHub automation
✗ CI/CD integration
✗ production authentication
✗ user accounts
✗ database infrastructure
✗ arbitrary web crawling
✗ distributed agents
✗ giant multi-agent architecture
✗ OCR pipeline
✗ browser extension
✗ ML training
✗ pixel-diff regression engine
✗ exhaustive multi-path exploration
✗ historical analytics platform
```

Every feature must pass one rule:

> **Does this make the three-minute live demo stronger?**

If not, skip it.

---

# 4. FINAL TECH STACK

## LangGraph

Purpose:

```text
state
closed-loop execution
conditional transitions
recovery
step budget
termination
```

Why:

Easy state-machine orchestration without custom agent infrastructure.

---

## Playwright Python Async

Purpose:

```text
browser execution
screenshots
keyboard/mouse
ARIA snapshot
visible element inspection
persistent Chromium session
```

Why:

Reliable Chromium automation with one API surface.

---

## axe-core

Purpose:

```text
deterministic accessibility violations
structured evidence
severity
affected nodes
```

Why:

Do not use an LLM to invent accessibility violations that deterministic tooling can test.

---

## Multimodal LLM

Purpose:

```text
screen understanding
goal planning
next-action selection
structured fact extraction
UX critique
recovery reasoning
```

Use ONE reasoning call per loop.

Do NOT create:

```text
Planner LLM
Vision LLM
Critic LLM
Recovery LLM
Report LLM
```

That wastes latency.

One model call should return:

```text
observation
goal progress
structured facts
friction findings
next browser action
```

Benchmark the event-approved/current candidate models against the actual demo workflow during Hour 0–2.

Choose based on:

```text
1. valid structured-output rate
2. action accuracy
3. P95 latency
```

Do not choose based on benchmark reputation alone.

---

## FastAPI

Purpose:

```text
REST API
WebSocket streaming
run orchestration
audit export
health endpoint
```

---

## WebSockets

Purpose:

Stream:

```text
browser frames
actions
findings
journey nodes
journey edges
scores
run status
```

---

## React + Tailwind

Purpose:

Fast polished dashboard.

---

## React Flow

Purpose:

Live journey graph.

---

## JSONL + local filesystem

No database.

Use:

```text
JSONL → replay event stream
filesystem → screenshots + audit artifacts
```

---

# 5. REPOSITORY STRUCTURE

```text
p8-agent/
│
├── backend/
│   ├── agent/
│   │   ├── graph.py
│   │   ├── models.py
│   │   ├── planner.py
│   │   ├── critic.py
│   │   ├── memory.py
│   │   └── completion.py
│   │
│   ├── runtime/
│   │   ├── browser.py
│   │   ├── registry.py
│   │   ├── executor.py
│   │   ├── observer.py
│   │   ├── accessibility.py
│   │   └── actions.py
│   │
│   ├── api/
│   │   ├── app.py
│   │   ├── websocket.py
│   │   ├── health.py
│   │   └── report.py
│   │
│   └── vendor/
│       └── axe.min.js
│
├── frontend/
│   └── React dashboard
│
├── demo_app/
│   └── index.html
│
├── artifacts/
│   └── run_<id>/
│       ├── step_01.jpg
│       ├── step_02.jpg
│       └── ...
│
├── replay_runs/
│   ├── golden.jsonl
│   └── golden/
│       ├── 001.jpg
│       └── ...
│
├── contracts/
│   └── websocket.md
│
├── requirements.txt
└── README.md
```

Ownership:

```text
Engineer A
backend/agent/

Engineer B
backend/runtime/
demo_app/

Engineer C
frontend/
backend/api/websocket.py

Engineer D, if available
replay_runs/
QA
demo rehearsal
integration support
```

This prevents merge conflicts.

---

# 6. LANGGRAPH ARCHITECTURE

```text
                         USER GOAL
                             │
                             ▼
                    ┌────────────────┐
                    │ Planner/Critic │
                    │      LLM       │
                    └───────┬────────┘
                            │
                    structured action
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Playwright Executor │
                 └─────────┬───────────┘
                           │
                           ▼
                  TARGET BLACK-BOX APP
                           │
                           ▼
                  ┌──────────────────┐
                  │   Observation    │
                  │ screenshot       │
                  │ ARIA snapshot    │
                  │ controls         │
                  │ axe results      │
                  └────────┬─────────┘
                           │
                           ▼
                    LLM Planner/Critic
                           │
                  ┌────────┴─────────┐
                  │                  │
                  ▼                  ▼
           Journey Facts      UX Findings
                  │                  │
                  └────────┬─────────┘
                           ▼
                 Journey Graph Memory
                           │
                 deterministic checks
                           │
             ┌─────────────┴────────────┐
             │                          │
           CONTINUE                   DONE
             │                          │
             └──── Planner             ▼
                                FINAL AUDIT
```

LangGraph:

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(GraphState)

graph.add_node("plan", planner_node)
graph.add_node("execute", execution_node)
graph.add_node("observe", observation_node)
graph.add_node("analyse", analysis_node)
graph.add_node("memory", memory_node)
graph.add_node("verify", verification_node)

graph.set_entry_point("plan")

graph.add_edge("plan", "execute")
graph.add_edge("execute", "observe")
graph.add_edge("observe", "analyse")
graph.add_edge("analyse", "memory")
graph.add_edge("memory", "verify")

graph.add_conditional_edges(
    "verify",
    route_after_verify,
    {
        "continue": "plan",
        "completed": END,
        "failed": END
    }
)

agent = graph.compile()
```

---

# 7. CORE STATE MODEL

```python
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now():
    return datetime.now(timezone.utc)


class RunStatus(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    ANALYSING = "analysing"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    BACK = "back"
    WAIT = "wait"
    DONE = "done"


class ObservedElement(BaseModel):
    element_id: int

    role: str | None = None
    name: str | None = None
    text: str | None = None
    placeholder: str | None = None

    disabled: bool = False

    bbox: dict[str, float] | None = None


class BrowserAction(BaseModel):
    observation_id: str

    action: ActionType

    element_id: int | None = None

    display_label: str | None = None

    text: str | None = None

    direction: Literal["up", "down"] | None = None

    rationale: str = Field(max_length=220)

    confidence: float = Field(ge=0.0, le=1.0)


class ExecutionStep(BaseModel):
    step_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    step_number: int

    timestamp: datetime = Field(
        default_factory=utc_now
    )

    url_before: str

    url_after: str | None = None

    action: BrowserAction

    outcome: Literal[
        "success",
        "stale",
        "blocked",
        "failed"
    ]

    duration_ms: int = 0

    error: str | None = None

    screenshot_id: str | None = None


class AxeNode(BaseModel):
    html: str | None = None

    target: list[str] = Field(
        default_factory=list
    )

    failure_summary: str | None = None


class AxeViolation(BaseModel):
    id: str

    impact: Literal[
        "minor",
        "moderate",
        "serious",
        "critical"
    ] | None = None

    description: str

    help: str

    help_url: str | None = None

    nodes: list[AxeNode] = Field(
        default_factory=list
    )


class CriticFinding(BaseModel):
    finding_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    category: Literal[
        "friction",
        "accessibility",
        "semantic_inconsistency",
        "dead_end",
        "occlusion",
        "ambiguity",
        "recovery",
        "goal_progress"
    ]

    severity: Literal[
        "info",
        "low",
        "medium",
        "high",
        "critical"
    ]

    title: str

    evidence: str

    recommendation: str | None = None

    step_number: int

    screenshot_id: str | None = None


class PageFact(BaseModel):
    kind: Literal[
        "product_price",
        "page_heading",
        "cart_total"
    ]

    entity: str

    value: str | float

    step_number: int

    url: str


class JourneyNode(BaseModel):
    id: str

    label: str

    url: str

    step_number: int

    page_type: str | None = None

    screenshot_id: str | None = None

    friction_count: int = 0

    accessibility_count: int = 0


class JourneyEdge(BaseModel):
    id: str

    source: str

    target: str

    action: str

    duration_ms: int

    recovered: bool = False


class AgentState(BaseModel):
    run_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    goal: str

    current_url: str = ""

    step_count: int = 0

    execution_history: list[
        ExecutionStep
    ] = Field(default_factory=list)

    screenshot_id: str | None = None

    axe_results: list[
        AxeViolation
    ] = Field(default_factory=list)

    critic_findings: list[
        CriticFinding
    ] = Field(default_factory=list)

    journey_graph_nodes: list[
        JourneyNode
    ] = Field(default_factory=list)

    journey_graph_edges: list[
        JourneyEdge
    ] = Field(default_factory=list)

    journey_facts: list[
        PageFact
    ] = Field(default_factory=list)

    status: RunStatus = RunStatus.IDLE

    next_action: BrowserAction | None = None

    last_action_success: bool | None = None

    goal_progress: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0
    )

    goal_completed: bool = False

    max_steps: int = 12

    recovery_attempts: int = 0

    max_recovery_attempts: int = 2

    accessibility_score: int = Field(
        default=100,
        ge=0,
        le=100
    )

    current_page_summary: str = ""

    run_error: str | None = None
```

LangGraph wrapper:

```python
from typing import TypedDict


class GraphState(TypedDict):
    state: AgentState
```

Do NOT place screenshot Base64 strings permanently in AgentState.

Store:

```text
screenshot_id
```

Actual files:

```text
artifacts/run_<id>/step_01.jpg
```

Base64 exists only temporarily for:

```text
LLM request
WebSocket frame
```

---

# 8. OBSERVATION-SCOPED ELEMENT REGISTRY

The model NEVER returns:

```text
"#checkout"
".modal-close"
"button:nth-child(3)"
```

And do NOT modify the target DOM by permanently stamping agent IDs.

Instead create an ephemeral registry inside the Playwright runtime.

Selector:

```python
INTERACTIVE_SELECTOR = """
button,
a[href],
input,
textarea,
select,
[role="button"],
[tabindex]:not([tabindex="-1"])
"""
```

Important:

Filter visible controls first.

THEN cap at 40.

```python
locator = page.locator(
    INTERACTIVE_SELECTOR
)

visible_locators = []

for i in range(
    await locator.count()
):
    loc = locator.nth(i)

    if await loc.is_visible():
        visible_locators.append(loc)

    if len(visible_locators) >= 40:
        break
```

Build registry:

```python
from uuid import uuid4


async def build_element_registry(page):

    observation_id = str(uuid4())

    registry = {}

    elements = []

    locator = page.locator(
        INTERACTIVE_SELECTOR
    )

    for i in range(
        await locator.count()
    ):

        loc = locator.nth(i)

        if not await loc.is_visible():
            continue

        handle = await loc.element_handle()

        if not handle:
            continue

        element_id = len(elements)

        info = await loc.evaluate("""
        el => {
            const r =
                el.getBoundingClientRect();

            return {
                role:
                    el.getAttribute("role"),

                text:
                    (
                        el.innerText || ""
                    )
                    .trim()
                    .slice(0,120),

                name:
                    el.getAttribute(
                        "aria-label"
                    )
                    ||
                    el.getAttribute(
                        "title"
                    )
                    ||
                    null,

                placeholder:
                    el.getAttribute(
                        "placeholder"
                    ),

                disabled:
                    !!el.disabled,

                bbox: {
                    x: r.x,
                    y: r.y,
                    width: r.width,
                    height: r.height
                }
            }
        }
        """)

        registry[
            (
                observation_id,
                element_id
            )
        ] = handle

        elements.append(
            ObservedElement(
                element_id=element_id,
                **info
            )
        )

        if len(elements) >= 40:
            break

    return (
        observation_id,
        elements,
        registry
    )
```

Model response:

```json
{
  "observation_id": "obs_xyz",
  "action": "click",
  "element_id": 7,
  "display_label": "Close promotion dialog",
  "rationale": "The dialog prevents progress toward checkout.",
  "confidence": 0.98
}
```

Executor:

```python
handle = registry[
    (
        action.observation_id,
        action.element_id
    )
]

await handle.click(
    timeout=2500
)
```

This gives a strong Q&A answer:

> “The LLM never generates selectors. On every perception cycle we build an ephemeral map of controls currently available to the user. The model chooses from that action space, and the map expires immediately after execution.”

---

# 9. EXECUTION ERROR SEMANTICS

Never turn every error into:

```text
stale observation
```

Use:

```text
SUCCESS
STALE
BLOCKED
FAILED
```

Example:

```python
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError
)


try:
    await handle.click(
        timeout=2500
    )

    outcome = "success"

except PlaywrightTimeoutError as exc:

    outcome = "blocked"

    # Important:
    # This becomes UX evidence.
    # Do not hide it as "stale".

except Exception as exc:

    message = str(exc).lower()

    if (
        "detached" in message
        or
        "not attached" in message
    ):
        outcome = "stale"

    else:
        outcome = "failed"
```

Behavior:

```text
STALE
→ re-observe

BLOCKED
→ record failed interaction
→ re-observe
→ critic reasons about obstruction

FAILED
→ controlled recovery
```

---

# 10. TARGET DEMO APPLICATION

Use one local SPA.

URL:

```text
http://127.0.0.1:4173
```

Routes:

```text
/#/
/#/results?q=nova
/#/product/nova
/#/cart
/#/checkout
/#/complete
```

Do not use one static URL with invisible JavaScript state.

The routes make the journey graph understandable.

---

# 11. THREE PLANTED DEMO DEFECTS

## Defect A — Cross-screen price mismatch

Product page:

```text
Nova Headphones
₹2,499
```

Cart:

```text
Nova Headphones
₹2,799
```

Detected using:

```text
LLM perception
+
journey facts
+
Python comparison
```

NOT axe.

---

## Defect B — Checkout obstruction

First Checkout action opens:

```text
Join Nova+
Save 10%
```

modal.

No timers.

Implementation:

```javascript
let checkoutAttempted = false;

function checkout() {

  if (!checkoutAttempted) {

    checkoutAttempted = true;

    document
      .querySelector(
        "#promo-modal"
      )
      .classList
      .remove("hidden");

    return;
  }

  location.hash =
    "#/checkout";
}
```

The second attempt succeeds.

---

## Defect C — Accessibility defects

Checkout page:

### Missing label

Bad:

```html
<input
  id="checkout-email"
  type="email"
  placeholder="Email address"
/>
```

No:

```html
<label>
```

---

### Low contrast

Keep solid background.

Example:

```css
.pay-button {
    background: #c4d4ff;
    color: #aab8df;
}
```

Do not use gradients.

Deterministic axe detection matters more than pretty CSS.

---

# 12. STRUCTURED FACT MEMORY

Never trust the LLM to remember old prices.

Each analysis returns facts.

```python
class PageFact(BaseModel):

    kind: Literal[
        "product_price"
    ]

    entity: str

    value: float

    currency: str = "INR"

    step_number: int

    url: str
```

Example:

```json
{
  "facts": [
    {
      "kind": "product_price",
      "entity": "Nova Headphones",
      "value": 2499,
      "currency": "INR",
      "step_number": 3,
      "url": "/#/product/nova"
    }
  ]
}
```

Normalize entities:

```python
def normalize_product(name: str):
    return " ".join(
        name
        .lower()
        .split()
    )
```

Comparison:

```python
def detect_price_conflicts(
    facts
):

    prices = {}

    for fact in facts:

        if (
            fact.kind
            !=
            "product_price"
        ):
            continue

        key = normalize_product(
            fact.entity
        )

        prices.setdefault(
            key,
            []
        ).append(fact)

    findings = []

    for (
        product,
        observations
    ) in prices.items():

        unique_prices = {
            f.value
            for f in observations
        }

        if len(unique_prices) <= 1:
            continue

        previous = (
            observations[-2]
        )

        latest = (
            observations[-1]
        )

        findings.append(
            CriticFinding(
                category=
                    "semantic_inconsistency",

                severity="high",

                title=
                    "Product price changed across journey",

                evidence=(
                    f"{latest.entity}: "
                    f"₹{previous.value:.0f} "
                    f"at step "
                    f"{previous.step_number}, "
                    f"₹{latest.value:.0f} "
                    f"at step "
                    f"{latest.step_number}"
                ),

                step_number=
                    latest.step_number
            )
        )

    return findings
```

Q&A:

> “AI converts user-visible content into structured observations. Deterministic code verifies conflicts, which gives us reliability without reducing the system to scripted testing.”

---

# 13. ACCESSIBILITY TREE

Use Playwright ARIA snapshots.

Preferred:

```python
try:

    aria_tree = await page.locator(
        "body"
    ).aria_snapshot(
        mode="ai",
        boxes=True,
        depth=6
    )

except TypeError:

    aria_tree = await page.locator(
        "body"
    ).aria_snapshot()
```

Test the installed Playwright API during Hour 0.

If enhanced arguments are unsupported:

```text
plain aria_snapshot()
```

is completely sufficient.

Pin your tested Playwright version before Hour 4.

Model input:

```text
GOAL

CURRENT SCREENSHOT

CURRENT URL

ARIA SNAPSHOT

VISIBLE INTERACTIVE CONTROLS

LAST ACTION RESULT

LATEST AXE FINDINGS

JOURNEY FACT SUMMARY
```

Do not send full HTML.

---

# 14. SCREENSHOT PIPELINE

```python
frame = await page.screenshot(
    type="jpeg",
    quality=58,
    full_page=False
)
```

Save:

```text
artifacts/
run_123/
step_01.jpg
```

Send Base64 only transiently.

Do NOT place Base64 into:

```text
AgentState
JSONL replay logs
```

---

# 15. AXE-CORE PIPELINE

Inject locally.

Do not depend on CDN during demo.

```python
AXE_PATH = (
    "backend/vendor/axe.min.js"
)

await context.add_init_script(
    path=AXE_PATH
)
```

During the active journey run only focused rules:

```python
AXE_LIVE_RULES = [
    "button-name",
    "label",
    "color-contrast",
    "aria-dialog-name"
]
```

Execution:

```python
axe = await page.evaluate(
"""
async (rules) => {

  const result =
    await axe.run(
      document,
      {
        runOnly: {
          type: "rule",
          values: rules
        },

        resultTypes: [
          "violations"
        ]
      }
    );

  return result.violations.map(
    v => ({
      id: v.id,

      impact:
        v.impact,

      description:
        v.description,

      help:
        v.help,

      helpUrl:
        v.helpUrl,

      nodes:
        v.nodes
        .slice(0,3)
        .map(
          n => ({
            html:
              n.html,

            target:
              n.target,

            failureSummary:
              n.failureSummary
          })
        )
    })
  );
}
""",
AXE_LIVE_RULES
)
```

Important:

Do not depend on the accessibility result while the promotional overlay is still active.

Run the final audit once the modal is gone.

---

# 16. MODEL OUTPUT CONTRACT

One model call per loop.

The model returns:

```json
{
  "page_summary":
    "Nova Headphones product page",

  "goal_progress":
    0.45,

  "facts": [
    {
      "kind":
        "product_price",

      "entity":
        "Nova Headphones",

      "value":
        2499,

      "currency":
        "INR"
    }
  ],

  "findings": [],

  "next_action": {
    "observation_id":
        "abc123",

    "action":
        "click",

    "element_id":
        4,

    "display_label":
        "Add to Cart",

    "rationale":
        "The target product satisfies the user's price constraint.",

    "confidence":
        0.97
  }
}
```

Do not request verbose reasoning.

Dashboard displays only concise decision summaries:

```text
Observed:
Nova Headphones — ₹2,499

Decision:
Add to Cart

Reason:
Matches goal and budget

Confidence:
97%
```

Never expose internal chain-of-thought.

---

# 17. DETERMINISTIC COMPLETION CHECK

Do NOT let the LLM alone decide when the mission ends.

```python
async def verify_goal_completion(
    page
):

    correct_route = (
        "#/checkout"
        in page.url
    )

    email_visible = (
        await page.locator(
            "#checkout-email"
        ).is_visible()
    )

    return (
        correct_route
        and
        email_visible
    )
```

If model says:

```text
DONE
```

but verifier returns False:

```text
ignore completion request
continue
```

If verifier returns True:

```text
stop
```

This prevents:

```text
early termination
wandering
hallucinated success
```

---

# 18. JOURNEY NODE IDENTITY

Do not identify states by URL only.

The cart modal open and cart modal closed share one URL.

Build:

```python
page_state_id = sha256(
    (
        current_url
        +
        normalized_heading
        +
        major_visible_text
    ).encode()
).hexdigest()[:12]
```

Journey:

```text
Home
 │
 ▼
Search Results
 │
 ▼
Product ₹2,499
 │
 ▼
Cart ₹2,799
 │
 ├── Checkout
 │
 ▼
Cart + Promo Modal ⚠
 │
 ├── Close Modal
 │
 ▼
Cart Recovered
 │
 ▼
Checkout ⚠ A11Y
```

---

# 19. ACCESSIBILITY RISK SCORE

Use a deterministic formula.

```text
critical = -25
serious  = -14
moderate = -6
minor    = -2
```

Formula:

```text
Score =
max(
  0,
  100
  -25 × critical
  -14 × serious
  -6 × moderate
  -2 × minor
)
```

Count unique violated rules rather than every affected node.

Example:

```text
2 serious violations

100
-14
-14

= 72 / 100
```

Dashboard label:

```text
AUTOMATED ACCESSIBILITY
RISK SCORE

72 / 100
```

NOT:

```text
WCAG Compliance Score
```

---

# 20. WEBSOCKET EVENT CONTRACT

Freeze this contract at Hour 1.

Envelope:

```json
{
  "run_id": "abc",
  "sequence": 18,
  "timestamp": "ISO-8601",
  "type": "finding",
  "payload": {}
}
```

Allowed event types:

```text
run_started
browser_frame

observation

decision

action_started
action_completed

axe_update

finding

journey_node
journey_edge

score_update

run_completed
run_failed
```

The frontend builds entirely around this contract.

---

# 21. FINAL DASHBOARD

One screen.

No tabs.

```text
┌─────────────────────────────────────────────────────────────────────┐
│ AUTONOMOUS UX AUDITOR     ● LIVE     Step 6/12    72% COMPLETE    │
├──────────────────────────────────┬──────────────────────────────────┤
│                                  │                                  │
│                                  │ DECISION STREAM                  │
│       LIVE BROWSER               │                                  │
│                                  │ ✓ Product located                │
│                                  │ ✓ ₹2,499 captured                │
│       60% width                  │ ⚠ Price changed to ₹2,799        │
│       62% height                 │ ⚠ Checkout interrupted           │
│                                  │ → Closing modal                  │
│                                  │ ✓ Recovery successful            │
│                                  │                                  │
├──────────────────────────────────┼──────────────────────────────────┤
│                                  │                                  │
│ JOURNEY GRAPH                    │ ACCESSIBILITY                    │
│                                  │                                  │
│ Home                             │ Risk Score                       │
│  ↓                               │                                  │
│ Search                           │        72 / 100                  │
│  ↓                               │                                  │
│ Product ₹2499                    │ ● 2 Serious                      │
│  ↓                               │ ● 0 Critical                     │
│ Cart ₹2799 ⚠                     │                                  │
│  ↓                               │ Missing label                    │
│ Modal ⚠                          │ Color contrast                   │
│  ↓                               │                                  │
│ Checkout                         │ [ Download Audit ]               │
│                                  │                                  │
└──────────────────────────────────┴──────────────────────────────────┘
```

Use colors:

```text
Green
success

Amber
friction / recovery

Red
critical defect

Blue
active node

Grey
completed journey
```

Animations only:

```text
current node pulse
new graph edge
finding slide-in
score change
```

No excessive visual effects.

---

# 22. HTML AUDIT EXPORT

Button:

```text
Download Audit
```

Endpoint:

```text
GET /api/runs/{run_id}/report
```

Generate:

```text
audit-{run_id}.html
```

Report:

```text
AUTONOMOUS UX AUDIT

Mission
Target
Timestamp
Status

EXECUTIVE SUMMARY

1 UX obstruction
1 semantic inconsistency
2 accessibility violations
1 autonomous recovery


JOURNEY

1. Home
2. Search
3. Product
4. Cart
5. Modal interruption
6. Recovery
7. Checkout


UX-001

Promotional modal interrupted
checkout flow.

Evidence:
screenshot

Impact:
+2 interactions

Recovery:
Autonomous


UX-002

Price inconsistency

Product:
₹2,499

Cart:
₹2,799


A11Y-001

Missing accessible label


A11Y-002

Insufficient CTA contrast
```

No PDF generation.

HTML is enough.

Do not spend presentation time downloading it.

Point at the button and say:

> “Every finding and screenshot is exportable.”

---

# 23. FAIL-SAFE REPLAY SYSTEM

Absolutely mandatory.

Every live WebSocket event gets simultaneously written to:

```text
replay_runs/golden.jsonl
```

Example:

```json
{
  "sequence": 7,
  "offset_ms": 3840,
  "type": "finding",
  "payload": {
    "severity": "high",
    "title": "Checkout flow interrupted by promotional modal"
  }
}
```

Screenshots:

```text
replay_runs/golden/
001.jpg
002.jpg
003.jpg
...
```

Replay sends exactly the same WebSocket events as live mode.

```python
@app.websocket(
    "/ws/run/{run_id}"
)
async def run_socket(
    ws,
    run_id
):

    await ws.accept()

    if RUN_MODE == "replay":

        await stream_replay(
            ws,
            "replay_runs/golden.jsonl"
        )

    else:

        await stream_live_agent(
            ws,
            run_id
        )
```

Preserve event timing:

```python
await asyncio.sleep(
    max(
        0,
        (
            event["offset_ms"]
            -
            previous_offset
        )
        /
        1000
    )
)
```

Dashboard controls:

```text
▶ RUN LIVE

Replay Last Golden Run
```

If live model fails:

```text
one retry
↓
switch to Replay
```

Say openly:

> “The model endpoint is unstable right now, so I'm switching to our captured golden run of the identical workflow.”

Never pretend replay is live.

---

# 24. HEALTH CHECK

Before stage demo:

```text
GET /health
```

Response:

```json
{
  "backend": true,
  "browser": true,
  "target_app": true,
  "axe": true,
  "model": true,
  "websocket": true,
  "replay": true
}
```

Every value green before presenting.

---

# 25. 24-HOUR TEAM EXECUTION

Three independent workstreams.

---

## WORKSTREAM A
### Agent Core + LangGraph

Owner:

```text
Engineer 1
```

Owns:

```text
backend/agent/
```

Build:

```text
AgentState
structured LLM output
LangGraph
fact extraction
journey memory
price comparison
completion verification
recovery decisions
```

---

## WORKSTREAM B
### Playwright + axe + Demo App

Owner:

```text
Engineer 2
```

Owns:

```text
backend/runtime/
demo_app/
vendor/axe.min.js
```

Build:

```text
browser lifecycle
element registry
ARIA snapshot
action executor
screenshots
axe runner
SPA
three bugs
```

---

## WORKSTREAM C
### Dashboard + WebSocket

Owner:

```text
Engineer 3
```

Owns:

```text
frontend/
backend/api/websocket.py
```

Build:

```text
dashboard
browser panel
decision stream
React Flow journey graph
scorecard
WebSocket
report button
live/replay controls
```

---

## ENGINEER 4
### Integration + Demo Reliability

If available:

```text
replay
external validation
QA
golden run
run-time measurement
stage rehearsal
backup laptop
```

No architecture ownership.

---

# 26. HOURS 0–4

## Hour 0–1

Freeze:

```text
repo structure
WebSocket schema
state schema
action schema
```

Also immediately test:

```text
Playwright installed API
aria_snapshot compatibility
axe injection
chosen model structured output
```

---

## Hour 1–2

Engineer A:

```text
fake observation
→ valid structured BrowserAction
```

Engineer B:

```text
demo app running
all bugs implemented
manual flow confirmed
```

Engineer C:

```text
dashboard layout complete
fake WebSocket feed working
```

---

## Hour 2–4

A:

```text
LangGraph loop compiles
```

B:

```text
Playwright:
click
type
scroll
screenshots
ARIA
axe
```

C:

```text
fake:
browser frame
decision
graph nodes
score updates
```

### HOUR 4 GATE

Must be GREEN:

```text
□ Browser manually reaches checkout

□ Price mismatch exists

□ Modal flow works deterministically

□ axe detects both planned defects

□ model returns valid structured action

□ fake WebSocket run renders correctly
```

---

# 27. HOURS 4–10

## Hours 4–6

Integrate:

```text
LangGraph
→ Playwright
→ screenshot
→ LLM
→ action
```

Terminal-only first.

No dashboard debugging.

---

## Hours 6–8

Implement:

```text
journey facts
price comparison
journey graph
deterministic completion
```

---

## Hours 8–10

Connect real backend to WebSocket.

Dashboard should display:

```text
screenshot
action
current status
first journey graph
axe results
```

---

# 28. HOURS 10–16

## Hours 10–12

Focus exclusively on golden scenario.

Expected flow:

```text
1. Home

2. Search Nova

3. Open product

4. Capture ₹2,499

5. Add to cart

6. Capture ₹2,799

7. Flag inconsistency

8. Attempt Checkout

9. Promotional modal appears

10. Detect friction

11. Close modal

12. Retry checkout

13. Deterministic completion

14. Accessibility audit
```

Some operations can happen inside the same LangGraph iteration, so do NOT equate this list directly with the `max_steps=12` action budget.

---

# 29. HOUR 12 HARD GATE

The system must now work end-to-end from a fresh browser.

```text
□ Natural-language goal

□ No action script

□ No generated CSS selectors

□ Search works

□ Product discovered

□ ₹2,499 extracted

□ Cart reached

□ ₹2,799 extracted

□ mismatch detected

□ checkout attempted

□ modal encountered

□ modal recovered autonomously

□ checkout reached

□ code verifier confirms completion

□ axe scan executes

□ mission terminates
```

Required:

```text
3 consecutive successful runs
```

If Hour 12 is red:

```text
STOP all stretch features.
```

No external website.

No keyboard pass.

No fancy animations.

Fix reliability.

---

# 30. HOURS 12–16

Polish:

```text
WebSocket sequencing
finding cards
journey graph updates
a11y scorecard
browser panel
loading states
error handling
```

Measure real performance:

```text
median mission runtime

P95 mission runtime

per-model-call latency

failed structured-output rate
```

Rewrite pitch timing based on REAL runtime.

Do not assume a one-minute execution.

---

# 31. HOUR 16 HARD GATE

Dashboard must run against the real agent.

```text
□ browser images streaming

□ decisions streaming

□ graph expanding

□ price mismatch visible

□ modal recovery visible

□ scorecard visible

□ audit export works

□ replay works
```

---

# 32. HOURS 16–20

No new architecture.

Harden:

```text
timeouts

stale element recovery

WebSocket reconnect

model JSON validation

one schema retry

modal determinism

graph layout

browser state reset

report generation

replay
```

Recommended:

```python
ACTION_TIMEOUT_MS = 2500

MODEL_TIMEOUT_S = 12

MAX_STEPS = 12

MAX_RECOVERIES = 2
```

LLM failure:

```text
invalid JSON
↓
one structured-output retry
↓
fallback / replay
```

---

# 33. HOUR 20 HARD GATE

DEMO FREEZE.

The exact stage workflow must succeed:

```text
3 / 3 times
```

Do not add features after Hour 20.

---

# 34. HOURS 20–24

## Hour 20–21

Capture:

```text
Golden Run 1
Golden Run 2
```

---

## Hour 21–22

Restart everything from zero:

```text
machine
backend
frontend
browser
demo app
```

Verify fresh startup.

---

## Hour 22–23

Practice exact three-minute pitch.

No improvisation.

---

## Hour 23–24

Do not code unless something is broken.

Prepare:

```text
Laptop A
main demo

Laptop B
backup

local target app

local axe file

installed Chromium

working API keys

golden replay

recorded external validation clip

charger

offline copy of repo
```

---

# 35. EXTERNAL VALIDATION

This is P2 priority.

Only attempt after MVP is green.

Use an external public demo web app such as SauceDemo.

Do NOT depend on it during stage.

Ideal validation:

```text
external site
+
known problematic user/workflow
+
agent discovers one real unexpected issue
```

Best-case recorded clip:

```text
Agent enters external app
↓
navigates without source code
↓
encounters abnormal behavior
↓
records finding
```

Label:

```text
EXTERNAL BLACK-BOX VALIDATION

Target application not built by our team
```

If autonomous bug discovery is unreliable:

record simple external navigation instead.

Do not spend more than:

```text
45–60 minutes
```

trying to make external validation perfect.

Its purpose is only to kill:

> “It only works because you created the demo site.”

---

# 36. OPTIONAL STRETCH FEATURE

Only one stretch feature is allowed.

## Keyboard-only user simulation

Do NOT touch this unless:

```text
Hour 12 green
Hour 16 green
3 consecutive golden runs complete
```

Mission:

> “Complete checkout without using a mouse.”

Actions:

```text
TAB
SHIFT+TAB
ENTER
SPACE
TYPE
```

Detect:

```text
focus escape
missing visible focus
keyboard unreachable control
broken modal focus trap
unexpected focus jump
```

Example:

```text
MODAL OPEN

Tab
↓
Close

Tab
↓
Join

Tab
↓
Background Checkout

⚠ Focus escaped modal
```

Finding:

```text
HIGH

Modal fails to contain keyboard focus.

Keyboard users can reach obscured
background controls.
```

This is much stronger than adding another browser or another agent.

---

# 37. REAL-TIME DEMO TIMING

Do not hard-code exact execution timing before Hour 12.

The final pitch is adapted to actual median runtime.

The audience only needs to see two findings deeply:

```text
1. Price inconsistency

2. Modal friction + recovery
```

axe gets:

```text
5–10 seconds
```

Do NOT individually explain every axe violation.

---

# 38. FINAL 3-MINUTE PITCH

## 0:00–0:30
### Hook

Show one tiny traditional automated test:

```text
click("#product")
click("#cart")
click("#checkout")
```

Say:

> “Traditional UI tests know exactly where every button is. Real users don't.”

Then:

> “Even when this script passes, it cannot tell you whether the journey was confusing, misleading, or inaccessible.”

Switch dashboard.

Say:

> **“So we built an autonomous synthetic user. We give it a goal—not a test script.”**

Enter:

> “Find the Nova headphones under ₹3,000, add them to cart, and reach checkout.”

Press:

```text
RUN LIVE
```

---

# 39. 0:30–1:30
## Live autonomous execution

Do not narrate every click.

Let judges WATCH.

Dashboard:

```text
OBSERVED

Nova Headphones
₹2,499

DECISION

Add to cart
```

Then cart:

```text
Nova Headphones
₹2,799
```

Dashboard:

```text
⚠ HIGH

PRICE INCONSISTENCY

Product page:
₹2,499

Cart:
₹2,799

Difference:
₹300
```

Say:

> “Axe can't detect this. The AI reads what the user sees, stores structured facts across the journey, and deterministic logic verifies contradictions.”

Then Checkout.

Modal opens.

Dashboard:

```text
⚠ UX FRICTION

Primary flow interrupted
by promotional dialog.
```

Agent closes it.

Retries.

Say:

> “This interruption was not part of the action plan. The agent recognized that the user's goal stopped progressing, recovered, and continued.”

Checkout reached.

---

# 40. 1:30–2:05
## Journey intelligence

Point at graph.

```text
Home
 ↓
Search
 ↓
Product ₹2499
 ↓
Cart ₹2799 ⚠
 ↓
Promo Modal ⚠
 ↓
Recovered
 ↓
Checkout
```

Say:

> “Every action becomes evidence. We preserve the exact screen, action, outcome, and finding for each state.”

Click Cart node briefly.

Show screenshot + mismatch.

Do not spend more than 20 seconds here.

---

# 41. 2:05–2:20
## Accessibility

Point at:

```text
AUTOMATED ACCESSIBILITY
RISK SCORE

72 / 100

2 serious
0 critical
```

Say:

> “In parallel, axe-core audits deterministic accessibility rules. Here it found an unlabelled input and insufficient button contrast.”

Do not open both findings unless asked.

---

# 42. 2:20–2:40
## Architecture

Show:

```text
Goal
 ↓
LangGraph
 ↓
Multimodal Planner
 ↓
Playwright
 ↓
Screenshot + ARIA Tree
 ↓
Journey Memory
 ↓
axe-core
 ↓
Evidence Graph
```

Say:

> “Playwright gives the agent hands. Screenshots and the accessibility tree give it perception. LangGraph keeps the investigation stateful. axe-core provides deterministic standards evidence.”

---

# 43. 2:40–3:00
## ROI + close

Show:

```text
MISSION PASSED

8 actions

1 autonomous recovery

1 semantic inconsistency

1 major UX obstruction

2 serious accessibility findings

full evidence trail
```

Point at:

```text
Download Audit
```

Say:

> “The result isn't another chatbot response. Product and QA teams get a reproducible journey with evidence they can act on.”

Final line:

> **“Traditional QA tests the software. We test the experience.”**

STOP.

Do not keep talking.

---

# 44. JUDGE Q&A — EXPECTED ATTACKS

## “Isn't this just Playwright with an LLM?”

Answer:

> “Playwright is only the execution layer. It doesn't know what the user's goal is, whether progress has stalled, whether a price changed across screens, or whether an unexpected state constitutes UX friction. Our agent observes, reasons, stores journey facts, adapts, and then uses Playwright only as its hands.”

---

## “Isn't axe doing the accessibility work?”

Answer:

> “Correct, intentionally. Deterministic rules should be tested deterministically. The AI is responsible for perception, planning, cross-screen semantics, unexpected-state reasoning, and recovery. axe gives us standards-based accessibility evidence rather than asking an LLM to guess.”

---

## “You built the site, so didn't you know the bugs?”

Answer:

> “The agent receives no source code or scripted defect locations. The local target gives us a deterministic stage demo. We also validated the same black-box approach against an external target we did not build.”

Then show 15-second external validation recording.

---

## “Is this actually black-box?”

Answer:

> “Yes. The agent receives only what a user or assistive technology can perceive: the rendered screenshot, normal accessibility representation, URLs, and controls currently exposed by the interface. There are no proprietary SDK hooks, source-code reads, test IDs supplied by the application, or hard-coded journey selectors.”

---

## “Why LangGraph?”

Answer:

> “Because the problem isn't a single prompt. It is an observe–act–verify loop with state, recovery, step budgets, and deterministic termination. LangGraph makes those transitions explicit and inspectable.”

---

## “How do you stop hallucinated actions?”

Answer:

> “The model doesn't generate selectors. Each observation creates an ephemeral action space of actual visible controls, and the model selects one by ID. Invalid or stale references force re-observation.”

---

## “What if the LLM says the mission is done too early?”

Answer:

> “It can't terminate the mission by itself. Completion is verified deterministically from the expected route and required visible UI state.”

---

## “How do you know the price really changed?”

Answer:

> “The LLM extracts each visible price into structured journey facts. Plain deterministic code compares facts for the same entity across states. The model interprets the screen; code verifies the contradiction.”

---

## “Is 72/100 a real accessibility compliance score?”

Answer:

> “No. We explicitly label it an Automated Accessibility Risk Score. It is a transparent weighted heuristic over axe severity and is not presented as WCAG certification.”

---

## “What if your AI API fails during this demo?”

Answer:

> “The live mode is our primary demo. Every run also records the exact event stream, screenshots, findings, and timing, so we can transparently replay a previously completed identical run without pretending it is live.”

---

# 45. FINAL PRIORITY ORDER

```text
P0
Deterministic element execution

P0
End-to-end LangGraph loop

P0
Structured fact extraction

P0
Price inconsistency verification

P0
Modal recovery

P0
Deterministic completion verification

P0
Replay


P1
WebSocket dashboard

P1
Journey graph

P1
axe scorecard

P1
HTML audit export


P2
External black-box validation


P3
Keyboard-only exploration
```

If Hour 12 is red:

```text
P2 and P3 no longer exist.
```

---

# 46. FINAL HOUR-12 SUCCESS TEST

A completely fresh browser must perform:

```text
Natural-language goal

↓

No pre-scripted steps

↓

Observe black-box UI

↓

Search Nova

↓

Open Nova Headphones

↓

Extract ₹2,499

↓

Add to cart

↓

Extract ₹2,799

↓

Python detects price inconsistency

↓

Attempt Checkout

↓

Unexpected modal appears

↓

Agent identifies UX friction

↓

Agent closes modal

↓

Retries Checkout

↓

Reaches #/checkout

↓

Code verifies email field visible

↓

axe runs

↓

Two accessibility findings

↓

Mission terminates automatically

↓

Journey graph complete

↓

Audit ready
```

Run:

```text
3 consecutive times.
```

Only after that do anything optional.

---

# 47. THE FINAL WINNING POSITIONING

Do not describe the project as:

> “AI automated testing.”

Describe it as:

> **“An autonomous synthetic user for continuous UX intelligence.”**

Do not say:

> “Our LLM tests accessibility.”

Say:

> **“The AI investigates the experience; deterministic tooling verifies what should be deterministic.”**

Do not say:

> “It can test every website.”

Say:

> **“Our 24-hour PoC proves the core black-box observe–act–recover–audit loop on a complete user journey.”**

Do not oversell production readiness.

The submission guidance itself favors a smaller working system over a giant unfinished promise.

The product vision is:

```text
Before deployment
      ↓
autonomous synthetic users
      ↓
explore critical journeys
      ↓
discover friction
      ↓
detect semantic inconsistencies
      ↓
audit accessibility
      ↓
generate evidence
      ↓
product + QA teams fix issues
      ↓
real users never encounter them
```

---

# FINAL FREEZE RULE

From this point onward:

> **No more architecture changes unless implementation proves something impossible.**

The biggest remaining competitive risk is not the idea.

It is:

```text
unstable execution
slow model calls
overbuilding
poor stage timing
bad visual hierarchy
```

Therefore the team should optimize for:

```text
Reliability
    >
Visual clarity
    >
Autonomous recovery
    >
Evidence
    >
Feature count
```

The winning demo is not the system with the most agents.

It is the system where judges can clearly WATCH:

```text
SEE
 ↓
UNDERSTAND
 ↓
ACT
 ↓
NOTICE SOMETHING WRONG
 ↓
REMEMBER
 ↓
VERIFY
 ↓
RECOVER
 ↓
FINISH
 ↓
EXPLAIN THE EXPERIENCE
```

That is the final build specification.