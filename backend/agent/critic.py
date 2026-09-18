"""Deterministic transition critic: compares intended action vs. what actually happened.

"The click happened" != "the user's intended outcome progressed". This module turns that difference into
objective friction events and evidence-backed findings, without asking the model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.schemas import (
    ActionType, AgentState, CriticFinding, ExecutionStep, Observation, ObservedElement, TargetDescriptor,
)


@dataclass
class TransitionReport:
    findings: list[CriticFinding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    recovered_edge: bool = False


# Dialogs whose purpose is named by the trigger or the dialog's own title are an expected part of normal
# UI flow (a filter panel, a login/signup form, an address/cart drawer, a cookie/consent notice) rather than
# an obstruction. This is a heuristic on OBSERVABLE labels, never on app source.
EXPECTED_DIALOG = re.compile(
    r"filter|sort|refine|address|shipping|delivery|login|log in|sign in|sign up|signup|register|account|"
    r"preference|setting|language|currency|newsletter|cookie|consent|quantity|size|variant|option|review", re.I)
# Primary-flow controls a dialog must never intercept without being one of the expected kinds above.
PRIMARY_FLOW = re.compile(r"checkout|buy|purchase|pay|place order|proceed", re.I)


def analyse_transition(state: AgentState, prev: Observation, obs: Observation, step: ExecutionStep) -> TransitionReport:
    rep = TransitionReport()
    m = state.friction
    a = step.action
    label = a.display_label or (step.target.name if step.target else a.action.value)
    same_route = prev.route == obs.route
    same_state = prev.fingerprint == obs.fingerprint

    if a.action == ActionType.BACK:
        m.backtracks += 1

    if step.outcome == "blocked":
        m.blocked_interactions += 1
        rep.notes.append(f'"{label}" could not be activated ({step.error}). Something is covering or blocking it: '
                         'close popups/suggestion lists (press Escape) or use a different control. Do not retry it as-is.')
        rep.findings.append(CriticFinding(
            category="occlusion" if obs.dialog_open else "friction", severity="medium",
            title=f'Interaction blocked: "{label}"',
            evidence=f"The control was visible but could not be activated: {step.error}",
            recommendation="Make sure primary controls are not covered or disabled without explanation.",
            step_number=step.step_number, state_id=obs.fingerprint, screenshot_id=obs.screenshot_id, verified=True))
        _count_failure(state, rep, step, label, obs)
        return rep

    if step.outcome in ("failed", "stale"):
        if step.outcome == "failed":
            m.failed_interactions += 1
        rep.notes.append(f'Previous action "{label}" {step.outcome}: {step.error}. The screen was re-observed.')
        return rep

    if step.outcome != "success":
        return rep

    # Intended outcome vs. actual outcome: an action opened a dialog instead of progressing.
    if a.action == ActionType.CLICK and not prev.dialog_open and obs.dialog_open and same_route:
        trigger_or_dialog = f"{label} {obs.dialog_name}"
        expected = bool(EXPECTED_DIALOG.search(trigger_or_dialog)) and not bool(PRIMARY_FLOW.search(label))
        if expected:
            # A filter/login/address/etc. panel opening is normal UI, not a friction event: no interruption
            # counter, no defect finding - just context for the model.
            rep.notes.append(f'Clicking "{label}" opened "{obs.dialog_name}", an expected panel/dialog for this control.')
            return rep
        m.interruptions += 1
        state.in_recovery = True
        state.recovery_attempts += 1
        state.consecutive_interruptions += 1
        severity = "high" if PRIMARY_FLOW.search(label) else "medium"
        rep.notes.append(f'Clicking "{label}" did NOT progress the journey: the page stayed on {obs.route} '
                         f'and a dialog "{obs.dialog_name}" appeared. Deal with the dialog before continuing.')
        rep.findings.append(CriticFinding(
            category="friction", severity=severity,
            title="Primary flow interrupted by an unexpected dialog" if severity == "high" else "Unexpected dialog interrupted the flow",
            evidence=(f'Clicking "{label}" opened the dialog "{obs.dialog_name}" instead of progressing; '
                      f"the URL stayed at {obs.route}. The user must dismiss it and retry."),
            recommendation="Do not intercept primary-flow actions (such as Checkout) with promotional dialogs.",
            step_number=step.step_number, state_id=obs.fingerprint, screenshot_id=obs.screenshot_id, verified=True,
            data={"trigger": label, "dialog": obs.dialog_name, "route": obs.route}))
        return rep

    if prev.dialog_open and not obs.dialog_open:
        if state.in_recovery:
            m.recoveries += 1
            state.consecutive_interruptions = 0
            rep.recovered_edge = True
            rep.notes.append(f'Dialog "{prev.dialog_name}" dismissed. Retry the action that was interrupted.')
            rep.findings.append(CriticFinding(
                category="recovery", severity="info",
                title="Autonomous recovery: obstruction dismissed",
                evidence=f'Dismissed "{prev.dialog_name}" using "{label}" and returned to the previous state.',
                step_number=step.step_number, state_id=obs.fingerprint, screenshot_id=obs.screenshot_id, verified=True))
        return rep

    if state.in_recovery and not same_route:
        state.in_recovery = False
        rep.notes.append("The journey is progressing again after the interruption.")

    failed_attempt = False
    for msg in new_error_messages(prev, obs):
        # A bare "required" message on a field the user just left empty is normal form validation, not an
        # app defect: only messages naming an actual failure (invalid/incorrect/failed/etc.) are findings.
        if _REQUIRED_ONLY.search(msg) and not _SERIOUS_VALIDATION.search(msg):
            rep.notes.append(f'The page now shows a validation message: "{msg}". Fill in the required field(s).')
            continue
        m.validation_errors += 1
        failed_attempt = True
        rep.notes.append(f'The page now shows a message: "{msg}".')
        rep.findings.append(CriticFinding(
            category="friction", severity="medium", title=f'Error message shown: "{msg[:60]}"',
            evidence=f'After {a.action.value} "{label}", the page displayed: "{msg}".',
            step_number=step.step_number, state_id=obs.fingerprint, screenshot_id=obs.screenshot_id, verified=True,
            data={"message": msg}))

    if not same_state:
        # Genuine progress on this control: forgive its past failures instead of letting a stale streak
        # (from before the user found the right approach) later block the mission.
        state.attempt_failures.pop(_failure_key(step, label), None)

    if a.action == ActionType.TYPE:
        # Read-back: did the field keep what the user typed, and did typing change any OTHER field?
        typed = a.text or ""
        target = _match(obs, step.target)
        others = _changed_other_fields(prev, obs, step.target)
        readback_applies = same_route and not a.submit  # submitted/navigated forms legitimately clear fields
        if readback_applies and target is not None and target.input_type != "password" and (target.value or "") != typed:
            m.failed_interactions += 1
            failed_attempt = True
            side = f' Meanwhile {", ".join(others)} changed.' if others else ""
            rep.notes.append(f'You typed "{typed}" into "{label}" but the field now shows "{target.value or ""}".{side}')
            rep.findings.append(CriticFinding(
                category="friction", severity="high", title=f'Field does not keep typed input: "{label}"',
                evidence=f'Typed "{typed}" into "{label}"; read back "{target.value or ""}".{side}',
                recommendation="Make sure each input keeps the value the user enters and only updates itself.",
                step_number=step.step_number, state_id=obs.fingerprint, screenshot_id=obs.screenshot_id, verified=True,
                data={"typed": typed, "read_back": target.value, "other_fields_changed": others}))
        if failed_attempt:
            _count_failure(state, rep, step, label, obs)
        return rep

    if failed_attempt:
        _count_failure(state, rep, step, label, obs)
        return rep

    if same_state and a.action == ActionType.CLICK:
        m.no_progress_actions += 1
        rep.notes.append(f'"{label}" produced no visible change. Try a different control.')
        repeats = [s for s in state.execution_history
                   if s.state_before == step.state_before and s.action.display_label == a.display_label
                   and s.state_before == s.state_after and s.action.action == a.action]
        if len(repeats) >= 2:
            rep.findings.append(CriticFinding(
                category="friction", severity="medium", title=f'Control appears unresponsive: "{label}"',
                evidence=f'"{label}" was activated {len(repeats)} times with no visible change.',
                step_number=step.step_number, state_id=obs.fingerprint, screenshot_id=obs.screenshot_id, verified=True))
        _count_failure(state, rep, step, label, obs)
    return rep


_ERROR_MSG = re.compile(r"[^.!?]{0,60}\b(?:error|required|invalid|incorrect|failed|not allowed|try again)\b[^.!?]{0,60}", re.I)
_REQUIRED_ONLY = re.compile(r"\brequired\b", re.I)
_SERIOUS_VALIDATION = re.compile(r"\b(?:error|invalid|incorrect|failed|not allowed|try again)\b", re.I)


def new_error_messages(prev: Observation, obs: Observation) -> list[str]:
    """Error/validation text visible now that was not visible on the previous screen."""
    before = prev.visible_text.lower()
    out = []
    for m in _ERROR_MSG.finditer(obs.visible_text):
        msg = " ".join(m.group(0).split())
        if msg and msg.lower() not in before and msg not in out:
            out.append(msg)
    return out[:2]


def _match(obs: Observation, target: TargetDescriptor | None) -> ObservedElement | None:
    if target is None:
        return None
    matches = [e for e in obs.elements if e.role == target.role and e.name == target.name
               and e.input_type == target.input_type]
    # A role/name/type triplet is not an identity when a form has duplicate or unlabelled inputs. Returning
    # either candidate would manufacture read-back evidence, so leave this transition indeterminate instead.
    return matches[0] if len(matches) == 1 else None


def _changed_other_fields(prev: Observation, obs: Observation, target: TargetDescriptor | None) -> list[str]:
    def keyed(elements: list[ObservedElement]) -> dict[tuple[str, str, str | None, int], ObservedElement]:
        counts: dict[tuple[str, str, str | None], int] = {}
        result: dict[tuple[str, str, str | None, int], ObservedElement] = {}
        for e in elements:
            if not e.input_type:
                continue
            base = (e.role, e.name, e.input_type)
            counts[base] = counts.get(base, 0) + 1
            result[(*base, counts[base])] = e
        return result

    before = keyed(prev.elements)
    changed = []
    for key, e in keyed(obs.elements).items():
        old = before.get(key)
        if old is None or (target and e.role == target.role and e.name == target.name
                           and e.input_type == target.input_type):
            continue
        if e.input_type != "password" and (e.value or "") != (old.value or ""):
            changed.append(f'"{e.name or e.input_type}" (now "{e.value or ""}")')
    return changed


def _failure_key(step: ExecutionStep, label: str) -> str:
    # Scoped by semantic state, not just action+label: two different "Continue" buttons on two different
    # screens must not accumulate into one shared failure count.
    return f"{step.state_before}:{step.action.action.value}:{label}"


def _count_failure(state: AgentState, rep: TransitionReport, step: ExecutionStep, label: str, obs: Observation) -> None:
    """Repeated failure on the same control = suspected dead end; the 3rd strike blocks the mission as a defect."""
    key = _failure_key(step, label)
    state.attempt_failures[key] = state.attempt_failures.get(key, 0) + 1
    n = state.attempt_failures[key]
    if n == 2:
        rep.notes.append(f'"{label}" has now failed twice. Try a genuinely different approach if one exists.')
    if n >= 3 and not state.blocked_reason:
        state.friction.dead_ends += 1
        state.blocked_reason = (f'journey blocked: "{label}" failed {n} times (possible application defect '
                                f'or automation limitation; review the evidence)')
        rep.findings.append(CriticFinding(
            category="dead_end", severity="high", title=f'Goal blocked: "{label}" fails repeatedly',
            evidence=(f'{step.action.action.value} "{label}" failed {n} times with the same result; '
                      "the journey cannot continue without a workaround."),
            recommendation="Check the evidence: if a person hits the same result, it is a defect blocking this journey.",
            step_number=step.step_number, state_id=obs.fingerprint, screenshot_id=obs.screenshot_id, verified=True))
