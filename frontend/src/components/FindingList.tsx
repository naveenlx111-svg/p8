import { SEVERITY_RANK, money } from '../lib'
import type { Finding } from '../types'
import type { RunState } from '../useRun'
import { SeverityIndicator } from './ui'

function Row({ f, canInspect, onInspect }: { f: Finding; canInspect: boolean; onInspect: (id: string) => void }) {
  const observed = f.source === 'model'
  const src = observed ? 'Model observation, not verified' : f.source === 'axe' ? 'Confirmed by axe-core' : 'Confirmed by a deterministic check'
  const price = f.category === 'semantic_inconsistency' && f.data.before !== undefined
  return (
    <article className={`finding ${observed ? 'is-observed' : ''}`}>
      <div className="finding-id">{f.code}</div>
      <div className="finding-body">
        <h3>{f.category === 'recovery' || observed ? f.title : <span>{f.title}</span>}</h3>
        {price ? (
          <div className="finding-price">
            <span>{String(f.data.before_context).replace('_', ' ')} <b>{money(f.data.before, f.data.currency)}</b></span>
            <span>→</span>
            <span>{String(f.data.after_context).replace('_', ' ')} <b>{money(f.data.after, f.data.currency)}</b></span>
            <em>{f.data.difference > 0 ? '+' : ''}{money(f.data.difference, f.data.currency)} ({f.data.percent > 0 ? '+' : ''}{f.data.percent}%)</em>
          </div>
        ) : <p>{f.evidence}</p>}
        {f.recommendation && <p className="fix"><b>Fix:</b> {f.recommendation}</p>}
      </div>
      <div className="finding-meta">
        <SeverityIndicator severity={f.severity} />
        <span className={`src ${observed ? 'is-observed' : ''}`}>{src}</span>
        <span className="step">step {f.step_number}</span>
        {canInspect && <button className="link-btn" onClick={() => onInspect(f.state_id!)}>View screen</button>}
      </div>
    </article>
  )
}

export function FindingList({ state, onInspect }: { state: RunState; onInspect: (id: string) => void }) {
  const sorted = state.findings
    .map((f, i) => ({ f, i }))
    .sort((a, b) => (SEVERITY_RANK[b.f.severity] ?? 0) - (SEVERITY_RANK[a.f.severity] ?? 0) || a.i - b.i)
    .map(x => x.f)
  return (
    <section className="section" aria-label="What it found">
      <div className="section-head">
        <h2>What it found</h2>
        <p>Highlighted problems were confirmed in code. Unhighlighted, italic ones are the model’s unconfirmed observations.</p>
      </div>
      {sorted.length === 0
        ? <div className="empty-line">{state.status === 'completed' || state.status === 'failed' ? 'No problems were recorded for this run.' : 'Findings appear here as the agent verifies them.'}</div>
        : <div className="findings">{sorted.map(f => <Row key={f.finding_id} f={f} canInspect={!!f.state_id && f.state_id in state.nodes} onInspect={onInspect} />)}</div>}
    </section>
  )
}
