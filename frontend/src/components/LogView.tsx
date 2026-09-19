import type { RunState } from '../useRun'

export function LogView({ state }: { state: RunState }) {
  if (state.stream.length === 0) return <div className="empty-line" style={{ marginTop: 28 }}>No events yet.</div>
  return (
    <div className="log">
      {state.stream.map(it => {
        const [kind, msg] =
          it.kind === 'decision' ? ['decision', `step ${it.d.step} · ${it.d.action}${it.d.label ? ` “${it.d.label}”` : ''}${it.d.text ? ` ← “${it.d.text}”` : ''} · ${Math.round(it.d.confidence * 100)}% · ${it.d.latency_ms} ms${it.outcome ? ` → ${it.outcome.outcome}${it.outcome.error ? ` (${it.outcome.error})` : ''}` : ''}`]
          : it.kind === 'finding' ? [it.f.source === 'model' ? 'observation' : 'finding', `${it.f.code} [${it.f.severity}] ${it.f.title} · step ${it.f.step_number}`]
          : it.kind === 'verified' ? [it.modelJudged ? 'model-judged' : 'verified', it.evidence.join(' · ')]
          : ['rejected', `step ${it.a.step} · ${it.a.action} · ${it.a.error ?? ''}`]
        return <div className="log-row" key={it.seq}><span className="n">#{it.seq}</span><span className="kind">{kind}</span><span className="msg">{msg}</span></div>
      })}
    </div>
  )
}
