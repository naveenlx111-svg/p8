"""Self-contained HTML audit (screenshots embedded as data URIs so the file works when downloaded)."""
from __future__ import annotations

import base64
from html import escape
from pathlib import Path

from backend.agent.graph import summarize
from backend.runtime.accessibility import DISCLAIMER
from backend.schemas import AgentState

SEV_COLOR = {"critical": "#b42318", "high": "#d92d20", "medium": "#dc6803", "low": "#667085", "info": "#1570ef"}
SECTIONS = [
    ("UX friction & obstructions", {"friction", "occlusion", "dead_end", "ambiguity", "goal_progress"}),
    ("Semantic inconsistencies", {"semantic_inconsistency"}),
    ("Accessibility (axe-core)", {"accessibility"}),
    ("Autonomous recoveries", {"recovery"}),
    ("Safety gate", {"safety"}),
]


def _img(run_dir: Path, shot: str | None, width: int = 420) -> str:
    if not shot or not (run_dir / shot).exists():
        return ""
    b64 = base64.b64encode((run_dir / shot).read_bytes()).decode()
    return f'<img src="data:image/jpeg;base64,{b64}" width="{width}" alt="Screenshot {escape(shot)}">'


def render_report(state: AgentState, run_dir: Path) -> str:
    s = summarize(state)
    nodes = {n.id: n for n in state.journey_graph_nodes}
    cats = s["findings_by_category"]
    ux = sum(cats.get(c, 0) for c in ("friction", "occlusion", "dead_end", "ambiguity"))
    status_ok = state.goal_completed

    journey_rows = []
    for st in state.execution_history:
        before, after = nodes.get(st.state_before), nodes.get(st.state_after)
        a = st.action
        what = f"{a.action.value} {escape(a.display_label or '')}" + (f" “{escape(a.text)}”" if a.text else "")
        journey_rows.append(
            f"<tr><td>{st.step_number}</td><td>{escape(before.label if before else '?')}</td><td>{what}</td>"
            f"<td class='o-{st.outcome}'>{st.outcome}{' · recovery' if st.recovery else ''}</td>"
            f"<td>{escape(after.label if after else '?')}</td><td>{escape(a.rationale)}</td></tr>")

    finding_html = []
    for title, cset in SECTIONS:
        items = [f for f in state.critic_findings if f.category in cset]
        if not items:
            continue
        cards = []
        for f in items:
            node = nodes.get(f.state_id or "")
            shot = f.screenshot_id or (node.screenshot_id if node else None)
            extra = ""
            if f.category == "semantic_inconsistency":
                d = f.data
                bn, an = nodes.get(d.get("before_state")), nodes.get(d.get("after_state"))
                extra = (f"<div class='pair'><figure>{_img(run_dir, bn.screenshot_id if bn else None, 300)}"
                         f"<figcaption>{escape(d.get('before_context', ''))}: ₹{d.get('before', 0):,.0f}</figcaption></figure>"
                         f"<figure>{_img(run_dir, an.screenshot_id if an else None, 300)}"
                         f"<figcaption>{escape(d.get('after_context', ''))}: ₹{d.get('after', 0):,.0f}</figcaption></figure></div>")
                shot = None
            if f.category == "accessibility" and f.data.get("html"):
                extra = f"<pre>{escape(f.data['html'])}</pre>"
            src = {"deterministic": "verified by deterministic check", "axe": "verified by axe-core",
                   "model": "AI observation (unverified)"}[f.source]
            cards.append(
                f"<div class='finding'><div class='fh'><span class='code'>{escape(f.code)}</span>"
                f"<span class='sev' style='background:{SEV_COLOR[f.severity]}'>{f.severity.upper()}</span>"
                f"<b>{escape(f.title)}</b></div><p>{escape(f.evidence)}</p>"
                + (f"<p class='rec'>Recommendation: {escape(f.recommendation)}</p>" if f.recommendation else "")
                + f"<p class='meta'>Step {f.step_number} · {src}</p>{extra}{_img(run_dir, shot)}</div>")
        finding_html.append(f"<h2>{title}</h2>{''.join(cards)}")

    fr = state.friction
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>PathLens audit {escape(state.run_id)}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:1000px;margin:32px auto;padding:0 20px;color:#101828;line-height:1.45}}
h1{{margin-bottom:4px}} h2{{margin-top:36px;border-bottom:2px solid #eaecf0;padding-bottom:6px}}
.meta{{color:#667085;font-size:13px}} table{{border-collapse:collapse;width:100%;font-size:14px}}
td,th{{border-bottom:1px solid #eaecf0;padding:7px 8px;text-align:left;vertical-align:top}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:20px 0}}
.kpi{{border:1px solid #eaecf0;border-radius:10px;padding:12px}} .kpi b{{font-size:26px;display:block}}
.finding{{border:1px solid #eaecf0;border-radius:10px;padding:14px;margin:12px 0}}
.fh{{display:flex;gap:10px;align-items:center}} .code{{font-family:monospace;color:#475467}}
.sev{{color:#fff;border-radius:6px;padding:1px 8px;font-size:12px;font-weight:700}}
.rec{{color:#344054}} pre{{background:#f2f4f7;padding:8px;border-radius:6px;white-space:pre-wrap;font-size:12px}}
.pair{{display:flex;gap:12px}} figure{{margin:0}} figcaption{{font-size:13px;font-weight:600}}
img{{border:1px solid #d0d5dd;border-radius:6px;margin-top:8px}}
.o-success{{color:#067647}} .o-blocked,.o-rejected{{color:#dc6803}} .o-failed,.o-stale{{color:#b42318}}
.status{{display:inline-block;padding:3px 10px;border-radius:6px;color:#fff;font-weight:700;background:{'#067647' if status_ok else '#b42318'}}}
</style></head><body>
<p class="meta">PATHLENS · AUTONOMOUS UX AUDIT</p>
<h1>{escape(state.goal.raw)}</h1>
<p class="meta">Target {escape(state.target_url)} · Run {escape(state.run_id)} · {state.metrics.started_at:%Y-%m-%d %H:%M UTC} ·
Model {escape(state.provider)}/{escape(state.model)}{' (OFFLINE TEST DOUBLE, not AI)' if state.provider == 'scripted' else ''}</p>
<p><span class="status">{'GOAL REACHED · VERIFIED' if status_ok else 'GOAL NOT REACHED'}</span>
{'' if status_ok else escape(state.run_error or '')}</p>

<h2>Executive summary</h2>
<div class="kpis">
<div class="kpi"><b>{ux}</b>UX obstruction{'s' if ux != 1 else ''}</div>
<div class="kpi"><b>{cats.get('semantic_inconsistency', 0)}</b>semantic inconsistenc{'ies' if cats.get('semantic_inconsistency', 0) != 1 else 'y'}</div>
<div class="kpi"><b>{cats.get('accessibility', 0)}</b>accessibility rule violations</div>
<div class="kpi"><b>{fr.recoveries}</b>autonomous recover{'ies' if fr.recoveries != 1 else 'y'}</div>
<div class="kpi"><b>{state.accessibility_score}/100</b>automated accessibility risk score</div>
</div>
<p class="meta">{escape(DISCLAIMER)}</p>
<p>{state.step_count} actions in {s['runtime_s']}s · {s['model_calls']} model calls (p50 {s['model_latency_p50_ms']} ms) ·
friction events: {fr.interruptions} interruption, {fr.blocked_interactions} blocked, {fr.failed_interactions} failed,
{fr.repeated_states} repeated state, {fr.backtracks} backtracks, {fr.no_progress_actions} no-progress actions
(internal friction heuristic {fr.score()}/100, lower is better; for relative comparison only).</p>

<h2>Journey</h2>
<table><tr><th>#</th><th>From state</th><th>Action</th><th>Outcome</th><th>To state</th><th>Agent rationale</th></tr>
{''.join(journey_rows)}</table>
{''.join(finding_html)}
<p class="meta" style="margin-top:40px">Generated by PathLens. The AI investigates the experience; deterministic tooling
verifies what should be deterministic (fact comparison, goal completion, axe-core rules).</p>
</body></html>"""


def write_report(state: AgentState, run_dir: Path) -> Path:
    path = run_dir / "report.html"
    path.write_text(render_report(state, run_dir), encoding="utf-8")
    return path
