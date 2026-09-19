"""LangGraph orchestration of the observe -> analyse/verify -> decide -> gate/execute loop.

    observe ──► route ──► decide ──► execute ──► observe ...
                  └──────► finalize ──► END

One reasoning-model call per loop (in `decide`). Everything else is deterministic.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agent import completion, critic, journey, memory, safety, scoring
from backend.agent.llm import ModelError, ReasoningModel
from backend.agent.planner import plan
from backend.config import settings
from backend.events import EventBus
from backend.runtime import accessibility, keyboard
from backend.schemas import (
    ActionType, AgentState, BrowserAction, CriticFinding, ExecutionStep, ModelDecision, Observation, RunStatus,
    utc_now,
)

CODE_PREFIX = {"friction": "UX", "occlusion": "UX", "dead_end": "UX", "ambiguity": "UX", "goal_progress": "UX",
               "semantic_inconsistency": "SEM", "accessibility": "A11Y", "recovery": "REC", "safety": "SAFE"}
IMPACT_TO_SEVERITY = {"critical": "critical", "serious": "high", "moderate": "medium", "minor": "low"}


@dataclass
class RunContext:
    state: AgentState
    session: Any  # BrowserSession or AndroidSession; both expose the platform adapter contract.
    model: ReasoningModel
    bus: EventBus
    run_dir: Path
    obs: Observation | None = None
    prev_obs: Observation | None = None
    pending: ExecutionStep | None = None
    decision: ModelDecision | None = None
    notes: list[str] = field(default_factory=list)
    reported: set[str] = field(default_factory=set)
    counters: dict[str, int] = field(default_factory=dict)
    verdict_missing: list[str] = field(default_factory=list)
    cart_product_seen: bool = False
    fail_reason: str | None = None
    audited_rule_states: set[tuple[str, str]] = field(default_factory=set)
    keyboard_audited_states: set[str] = field(default_factory=set)


class GraphState(TypedDict):
    state: AgentState


# ------------------------------------------------------------------ helpers

def _add_finding(ctx: RunContext, f: CriticFinding) -> None:
    key = f"{f.category}:{f.title}:{f.state_id if f.category != 'semantic_inconsistency' else ''}"
    if key in ctx.reported:
        return
    ctx.reported.add(key)
    prefix = "AI" if f.source == "model" else CODE_PREFIX.get(f.category, "UX")
    ctx.counters[prefix] = ctx.counters.get(prefix, 0) + 1
    f.code = f"{prefix}-{ctx.counters[prefix]:03d}"
    ctx.state.critic_findings.append(f)
    node = journey.get_node(ctx.state, f.state_id)
    if node:
        if f.category == "semantic_inconsistency":
            node.semantic_count += 1
        elif f.category == "accessibility":
            node.accessibility_count += 1
        elif f.category in ("friction", "occlusion", "dead_end", "ambiguity"):
            node.friction_count += 1
        ctx.bus.emit("journey_node", node.model_dump())
    ctx.bus.emit("finding", f.model_dump(mode="json"))


def _emit_scores(ctx: RunContext, final: bool = False) -> None:
    s = ctx.state
    experience = scoring.update(s)
    by_cat: dict[str, int] = {}
    for f in s.critic_findings:
        by_cat[f.category] = by_cat.get(f.category, 0) + 1
    ctx.bus.emit("score_update", {
        "accessibility_score": s.accessibility_score,
        "accessibility_counts": accessibility.impact_counts(s.axe_results),
        "disclaimer": accessibility.DISCLAIMER,
        "findings_by_category": by_cat,
        "friction": s.friction.model_dump(),
        "friction_score": s.friction.score(),
        "goal_progress": s.goal_progress,
        "step": s.step_count, "max_steps": s.max_steps,
        "final": final,
        "experience_score": experience.model_dump(mode="json"),
    })


def _detect_action_loop(ctx: RunContext, step: ExecutionStep, obs: Observation) -> None:
    """Describe a semantic cycle as actions and suggest currently available exits."""
    history = ctx.state.execution_history
    if not step.state_after or len(history) < 2:
        return
    trace: list[ExecutionStep] = []
    if step.state_before == step.state_after:
        repeated = [past for past in reversed(history)
                    if past.state_before == step.state_before and past.state_after == step.state_after]
        if len(repeated) >= 2:
            trace = list(reversed(repeated[:4]))
    else:
        for index in range(len(history) - 2, -1, -1):
            if history[index].state_before == step.state_after:
                candidate = history[index:]
                if 2 <= len(candidate) <= 6:
                    trace = candidate
                break
    if not trace:
        return
    actions = [f'{item.step_number}. {item.action.action.value} "{item.action.display_label or item.action.text or "unnamed control"}"'
               for item in trace]
    used_names = {item.target.name.lower() for item in trace if item.target and item.target.name}
    alternatives: list[str] = []
    for element in obs.elements:
        if element.disabled or element.covered or not element.name or element.name.lower() in used_names:
            continue
        alternatives.append(f'{element.role} "{element.name}"')
        if len(alternatives) == 3:
            break
    recommendation = ("Try an unattempted control from the current state"
                      + (": " + ", ".join(alternatives) if alternatives else ", or return to the previous milestone")
                      + ".")
    _add_finding(ctx, CriticFinding(
        category="friction", severity="medium", title="Action loop returned the journey to a previous state",
        evidence=" → ".join(actions), recommendation=recommendation,
        step_number=step.step_number, state_id=obs.fingerprint, screenshot_id=obs.screenshot_id,
        source="deterministic", verified=True,
        data={"rule": "semantic-action-cycle", "action_trace": actions,
              "alternative_actions": alternatives, "cycle_length": len(trace)},
    ))


async def _audit(ctx: RunContext, final: bool) -> None:
    s = ctx.state
    try:
        violations = await ctx.session.audit(final=final)
    except Exception as exc:  # axe failure must not kill the run; it is surfaced in the event stream
        ctx.bus.emit("axe_update", {"error": str(exc), "final": final})
        s.accessibility_coverage = "failed" if s.accessibility_coverage == "not_run" else s.accessibility_coverage
        return
    state_id = ctx.obs.fingerprint
    # Occurrences are tracked per (rule, semantic state): the same rule failing on two different screens
    # (or inside a dialog) must retain both locations, not collapse into a single run-wide sighting.
    new = [v for v in violations if (v.id, state_id) not in ctx.audited_rule_states]
    for v in new:
        ctx.audited_rule_states.add((v.id, state_id))
    s.axe_results.extend(new)
    s.accessibility_score = accessibility.risk_score(s.axe_results)
    s.accessibility_coverage = "complete" if final else ("partial" if s.accessibility_coverage != "complete" else s.accessibility_coverage)
    ctx.bus.emit("axe_update", {
        "final": final, "state_id": state_id, "url": ctx.obs.route,
        "violations": [v.model_dump() for v in violations], "new_rules": [v.id for v in new],
        "score": s.accessibility_score, "counts": accessibility.impact_counts(s.axe_results),
        "coverage": s.accessibility_coverage,
        "engine": "axe-core" if s.platform == "web" else "android-uiautomator",
        "accessibility_tree_id": ctx.obs.accessibility_tree_id,
    })
    for v in new:
        node = v.nodes[0] if v.nodes else None
        _add_finding(ctx, CriticFinding(
            category="accessibility", severity=IMPACT_TO_SEVERITY.get(v.impact or "minor", "low"),
            title=v.help, evidence=(node.failure_summary or v.description).replace("\n", " ")[:400] if node else v.description,
            recommendation=v.help_url if s.platform == "web" else v.description,
            step_number=s.step_count, state_id=state_id,
            screenshot_id=ctx.obs.screenshot_id,
            source="axe" if s.platform == "web" else "deterministic", verified=True,
            data={"rule": v.id, "impact": v.impact, "html": node.html if node else None,
                  "target": node.target if node else None, "affected_nodes": v.total_nodes or len(v.nodes),
                  "method": "axe-core DOM analysis" if s.platform == "web" else "UIAutomator accessibility hierarchy",
                  "accessibility_tree_id": ctx.obs.accessibility_tree_id}))
    keyboard_issues = []
    if ctx.session.page is not None and ctx.obs.dialog_open and state_id not in ctx.keyboard_audited_states:
        ctx.keyboard_audited_states.add(state_id)
        try:
            keyboard_issues = await keyboard.audit_modal_focus(ctx.session.page)
        except Exception as exc:
            ctx.bus.emit("axe_update", {"keyboard_error": str(exc), "state_id": state_id, "final": final})
            keyboard_issues = []
        for issue in keyboard_issues:
            _add_finding(ctx, CriticFinding(
                category="accessibility", severity="high", title=issue["title"], evidence=issue["evidence"],
                recommendation="Move focus into the modal on open, keep Tab/Shift+Tab within it, and restore focus on close.",
                step_number=s.step_count, state_id=state_id, screenshot_id=ctx.obs.screenshot_id,
                source="deterministic", verified=True, data={"rule": issue["rule"], "method": "keyboard-tab-sequence"},
            ))
    if new or keyboard_issues:
        _emit_scores(ctx)


# ------------------------------------------------------------------ nodes

def _repeats_no_progress(s: AgentState, action: BrowserAction, element=None) -> bool:
    """True when this exact action already ran twice on this screen without changing anything."""
    if action.action in (ActionType.SCROLL, ActionType.WAIT, ActionType.BACK, ActionType.DONE):
        return False  # scrolling has its own streak control
    target = element.descriptor() if element else None

    def same_target(p: ExecutionStep) -> bool:
        if target and p.target:
            return p.target == target
        return p.action.display_label == action.display_label and p.action.element_id == action.element_id

    same = [p for p in s.execution_history
            if p.state_before == s.current_state_id and p.state_after == p.state_before
            and p.action.action == action.action and same_target(p)
            and (safety.is_sensitive_target(element) or (p.action.text or "") == (action.text or ""))]
    return len(same) >= 2


def build_graph(ctx: RunContext):
    s = ctx.state

    async def observe(gs: GraphState) -> GraphState:
        s.status = RunStatus.OBSERVING
        obs = await ctx.session.observe()
        ctx.prev_obs, ctx.obs = ctx.obs, obs
        s.current_url, s.screenshot_id = obs.url, obs.screenshot_id
        ctx.bus.emit("browser_frame", {"image": obs.screenshot_id, "url": obs.url, "step": s.step_count,
                                       "state_id": obs.fingerprint,
                                       "accessibility_tree_id": obs.accessibility_tree_id})
        came_from = s.current_state_id
        node, is_new = journey.upsert_node(s, obs)
        if not is_new and came_from and came_from != node.id:
            s.friction.repeated_states += 1
        scrolled_only = bool(ctx.pending and ctx.pending.action.action in (ActionType.SCROLL, ActionType.WAIT))
        if is_new and not scrolled_only:
            # A screen we have never seen = exploration progress. Scrolling alone is not: lazily loaded
            # content (infinite feeds) would otherwise look like endless new screens.
            s.last_progress_step = s.step_count
        s.current_state_id = node.id
        ctx.bus.emit("journey_node", {**node.model_dump(), "active": True})

        ctx.notes = []
        if obs.controls_truncated:
            ctx.notes.append(f"Only {len(obs.elements)} of {obs.total_interactive} interactive controls are listed, prioritised by relevance to your goal. "
                             "If a suitable control is already listed and visible, use it; scroll only if what you need is missing.")
        streak = 0
        for past in reversed(s.execution_history):
            if past.action.action != ActionType.SCROLL:
                break
            streak += 1
        if streak >= 3:
            ctx.notes.append(f"You have scrolled {streak} times in a row without acting. Stop scrolling: pick the best "
                             "matching control from the list now, or change approach (search, menu link, back).")
        if obs.text_truncated:
            ctx.notes.append("Visible page text was truncated; absence from this observation is not proof that text is absent from the page.")
        filled_secrets = [e for e in obs.elements if safety.is_sensitive_target(e) and e.value]
        if filled_secrets:
            ctx.notes.append(
                "Sensitive field already filled (its value is intentionally hidden). Do NOT type it again; "
                "activate the visible submit/login/continue control instead."
            )
        if ctx.pending:
            step = ctx.pending
            step.url_after, step.state_after = obs.url, obs.fingerprint
            if ctx.prev_obs is not None and step.outcome != "rejected":
                rep = critic.analyse_transition(s, ctx.prev_obs, obs, step)
                step.recovery = step.recovery or rep.recovered_edge
                ctx.notes.extend(rep.notes)
                edge = journey.add_edge(s, step)
                ctx.bus.emit("journey_edge", edge.model_dump())
                _detect_action_loop(ctx, step, obs)
                for f in rep.findings:
                    _add_finding(ctx, f)
                if rep.findings:
                    _emit_scores(ctx)
            ctx.pending = None
        if s.last_outcome_note:
            ctx.notes.append(s.last_outcome_note)
            s.last_outcome_note = ""

        ctx.bus.emit("observation", {
            "observation_id": obs.observation_id, "url": obs.url, "route": obs.route, "heading": obs.heading,
            "dialog_open": obs.dialog_open, "dialog_name": obs.dialog_name, "element_count": len(obs.elements),
            "total_interactive": obs.total_interactive, "controls_truncated": obs.controls_truncated,
            "text_truncated": obs.text_truncated,
            "state_id": obs.fingerprint, "image": obs.screenshot_id, "step": s.step_count,
            "accessibility_tree_id": obs.accessibility_tree_id,
            "elements": [e.describe() for e in obs.elements[:25]],
        })

        await _audit(ctx, final=False)  # audit the state as observed, including an open dialog: it is user-facing too

        product = s.goal.success.cart_contains
        if product:
            ctx.cart_product_seen = completion.update_cart_seen(ctx.cart_product_seen, obs, product)
        verdict = completion.verify(s.goal, obs, s.journey_facts, ctx.cart_product_seen)
        if len(verdict.evidence) > s.verified_evidence_count:
            s.verified_evidence_count = len(verdict.evidence)
            s.last_progress_step = s.step_count
        if verdict.completed:
            s.goal_completed, s.goal_progress, s.completion_mode = True, 1.0, "verified"
            ctx.bus.emit("observation", {"verification": {"completed": True, "evidence": verdict.evidence},
                                         "state_id": obs.fingerprint, "step": s.step_count})
        else:
            ctx.verdict_missing = verdict.missing
            if verdict.evidence:  # partially there: tell the agent exactly what is still unmet
                ctx.notes.append("Goal NOT yet verified. Satisfied: " + "; ".join(verdict.evidence)
                                 + ". Missing: " + "; ".join(verdict.missing) + ".")
        return gs

    def route(gs: GraphState) -> str:
        if s.goal_completed:
            return "finalize"
        if s.step_count - s.last_progress_step >= s.stall_limit:
            ctx.fail_reason = (f"stalled: {s.stall_limit} actions without reaching a new screen or advancing the goal")
            return "finalize"
        if s.step_count >= s.max_steps:
            ctx.fail_reason = f"action budget of {s.max_steps} exhausted before the goal was verified"
            return "finalize"
        if s.blocked_reason:
            ctx.fail_reason = s.blocked_reason
            return "finalize"
        if s.consecutive_interruptions > s.max_recovery_attempts:
            ctx.fail_reason = "too many unrecovered interruptions"
            return "finalize"
        return "decide"

    async def decide(gs: GraphState) -> GraphState:
        s.status = RunStatus.RECOVERING if s.in_recovery else RunStatus.PLANNING
        obs = ctx.obs
        shot = (ctx.run_dir / obs.screenshot_id).read_bytes() if obs.screenshot_id else None
        try:
            result = await plan(ctx.model, s, obs, ctx.notes, shot)
        except ModelError as exc:
            ctx.fail_reason = f"model unavailable: {exc}"
            s.run_error = str(exc)
            ctx.decision = None
            return gs
        d = result.decision
        ctx.decision = d
        s.current_page_summary = d.page_summary
        s.goal_progress = max(0.0, min(0.99, d.goal_progress))
        s.best_progress = max(s.best_progress, s.goal_progress)

        accepted, rejected = memory.absorb_facts(s.journey_facts, d.facts, obs, s.step_count + 1, obs.fingerprint)
        node = journey.get_node(s, obs.fingerprint)
        product = str(s.goal.constraints.get("product", ""))
        for f in accepted:
            if node and f.kind == "product_price" and (
                    memory.normalize_entity(f.entity) == memory.normalize_entity(product) or len(accepted) == 1):
                node.annotation = memory.money(f.value, f.currency)
                ctx.bus.emit("journey_node", node.model_dump())

        proposed = (ctx.session.registry.resolve(d.next_action.observation_id, d.next_action.element_id)
                    if ctx.session.registry else None)
        ctx.bus.emit("decision", {
            "step": s.step_count + 1, "state_id": obs.fingerprint,
            "observed": d.page_summary, "goal_progress": s.goal_progress,
            "facts": [f.model_dump() for f in accepted],
            "facts_rejected": [f.model_dump() for f in rejected],
            "action": d.next_action.action.value, "label": d.next_action.display_label,
            "text": safety.masked_text(d.next_action.text, proposed[1] if proposed else None),
            "rationale": d.next_action.rationale,
            "confidence": d.next_action.confidence, "latency_ms": result.latency_ms,
            "vision": result.used_vision, "attempts": result.attempts,
        })

        for f in memory.detect_price_conflicts(s.journey_facts, ctx.reported):
            _add_finding(ctx, f)
        for mf in d.findings[:1]:
            if mf.category == "semantic_inconsistency" or mf.severity in ("info", "low"):
                continue  # contradictions are only reported when verified from facts; low-value opinions are noise
            _add_finding(ctx, CriticFinding(category=mf.category, severity=mf.severity, title=mf.title,
                                            evidence=mf.evidence, step_number=s.step_count + 1,
                                            state_id=obs.fingerprint, screenshot_id=obs.screenshot_id,
                                            source="model", verified=False))
        _emit_scores(ctx)
        return gs

    def after_decide(gs: GraphState) -> str:
        return "finalize" if ctx.decision is None else "execute"

    async def execute(gs: GraphState) -> GraphState:
        s.status = RunStatus.EXECUTING
        action: BrowserAction = ctx.decision.next_action
        s.next_action = action
        s.step_count += 1
        obs = ctx.obs
        resolved = ctx.session.registry.resolve(action.observation_id, action.element_id) if ctx.session.registry else None
        element = resolved[1] if resolved else None
        if action.action == ActionType.PRESS and action.key == "Enter" and element is None:
            # Enter activates the browser's real focused control/form, not the label the model wrote.
            element = next((candidate for candidate in obs.elements if candidate.focused), None)
        step = ExecutionStep(step_number=s.step_count, url_before=obs.url, state_before=obs.fingerprint,
                             action=action, target=element.descriptor() if element else None, outcome="success",
                             recovery=s.in_recovery, screenshot_id=obs.screenshot_id)

        rejection = None
        no_criteria = ctx.verdict_missing == ["goal has no deterministic success criteria"]
        if action.action == ActionType.DONE and no_criteria:
            # Information goals ("find the placements record") have no machine-checkable end state. Accept the
            # model's judgement, but label it honestly as model-judged rather than code-verified.
            s.goal_completed, s.goal_progress, s.completion_mode = True, 1.0, "model_judged"
            ctx.bus.emit("observation", {"verification": {
                "completed": True, "model_judged": True,
                "evidence": [f"model-judged: {action.rationale or 'goal reached'}",
                             "no deterministic success criteria were given (add 'Done when' criteria to verify in code)"]},
                "state_id": obs.fingerprint, "step": s.step_count})
        elif action.action == ActionType.DONE:
            rejection = "Model reported DONE but deterministic verification failed: missing " + \
                        ", ".join(ctx.verdict_missing or ["success signals"])
        elif action.action == ActionType.TYPE and element is not None and safety.is_sensitive_target(element) \
                and element.value and not action.submit:
            rejection = (f'"{element.name or element.role}" is already filled (the secret is hidden). '
                         "Do not type it again; activate the form's submit/login/continue control.")
        elif action.action == ActionType.TYPE and element is not None and (element.value or "") == (action.text or "") \
                and not action.submit:
            # Retyping what the field already shows changes nothing; small models loop on this.
            rejection = (f'"{element.name or element.role}" already contains "{action.text}". Do not retype it: '
                         "submit it (press Enter / click the button) or act on the results.")
        elif _repeats_no_progress(s, action, element):
            rejection = (f'{action.action.value} "{action.display_label or action.text or ""}" was already tried here '
                         "without any effect. Choose a different control or approach.")
        elif action.action in (ActionType.CLICK, ActionType.TYPE, ActionType.SELECT, ActionType.CHECK,
                               ActionType.UNCHECK, ActionType.HOVER) and element is None:
            rejection = f"element {action.element_id} does not exist in observation {action.observation_id}"
        else:
            if element is not None and element.visibility == "offscreen" and action.action != ActionType.SCROLL:
                # The browser scrolls to it the way a user would; record the discovery cost instead of blocking.
                s.friction.offscreen_discoveries += 1
            rejection = safety.check(action, element, settings.allow_irreversible, s.goal.raw, s.goal.forbidden_actions)
            if rejection:
                s.friction.rejected_actions += 1
                _add_finding(ctx, CriticFinding(category="safety", severity="info", title="Unsafe action blocked by safety gate",
                                                evidence=rejection, step_number=s.step_count, state_id=obs.fingerprint,
                                                screenshot_id=obs.screenshot_id, verified=True))

        ctx.bus.emit("action_started", {"step": s.step_count, "action": action.action.value,
                                        "label": action.display_label, "text": safety.masked_text(action.text, element),
                                        "target": step.target.model_dump() if step.target else None})
        if rejection:
            step.outcome, step.error = "rejected", rejection
            s.last_outcome_note = f"Your last proposal was rejected: {rejection}. Choose a different action."
        else:
            result = await ctx.session.execute(action)
            step.outcome, step.duration_ms, step.error = result.outcome, result.duration_ms, result.error
            if safety.is_sensitive_target(element):
                # Real text was already used to fill the field; from here on only the masked value is
                # ever persisted (state.json, exported reports, action_completed event below).
                action.text = safety.masked_text(action.text, element)
            if result.note:
                s.last_outcome_note = result.note
        s.last_outcome = step.outcome
        s.execution_history.append(step)
        s.friction.total_actions += 1
        if action.action == ActionType.SCROLL:
            s.friction.scroll_actions += 1
        ctx.pending = step
        ctx.bus.emit("action_completed", {"step": s.step_count, "action": action.action.value,
                                          "label": action.display_label, "outcome": step.outcome,
                                          "duration_ms": step.duration_ms, "error": step.error,
                                          "recovery": step.recovery})
        return gs

    async def finalize(gs: GraphState) -> GraphState:
        if ctx.obs:
            await _audit(ctx, final=True)
        s.status = RunStatus.COMPLETED if s.goal_completed else RunStatus.FAILED
        s.run_error = s.run_error or (None if s.goal_completed else ctx.fail_reason)
        s.metrics.finished_at = utc_now()
        _emit_scores(ctx, final=True)
        return gs

    g = StateGraph(GraphState)
    g.add_node("observe", observe)
    g.add_node("decide", decide)
    g.add_node("execute", execute)
    g.add_node("finalize", finalize)
    g.add_edge(START, "observe")
    g.add_conditional_edges("observe", route, {"decide": "decide", "finalize": "finalize"})
    g.add_conditional_edges("decide", after_decide, {"execute": "execute", "finalize": "finalize"})
    g.add_edge("execute", "observe")
    g.add_edge("finalize", END)
    return g.compile()


def summarize(state: AgentState) -> dict:
    experience = scoring.update(state)
    cats: dict[str, int] = {}
    for f in state.critic_findings:
        if f.verified:  # unverified AI observations are reported separately, never counted as defects
            cats[f.category] = cats.get(f.category, 0) + 1
    lat = sorted(state.metrics.model_latencies_ms)
    runtime = ((state.metrics.finished_at or utc_now()) - state.metrics.started_at).total_seconds()
    return {
        "status": state.status.value, "goal_completed": state.goal_completed, "actions": state.step_count,
        "completion_mode": state.completion_mode,
        "ai_observations": sum(1 for f in state.critic_findings if not f.verified),
        "recoveries": state.friction.recoveries, "findings_by_category": cats,
        "accessibility_score": state.accessibility_score,
        "accessibility_counts": accessibility.impact_counts(state.axe_results),
        "friction": state.friction.model_dump(), "friction_score": state.friction.score(),
        "runtime_s": round(runtime, 1), "model_calls": state.metrics.model_calls,
        "model_latency_p50_ms": lat[len(lat) // 2] if lat else None,
        "model_latency_p95_ms": lat[min(len(lat) - 1, int(len(lat) * 0.95))] if lat else None,
        "schema_failures": state.metrics.schema_failures, "error": state.run_error,
        "platform": state.platform, "video_path": state.video_path,
        "accessibility_trees": sum(1 for node in state.journey_graph_nodes if node.accessibility_tree_id),
        "action_loops": sum(1 for finding in state.critic_findings
                            if finding.data.get("rule") == "semantic-action-cycle"),
        "experience_score": experience.model_dump(mode="json"),
    }


def save_state(state: AgentState, run_dir: Path) -> None:
    (run_dir / "state.json").write_text(json.dumps(state.model_dump(mode="json"), indent=1), encoding="utf-8")
