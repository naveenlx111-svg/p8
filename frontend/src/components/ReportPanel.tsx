import { artifactBase, backendUrl } from '../lib'
import type { RunState } from '../useRun'

const IMPACT_COLOR: Record<string, string> = { critical: 'var(--bad)', serious: 'var(--bad)', moderate: 'var(--warn)', minor: 'var(--faint)' }

export function ReportPanel({ state, platform, onInspect }: { state: RunState; platform: 'web' | 'android'; onInspect: (id: string) => void }) {
  const sc = state.score
  const score = sc?.accessibility_score ?? 100
  const counts = sc?.accessibility_counts ?? { critical: 0, serious: 0, moderate: 0, minor: 0 }
  const tone = score >= 90 ? 'good' : score >= 70 ? 'warning' : 'poor'
  const fr = sc?.friction
  const base = artifactBase(state)
  const report = state.summary?.report_url ? `${backendUrl}${state.summary.report_url}` : null
  const video = state.summary?.video_url ? `${backendUrl}${state.summary.video_url}` : null
  const a11yFindings = state.findings.filter(f => f.category === 'accessibility')
  const method = (state.started?.platform ?? platform) === 'android'
    ? 'UIAutomator hierarchy + deterministic accessible-name and 48dp touch-target checks.'
    : 'Browser accessibility snapshot + axe-core rules + keyboard focus traversal for dialogs.'
  const nFindings = (id: string) => state.findings.filter(f => f.state_id === id).length
  const experience = state.summary?.experience_score
  const loopFindings = state.findings.filter(f => f.data?.rule === 'semantic-action-cycle')

  return (
    <>
      <div className="report-grid">
        <section>
          {experience && (
            <>
              <div className="subhead">Evidence-weighted experience score</div>
              <div className={`score ${experience.overall >= 80 ? 'good' : experience.overall >= 60 ? 'warning' : 'poor'}`}>{experience.overall}<small>/100</small></div>
              <p className="fineprint"><b>{experience.verdict.replaceAll('_', ' ')}</b> · {experience.method}</p>
              <div className="score-breakdown">
                {([['outcome', experience.outcome], ['efficiency', experience.efficiency], ['accessibility', experience.accessibility], ['consistency', experience.consistency], ['resilience', experience.resilience], ['coverage', experience.coverage]] as const).map(([label, value]) => <span key={label}><b>{value}</b><small>{label}</small></span>)}
              </div>
              <ul className="rows">{experience.explanation.map((item, i) => <li key={i}>{item}</li>)}</ul>
            </>
          )}
          <div className="subhead">{sc ? 'Accessibility score' : 'Awaiting first audit'}</div>
          <div className={`score ${tone}`} key={score}>{sc ? score : '—'}<small>/100</small></div>
          <div className="counts">
            {(['critical', 'serious', 'moderate', 'minor'] as const).map(k => <span key={k}><i style={{ background: IMPACT_COLOR[k] }} />{counts[k] ?? 0} {k}</span>)}
          </div>
          {state.violations.length > 0 && (
            <>
              <div className="subhead">Rule violations</div>
              <ul className="rows">
                {state.violations.map(v => <li key={v.id}><span className="k">{v.id}</span><span>{v.help}</span><span className="muted" style={{ marginLeft: 'auto' }}>{v.impact}</span></li>)}
              </ul>
            </>
          )}
          <p className="fineprint"><b>Approach:</b> {method} {sc?.disclaimer ?? 'Automated heuristic based on detected accessibility violations; not a WCAG certification.'}</p>
        </section>

        <section>
          {fr && (
            <>
              <div className="subhead">Measured friction events</div>
              <div className="kv">
                {([['interruptions', fr.interruptions], ['recoveries', fr.recoveries], ['blocked', fr.blocked_interactions],
                  ['repeated states', fr.repeated_states], ['backtracks', fr.backtracks], ['no progress', fr.no_progress_actions]] as const)
                  .map(([k, v]) => <div key={k}><b>{v}</b><span>{k}</span></div>)}
              </div>
            </>
          )}
          {a11yFindings.length > 0 && (
            <>
              <div className="subhead">Accessibility evidence and fixes</div>
              <ul className="rows">
                {a11yFindings.map(f => (
                  <li key={f.finding_id} style={{ flexDirection: 'column', gap: 3 }}>
                    <span><span className="k">{f.code}</span> · <b style={{ fontWeight: 500 }}>{f.title}</b></span>
                    <span className="muted">{f.evidence}</span>
                    {f.recommendation && <span><b style={{ fontWeight: 500 }}>Fix:</b> {f.recommendation}</span>}
                    {f.data.accessibility_tree_id && <a href={`${base}${f.data.accessibility_tree_id}`} target="_blank" rel="noreferrer">Open captured accessibility tree</a>}
                  </li>
                ))}
              </ul>
            </>
          )}
          {loopFindings.length > 0 && (
            <>
              <div className="subhead">Journey loop and alternate paths</div>
              <ul className="rows">
                {loopFindings.map(f => <li key={f.finding_id} style={{ flexDirection: 'column', gap: 4 }}>
                  <b>{f.title}</b><span className="muted">{f.data.action_trace?.join(' → ')}</span>
                  {f.data.alternative_actions?.length > 0 && <span><b>Available exits:</b> {f.data.alternative_actions.join(' · ')}</span>}
                </li>)}
              </ul>
            </>
          )}
          {(video || report) && (
            <>
              <div className="subhead">Artifacts</div>
              <div className="downloads">
                {video && <a className="btn btn-link" href={video} target="_blank" rel="noreferrer">Journey video</a>}
                {report && <a className="btn btn-link btn-primary" href={`${report}?download=true`}>Download audit</a>}
              </div>
            </>
          )}
        </section>
      </div>

      <section className="section" aria-label="Evidence">
        <div className="section-head"><h2>Evidence</h2><p>The screen captured at each state the agent reached.</p></div>
        {state.nodeOrder.length === 0
          ? <div className="empty-line">Screens are captured as the run progresses.</div>
          : <div style={{ borderTop: '1px solid var(--line)' }}>
              {state.nodeOrder.map((id, i) => {
                const n = state.nodes[id]
                const count = nFindings(id)
                return (
                  <div className="evidence-row" key={id}>
                    <button className="thumb" onClick={() => onInspect(id)} title="Open in the browser view">
                      {n.screenshot_id && <img src={base + n.screenshot_id} alt={n.label} loading="lazy" />}<b>{i + 1}</b>
                    </button>
                    <div>
                      <h3>{n.label}</h3>
                      <p className="mono">{n.route || n.url}</p>
                      <p>step {n.step_number}{n.visits > 1 ? ` · visited ${n.visits}×` : ''} · {count} {count === 1 ? 'finding' : 'findings'}</p>
                    </div>
                    <div className="links">
                      {n.accessibility_tree_id && <a href={base + n.accessibility_tree_id} target="_blank" rel="noreferrer">Accessibility tree</a>}
                      <button className="link-btn" onClick={() => onInspect(id)}>View screen</button>
                    </div>
                  </div>
                )
              })}
            </div>}
      </section>
    </>
  )
}
