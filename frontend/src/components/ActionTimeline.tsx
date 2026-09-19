import { useEffect, useRef } from 'react'
import { VERBS, isLive, money } from '../lib'
import type { RunState, StreamItem } from '../useRun'
import { SeverityIndicator } from './ui'

const OUTCOME_TONE: Record<string, string> = { success: 'ok', blocked: 'warn', rejected: 'warn', stale: '', failed: 'bad' }

function Step({ it, current, detailed }: { it: Extract<StreamItem, { kind: 'decision' }>; current: boolean; detailed: boolean }) {
  const d = it.d, o = it.outcome
  const verb = VERBS[d.action] ?? d.action.charAt(0).toUpperCase() + d.action.slice(1)
  const tone = o ? OUTCOME_TONE[o.outcome] : ''
  return (
    <li className={`tl-item ${current ? 'is-current' : ''} ${o?.outcome === 'blocked' || o?.outcome === 'rejected' ? 'is-blocked' : ''} ${o?.outcome === 'failed' ? 'is-failed' : ''}`}>
      <span className="tl-num">{String(d.step).padStart(2, '0')}</span>
      <div>
        <div className="tl-title">{verb}{d.label && <> <b>“{d.label}”</b></>}{d.text && <> with <b>“{d.text}”</b></>}</div>
        <div className="tl-desc">{d.rationale}</div>
      </div>
      <span className={`tl-state ${tone}`}>
        {o ? (o.outcome === 'success' ? '✓' : o.outcome) : current ? 'acting…' : ''}{o?.recovery ? ' · recovery' : ''}
      </span>
      <div className="tl-meta" style={{ gridColumn: '2 / 4' }}>
        <span>{d.observed}</span>
        <span>{(d.latency_ms / 1000).toFixed(1)} s to decide</span>
        {d.facts.map((f, i) => <span key={i} className="fact">read {f.entity} {money(f.value, f.currency)}</span>)}
      </div>
      {detailed && (
        <dl className="tl-detail">
          <dt>Confidence</dt><dd>{Math.round(d.confidence * 100)}% · goal progress {Math.round(d.goal_progress * 100)}% (model estimate)</dd>
          <dt>Model input</dt><dd>{d.vision ? 'text + screenshot' : 'text only'}{d.attempts > 1 ? ` · ${d.attempts} attempts` : ''}</dd>
          {o && <><dt>Action took</dt><dd>{(o.duration_ms / 1000).toFixed(1)} s{o.error ? ` · ${o.error}` : ''}</dd></>}
          {d.facts_rejected.length > 0 && <><dt>Not remembered</dt><dd>{d.facts_rejected.map(f => `${f.entity} ${money(f.value, f.currency)}`).join(', ')} (not found in visible text)</dd></>}
        </dl>
      )}
    </li>
  )
}

function Note({ it }: { it: Exclude<StreamItem, { kind: 'decision' }> }) {
  if (it.kind === 'finding') {
    const f = it.f
    return (
      <li className="tl-note">
        <SeverityIndicator severity={f.severity} /><span><b>{f.title}</b></span>
        <span className="tag">{f.source === 'model' ? 'model observation' : 'verified'}</span>
      </li>
    )
  }
  if (it.kind === 'verified')
    return <li className="tl-note"><span style={{ color: 'var(--ok)' }}>✓</span><span><b>{it.modelJudged ? 'Goal judged by the model' : 'Goal verified by code'}</b> · {it.evidence.join(' · ')}</span></li>
  return <li className="tl-note"><span style={{ color: 'var(--warn)' }}>!</span><span><b>Action rejected</b> · {it.a.error}</span></li>
}

export function ActionTimeline({ state, detailed = false, onReplay }: { state: RunState; detailed?: boolean; onReplay: () => void }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!detailed) ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: 'smooth' })
  }, [state.stream.length, state.status, detailed])
  const s = state.summary
  const lastDecision = [...state.stream].reverse().find(i => i.kind === 'decision')

  return (
    <div ref={ref} className={`timeline ${detailed ? 'is-detailed' : ''}`}>
      {state.stream.length === 0 && (
        <div className="tl-empty">
          {isLive(state) ? 'Waiting for the first decision.' : 'The agent’s actions appear here as they happen.'}
          <ol><li><b>01</b>Observe</li><li><b>02</b>Decide</li><li><b>03</b>Act</li></ol>
        </div>
      )}
      <ol style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {state.stream.map(it => it.kind === 'decision'
          ? <Step key={it.seq} it={it} detailed={detailed} current={state.status === 'running' && it === lastDecision && !it.outcome} />
          : <Note key={it.seq} it={it} />)}
      </ol>
      {state.status === 'completed' && s && (
        <div className={`tl-end ${s.goal_completed ? 'ok' : ''}`}>
          <strong>{s.goal_completed ? (s.completion_mode === 'model_judged' ? 'Goal reached, judged by the model' : 'Goal reached and confirmed by code') : 'Run finished without reaching the goal'}</strong>
          <p>{s.actions} actions · {s.recoveries} recoveries · {s.runtime_s} s{s.reason ? ` · ${s.reason}` : ''}</p>
        </div>
      )}
      {state.status === 'failed' && s && (
        <div className="tl-end bad">
          <strong>Run not completed</strong>
          <p>{s.reason ?? s.error}</p>
          <button onClick={onReplay} className="btn btn-sm">Switch to golden replay (recorded run, not live)</button>
        </div>
      )}
    </div>
  )
}
