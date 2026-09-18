import { useEffect, useState } from 'react'
import { AccessibilityPanel } from './components/AccessibilityPanel'
import { BrowserPanel } from './components/BrowserPanel'
import { DecisionStream } from './components/DecisionStream'
import { Header } from './components/Header'
import { JourneyGraph } from './components/JourneyGraph'
import { PRESETS, TargetBar, type Target } from './components/TargetBar'
import { useRun } from './useRun'


export default function App() {
  const { state, start } = useRun()
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try {
      const saved = localStorage.getItem('pathlens-theme')
      if (saved === 'light' || saved === 'dark') return saved
    } catch { /* Storage may be unavailable in private browsing. */ }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('pathlens-theme', theme) } catch { /* Keep the toggle usable. */ }
  }, [theme])
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
    <div className="app-shell flex h-screen flex-col">
      <Header
        theme={theme} onToggleTheme={() => setTheme(theme === 'light' ? 'dark' : 'light')}
        state={state} goal={target.goal} setGoal={goal => setTarget({ ...target, goal })} busy={busy}
        onLive={() => launch({
          goal: target.goal, mode: 'live', target_url: target.url.trim() || null,
          success_url: target.successUrl.trim() ? [target.successUrl.trim()] : null,
          success_text: target.successText.trim() ? [target.successText.trim()] : null,
          max_steps: Number(target.maxSteps) > 0 ? Number(target.maxSteps) : null,
        })}
        onReplay={() => launch({ mode: 'replay', replay: 'golden' })}
      />
      <TargetBar target={target} setTarget={setTarget} disabled={busy || state.status === 'running' || state.status === 'connecting'} />
      {error && <div className="bg-red-600 px-5 py-1.5 text-sm text-white">Could not start run: {error}</div>}
      <div className="workspace-intro">
        <div><div className="eyebrow">THE EXPERIENCE LAB</div><h1>See the journey. <span>Find the friction.</span></h1></div>
        <div className="workspace-status"><span className={busy || state.status === 'running' || state.status === 'connecting' ? 'status-dot active' : 'status-dot'} />{busy || state.status === 'connecting' ? 'Connecting to browser' : state.status === 'running' ? 'Exploring your experience' : state.status === 'completed' ? 'Journey complete' : state.status === 'failed' ? 'Run needs attention' : 'Ready to explore'}</div>
      </div>
      <main className="dashboard-grid min-h-0 flex-1">
        <BrowserPanel state={state} inspect={inspect} clearInspect={() => setInspect(null)} />
        <DecisionStream state={state} onReplay={() => launch({ mode: 'replay', replay: 'golden' })} />
        <JourneyGraph state={state} onInspect={setInspect} />
        <AccessibilityPanel state={state} />
      </main>
    </div>
  )
}
