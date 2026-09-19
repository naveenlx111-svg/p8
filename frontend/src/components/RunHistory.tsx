import type { RunHistoryItem } from '../types'

interface Props {
  runs: RunHistoryItem[]
  currentId?: string | null
  baselineId?: string | null
  onRefresh: () => void
  onUseAsBaseline: (runId: string) => void
}

export function RunHistory({ runs, currentId, baselineId, onRefresh, onUseAsBaseline }: Props) {
  return (
    <section className="section history-panel" aria-label="Run history">
      <div className="section-head">
        <div><h2>Run memory</h2><p>Recent journeys stay available for evidence-based comparison.</p></div>
        <button className="btn btn-sm" onClick={onRefresh}>Refresh</button>
      </div>
      {!runs.length ? <p className="muted">No completed runs recorded yet.</p> : (
        <div className="history-list">
          {runs.slice(0, 12).map(run => {
            const score = run.experience_score ?? run.accessibility_score
            const isCurrent = run.run_id === currentId
            return <div className={`history-row ${isCurrent ? 'is-current' : ''}`} key={run.run_id}>
              <div className="history-main"><b>{run.goal}</b><span className="muted">{run.platform === 'android' ? 'Android' : (run.target_url || 'Web')} · {run.run_id.slice(0, 8)}</span></div>
              <div className="history-metrics"><strong>{score ?? '—'}</strong><span>experience</span><span className={run.goal_completed ? 'history-ok' : 'history-bad'}>{run.goal_completed ? 'verified' : run.status}</span></div>
              <button className="btn btn-sm" disabled={isCurrent} onClick={() => onUseAsBaseline(run.run_id)}>{baselineId === run.run_id ? 'Baseline selected' : 'Use as baseline'}</button>
            </div>
          })}
        </div>
      )}
    </section>
  )
}
