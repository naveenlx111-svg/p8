import type { RunComparison } from '../types'
import type { RunState } from '../useRun'

interface Props {
  state: RunState
  baselineId: string | null
  comparison: RunComparison | null
  busy: boolean
  onSetBaseline: () => void
  onCompare: () => void
  onClear: () => void
}

const signed = (value: number, suffix = '') => `${value > 0 ? '+' : ''}${value}${suffix}`

export function ComparisonBar({ state, baselineId, comparison, busy, onSetBaseline, onCompare, onClear }: Props) {
  const finished = state.status === 'completed' || state.status === 'failed'
  const canCompare = finished && !!state.runId && !!baselineId && baselineId !== state.runId

  return (
    <section className="section" aria-label="Release comparison">
      <div className="section-head">
        <h2>Release comparison</h2>
        <p>Same goal, deterministic evidence, no AI judge.</p>
      </div>
      <div className="compare">
        {!comparison ? (
          <div className="compare-actions">
            <span className="mono muted" style={{ fontSize: 12 }}>Baseline: {baselineId ? baselineId.slice(0, 8) : 'not selected'}</span>
            <button className="btn btn-sm" disabled={!finished || busy} onClick={onSetBaseline}>{baselineId ? 'Replace baseline' : 'Set current as baseline'}</button>
            <button className="btn btn-sm btn-primary" disabled={!canCompare || busy} onClick={onCompare}>{busy ? 'Comparing…' : 'Compare candidate'}</button>
          </div>
        ) : (
          <>
            <div className="compare-line">
              <span className={`verdict ${comparison.verdict}`}>{comparison.verdict.replaceAll('_', ' ').toUpperCase()}</span>
              <span><b>{signed(comparison.deltas.actions)}</b> actions</span>
              <span><b>{signed(comparison.deltas.runtime_s, ' s')}</b> time</span>
              <span><b>{signed(comparison.deltas.friction_score)}</b> friction</span>
              <span><b>{signed(comparison.deltas.accessibility_score)}</b> accessibility</span>
              <span><b>{signed(comparison.deltas.experience_score)}</b> experience</span>
              <span><b>{comparison.new_findings.length}</b> new verified</span>
              <button className="btn btn-sm" style={{ marginLeft: 'auto' }} onClick={onClear}>Close</button>
            </div>
            <ul>
              {(comparison.reasons.length ? comparison.reasons : comparison.improvements.length ? comparison.improvements : ['No material evidence changed.']).map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </>
        )}
      </div>
    </section>
  )
}
