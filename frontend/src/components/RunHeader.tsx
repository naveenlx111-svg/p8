import { useEffect, useState } from 'react'
import { duration, isLive } from '../lib'
import type { RunState } from '../useRun'
import { ModeBadge, StatusBadge } from './ui'

export type Tab = 'watch' | 'actions' | 'report' | 'log'

// Remounted per run (keyed by run id), so the counter always starts at zero.
function useElapsed(status: RunState['status'], final: number | undefined) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (status !== 'running' && status !== 'connecting') return
    const i = setInterval(() => setSeconds(t => t + 1), 1000)
    return () => clearInterval(i)
  }, [status])
  return final ?? seconds
}

interface Props {
  state: RunState
  tab: Tab
  setTab: (t: Tab) => void
  onBack: () => void
  onCancel: () => void
  onReplay: () => void
  busy: boolean
}

export function RunHeader({ state, tab, setTab, onBack, onCancel, onReplay, busy }: Props) {
  const st = state.started
  const elapsed = useElapsed(state.status, state.summary?.runtime_s)
  const decisions = state.stream.filter(i => i.kind === 'decision').length
  const actions = state.summary?.actions ?? decisions
  const step = state.score?.step ?? state.frame?.step ?? 0
  const running = isLive(state)
  const tabs: [Tab, string, number | null][] = [
    ['watch', 'Watch', null], ['actions', 'Actions', decisions || null], ['report', 'Report', state.findings.length || null], ['log', 'Log', state.stream.length || null],
  ]

  return (
    <div className="run-head">
      <button className="back-link" onClick={onBack}>← Test</button>
      <div className="run-title-row">
        <div>
          <h1 className="run-title">{st?.goal.raw ?? 'Starting run…'}</h1>
          {st && <div className="run-sub">{st.platform === 'android' ? st.android_package ?? 'Android app' : st.target_url}</div>}
        </div>
        <div className="run-actions">
          {running
            ? <button className="btn btn-danger" disabled={busy} onClick={onCancel}>Stop run</button>
            : <button className="btn" disabled={busy} onClick={onReplay}>Replay golden run</button>}
        </div>
      </div>
      <div className="meta">
        <StatusBadge status={state.status} />
        <ModeBadge state={state} />
        <span>{duration(elapsed)}</span>
        <span>{actions} {actions === 1 ? 'action' : 'actions'}{running && st ? ` · step ${step}/${st.max_steps}` : ''}</span>
        {state.summary && <span>{state.summary.model_calls} model {state.summary.model_calls === 1 ? 'call' : 'calls'}</span>}
        {st && <span>{st.model} · {st.provider}</span>}
        {st && <span>{st.platform === 'android' ? 'Android' : 'Web'}</span>}
      </div>
      {state.status === 'disconnected' && (
        <div className="banner banner-warn"><span>{state.connectionError}</span><button className="btn btn-sm" onClick={onReplay}>Replay verified run</button></div>
      )}
      <div className="tabs" role="tablist">
        {tabs.map(([id, label, n]) => (
          <button key={id} role="tab" aria-selected={tab === id} className={`tab ${tab === id ? 'is-active' : ''}`} onClick={() => setTab(id)}>
            {label}{n !== null && <sup>{n}</sup>}
          </button>
        ))}
      </div>
    </div>
  )
}
