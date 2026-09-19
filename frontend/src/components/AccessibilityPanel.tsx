import type { RunState } from '../useRun'

const IMPACT: Record<string, string> = {
  critical: 'bg-red-600', serious: 'bg-orange-500', moderate: 'bg-amber-400', minor: 'bg-slate-400',
}

export function AccessibilityPanel({ state, platform }: { state: RunState; platform: 'web' | 'android' }) {
  const sc = state.score
  const score = sc?.accessibility_score ?? 100
  const counts = sc?.accessibility_counts ?? { critical: 0, serious: 0, moderate: 0, minor: 0 }
  const color = score >= 90 ? 'score-good' : score >= 70 ? 'score-warning' : 'score-poor'
  const fr = sc?.friction
  const backend = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '')
  const report = state.summary?.report_url ? `${backend}${state.summary.report_url}` : null
  const video = state.summary?.video_url ? `${backend}${state.summary.video_url}` : null
  const artifactBase = state.started?.artifact_base ? `${backend}${state.started.artifact_base}` : ''
  const accessibilityFindings = state.findings.filter(f => f.category === 'accessibility')
  const method = (state.started?.platform ?? platform) === 'android'
    ? 'UIAutomator hierarchy + deterministic accessible-name and 48dp touch-target checks.'
    : 'Browser accessibility snapshot + axe-core rules + keyboard focus traversal for dialogs.'

  return (
    <section className="workspace-panel accessibility-panel flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white">
      <h2 className="border-b border-slate-200 px-3 py-2 text-xs font-bold tracking-widest text-slate-500">ACCESSIBILITY &amp; FRICTION</h2>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3">
        <div className="accessibility-summary flex items-center gap-4">
          <div>
            <div className="text-[10px] font-bold tracking-widest text-slate-500">{sc ? 'ACCESSIBILITY RISK SCORE' : 'AWAITING FIRST AUDIT'}</div>
            <div className={`score-pop text-4xl font-extrabold ${color}`} key={score}>
              {sc ? score : '—'}<span className="text-lg text-slate-400">/100</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
            {(['critical', 'serious', 'moderate', 'minor'] as const).map(k => (
              <span key={k} className="flex items-center gap-1.5 text-slate-700">
                <span className={`h-2 w-2 rounded-full ${IMPACT[k]}`} /> {counts[k] ?? 0} {k}
              </span>
            ))}
          </div>
        </div>
        {state.violations.length > 0 && (
          <ul className="flex flex-col gap-1">
            {state.violations.map(v => (
              <li key={v.id} className="slide-in flex items-center gap-2 text-xs">
                <span className={`rounded px-1.5 py-0.5 font-bold text-white ${IMPACT[v.impact ?? 'minor']}`}>{v.impact}</span>
                <span className="font-mono text-slate-500">{v.id}</span>
                <span className="truncate text-slate-800">{v.help}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="text-[10px] leading-tight text-slate-400">
          <b>Approach:</b> {method} {sc?.disclaimer ?? 'Automated heuristic based on detected accessibility violations; not a WCAG certification.'}
        </p>
        {accessibilityFindings.length > 0 && <div className="flex flex-col gap-1.5">
          <div className="text-[10px] font-bold tracking-widest text-slate-500">EVIDENCE &amp; RECOMMENDATIONS</div>
          {accessibilityFindings.slice(-4).map(finding => <div key={finding.finding_id} className="rounded bg-slate-50 p-2 text-xs">
            <div className="font-semibold text-slate-900">{finding.code} · {finding.title}</div>
            <div className="mt-0.5 text-slate-600">{finding.evidence}</div>
            {finding.recommendation && <div className="mt-1 text-blue-700"><b>Fix:</b> {finding.recommendation}</div>}
            {finding.data.accessibility_tree_id && <a className="mt-1 inline-block font-semibold text-blue-700 underline"
              href={`${artifactBase}${finding.data.accessibility_tree_id}`} target="_blank" rel="noreferrer">Open captured accessibility tree</a>}
          </div>)}
        </div>}
        {fr && (
          <div>
            <div className="text-[10px] font-bold tracking-widest text-slate-500">MEASURED FRICTION EVENTS</div>
            <div className="mt-1 grid grid-cols-3 gap-1 text-xs">
              {[
                ['interruptions', fr.interruptions], ['recoveries', fr.recoveries], ['blocked', fr.blocked_interactions],
                ['repeated states', fr.repeated_states], ['backtracks', fr.backtracks], ['no-progress', fr.no_progress_actions],
              ].map(([k, v]) => (
                <div key={k as string} className="rounded bg-slate-50 px-2 py-1">
                  <b className="text-slate-900">{v}</b> <span className="text-slate-600">{k}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="mt-auto grid gap-1.5">
          {video && <a href={video} target="_blank" rel="noreferrer" className="rounded-lg bg-blue-700 px-3 py-2 text-center text-sm font-semibold text-white hover:bg-blue-600">
            ▶ Journey video
          </a>}
          {report && <a href={`${report}?download=true`} className="rounded-lg bg-slate-900 px-3 py-2 text-center text-sm font-semibold text-white hover:bg-slate-700">
            ⬇ Download audit
          </a>}
        </div>
      </div>
    </section>
  )
}
