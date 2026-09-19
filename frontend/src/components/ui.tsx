import type { Severity } from '../types'
import type { RunState } from '../useRun'

const STATUS: Record<RunState['status'], [string, string]> = {
  idle: ['Ready', 'idle'], connecting: ['Connecting', 'run'], running: ['Running', 'run'],
  disconnected: ['Disconnected', 'warn'], completed: ['Completed', 'ok'], failed: ['Failed', 'bad'],
}

export function StatusBadge({ status }: { status: RunState['status'] }) {
  const [label, tone] = STATUS[status]
  return <span className={`badge badge-${tone}`}><i />{label}</span>
}

export function ModeBadge({ state }: { state: RunState }) {
  const st = state.started
  if (!st) return null
  const mode = st.mode === 'replay' ? 'REPLAY' : st.offline_test_double ? 'TEST DOUBLE' : 'LIVE'
  const title = mode === 'REPLAY' ? 'Recorded run of the identical workflow — not live' : mode === 'TEST DOUBLE' ? 'Offline heuristic test double — not AI' : 'Live autonomous run'
  return <span className={`mode mode-${mode === 'LIVE' ? 'live' : mode === 'REPLAY' ? 'replay' : 'double'}`} title={title}>{mode}</span>
}

const LEVEL: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 1 }

export function SeverityIndicator({ severity }: { severity: Severity | string }) {
  const level = LEVEL[severity] ?? 1
  return (
    <span className={`sev sev-${severity}`}>
      <span className="sev-bars" aria-hidden="true">{[1, 2, 3, 4].map(i => <i key={i} className={i <= level ? 'on' : ''} style={{ height: 3 + i * 2 }} />)}</span>
      {severity}
    </span>
  )
}
