"""Frozen shared contracts for PathLens.

Everything that crosses a module boundary (agent <-> runtime <-> API <-> frontend <-> replay) is defined here.
The WebSocket envelope and event types mirror contracts/websocket.md; frontend/src/types.ts mirrors this file.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def short_id() -> str:
    return uuid4().hex[:10]


# ---------------------------------------------------------------- enums

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
    PRESS = "press"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    HOVER = "hover"
    DONE = "done"


Outcome = Literal["success", "stale", "blocked", "failed", "rejected"]
Severity = Literal["info", "low", "medium", "high", "critical"]
FindingCategory = Literal[
    "friction", "accessibility", "semantic_inconsistency", "dead_end",
    "occlusion", "ambiguity", "recovery", "goal_progress", "safety",
]


# ---------------------------------------------------------------- goal

class SuccessCriteria(BaseModel):
    """Deterministic, app-agnostic completion signals. Derived from the goal, never from app source."""
    url_contains: list[str] = Field(default_factory=list)
    visible_input_types: list[str] = Field(default_factory=list)  # e.g. ["email"]
    visible_text_any: list[str] = Field(default_factory=list)
    # The goal's named product must have been visibly present on a cart screen during the journey.
    cart_contains: str | None = None
    # Text that proves the goal is NOT met even if the URL looks right (e.g. "your cart is empty").
    forbid_text_any: list[str] = Field(default_factory=list)
    # Route must NOT contain any of these once the goal is met (e.g. still on the login page).
    forbid_url_contains: list[str] = Field(default_factory=list)
    # These input types must NOT still be visible (e.g. a password field proves a login form is still showing).
    forbid_visible_input_types: list[str] = Field(default_factory=list)
    # The goal's price constraint, checked against grounded facts for price_entity (never against model opinion alone).
    max_price: float | None = None
    price_entity: str | None = None


class GoalSpec(BaseModel):
    raw: str
    objective: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)
    success: SuccessCriteria = Field(default_factory=SuccessCriteria)
    forbidden_actions: list[str] = Field(default_factory=lambda: [
        "complete payment", "place order", "delete data", "close account", "send message",
    ])


# ---------------------------------------------------------------- observation

class ObservedElement(BaseModel):
    element_id: int
    role: str
    name: str = ""
    tag: str = ""
    input_type: str | None = None
    placeholder: str | None = None
    value: str | None = None
    disabled: bool = False
    in_dialog: bool = False
    covered: bool = False  # centre point is obscured by another element (e.g. an overlay)
    visibility: Literal["visible", "offscreen"] = "visible"
    checked: bool | None = None
    selected: bool | None = None
    bbox: dict[str, float] | None = None

    def describe(self) -> str:
        bits = [f"[{self.element_id}] {self.role}"]
        bits.append(f'"{self.name}"' if self.name else "(no accessible name)")
        if self.input_type and self.input_type not in ("text", "submit", "button"):
            bits.append(f"type={self.input_type}")
        if self.placeholder:
            bits.append(f'placeholder="{self.placeholder}"')
        if self.value:
            bits.append(f'value="{self.value}"')
        if self.disabled:
            bits.append("disabled")
        if self.in_dialog:
            bits.append("(inside dialog)")
        if self.covered:
            bits.append("(covered by overlay)")
        if self.visibility == "offscreen":
            bits.append("(off-screen; scroll to discover)")
        if self.checked is not None:
            bits.append("checked" if self.checked else "not checked")
        if self.selected is not None:
            bits.append("selected" if self.selected else "not selected")
        return " ".join(bits)

    def fingerprint_descriptor(self) -> str:
        """Stable task-state data; values are already masked by the observer for passwords."""
        return "|".join((self.role, self.name, self.input_type or "", self.value or "",
                         str(self.checked), str(self.selected), self.visibility, str(self.covered)))

    def descriptor(self) -> "TargetDescriptor":
        return TargetDescriptor(role=self.role, name=self.name, input_type=self.input_type)


class TargetDescriptor(BaseModel):
    """Stable semantic description of an element, for replay/evidence. Never a CSS selector."""
    role: str
    name: str = ""
    input_type: str | None = None


class Observation(BaseModel):
    observation_id: str
    url: str
    route: str
    title: str = ""
    heading: str = ""
    visible_text: str = ""
    aria_snapshot: str = ""
    elements: list[ObservedElement] = Field(default_factory=list)
    dialog_open: bool = False
    dialog_name: str = ""
    screenshot_id: str | None = None
    fingerprint: str = ""
    total_interactive: int = 0
    controls_truncated: bool = False
    text_truncated: bool = False


# ---------------------------------------------------------------- actions / model output

class BrowserAction(BaseModel):
    observation_id: str
    action: ActionType
    element_id: int | None = None
    display_label: str | None = None
    text: str | None = None
    submit: bool = False  # for TYPE: press Enter afterwards
    direction: Literal["up", "down"] | None = None
    key: Literal["Escape", "Enter", "Tab", "ArrowDown", "ArrowUp"] | None = None
    rationale: str = Field(default="", max_length=300)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def require_action_fields(self) -> "BrowserAction":
        """Reject incomplete actions instead of silently turning them into another action."""
        targeted = {ActionType.CLICK, ActionType.TYPE, ActionType.SELECT, ActionType.CHECK,
                    ActionType.UNCHECK, ActionType.HOVER}
        if self.action in targeted and self.element_id is None:
            raise ValueError(f"{self.action.value} requires element_id")
        if self.action in (ActionType.TYPE, ActionType.SELECT) and self.text is None:
            raise ValueError(f"{self.action.value} requires text")
        if self.action == ActionType.SCROLL and self.direction is None:
            raise ValueError("scroll requires direction")
        if self.action == ActionType.PRESS and self.key is None:
            raise ValueError("press requires key")
        if self.submit and self.action != ActionType.TYPE:
            raise ValueError("submit is only valid for type")
        return self


class ModelFact(BaseModel):
    kind: Literal["product_price", "cart_total", "page_heading"]
    entity: str
    value: float
    currency: str = "INR"
    context: Literal["product_page", "search_results", "cart", "checkout", "other"] = "other"


class ModelFinding(BaseModel):
    category: FindingCategory
    severity: Severity
    title: str
    evidence: str


class ModelDecision(BaseModel):
    """The single structured output of one reasoning call."""
    page_summary: str
    goal_progress: float = Field(ge=0.0, le=1.0)
    facts: list[ModelFact] = Field(default_factory=list)
    findings: list[ModelFinding] = Field(default_factory=list)
    next_action: BrowserAction


# ---------------------------------------------------------------- execution / memory

class ExecutionStep(BaseModel):
    step_id: str = Field(default_factory=short_id)
    step_number: int
    timestamp: datetime = Field(default_factory=utc_now)
    url_before: str
    url_after: str | None = None
    state_before: str | None = None
    state_after: str | None = None
    action: BrowserAction
    target: TargetDescriptor | None = None
    outcome: Outcome
    duration_ms: int = 0
    error: str | None = None
    screenshot_id: str | None = None
    recovery: bool = False


class AxeNode(BaseModel):
    html: str | None = None
    target: list[Any] = Field(default_factory=list)
    failure_summary: str | None = None


class AxeViolation(BaseModel):
    id: str
    impact: Literal["minor", "moderate", "serious", "critical"] | None = None
    description: str
    help: str
    help_url: str | None = None
    nodes: list[AxeNode] = Field(default_factory=list)
    total_nodes: int = 0  # true affected-element count; `nodes` is capped to a few examples


class CriticFinding(BaseModel):
    finding_id: str = Field(default_factory=short_id)
    code: str = ""  # human-facing id, e.g. UX-001, SEM-001, A11Y-001
    category: FindingCategory
    severity: Severity
    title: str
    evidence: str
    recommendation: str | None = None
    step_number: int
    state_id: str | None = None
    screenshot_id: str | None = None
    source: Literal["deterministic", "model", "axe"] = "deterministic"
    verified: bool = False
    data: dict[str, Any] = Field(default_factory=dict)


class PageFact(BaseModel):
    kind: Literal["product_price", "cart_total", "page_heading"]
    entity: str
    value: float
    currency: str = "INR"
    context: str = "other"
    step_number: int
    url: str
    state_id: str | None = None


class JourneyNode(BaseModel):
    id: str
    label: str
    url: str
    route: str
    step_number: int
    page_type: str | None = None
    annotation: str | None = None  # e.g. the goal product's price observed in this state
    dialog: bool = False
    screenshot_id: str | None = None
    friction_count: int = 0
    semantic_count: int = 0
    accessibility_count: int = 0
    visits: int = 1


class JourneyEdge(BaseModel):
    id: str
    source: str
    target: str
    action: str
    step_number: int
    duration_ms: int
    outcome: Outcome = "success"
    recovered: bool = False


class FrictionMetrics(BaseModel):
    total_actions: int = 0
    failed_interactions: int = 0
    blocked_interactions: int = 0
    backtracks: int = 0
    repeated_states: int = 0
    recoveries: int = 0
    interruptions: int = 0
    dead_ends: int = 0
    no_progress_actions: int = 0
    rejected_actions: int = 0
    validation_errors: int = 0

    def score(self) -> int:
        """Transparent internal heuristic (0 = frictionless). For relative comparison only."""
        raw = (5 * self.backtracks + 6 * self.repeated_states + 8 * self.failed_interactions
               + 8 * self.blocked_interactions + 10 * self.interruptions + 15 * self.dead_ends
               + 3 * self.no_progress_actions + 4 * self.validation_errors)
        return min(100, raw)


class RunMetrics(BaseModel):
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    model_calls: int = 0
    model_latencies_ms: list[int] = Field(default_factory=list)
    schema_failures: int = 0


class AgentState(BaseModel):
    run_id: str = Field(default_factory=short_id)
    goal: GoalSpec
    target_url: str
    provider: str = ""
    model: str = ""
    current_url: str = ""
    step_count: int = 0
    execution_history: list[ExecutionStep] = Field(default_factory=list)
    screenshot_id: str | None = None
    axe_results: list[AxeViolation] = Field(default_factory=list)
    critic_findings: list[CriticFinding] = Field(default_factory=list)
    journey_graph_nodes: list[JourneyNode] = Field(default_factory=list)
    journey_graph_edges: list[JourneyEdge] = Field(default_factory=list)
    journey_facts: list[PageFact] = Field(default_factory=list)
    status: RunStatus = RunStatus.IDLE
    next_action: BrowserAction | None = None
    last_outcome: Outcome | None = None
    last_outcome_note: str = ""
    goal_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    goal_completed: bool = False
    max_steps: int = 100
    stall_limit: int = 8
    last_progress_step: int = 0
    best_progress: float = 0.0
    recovery_attempts: int = 0
    consecutive_interruptions: int = 0  # unrecovered interruptions in a row; reset on each successful recovery
    max_recovery_attempts: int = 2
    in_recovery: bool = False
    attempt_failures: dict[str, int] = Field(default_factory=dict)
    blocked_reason: str | None = None
    accessibility_score: int = Field(default=100, ge=0, le=100)
    accessibility_coverage: Literal["not_run", "partial", "complete", "failed"] = "not_run"
    current_page_summary: str = ""
    current_state_id: str | None = None
    friction: FrictionMetrics = Field(default_factory=FrictionMetrics)
    metrics: RunMetrics = Field(default_factory=RunMetrics)
    run_error: str | None = None


# ---------------------------------------------------------------- websocket contract

EventType = Literal[
    "run_started", "browser_frame", "observation", "decision",
    "action_started", "action_completed", "axe_update", "finding",
    "journey_node", "journey_edge", "score_update", "run_completed", "run_failed",
]


class Event(BaseModel):
    run_id: str
    sequence: int
    timestamp: datetime = Field(default_factory=utc_now)
    offset_ms: int = 0
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
