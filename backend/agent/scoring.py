"""Evidence-weighted experience scoring.

The navigator may be agentic, but a model-generated number is not evidence. This
module turns the recorded trajectory into a stable, explainable score that can be
compared across releases and platforms.
"""
from __future__ import annotations

from backend.schemas import AgentState, ExperienceScore


_SEVERITY_PENALTY = {"critical": 28, "high": 18, "medium": 10, "low": 4, "info": 1}


def _consistency(state: AgentState) -> int:
    penalty = sum(
        _SEVERITY_PENALTY.get(f.severity, 4)
        for f in state.critic_findings
        if f.verified and f.category in {"semantic_inconsistency", "ambiguity"}
    )
    return max(0, 100 - min(100, penalty))


def _efficiency(state: AgentState) -> int:
    m = state.friction
    weighted = (
        5 * m.backtracks + 6 * m.repeated_states + 8 * m.failed_interactions
        + 8 * m.blocked_interactions + 10 * m.interruptions + 15 * m.dead_ends
        + 3 * m.no_progress_actions + 4 * m.validation_errors
        + 4 * m.rejected_actions + 2 * m.offscreen_discoveries + 0.25 * m.scroll_actions
    )
    pressure = weighted / max(1, m.total_actions)
    return max(0, min(100, round(100 - pressure * 8)))


def _resilience(state: AgentState) -> int:
    m = state.friction
    penalty = 18 * m.failed_interactions + 16 * m.blocked_interactions + 12 * m.rejected_actions \
        + 12 * m.interruptions + 20 * m.dead_ends + 8 * m.repeated_states
    recovery_credit = min(18, 6 * m.recoveries)
    return max(0, min(100, 100 - penalty + recovery_credit))


def compute(state: AgentState) -> ExperienceScore:
    """Compute a score from verified run evidence; never from model confidence."""
    outcome = 100 if state.goal_completed and state.completion_mode == "verified" else (
        35 if state.verified_evidence_count else 0
    )
    coverage = {"complete": 100, "partial": 70, "not_run": 25, "failed": 0}.get(
        state.accessibility_coverage, 0
    )
    evidence_confidence = min(
        100,
        (35 if state.goal_completed else 10)
        + (35 if state.completion_mode == "verified" else 0)
        + (20 if state.accessibility_coverage == "complete" else 0)
        + min(10, len(state.journey_graph_nodes) * 2),
    )
    efficiency = _efficiency(state)
    accessibility_score = state.accessibility_score
    consistency = _consistency(state)
    resilience = _resilience(state)
    overall = round(
        0.30 * outcome + 0.20 * efficiency + 0.20 * accessibility_score
        + 0.15 * consistency + 0.10 * resilience + 0.05 * coverage
    )

    explanation: list[str] = []
    if outcome < 100:
        explanation.append("The goal was not fully code-verified.")
    if efficiency < 80:
        explanation.append(f"Observed interaction cost reduced efficiency to {efficiency}/100.")
    if accessibility_score < 90:
        explanation.append(f"Verified accessibility findings reduced the score to {accessibility_score}/100.")
    if consistency < 90:
        explanation.append(f"Cross-screen consistency evidence reduced the score to {consistency}/100.")
    if state.friction.recoveries:
        explanation.append(f"The agent recovered autonomously {state.friction.recoveries} time(s).")
    if not explanation:
        explanation.append("No material friction or verified accessibility/consistency defect was observed.")

    if state.accessibility_coverage in {"not_run", "failed"} and not state.goal_completed:
        verdict = "inconclusive"
    elif outcome < 40:
        verdict = "blocked"
    elif overall >= 90:
        verdict = "excellent"
    elif overall >= 75:
        verdict = "good"
    else:
        verdict = "needs_attention"
    return ExperienceScore(
        overall=max(0, min(100, overall)), outcome=outcome, efficiency=efficiency,
        accessibility=accessibility_score, consistency=consistency, resilience=resilience,
        coverage=coverage, confidence=evidence_confidence, verdict=verdict,
        explanation=explanation,
    )


def update(state: AgentState) -> ExperienceScore:
    state.experience_score = compute(state)
    return state.experience_score
