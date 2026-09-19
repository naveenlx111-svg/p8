import type { RunState } from '../useRun'

export function MetricStrip({ state }: { state: RunState }) {
  const sc = state.score
  const decisions = state.stream.filter(i => i.kind === 'decision').length
  const verified = state.findings.filter(f => f.source !== 'model' && f.category !== 'recovery').length
  const observed = state.findings.filter(f => f.source === 'model').length
  const experience = state.summary?.experience_score
  const experienceTone = experience
    ? (experience.overall < 60 ? 'bad' : experience.overall < 80 ? 'warn' : '')
    : ''
  const items: { n: string | number; label: string; tone?: string }[] = [
    { n: state.summary?.actions ?? decisions, label: 'actions' },
    { n: verified, label: 'verified problems', tone: verified ? 'bad' : '' },
    ...(observed ? [{ n: observed, label: 'model observations, unverified' }] : []),
    ...(sc ? [
      { n: sc.friction_score, label: 'friction score, lower is better', tone: sc.friction_score > 0 ? 'warn' : '' },
      { n: sc.accessibility_score, label: 'accessibility score out of 100, higher is better', tone: sc.accessibility_score < 70 ? 'bad' : '' },
    ] : []),
    ...(experience ? [{ n: experience.overall, label: `experience score /100 · ${experience.verdict.replaceAll('_', ' ')}`, tone: experienceTone }] : []),
    { n: state.nodeOrder.length, label: 'distinct screens' },
    ...((state.summary?.recoveries ?? sc?.friction?.recoveries) ? [{ n: (state.summary?.recoveries ?? sc?.friction?.recoveries) as number, label: 'autonomous recoveries' }] : []),
  ]
  return (
    <div className="metrics">
      {items.map(m => <div key={m.label} className={`metric ${m.tone ? `is-${m.tone}` : ''}`}><b>{m.n}</b><span>{m.label}</span></div>)}
    </div>
  )
}
