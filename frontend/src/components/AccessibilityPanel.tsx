import type { RunState } from '../useRun'

const IMPACT: Record<string, string> = {
  critical: 'bg-red-600', serious: 'bg-orange-500', moderate: 'bg-amber-400', minor: 'bg-slate-400',
}

export function AccessibilityPanel({ state }: { state: RunState }) {
  const sc = state.score
  const score = sc?.accessibility_score ?? 100
  const counts = sc?.accessibility_counts ?? { critical: 0, serious: 0, moderate: 0, minor: 0 }
  const color = score >= 90 ? 'text-emerald-600' : score >= 70 ? 'text-amber-600' : 'text-red-600'
  const fr = sc?.friction
  const report = state.summary?.report_url

  return (
    <section className="flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white">
      <h2 className="border-b border-slate-200 px-3 py-2 text-xs font-bold tracking-widest text-slate-500">ACCESSIBILITY &amp; FRICTION</h2>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3">
        <div className="flex items-center gap-4">
          <div>
            <div className="text-[10px] font-bold tracking-widest text-slate-500">AUTOMATED ACCESSIBILITY RISK SCORE</div>
            <div className={`score-pop text-4xl font-extrabold ${color}`} key={score}>
              {score}<span className="text-lg text-slate-400">/100</span>
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
          {sc?.disclaimer ?? 'Automated heuristic based on detected accessibility violations; not a WCAG certification.'} Rules checked by axe-core.
        </p>
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
        {report && (
          <a href={`${report}?download=true`} className="mt-auto rounded-lg bg-slate-900 px-3 py-2 text-center text-sm font-semibold text-white hover:bg-slate-700">
            ⬇ Download audit
          </a>
        )}
      </div>
    </section>
  )
}
