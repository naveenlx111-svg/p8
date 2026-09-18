# PathLens agent review and improvement plan

Reviewed: 18 September 2026. Scope: the supplied P8 challenge specification, current backend, frontend, tests, and project documentation. The missing API key is deliberately excluded from the findings.

**Implementation status (continued after review):** the initial correctness fixes now cover the F01/F03 completion and price cases, F04 dialog/validation classification, F05 audit occurrence and coverage reporting, F06 action gating, F07 recovery scoping, and replay-name confinement from F16. The follow-up adds part of F12–F14: observations label off-screen controls and truncation, actions have required per-action fields plus select/check/uncheck/hover support, and fingerprints include origin plus observable task state. F08–F11, the remaining F12 frame/shadow-root work, full credential-redaction lifecycle, cancellation/retention, and the comparison system remain planned work rather than implemented capabilities.

**Main conclusion:** PathLens has a useful foundation for a web proof of concept, but currently behaves mainly as a single-journey navigator with accessibility scanning. To address the broader problem statement, it needs deliberate alternative-path exploration and version comparison. Before adding those, strengthen the completion verifier and defect evidence: deterministic code currently turns several weak assumptions into “verified” conclusions.

Evidence boundary: findings below come from source inspection. `python -m pytest tests/test_deterministic.py -q -p no:cacheprovider` could not run because the available Python lacks pytest; pydantic, Playwright and LangGraph are also absent. No new live browser/model run was performed. Existing README reliability claims and recorded runs are historical evidence, not results reproduced in this review. Examples below are code-derived failure scenarios, not claims of observed failures on external websites.

## 1. Fit against the actual problem statement

The source of requirements is `P8-Autonomous Agentic Black-Box UI_UX & Accessibility Testing Framework.docx`. The team's plans describe intended behavior, not proof that those capabilities are implemented.

| Requirement | Current implementation | Main remaining work |
|---|---|---|
| Natural-language intent and autonomous navigation | Observe → decide → execute loop; observation-scoped controls | General goal contracts, stronger actions, independent target validation |
| Black-box operation | Browser-rendered text, ARIA snapshot, screenshots, generic control discovery | More faithful viewport perception; frames and shadow roots; explicit separation of observation from app internals |
| Multi-path discovery | Graph records the path taken, including recovery loops | Frontier of unexplored branches, controlled reset/revisit, branch budgets |
| Friction detection | Dialog, blocked-action, validation, no-progress and price heuristics | Separate agent mistakes from application defects; establish expected transitions |
| UI/UX regression detection | Per-run artifacts exist | Baseline/candidate comparison, aligned states, comparable conditions |
| Accessibility and navigation hierarchy | axe scans; ARIA available to model | Audit dialogs, preserve occurrences, keyboard/focus checks |
| Visual tracing and audit report | Screenshots, events, graph and downloadable HTML | Evidence provenance, coverage, reproducibility, consistent counts |
| At least one target platform | Chromium web adapter implemented | Validate web coverage first; additional platforms are encouraged, not minimum-PoC requirements |

The minimum PoC is narrower than the full theme list. A reliable web demonstration is defensible; claiming complete multi-path, regression or cross-platform support is not yet supported by the implementation.

## 2. Preserve these architectural strengths

- Keep observation-scoped element IDs. The model chooses a currently observed control rather than inventing CSS selectors.
- Keep the distinction between an executed action and verified task completion.
- Keep structured actions, facts, findings and event contracts.
- Keep explicit source labels for model suggestions and deterministic/axe results.
- Keep fresh browser contexts, local axe assets, screenshots and self-contained reports.
- Keep replay and the scripted test double visibly labelled. Neither establishes live model generalization.

These are worth extending; a wholesale rewrite is unnecessary.

## 3. Correctness fixes to prioritize first

### F01 — Completion can succeed without fulfilling the complete goal

**Priority: P0. Evidence:** `backend/agent/goal.py:38`, `backend/agent/completion.py:25`, `backend/agent/graph.py:174`.

The goal compiler extracts `max_price`, but `verify()` never checks it. Color, size, quantity, guest checkout and ordered milestones have no equivalent verified contract. Checkout accepts either an email or a generic text input. A “log in” goal can be considered complete on the login page merely because a password field exists: the compiler maps it to `reach_login`.

Product presence is a historical boolean. Once seen on a route containing `cart`, it remains true even if the item is removed later. Custom URL/text criteria explicitly remove the product-presence requirement. Route substring matching can also match a query parameter rather than a destination.

**Improve:** compile goals into ordered milestones and typed constraints. Distinguish reaching a form from completing its task. Use current, product-specific evidence for item identity, variant, quantity, currency and price. Treat URLs as supporting signals, with parsed path matching where appropriate. Custom acceptance criteria should explicitly augment or replace the contract, with the resulting contract visible to the tester. Allow `unknown` when the required evidence cannot be obtained.

**Acceptance checks:** an over-budget item must fail; removing the item invalidates cart success; displaying a login form must not prove login; checkout without an email input can succeed if the actual requested checkout milestone is evidenced; `/search?q=checkout` must not prove checkout.

### F02 — Goal parsing is too narrow for the challenge's own example

**Priority: P0. Evidence:** `backend/agent/goal.py`, `backend/schemas.py::GoalSpec`.

Regex extraction works for selected shopping phrases, but “Filter for blue running shoes under $100 and complete guest checkout” requires filtering, color, product class, budget, guest status and a final transaction boundary. Current destination parsing collapses checkout wording into reaching checkout. Generic tasks without recognized destinations have no deterministic success criteria and cannot finish successfully.

**Improve:** use a structured goal compiler with schema validation and deterministic normalization. Let the model propose milestones; do not let it certify its own success. Support explicit test data and clarify whether the task stops before purchase or permits a sandbox transaction. Return a clear unsupported/ambiguous-goal result before navigation when no defensible acceptance contract exists.

**Acceptance checks:** maintain a paraphrase set spanning shopping, filtering, login, search and multi-step forms; inspect compiled milestones and predicates independently of navigation.

### F03 — “Grounded price” currently means only that a number appears somewhere

**Priority: P0. Evidence:** `backend/agent/memory.py:39`, `backend/agent/memory.py:85`.

`is_grounded()` does not establish that the number belongs to the proposed product or is a unit price. Entity and page context remain model assertions. `_price_variants()` also includes rounded integers for decimal values, so a proposed 29.99 can be accepted against visible 30. Conflict detection groups by normalized name without checking currency, variant, quantity, discounts or taxes.

**Failure scenario:** a page shows product A at ₹2,499 and product B at ₹2,799. A model assigns ₹2,799 to A; the number-only check accepts it, and later comparison can produce a false “verified” price defect.

**Improve:** require a quoted evidence span and an observed product/card or cart-row association. Store currency, unit/line-total semantics, quantity, variant, screenshot and observation IDs. Compare like-for-like prices; keep unexplained differences as suspected until alternatives such as tax or quantity are ruled out. Parse decimal amounts exactly.

**Acceptance checks:** two products with different prices, integer versus decimal amounts, sale/list prices, two-item totals, shipping charges and currency changes must not create unsupported verified defects.

### F04 — Expected dialogs and normal validation can become verified UX defects

**Priority: P0. Evidence:** `backend/agent/critic.py:23`, `backend/runtime/executor.py::_classify`.

Any successful click that opens a dialog on the same route is classified as a high-severity interruption. That includes legitimate filter, address, cart and authentication dialogs. New text containing “required”, “invalid” or “error” becomes a friction finding without determining whether the agent caused normal validation. All Playwright timeouts are classified as blocked, although the cause need not be occlusion. Strict input read-back can flag legitimate formatting such as phone-number normalization.

**Improve:** attach an expected observable effect to each proposed action. Record the transition separately from the defect judgment. Classify dialogs as expected, required, optional or obstructive using the task and trigger. Require visual/hit-test evidence for occlusion. Distinguish normal validation, agent error, platform limitation and app defect. Use field-aware normalization for read-back.

**Acceptance checks:** opening Filters is not an obstruction; a promotional modal intercepting Checkout is a candidate obstruction; submitting an empty required field is not automatically an app defect; a disconnected node is not an occlusion defect.

### F05 — Accessibility coverage and occurrence counts are incomplete

**Priority: P0. Evidence:** `backend/agent/graph.py::_audit`, `observe`, `finalize`; `backend/runtime/accessibility.py`; `frontend/src/useRun.ts`.

Auditing is skipped whenever a blocking dialog is open, which excludes an important accessibility surface. Only six rules run during the journey; broader scanning happens only at the final state. Violations are merged globally by rule ID, losing later occurrences on different pages. The runtime truncates nodes to three and later reports that truncated length as `affected_nodes`. Audit failures emit an event but leave the score potentially looking clean; the frontend ignores audit updates without violations.

**Improve:** audit the active dialog and meaningful stable states. Store occurrences by rule + semantic state + target, with a separate unique-rule summary. Keep total affected-node counts even when examples are capped. Persist audit status as complete, partial, failed or not run. Show coverage next to the score and retain axe results requiring manual review separately.

**Acceptance checks:** the same rule on two pages retains both locations; ten failing elements report ten with three examples; a dialog can contain findings; an axe failure cannot appear as a successfully audited 100/100.

### F06 — The action gate does not cover every way to submit an action

**Priority: P0. Evidence:** `backend/agent/safety.py:16`, `backend/agent/graph.py::execute`, `backend/runtime/executor.py:65`, `backend/schemas.py::GoalSpec`.

The safety function returns immediately when no element is supplied. `press Enter` is page-level and normally has no resolved element, so it can activate a focused submission control without the click checks. `TYPE` can also submit with Enter. `GoalSpec.forbidden_actions` is not consumed by the gate. The prompt forbids passwords unconditionally while code allows tester-provided passwords, creating conflicting instructions.

**Improve:** gate effects, including focused-control activation and form submission, rather than just click labels. Use one structured policy shared by prompt and executor, covering authorized test data, origins and the transaction stop boundary. Treat website content as untrusted observation data that cannot change the user's task or policy. Add explicit sandbox-only authorization for transaction testing where needed.

**Acceptance checks:** clicking and pressing Enter on the same final-payment control must receive the same policy decision; supplied test credentials have consistent treatment; page text asking the agent to ignore its goal cannot alter allowed actions.

### F07 — Recovery counters can end a recoverable mission

**Priority: P1. Evidence:** `backend/agent/critic.py:173`, `backend/agent/graph.py::route`, `decide`.

Failure counts are keyed only by action type and label. Different “Continue” controls can accumulate into one failure count, and a successful later attempt does not reset it. `recovery_attempts` accumulates dialog interruptions across the run despite the termination message referring to unrecovered interruptions. New fingerprints and model-reported progress both reset stall tracking, even if no objective milestone advanced.

**Improve:** key attempts by semantic state, control identity and intended effect; reset consecutive failures after verified progress. Separate active recovery failures from lifetime interruptions. Track milestone progress independently of exploration novelty. Enforce run time and call budgets alongside action limits.

**Acceptance checks:** failures on separate Continue controls do not combine; successful recovery clears its local budget; changing banners cannot indefinitely reset a stalled task.

## 4. Missing capabilities central to the required solution

### F08 — A recorded journey graph is not multi-path exploration

**Priority: P1, high problem-statement value. Evidence:** `backend/agent/graph.py::route`, `backend/agent/journey.py`.

The run ends as soon as one goal is verified. There is no branch frontier, coverage target or alternative-route scheduler. A detour recorded during one attempt is useful tracing but does not demonstrate systematic path discovery.

**Improve:** add a bounded exploration mode. At decision points, retain plausible untried actions with their expected milestones. Complete the first route, reset to a known baseline, then pursue another branch. Re-resolve semantic controls from fresh observations; never reuse element IDs. Prefer fresh test sessions and UI-based restoration: browser Back alone does not undo cart or server-side changes. Track discovered, attempted, completed, blocked and unexplored branches.

**Small first deliverable:** discover a product through search and through category navigation, reach the same goal via both, and identify a third dead-end branch. Report best observed path, alternative cost and remaining frontier. Do not call the best observed path globally optimal.

### F09 — Regression detection does not exist yet

**Priority: P1, high problem-statement value. Evidence:** current run schemas, API and report store individual runs; no baseline/candidate comparison pipeline exists.

**Improve:** introduce a comparison manifest containing goal contract, app version/URL, test-data setup, viewport, browser, locale and model configuration. Run equivalent missions against baseline and candidate, align semantic milestones, then compare completion, branch reachability, extra steps, obstructions and accessibility occurrences. Exact fingerprint hashes are unsuitable for matching changed UI states by themselves. Repeated trials should separate likely regressions from model variance.

**Small first deliverable:** two controlled app versions where the candidate adds an unnecessary checkout modal and an unlabeled field. A comparison report should show before/after evidence, additional actions and new findings. An unchanged control version should not invent a regression.

### F10 — Keyboard accessibility and focus behavior are largely untested

**Priority: P1. Evidence:** action schema supports a few keys, but no focus-audit workflow or focus history exists.

**Improve:** add an explicit keyboard-only audit using Tab, Shift+Tab, Enter, Space and Escape. Record focused element, focus visibility, reachability, logical order, modal containment and focus restoration after dismissal. Check keyboard reachability of primary actions separately from mouse reachability.

**Acceptance checks:** detect a keyboard-inaccessible checkout button and a modal that loses focus; do not infer logical focus-order correctness solely from a successful axe scan.

### F11 — Visual UX problems are not measured systematically

**Priority: P1/P2. Evidence:** screenshots are captured, but `critic.py` primarily compares semantic snapshots; `planner.py::_wants_vision` uses only a small set of fallback triggers.

**Improve:** add targeted before/after geometry and screenshot checks for overlap, clipping, control movement and viewport obstruction. Preserve expected transitions so an intentional drawer opening is not a layout defect. Use image-based hypotheses with evidence and confirmation. Test a narrow viewport first; describe it as responsive-web coverage, not native-device support.

**Acceptance checks:** detect an important button covered by a sticky banner and a checkout control pushed outside a usable viewport, while distinguishing intentional animations from persistent problems.

## 5. Generalization and engineering improvements

### F12 — Perception sees some off-screen content while missing other user-visible content

**Priority: P1. Evidence:** `backend/runtime/observer.py:21`, `:81`, `backend/agent/prompt.py:74`.

The collector includes vertically off-screen controls, and Playwright can scroll them into view when clicked. Text is not strictly viewport-limited. This can hide discoverability and scrolling costs. Conversely, main-document `querySelectorAll` misses controls inside frames and shadow roots. Control and text caps can exclude relevant content without exposing how much was omitted. Accessible names are reconstructed by a simplified algorithm.

**Improve:** distinguish visible-now, off-screen and inaccessible controls. Record scroll-to-discover actions explicitly in human-like mode. Traverse supported frames/open shadow roots with correct coordinate mapping. Prefer browser accessibility semantics where available; keep visible labels separate from accessible names. Report truncated observation coverage and allow targeted expansion. Reserve navigation controls in ranking so a large product listing cannot crowd out category routes.

**Acceptance checks:** locate controls in a frame and open shadow root; record the scroll needed to find a bottom-page action; surface observation truncation instead of treating omitted content as absent.

### F13 — Actions and their schema need stronger semantics

**Priority: P1. Evidence:** `backend/schemas.py::BrowserAction`, `backend/runtime/executor.py`.

The schema does not require action-specific fields. A missing direction defaults to scrolling down; missing key becomes Escape; missing type text clears the field. Native selects, explicit check/uncheck and hover are not first-class operations. Search inputs auto-submit even if the model intended only to type and inspect suggestions.

**Improve:** use discriminated action variants with required fields and observed capability checks. Add select, check/uncheck and hover as needed. Make submit explicit and gate it separately. Add frame/tab context and supported native-dialog handling. Reject unsupported actions with a specific limitation rather than converting them into another action.

**Acceptance checks:** incomplete actions fail before execution; selecting size/color works; typing into autocomplete does not unexpectedly navigate; a control opening a browser dialog produces an explicit recorded outcome.

### F14 — State identity can hide changes or invent progress

**Priority: P1. Evidence:** `backend/runtime/fingerprint.py:49`, `backend/agent/critic.py::_match`.

Fingerprints omit input values and checked/selected state, use only an initial text slice, and omit origin from the canonical route. Different task states can collapse, while changing content can create new states. Read-back matching uses role/name/type, which is ambiguous when fields have identical names or no labels.

**Improve:** separate stable page identity from dynamic task state. Include origin, selected filters, relevant cart/form state and modal state, with deliberate masking of volatile or sensitive values. Match duplicate controls using semantic container context and other observable evidence. Keep visited-state novelty separate from task progress.

**Acceptance checks:** selecting a filter is recorded; a rotating timestamp does not create a new branch; identical paths on different origins do not merge; two unlabeled inputs are not silently treated as one.

### F15 — Scores and report labels can overstate what was established

**Priority: P1. Evidence:** `backend/schemas.py::FrictionMetrics.score`, `backend/agent/graph.py::_emit_scores`, `summarize`, `backend/api/report.py:29`.

The friction score adds fixed penalties without accounting for task length or necessary exploration. Live category counts include unverified findings while final summary counts exclude them. Report price-comparison captions hard-code ₹ even though stored facts support other currencies. A deterministic rule firing is displayed as verification even when its underlying UX assumption is uncertain.

**Improve:** report task outcome, evidence status and audit coverage separately. Use consistent observed/suspected/confirmed classifications across live UI and export. Show raw friction counts, path length and avoidable-action estimates; compare normalized metrics only for comparable tasks. Format currencies from evidence. Include unmet predicates, branch coverage, environment configuration and reproducible steps in the report.

**Acceptance checks:** live and final totals agree under the same filters; USD evidence remains USD; an unaudited page is visible as a coverage gap; longer legitimate exploration is not automatically ranked as worse UX.

### F16 — Artifact and run management need concrete fixes

**Priority: P0 for replay-path confinement; P1/P2 for lifecycle and service deployment. Evidence:** `backend/api/app.py::save_replay`, `backend/events.py`, `backend/agent/runner.py`, `frontend/src/useRun.ts`.

`save_replay` appends a caller-controlled name to the replay directory and recursively deletes an existing destination. Without name validation/resolved-path confinement, an absolute or traversing name can escape the intended directory. Credentials supplied in goals and typed actions are persisted to events, state and HTML; masking password observations does not redact those paths. There is no run cancellation endpoint; starting a replacement run disconnects the UI but does not stop the old backend task. Buses, event histories and subscriber queues have no bounded retention.

**Improve:** restrict replay names and enforce resolved-path containment before read/write/delete operations; use safe atomic replacement. Store credential references separately from public goal text and redact sensitive values before events, prompts/history displays, screenshots where feasible, and exports. Add cancel/status endpoints, bounded run concurrency, retention and cleanup. Surface reconnect exhaustion as a disconnected state. If deploying as a shared service, restrict target-network scope and access to run artifacts; preserve explicitly authorized local demo access.

**Acceptance checks:** traversal/absolute replay names are rejected; a test password never appears in exported files; cancelling a run closes its browser; a lost connection does not look like indefinite live progress.

### F17 — Model/runtime failures need their own outcome and budget

**Priority: P1. Evidence:** `backend/agent/llm.py::ReasoningModel.complete`, `backend/agent/planner.py::plan`, `backend/agent/runner.py`.

Transport retries catch all exceptions with the same behavior. Latency/call accounting omits failed transport attempts. Some malformed JSON shapes can fail before schema validation handles them. Model failure, unsupported task, policy block, exhausted exploration and app obstruction largely converge into a failed run.

**Improve:** distinguish retryable transport errors from invalid configuration and invalid output; validate the top-level output shape before coercion. Count all attempts and elapsed time. Use explicit terminal reason codes, per-run time/call budgets, and guaranteed cleanup/finalization. Keep model capability configuration and provider smoke tests separate from the agent-quality benchmark.

**Acceptance checks:** a transient timeout recovers within budget; malformed output is repaired or reported cleanly; infrastructure failure never becomes a target-app defect.

### F18 — Validation is concentrated on a known demo

**Priority: P1, beginning alongside the P0 fixes. Evidence:** `tests/test_deterministic.py`, `tests/test_golden_journey.py`, README.

The integration test defaults to the scripted test double and skips when the demo server is unavailable. This is useful pipeline testing but does not establish autonomous navigation quality. External-site presets are not evidence of successful coverage. Existing deterministic tests primarily validate intended positive behavior, leaving the negative cases above uncovered.

**Improve:** maintain separate deterministic-unit, browser-integration and real-model benchmark suites. Start the local fixture automatically in integration tests and make accidental skips visible in CI. Add unfamiliar layouts and non-shopping tasks. Use clean fixtures as well as seeded defects, with evaluator-defined ground truth hidden from the navigator. Pin reproducible dependency versions and record browser/model configuration.

**Acceptance checks:** report task success, false completion, defect precision/recall, recovery success, branch coverage, runtime and model calls, with denominators and repeated runs. A claimed improvement must reduce failures without increasing false alarms on clean cases.

## 6. Recommended implementation order

| Stage | Concrete work | Exit evidence |
|---|---|---|
| 1 — Make conclusions trustworthy | F01–F06; replay path confinement and credential redaction from F16; negative-case fixtures from F18 | Incorrect completion and known false-defect scenarios no longer pass as verified |
| 2 — Make navigation generalize | F07, F12–F14, F17; test an unfamiliar target | Multiple task families complete with observable milestones and bounded recovery |
| 3 — Demonstrate the missing challenge features | Bounded multi-path exploration F08; controlled A/B comparison F09 | Two routes to one goal, one dead end, and an evidence-backed regression report |
| 4 — Deepen UX/accessibility coverage | F10–F11; scoring/report consistency F15 | Keyboard defect, modal defect and viewport obstruction detected with reproducible evidence |
| 5 — Expand and operationalize | Additional browser/device adapters; remaining lifecycle work F16; benchmark expansion F18 | Capability matrix and measured results per supported environment |

For a short hackathon window, prioritize trustworthy completion, correct dialog classification, a two-route exploration demonstration and one baseline/candidate report. A second native platform can wait: the specification explicitly permits a one-platform PoC.

## 7. Suggested target architecture

Extend the current loop with a validated goal contract and exploration controller:

1. Compile intent into milestones, constraints, authorized test data and stop boundary.
2. Observe the current viewport, accessibility semantics and screenshot; record observation completeness.
3. Verify milestones and update task state using attributable evidence.
4. Maintain an exploration frontier and select the next branch within budget.
5. Ask the model for one structured action and its expected observable effect.
6. Validate action capability and policy, execute, then observe the transition.
7. Classify outcome and candidate defects separately; confirm where evidence permits.
8. Audit meaningful states, retaining occurrence locations and coverage gaps.
9. Stop with a precise outcome or restore a known baseline to explore another branch.
10. Export reproducible findings and optionally compare against a compatible baseline run.

Milestones, evidence references, branch records, audit coverage and comparison manifests should be explicit data structures. Existing observation, action, event and report modules can evolve around them.

## 8. What the improved demonstration should prove

A strong demonstration would use a supplied goal with product constraints, discover both search and category routes, verify the correct item and price at the requested checkout boundary, recover from a genuine obstruction, and preserve evidence for each finding. A candidate app version would then introduce an extra step and an accessibility defect; the comparison should identify both without flagging clean controls or expected dialogs.

The report should answer: **Was the requested goal actually achieved? Which paths were explored? What specifically made them difficult? What changed between versions? What was audited, what remains unknown, and what evidence supports each claim?**

Keep submission claims aligned with measured implementation status, update stale README/test-count statements, and fill the remaining team-detail placeholders in `pathlens.md` before submission. The strongest improvement is greater trust in those answers, followed by demonstrable exploration and regression capabilities.
