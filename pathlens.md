# PathLens

## 1. Team Details

**Team Name / ID:** TODO-TEAM-NAME

**Team Lead:** TODO-LEAD-NAME

**Team Members:**
<!--
One line per person, including the team lead. Role is optional.
Pick one, combine two, write your own, or leave it blank:
  Agent Whisperer (agents, prompts, LLMs)
  Backend Developer
  Frontend Developer
  UI/UX Designer
  Integrations Engineer (APIs, tools, connecting services)
  Data Engineer (data, databases, retrieval)
  Product & Pitch Lead (idea, presentation, demo)
  Cool Team Member (a bit of everything)
-->
- TODO-NAME | Agent Whisperer
- TODO-NAME | Backend Developer
- TODO-NAME | Frontend Developer
- TODO-NAME | Product & Pitch Lead

**Repo Link (Optional):** N/A: private until the evaluation

**Demo Link (Optional):** N/A: runs locally (live demo on our laptop)

---

## 2. Problem Statement

<!-- Paste the full problem statement exactly as it was given to you. Don't shorten, fix, or reword anything. No character limit here. -->

Autonomous Agentic Black-Box UI/UX & Accessibility Testing Framework

Autonomous, human-like agent navigation for friction mapping, flow regression detection, multi-path discovery, and cross-platform usability auditing.

Challenge Specification

| Details | |
|---|---|
| Track | Developer Tools / AI Agents / Automated QA & Accessibility |
| Challenge Lead | Jai A Parmar |
| Minimum PoC Scope | Demonstrate autonomous UI testing on at least 1 target platform (multi-platform support encouraged) |

1. Premise & Context

Modern software engineering heavily relies on automated End-to-End (E2E) testing frameworks such as Selenium, Playwright, Cypress, and Appium. While these tools are effective at verifying functional code paths and static assertions (e.g., "does clicking button X return status code 200?"), they suffer from architectural limitations when evaluated against modern, fluid user interfaces:

- Brittle & Framework-Dependent Locators: Traditional automation relies on explicit DOM selectors, XPaths, or accessibility IDs. Simple UI refactoring, class renaming, or layout restructuring breaks test suites even when the core user experience remains intact.
- Inability to Evaluate User Experience & Friction: Standard test runners confirm whether a goal is technically reachable, but cannot measure how frustrating, confusing, or convoluted it was to reach that goal. They are blind to layout shifts, redundant navigation loops, occluded controls, and poor visual hierarchy.
- Single-Path Bias: Automated scripts execute deterministic linear steps. They fail to discover alternative navigation branches, redundant entry points, or dead-end user flows that real users encounter during unscripted exploration.
- Ecosystem & OS Vendor Drift: Applications execute across diverse environments with custom OS behaviors and browser engines (e.g., Stock Android vs. Vendor overlaid UIs; Chrome V8 vs. Firefox Gecko). A flow that feels seamless on one device often suffers from keyboard occlusion, modal overlap, or touch-target misalignment on another.

To solve these challenges, testing must transition from scripted functional execution to agentic, intent-driven exploration. Instead of writing rigid locators, developers should give an AI agent a high-level natural language goal (e.g., "Filter for blue running shoes under $100 and complete guest checkout") and allow the agent to experience, evaluate, and audit the application like a real human user who doesn’t have any info about implementation details.

2. Problem Statement

Build an agentic, framework-agnostic, black-box UI/UX testing engine that accepts high-level natural language intent descriptions and autonomously navigates target applications to discover usability friction, map multi-path user journeys, detect UI/UX regressions, and audit accessibility tree structures.

The system should treat the target application as a true black box—relying on visible UI cues, layout context, or standard accessibility nodes rather than proprietary test hooks or embedded SDKs.

3. Key Exploration Themes

A. Autonomous Navigation & Discovery
- Intent-Based Action: Dynamically translate natural language user goals into visual clue based UI interaction sequences without pre-scripted steps.
- Multi-Path Exploration: Discover alternative navigational paths, redundant loops, or unexpected dead-ends encountered during goal completion.

B. UX Friction & Accessibility Insights
- Friction & Regression Identification: Detect unnecessary complexity, visual shifts, confusing layouts, or regressions between app versions.
- Accessibility Verification: Evaluate screen elements and navigation hierarchies for accessibility flaws (e.g., unlabeled controls or poor focus order).

C. Framework-Agnostic & Native Platform Tracing
- Zero Application Instrumentation: Require no embedded testing libraries, source code modifications, or app-level SDK integrations.
- Native Driver Integration: Communicate exclusively through native platform interfaces:

D. Step-by-step tracing & Reporting
- Visual Tracing: Capture visual or execution logs that make agent decisions and pathways clear and reproducible.
- Audit Output: Produce intuitive summary reports or visualization tools highlighting discovered friction points and usability metrics.

4. Expected Deliverables & Evaluation Criteria
- Agent Core Framework: A functional black-box engine capable of navigating an application based on high-level goals.
- Working Proof of Concept: Demonstration of goal execution, friction detection, or accessibility evaluation on a target app.
- Audit Summary / Report: Clear output showcasing the agent's findings, trajectory step details, and detected issues.

5. References & External Links
- GitHub - callstack/agent-device: Mobile app automation and verification for AI coding agents
- GitHub - lycorp-jp/sim-use: Give your AI agent eyes and hands on iOS Simulator and Android emulator/devices
- GitHub - TencentQQGYLab/AppAgent: AppAgent: Multimodal Agents as Smartphone Users
- Chrome DevTools for agents
- AI Agent Tools for Firefox Development — Firefox Source Docs documentation

---

## 3. TL;DR

<!-- One line each. A judge should get your idea in 10 seconds. -->

**Problem:** UI tests check that clicks work, not whether a real user can finish a task without confusion, traps or barriers.

**Solution:** Given only a goal, our agent uses a web or Android app like a user, flags friction and inconsistencies, recovers, and audits.

**Who benefits:** QA and product teams catch journey-breaking UX, pricing and accessibility bugs before users do, without writing scripts.

---

## 4. Scope of the Project

**What are you building?**

PathLens is a platform-neutral synthetic-user agent. It takes a target URL or Android APK/installed package plus a plain-English goal and drives a real Chromium browser, phone, or emulator one action at a time, using only visible UI and the platform accessibility tree. It records video, remembers facts across screens, detects action loops and friction, suggests alternative controls, recovers, verifies success in code, and streams evidence to a live dashboard and HTML audit.

**How does it solve the problem statement?**

No selectors or scripts: the agent picks from controls it can currently see, so UI refactors don't break it. It reports what scripts can't: interruptions, blocked controls, repeated states, cross-screen contradictions, and accessibility violations, each with screenshots.

**Key features you're building for this hackathon:**
<!-- Up to 5 features. -->

- Goal-driven black-box navigation: LLM chooses one action per step from an ephemeral control list
- Spots "click worked, goal didn't": unplanned dialogs, blocked controls; then recovers on its own
- Cross-screen memory: prices read by the LLM, checked against the page and compared in plain code
- Code-verified completion + platform accessibility-tree capture, axe/native checks, approach and remediation
- Web + Android ADB execution, live journey graph, HTML audit, per-run video and replay evidence

**What are you deliberately NOT doing? (Optional)**

iOS, cross-browser runs, full WCAG certification, auto-fixing code, exhaustive crawling, and any irreversible action (paying, ordering, subscribing, deleting).

---

## 5. Why an Agentic Approach?

<!-- This is an Agentic AI hackathon, so this is one of the most important answers in the file. Be specific. "It uses an LLM" is not an answer. -->

**What does your agent decide or do on its own?**

Each step it reads the screen, decides the next action (search, open, add, dismiss), and picks which visible control to use. When a click opens an unplanned promo instead of checkout, it notices the goal stalled, closes the dialog and retries. It extracts facts (prices) from each screen and knows when to stop, but stopping is only accepted if code verifies it.

**Why wouldn't a fixed script, if-else rules, or a simple chatbot be enough?**

A script needs the path and selectors in advance and breaks on UI changes; it would click Checkout, fail on the popup, and report a crash, not friction. Rules can't read an unfamiliar page and map "Nova headphones under ₹3,000" to the right result. A chatbot can't act. We need a loop that perceives, decides, acts and re-checks.

---

## 6. Who It's For & What Changes

**Who or what is this for?**

QA engineers, frontend teams and product/UX owners who ship web journeys like signup, search and checkout, and want UX checks before release.

**The world today, without your solution:**

Teams write and repair locator-based E2E scripts that only prove a path is technically reachable. Popups hijacking checkout, prices changing between product page and cart, or unlabelled fields reach production and are found by users, support tickets or manual QA passes that take hours per release.

**The world with your solution, fully built and scaled to production:**

Every release, synthetic users with different goals and personas (keyboard-only, first-time) walk critical journeys on web and mobile, compare against the last version, and file evidence-backed friction, consistency and accessibility regressions, so fewer broken or misleading flows reach users.

**What your hackathon build actually delivers today:**

One shared agent loop on web and Android. On web, a local 7B model completes search → product → cart → checkout 3/3 fresh runs, finds a price mismatch, recovers from a checkout popup, and detects accessibility issues. On Android, the ADB adapter installs/launches apps, derives semantic actions from UIAutomator, taps/types/presses like a user, captures the native accessibility tree and frames, applies deterministic mobile checks, and records MP4 evidence. It was live-tested on an Android 36 emulator through a real Settings navigation.

**Before vs. After**

<!--
2 to 4 rows. Pick things that change: time, cost, effort, accuracy, scale, reach, manual work, risk.
Max 80 characters per cell. Replace the example row with your own.
-->

| What Changes | Today | With Our Current Build | At Production Scale |
|---|---|---|---|
| Writing a journey test | Hand-coded selectors + steps per flow | One English sentence, no selectors | Goal library per product, run on every deploy |
| Checkout popup / blocked control | Script crashes or passes silently | Flagged as friction with screenshot; agent recovers | Tracked across releases as a regression |
| Price differs product vs cart | Found by users or manual QA | Detected and verified in ~30 s on our demo app | Checked across many journeys and variants |
| Evidence for a bug report | Manual repro, screenshots by hand | Auto audit: steps, screenshots, findings, replay | Linked straight into issue trackers |

---

## 7. Architecture & Agents

<!--
All the examples in this section describe ONE made-up project, a college helpdesk agent,
so you can see how the parts fit together. Aim for this level of detail, no more.
You don't need to list every library or every function.
-->

**How is your system put together?**

A FastAPI backend runs a LangGraph loop: Observe (Playwright snapshot of the page) → Decide (one LLM call) → safety gate → Execute → Observe. Plain-code checks sit between steps: state fingerprinting, fact comparison, friction detection, goal verification, axe-core. Events stream over WebSocket to a React dashboard and are saved as JSONL for replay and reports.

### 7.1 Agents

<!--
One line per agent. For each one, say what its job is, which model it uses and why that model
fits the job, and what it talks to (other agents, APIs, databases, services).
-->

- **Navigator Agent (the only LLM):** Reads the current screen, picks one action on a listed control, extracts visible prices, notes UX problems. Tested with qwen2.5:7b on Ollama (fast, runs on our 8 GB GPU); provider-swappable (Gemini/Claude/OpenAI). Talks to the Browser Runtime via LangGraph.

### 7.2 Services, APIs, Databases & Memory

<!--
One line for everything that isn't an agent: databases, APIs, external services, tools,
and your interface (web app, bot, CLI). Say what it is, what it does, and who uses it.
Mention if it's mocked.
-->

- **Browser Runtime (Playwright + Chromium):** Screenshots, ARIA tree, visible-control registry, executes clicks/typing. Used by the loop.
- **Journey Critic & Verifier (Python, no LLM):** Detects dialogs/blocked clicks, compares facts, verifies goal completion.
- **Accessibility Auditor (axe-core, vendored locally):** Runs WCAG A/AA rules on each screen; feeds the risk score.
- **NovaMart demo shop (our own local SPA):** Target app with 3 planted defects for a reliable demo. Not seen by the agent's code.
- **Dashboard (React + React Flow) & CLI:** Live browser view, decision stream, journey graph, scores, audit download.
- **Run store (JSONL + files):** Every event and screenshot per run; used for replay and the HTML audit.

**How does your system remember things (memory & state)?**

Typed run state in LangGraph: action history, visited UI states (fingerprint hash), journey graph, and a fact store of prices per screen. Facts are kept only if the value is literally visible on the page. Runs persist as JSONL + screenshots.

**Diagram Link (Optional):** N/A: diagram shown in the live dashboard and our slides

### 7.3 Example Walkthrough

<!--
Take ONE realistic input and show how it moves through your system: which agent picks it up,
what gets passed on, which tools or databases are used, and what comes out at the end.
Up to 8 steps. If the flow branches, use 3a / 3b.
-->

**Example input:** "Find the Nova headphones under ₹3,000, add them to cart, and reach checkout." + the shop's URL

1. **Goal compiler:** Extracts product, max price ₹3,000 and success signals (checkout route, email field, product seen in cart).
2. **Navigator:** Sees the home page controls and types "Nova headphones" into search (uses: Browser Runtime).
3. **Navigator:** Opens the matching result; reads "₹2,499" on the product page; code confirms it is visible and stores it.
4. **Navigator:** Adds to cart; reads ₹2,799. **Verifier:** Same product, new price: HIGH "price inconsistency +₹300 (+12%)".
5. **Navigator:** Clicks Checkout. **Critic:** URL unchanged, a "Join Nova+" dialog appeared: HIGH friction, flow interrupted.
6. **Navigator:** Dismisses the dialog via "Close" (the safety gate would block "Join"), then retries Checkout.
7. **Verifier:** Checkout route + email field + product was in cart: goal verified. **axe-core:** Unlabelled email, low-contrast Pay.
8. **Report:** Journey graph, findings with screenshots, risk score 61/100 and replay are saved and streamed.

**Final output:** Mission verified in 6 actions: 1 price inconsistency, 1 checkout obstruction + recovery, 2 accessibility violations, HTML audit.

**Anything special about how your workflow runs? (Optional)**

The LLM never writes selectors: each step we list visible controls and it picks an id valid only for that snapshot. The LLM perceives; code verifies: facts must be visible on the page, contradictions and completion are checked in plain code, and "DONE" is ignored unless the verifier agrees.

---

## 8. Tech Stack

<!-- Write N/A for any row that doesn't apply. Models are already listed per agent in 7.1. Max 60 characters per cell. -->

| Layer | Technology |
|---|---|
| Frontend / Interface | React + Vite + Tailwind, React Flow graph; Python CLI |
| Backend | Python, FastAPI, WebSockets, Playwright, Android ADB/UIAutomator |
| Agent Framework | LangGraph (small state machine) + Pydantic schemas |
| Database / Storage | No DB: JSONL + screenshots + trees + journey video |
| Hosting | Local laptop; LLM local via Ollama (cloud API optional) |
| Other | axe-core 4.10, ADB/aapt/screenrecord, pytest |

---

## 9. What to Expect From Our Current Build

<!--
Be honest. Unfinished, faked, or hard-coded parts are completely normal at a hackathon.
Telling us means we judge what you actually built, and that works in your favour.
Max 120 characters per bullet.
-->

**Working:**

- Golden journey from goal text alone: 3/3 fresh-browser runs with local qwen2.5:7b, 6 actions, ~30 s
- Price mismatch, checkout-popup friction + autonomous recovery, code-verified completion, axe audit
- Real Tab-sequence modal audit verifies focus-entry and focus-trap failures beyond static axe checks
- Android phone/emulator/APK mode: UIAutomator tree, semantic actions, native a11y checks, MP4 recording
- Live dashboard, journey graph, HTML audit export, replay, /health check, cancellation, 44 tests
- Deterministic A/B release comparison: matched milestones, action/friction deltas, and new verified findings
- Also completes goals on 3rd-party sites (SauceDemo, Demoblaze) from just a URL + goal typed in the dashboard
- Caught a real SauceDemo bug unaided: typing in Last Name overwrites First Name (read-back check)

**Partly working, mocked, or hard-coded:**

- Stage demo uses our own shop with planted bugs; external sites tested on only a few public demo stores so far
- Screenshots aren't used for decisions yet: local vision model took 30-70 s/step, so our 7B runs on text + ARIA
- Goal parsing and success checks are rule-based and cover checkout/cart/login-style goals only
- Friction score weights are our own heuristic for comparison, not an industry standard

**Not working or not built yet:**

- Multi-path exploration and a full keyboard-only journey persona (modal focus auditing is already working)
- iOS apps and other browser engines

**What we'd most like to be judged on:**

The perceive → act → verify loop: the agent recovers from a popup no one scripted, and every finding it reports is checked by code (visible-text grounding, fact comparison, goal verifier, axe), not just trusted from the LLM.

---

## 10. Future Scope

<!-- 2 or 3 things you're NOT building yet but plan to. If you clear the checkpoint, you may be asked to build one of them, so keep them concrete and doable. -->

### Idea 1

**Name:** Bounded multi-path exploration

**What it is:** Continue after first success to discover a second route and one dead end within an explicit branch budget.

**Why it matters:** It directly removes scripted testing's single-path bias and makes unexplored coverage visible.

**How we'd build it:** Save semantic branch candidates, restore a clean baseline, re-resolve controls by role/name, and merge paths into the journey graph.

**Done when:** The same goal completes through search and category navigation, while a deals branch is recorded as a dead end.

### Idea 2

**Name:** Keyboard-only user and focus-order audit

**What it is:** A keyboard-only persona: actions become Tab/Shift+Tab/Enter/Escape, and we track where focus goes each step.

**Why it matters:** The problem statement calls out poor focus order; axe can't catch focus escaping a modal or unreachable buttons.

**How we'd build it:** New action adapter on the same loop; log document.activeElement after each key, flag focus leaving an open dialog.

**Done when:** On the demo shop the agent reaches checkout by keyboard and flags focus escaping the promo dialog, with evidence.

### Idea 3 (Optional)

**Name:** Multi-path exploration

**What it is:** After one success, replay to earlier branch points and try unused actions (e.g. browse categories instead of search).

**Why it matters:** Finds dead ends, loops and slower paths that a single greedy run never sees.

**How we'd build it:** Reuse saved traces to restart at a state, pick an untried control, cap the action budget, merge into one graph.

**Done when:** The graph shows 2 successful paths plus 1 dead end, with the shortest path and extra-step count highlighted.

---

## 11. Additional Notes (Optional)

<!-- Anything else you'd like us to know. -->

Honest limits: the stage target is our own app so the demo is deterministic; the agent gets no source code or selectors. On public demo stores it also works, but a 7B model sometimes wanders (wasted steps) on unfamiliar sites. The accessibility score is a heuristic from axe results, not WCAG certification. The LLM is swappable; we tested locally to avoid API dependence.
