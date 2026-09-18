import { useState } from 'react'
import { AccessibilityPanel } from './components/AccessibilityPanel'
import { BrowserPanel } from './components/BrowserPanel'
import { DecisionStream } from './components/DecisionStream'
import { Header } from './components/Header'
import { JourneyGraph } from './components/JourneyGraph'
import { PRESETS, TargetBar, type Target } from './components/TargetBar'
import { useRun } from './useRun'


export default function App() {
  const { state, start } = useRun()
  const [target, setTarget] = useState<Target>(PRESETS[0].t)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [inspect, setInspect] = useState<string | null>(null)

  const launch = async (body: Record<string, unknown>) => {
    setBusy(true)
    setError(null)
    setInspect(null)
    try {
      await start(body)
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-screen flex-col bg-slate-100">
      <Header
        state={state} goal={target.goal} setGoal={goal => setTarget({ ...target, goal })} busy={busy}
        onLive={() => launch({
          goal: target.goal, mode: 'live', target_url: target.url.trim() || null,
          success_url: target.successUrl.trim() ? [target.successUrl.trim()] : null,
          success_text: target.successText.trim() ? [target.successText.trim()] : null,
        })}
        onReplay={() => launch({ mode: 'replay', replay: 'golden' })}
      />
      <TargetBar target={target} setTarget={setTarget} disabled={busy || state.status === 'running' || state.status === 'connecting'} />
      {error && <div className="bg-red-600 px-5 py-1.5 text-sm text-white">Could not start run: {error}</div>}
      <main className="grid min-h-0 flex-1 grid-cols-[3fr_2fr] grid-rows-[3fr_2fr] gap-3 p-3">
        <BrowserPanel state={state} inspect={inspect} clearInspect={() => setInspect(null)} />
        <DecisionStream state={state} onReplay={() => launch({ mode: 'replay', replay: 'golden' })} />
        <JourneyGraph state={state} onInspect={setInspect} />
        <AccessibilityPanel state={state} />
      </main>
    </div>
  )
}
