import { useEffect, useRef } from 'react'
import type { Finding } from '../types'
import type { RunState, StreamItem } from '../useRun'

const SEV: Record<string, string> = {
  critical: 'border-red-600 bg-red-50 text-red-900',
  high: 'border-red-500 bg-red-50 text-red-900',
  medium: 'border-amber-500 bg-amber-50 text-amber-900',
  low: 'border-slate-400 bg-slate-50 text-slate-800',
  info: 'border-emerald-500 bg-emerald-50 text-emerald-900',
}
const OUTCOME: Record<string, string> = {
  success: 'bg-emerald-100 text-emerald-800', blocked: 'bg-amber-100 text-amber-800', rejected: 'bg-amber-100 text-amber-800',
  stale: 'bg-slate-200 text-slate-700', failed: 'bg-red-100 text-red-800',
}
const SYMBOL: Record<string, string> = { INR: '₹', USD: '$', EUR: '€', GBP: '£' }
const money = (v: number, cur = 'INR') =>
  cur === 'INR'
    ? '₹' + Math.round(v).toLocaleString('en-IN')
    : (SYMBOL[cur] ?? cur + ' ') + v.toLocaleString('en-US', { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 })

function FindingCard({ f }: { f: Finding }) {
  const verified = f.source === 'model' ? 'AI observation · unverified' : f.source === 'axe' ? 'verified by axe-core' : 'verified deterministically'
  return (
    <div className={`slide-in rounded-lg border-l-4 px-3 py-2 ${SEV[f.severity]}`}>
      <div className="flex items-center gap-2 text-xs font-bold tracking-wide">
        <span>{f.category === 'recovery' ? '✓' : '⚠'} {f.severity.toUpperCase()}</span>
        <span className="font-mono font-medium opacity-70">{f.code}</span>
        <span className="ml-auto font-medium opacity-70">{verified}</span>
      </div>
      <div className="mt-0.5 text-sm font-semibold">{f.title}</div>
      {f.category === 'semantic_inconsistency' && f.data.before !== undefined ? (
        <div className="mt-1 flex items-center gap-3 text-sm">
          <span>{String(f.data.before_context).replace('_', ' ')} <b className="text-base">{money(f.data.before, f.data.currency)}</b></span>
          <span>→</span>
          <span>{String(f.data.after_context).replace('_', ' ')} <b className="text-base">{money(f.data.after, f.data.currency)}</b></span>
          <span className="ml-auto rounded bg-red-600 px-1.5 py-0.5 text-xs font-bold text-white">
            {f.data.difference > 0 ? '+' : ''}{money(f.data.difference, f.data.currency)} ({f.data.percent > 0 ? '+' : ''}{f.data.percent}%)
          </span>
        </div>
      ) : f.data.rule === 'semantic-action-cycle' ? (
        <div className="mt-1 text-xs">
          <div className="font-mono opacity-90">{(f.data.action_trace ?? []).join(' → ')}</div>
          {(f.data.alternative_actions ?? []).length > 0 && <div className="mt-1"><b>Alternative paths:</b> {(f.data.alternative_actions ?? []).join(' · ')}</div>}
        </div>
      ) : (
        <div className="mt-0.5 line-clamp-2 text-xs opacity-80">{f.evidence}</div>
      )}
      {f.recommendation && <div className="mt-1 text-xs"><b>Recommendation:</b> {f.recommendation}</div>}
    </div>
  )
}

function Item({ it }: { it: StreamItem }) {
  if (it.kind === 'finding') return <FindingCard f={it.f} />
  if (it.kind === 'verified')
    return (
      <div className={`slide-in rounded-lg border-l-4 px-3 py-2 ${it.modelJudged ? 'border-amber-500 bg-amber-50 text-amber-900' : 'border-emerald-600 bg-emerald-50 text-emerald-900'}`}>
        <div className="text-xs font-bold tracking-wide">{it.modelJudged ? '◐ GOAL REACHED · MODEL-JUDGED (NOT CODE-VERIFIED)' : '✓ GOAL VERIFIED BY CODE'}</div>
        <div className="text-sm">{it.evidence.join(' · ')}</div>
      </div>
    )
  if (it.kind === 'rejected')
    return (
      <div className="rounded-lg border-l-4 border-amber-500 bg-amber-50 px-3 py-2 text-xs text-amber-900">
        <b>Action rejected:</b> {it.a.error}
      </div>
    )
  const d = it.d
  const verb = d.action.toUpperCase()
  return (
    <div className="rounded-lg border border-slate-200 px-3 py-2">
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
        <span className="text-slate-900">STEP {d.step}</span>
        <span className="truncate">Observed: {d.observed}</span>
        <span className="ml-auto shrink-0">{Math.round(d.confidence * 100)}% · {(d.latency_ms / 1000).toFixed(1)}s</span>
      </div>
      {d.facts.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {d.facts.map((f, i) => (
            <span key={i} className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-800">
              remembered: {f.entity} {money(f.value, f.currency)}
            </span>
          ))}
        </div>
      )}
      <div className="mt-1 flex items-center gap-2">
        <span className="text-sm font-bold text-slate-900">
          → {verb} {d.label ? `“${d.label}”` : ''}{d.text ? ` “${d.text}”` : ''}
        </span>
        {it.outcome && (
          <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${OUTCOME[it.outcome.outcome]}`}>
            {it.outcome.outcome}{it.outcome.recovery ? ' · recovery' : ''}
          </span>
        )}
      </div>
      <div className="text-xs text-slate-600">{d.rationale}</div>
    </div>
  )
}

export function DecisionStream({ state, onReplay }: { state: RunState; onReplay: () => void }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: 'smooth' })
  }, [state.stream.length, state.status])
  const s = state.summary

  return (
    <section className="workspace-panel flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white">
      <h2 className="border-b border-slate-200 px-3 py-2 text-xs font-bold tracking-widest text-slate-500">DECISION STREAM</h2>
      <div ref={ref} className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-3">
        {state.stream.length === 0 && <div className="stream-empty"><div className="empty-icon" aria-hidden="true">≋</div><h3>Every decision, in the open.</h3><p>Follow the reasoning behind each action.<br />Findings and recoveries will appear here.</p><div className="stream-steps"><span><b>01</b> Observe</span><span><b>02</b> Decide</span><span><b>03</b> Act</span></div></div>}
        {state.stream.map(it => <Item key={it.seq} it={it} />)}
        {state.status === 'completed' && s && (
          <div className="slide-in rounded-lg bg-emerald-600 px-3 py-3 text-white">
            <div className="text-sm font-extrabold tracking-wide">{s.completion_mode === 'model_judged' ? 'MISSION COMPLETE · MODEL-JUDGED (add "Done when" criteria to verify)' : 'MISSION COMPLETE · GOAL VERIFIED'}</div>
            <div className="mt-1 text-sm">
              {s.actions} actions · {s.recoveries} autonomous recovery · {s.findings_by_category.semantic_inconsistency ?? 0} semantic
              inconsistency · {(s.findings_by_category.friction ?? 0) + (s.findings_by_category.occlusion ?? 0)} UX obstruction ·{' '}
              {s.findings_by_category.accessibility ?? 0} accessibility violations · {s.runtime_s}s
            </div>
          </div>
        )}
        {state.status === 'failed' && s && (
          <div className="slide-in rounded-lg bg-red-600 px-3 py-3 text-white">
            <div className="text-sm font-extrabold tracking-wide">MISSION NOT COMPLETED</div>
            <div className="mt-1 text-sm">{s.reason ?? s.error}</div>
            <button onClick={onReplay} className="mt-2 rounded-md bg-white px-3 py-1 text-sm font-semibold text-red-700">
              Switch to golden replay (recorded run, not live)
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
