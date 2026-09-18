"""LangGraph orchestration of the observe -> analyse/verify -> decide -> gate/execute loop.

    observe ──► route ──► decide ──► execute ──► observe ...
                  └──────► finalize ──► END

One reasoning-model call per loop (in `decide`). Everything else is deterministic.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agent import completion, critic, journey, memory, safety
from backend.agent.llm import ModelError, ReasoningModel
from backend.agent.planner import plan
from backend.config import settings
from backend.events import EventBus
from backend.runtime import accessibility
from backend.runtime.browser import BrowserSession
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
    session: BrowserSession
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
    })


async def _audit(ctx: RunContext, final: bool) -> None:
    s = ctx.state
    try:
        violations = await ctx.session.audit(final=final)
    except Exception as exc:  # axe failure must not kill the run; it is surfaced in the event stream
        ctx.bus.emit("axe_update", {"error": str(exc), "final": final})
        return
    known = {v.id for v in s.axe_results}
    new = [v for v in violations if v.id not in known]
    s.axe_results.extend(new)
    s.accessibility_score = accessibility.risk_score(s.axe_results)
    ctx.bus.emit("axe_update", {
        "final": final, "state_id": ctx.obs.fingerprint, "url": ctx.obs.route,
        "violations": [v.model_dump() for v in violations], "new_rules": [v.id for v in new],
        "score": s.accessibility_score, "counts": accessibility.impact_counts(s.axe_results),
    })
    for v in new:
        node = v.nodes[0] if v.nodes else None
        _add_finding(ctx, CriticFinding(
            category="accessibility", severity=IMPACT_TO_SEVERITY.get(v.impact or "minor", "low"),
            title=v.help, evidence=(node.failure_summary or v.description).replace("\n", " ")[:400] if node else v.description,
            recommendation=v.help_url, step_number=s.step_count, state_id=ctx.obs.fingerprint,
            screenshot_id=ctx.obs.screenshot_id, source="axe", verified=True,
            data={"rule": v.id, "impact": v.impact, "html": node.html if node else None,
                  "target": node.target if node else None, "affected_nodes": len(v.nodes)}))
    if new:
        _emit_scores(ctx)


# ------------------------------------------------------------------ nodes

def build_graph(ctx: RunContext):
    s = ctx.state

    async def observe(gs: GraphState) -> GraphState:
        s.status = RunStatus.OBSERVING
        obs = await ctx.session.observe()
        ctx.prev_obs, ctx.obs = ctx.obs, obs
        s.current_url, s.screenshot_id = obs.url, obs.screenshot_id
        ctx.bus.emit("browser_frame", {"image": obs.screenshot_id, "url": obs.url, "step": s.step_count,
                                       "state_id": obs.fingerprint})
        came_from = s.current_state_id
        node, is_new = journey.upsert_node(s, obs)
        if not is_new and came_from and came_from != node.id:
            s.friction.repeated_states += 1
        if is_new:
            s.last_progress_step = s.step_count  # a screen we have never seen = exploration progress
        s.current_state_id = node.id
        ctx.bus.emit("journey_node", {**node.model_dump(), "active": True})

        ctx.notes = []
        if ctx.pending:
            step = ctx.pending
            step.url_after, step.state_after = obs.url, obs.fingerprint
            if ctx.prev_obs is not None and step.outcome != "rejected":
                rep = critic.analyse_transition(s, ctx.prev_obs, obs, step)
                step.recovery = step.recovery or rep.recovered_edge
                ctx.notes.extend(rep.notes)
                edge = journey.add_edge(s, step)
                ctx.bus.emit("journey_edge", edge.model_dump())
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
            "state_id": obs.fingerprint, "image": obs.screenshot_id, "step": s.step_count,
            "elements": [e.describe() for e in obs.elements[:25]],
        })

        if not obs.dialog_open:  # never audit through a transient overlay
            await _audit(ctx, final=False)

        product = s.goal.success.cart_contains
        if product and not obs.dialog_open and completion.cart_shows(obs, product):
            ctx.cart_product_seen = True
        verdict = completion.verify(s.goal, obs, ctx.cart_product_seen)
        if verdict.completed:
            s.goal_completed, s.goal_progress = True, 1.0
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
        if s.recovery_attempts > s.max_recovery_attempts:
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
        if s.goal_progress > s.best_progress + 0.04:
            s.best_progress = s.goal_progress
            s.last_progress_step = s.step_count

        accepted, rejected = memory.absorb_facts(s.journey_facts, d.facts, obs, s.step_count + 1, obs.fingerprint)
        node = journey.get_node(s, obs.fingerprint)
        product = str(s.goal.constraints.get("product", ""))
        for f in accepted:
            if node and f.kind == "product_price" and (
                    memory.normalize_entity(f.entity) == memory.normalize_entity(product) or len(accepted) == 1):
                node.annotation = memory.money(f.value, f.currency)
                ctx.bus.emit("journey_node", node.model_dump())

        ctx.bus.emit("decision", {
            "step": s.step_count + 1, "state_id": obs.fingerprint,
            "observed": d.page_summary, "goal_progress": s.goal_progress,
            "facts": [f.model_dump() for f in accepted],
            "facts_rejected": [f.model_dump() for f in rejected],
            "action": d.next_action.action.value, "label": d.next_action.display_label,
            "text": d.next_action.text, "rationale": d.next_action.rationale,
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
        step = ExecutionStep(step_number=s.step_count, url_before=obs.url, state_before=obs.fingerprint,
                             action=action, target=element.descriptor() if element else None, outcome="success",
                             recovery=s.in_recovery, screenshot_id=obs.screenshot_id)

        rejection = None
        if action.action == ActionType.DONE:
            rejection = "Model reported DONE but deterministic verification failed: missing " + \
                        ", ".join(ctx.verdict_missing or ["success signals"])
        elif action.action in (ActionType.CLICK, ActionType.TYPE) and element is None:
            rejection = f"element {action.element_id} does not exist in observation {action.observation_id}"
        else:
            rejection = safety.check(action, element, settings.allow_irreversible, s.goal.raw)
            if rejection:
                s.friction.rejected_actions += 1
                _add_finding(ctx, CriticFinding(category="safety", severity="info", title="Unsafe action blocked by safety gate",
                                                evidence=rejection, step_number=s.step_count, state_id=obs.fingerprint,
                                                screenshot_id=obs.screenshot_id, verified=True))

        ctx.bus.emit("action_started", {"step": s.step_count, "action": action.action.value,
                                        "label": action.display_label, "text": action.text,
                                        "target": step.target.model_dump() if step.target else None})
        if rejection:
            step.outcome, step.error = "rejected", rejection
            s.last_outcome_note = f"Your last proposal was rejected: {rejection}. Choose a different action."
        else:
            result = await ctx.session.execute(action)
            step.outcome, step.duration_ms, step.error = result.outcome, result.duration_ms, result.error
        s.last_outcome = step.outcome
        s.execution_history.append(step)
        s.friction.total_actions += 1
        ctx.pending = step
        ctx.bus.emit("action_completed", {"step": s.step_count, "action": action.action.value,
                                          "label": action.display_label, "outcome": step.outcome,
                                          "duration_ms": step.duration_ms, "error": step.error,
                                          "recovery": step.recovery})
        return gs

    async def finalize(gs: GraphState) -> GraphState:
        if ctx.obs and not ctx.obs.dialog_open:
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
    cats: dict[str, int] = {}
    for f in state.critic_findings:
        if f.verified:  # unverified AI observations are reported separately, never counted as defects
            cats[f.category] = cats.get(f.category, 0) + 1
    lat = sorted(state.metrics.model_latencies_ms)
    runtime = ((state.metrics.finished_at or utc_now()) - state.metrics.started_at).total_seconds()
    return {
        "status": state.status.value, "goal_completed": state.goal_completed, "actions": state.step_count,
        "ai_observations": sum(1 for f in state.critic_findings if not f.verified),
        "recoveries": state.friction.recoveries, "findings_by_category": cats,
        "accessibility_score": state.accessibility_score,
        "accessibility_counts": accessibility.impact_counts(state.axe_results),
        "friction": state.friction.model_dump(), "friction_score": state.friction.score(),
        "runtime_s": round(runtime, 1), "model_calls": state.metrics.model_calls,
        "model_latency_p50_ms": lat[len(lat) // 2] if lat else None,
        "model_latency_p95_ms": lat[min(len(lat) - 1, int(len(lat) * 0.95))] if lat else None,
        "schema_failures": state.metrics.schema_failures, "error": state.run_error,
    }


def save_state(state: AgentState, run_dir: Path) -> None:
    (run_dir / "state.json").write_text(json.dumps(state.model_dump(mode="json"), indent=1), encoding="utf-8")
