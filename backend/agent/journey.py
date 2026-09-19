"""Journey graph: every semantic UI state is a node (keyed by fingerprint), every attempted action is an edge."""
from __future__ import annotations

import re

from backend.schemas import AgentState, ExecutionStep, JourneyEdge, JourneyNode, Observation


def page_type(route: str) -> str:
    frag = route.split("#", 1)[1] if "#" in route else route
    seg = [s for s in frag.split("?")[0].split("/") if s]
    if not seg:
        return "home"
    return re.sub(r"\.(html?|php|aspx?|jsp)$", "", seg[0], flags=re.I)


def node_label(obs: Observation) -> str:
    base = (obs.heading or page_type(obs.route).replace("-", " ").replace("_", " ").title())[:40]
    return f"{base} + dialog" if obs.dialog_open else base


def upsert_node(state: AgentState, obs: Observation) -> tuple[JourneyNode, bool]:
    """Returns (node, is_new)."""
    for n in state.journey_graph_nodes:
        if n.id == obs.fingerprint:
            n.visits += 1
            return n, False
    node = JourneyNode(
        id=obs.fingerprint, label=node_label(obs), url=obs.url, route=obs.route, step_number=state.step_count,
        page_type=page_type(obs.route), dialog=obs.dialog_open, screenshot_id=obs.screenshot_id,
        accessibility_tree_id=obs.accessibility_tree_id,
    )
    state.journey_graph_nodes.append(node)
    return node, True


def get_node(state: AgentState, node_id: str | None) -> JourneyNode | None:
    return next((n for n in state.journey_graph_nodes if n.id == node_id), None)


def add_edge(state: AgentState, step: ExecutionStep) -> JourneyEdge:
    a = step.action
    label = a.action.value if not a.display_label else f"{a.action.value} “{a.display_label}”"
    if a.action.value == "type" and a.text:
        label = f"type “{a.text}”"
    edge = JourneyEdge(
        id=f"e{step.step_number}", source=step.state_before or "", target=step.state_after or step.state_before or "",
        action=label, step_number=step.step_number, duration_ms=step.duration_ms, outcome=step.outcome,
        recovered=step.recovery,
    )
    state.journey_graph_edges.append(edge)
    return edge
