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
  const verdict = comparison?.verdict.replaceAll('_', ' ').toUpperCase()

  return (
    <section className={`comparison-bar ${comparison ? `comparison-${comparison.verdict}` : ''}`} aria-label="Release comparison">
      <div className="comparison-title">
        <span className="comparison-icon" aria-hidden="true">⇄</span>
        <div><b>Release intelligence</b><small>Same goal. Deterministic evidence. No AI judge.</small></div>
      </div>
      {!comparison && (
        <>
          <span className="comparison-baseline">Baseline: {baselineId ? baselineId.slice(0, 8) : 'not selected'}</span>
          <button className="secondary-action comparison-button" disabled={!finished || busy} onClick={onSetBaseline}>
            {baselineId ? 'Replace baseline' : 'Set current as baseline'}
          </button>
          <button className="primary-action comparison-button" disabled={!canCompare || busy} onClick={onCompare}>
            {busy ? 'Comparing…' : 'Compare candidate'}
          </button>
        </>
      )}
      {comparison && (
        <>
          <span className="comparison-verdict">{verdict}</span>
          <div className="comparison-deltas">
            <span><b>{signed(comparison.deltas.actions)}</b> actions</span>
            <span><b>{signed(comparison.deltas.runtime_s, 's')}</b> time</span>
            <span><b>{signed(comparison.deltas.friction_score)}</b> friction</span>
            <span><b>{signed(comparison.deltas.accessibility_score)}</b> a11y</span>
            <span><b>{comparison.new_findings.length}</b> new verified</span>
          </div>
          <span className="comparison-reason">{comparison.reasons[0] ?? comparison.improvements[0] ?? 'No material evidence changed.'}</span>
          <button className="secondary-action comparison-button" onClick={onClear}>Close</button>
        </>
      )}
    </section>
  )
}
