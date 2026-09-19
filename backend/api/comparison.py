"""Deterministic, evidence-backed comparison of two completed PathLens runs.

The comparator never asks a model whether a release regressed. It aligns semantic
journey milestones and compares observed outcomes, costs and verified findings.
"""
from __future__ import annotations

import re
from typing import Any

from backend.agent.graph import summarize
from backend.schemas import AgentState, CriticFinding


def _norm(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _finding_key(finding: CriticFinding) -> str:
    if finding.category == "accessibility" and finding.data.get("rule"):
        return f"accessibility:{finding.data['rule']}"
    return f"{finding.category}:{_norm(finding.title)}"


def _verified_findings(state: AgentState) -> dict[str, CriticFinding]:
    return {_finding_key(f): f for f in state.critic_findings if f.verified}


def _milestones(state: AgentState) -> list[dict[str, Any]]:
    """First visit to each semantic page type, ordered as experienced."""
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for node in sorted(state.journey_graph_nodes, key=lambda n: n.step_number):
        kind = node.page_type or _norm(node.label) or "unknown"
        if node.dialog:
            kind = f"{kind}:dialog"
        if kind in seen:
            continue
        seen.add(kind)
        result.append({
            "milestone": kind,
            "label": node.label,
            "step": node.step_number,
            "route": node.route,
            "screenshot_id": node.screenshot_id,
        })
    return result


def compare_runs(baseline: AgentState, candidate: AgentState) -> dict[str, Any]:
    base_summary = summarize(baseline)
    cand_summary = summarize(candidate)
    base_findings = _verified_findings(baseline)
    cand_findings = _verified_findings(candidate)
    new_keys = sorted(cand_findings.keys() - base_findings.keys())
    resolved_keys = sorted(base_findings.keys() - cand_findings.keys())

    new_findings = [cand_findings[k] for k in new_keys]
    resolved_findings = [base_findings[k] for k in resolved_keys]
    action_delta = candidate.step_count - baseline.step_count
    runtime_delta = round(cand_summary["runtime_s"] - base_summary["runtime_s"], 1)
    friction_delta = candidate.friction.score() - baseline.friction.score()
    accessibility_delta = candidate.accessibility_score - baseline.accessibility_score

    reasons: list[str] = []
    severity = "none"
    if baseline.goal_completed and not candidate.goal_completed:
        reasons.append("The goal completed in the baseline but not in the candidate.")
        severity = "critical"
    if action_delta > 0:
        reasons.append(f"The candidate required {action_delta} additional observed action{'s' if action_delta != 1 else ''}.")
        severity = "high" if action_delta >= 3 and severity != "critical" else ("medium" if severity == "none" else severity)
    if friction_delta > 0:
        reasons.append(f"Measured friction increased by {friction_delta} points.")
        if severity == "none":
            severity = "medium"
    if new_findings:
        reasons.append(f"The candidate introduced {len(new_findings)} new verified finding{'s' if len(new_findings) != 1 else ''}.")
        if any(f.severity in ("critical", "high") for f in new_findings) and severity != "critical":
            severity = "high"
        elif severity == "none":
            severity = "medium"
    if accessibility_delta < 0:
        reasons.append(f"The automated accessibility risk score fell by {abs(accessibility_delta)} points.")
        if severity == "none":
            severity = "medium"

    improvements: list[str] = []
    if action_delta < 0:
        improvements.append(f"The candidate used {abs(action_delta)} fewer observed actions.")
    if friction_delta < 0:
        improvements.append(f"Measured friction decreased by {abs(friction_delta)} points.")
    if resolved_findings:
        improvements.append(f"The candidate resolved {len(resolved_findings)} verified finding{'s' if len(resolved_findings) != 1 else ''}.")
    if accessibility_delta > 0:
        improvements.append(f"The automated accessibility risk score improved by {accessibility_delta} points.")

    verdict = "regression" if reasons else ("improvement" if improvements else "no_material_change")
    base_milestones, cand_milestones = _milestones(baseline), _milestones(candidate)
    base_names = {m["milestone"] for m in base_milestones}
    cand_names = {m["milestone"] for m in cand_milestones}

    return {
        "verdict": verdict,
        "severity": severity,
        "comparable_goal": _norm(baseline.goal.raw) == _norm(candidate.goal.raw),
        "baseline": {
            "run_id": baseline.run_id,
            "target_url": baseline.target_url,
            "goal_completed": baseline.goal_completed,
            "actions": baseline.step_count,
            "runtime_s": base_summary["runtime_s"],
            "friction_score": baseline.friction.score(),
            "accessibility_score": baseline.accessibility_score,
        },
        "candidate": {
            "run_id": candidate.run_id,
            "target_url": candidate.target_url,
            "goal_completed": candidate.goal_completed,
            "actions": candidate.step_count,
            "runtime_s": cand_summary["runtime_s"],
            "friction_score": candidate.friction.score(),
            "accessibility_score": candidate.accessibility_score,
        },
        "deltas": {
            "actions": action_delta,
            "runtime_s": runtime_delta,
            "friction_score": friction_delta,
            "accessibility_score": accessibility_delta,
        },
        "reasons": reasons,
        "improvements": improvements,
        "new_findings": [f.model_dump(mode="json") for f in new_findings],
        "resolved_findings": [f.model_dump(mode="json") for f in resolved_findings],
        "milestones": {
            "baseline": base_milestones,
            "candidate": cand_milestones,
            "added": sorted(cand_names - base_names),
            "missing": sorted(base_names - cand_names),
        },
        "method": "Deterministic comparison of matched goals, semantic milestones, observed actions, friction counters and verified findings. No LLM judges the regression.",
    }
