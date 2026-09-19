import { useEffect, useState } from 'react'
import { AccessibilityPanel } from './components/AccessibilityPanel'
import { BrowserPanel } from './components/BrowserPanel'
import { ComparisonBar } from './components/ComparisonBar'
import { DecisionStream } from './components/DecisionStream'
import { Header } from './components/Header'
import { JourneyGraph } from './components/JourneyGraph'
import { TargetBar, type AndroidDevice } from './components/TargetBar'
import { PRESETS, type Target } from './presets'
import { useRun } from './useRun'
import type { RunComparison } from './types'


export default function App() {
  const { state, start, cancel } = useRun()
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
  const [baselineId, setBaselineId] = useState<string | null>(() => {
    try { return localStorage.getItem('pathlens-baseline-run') } catch { return null }
  })
  const [comparison, setComparison] = useState<RunComparison | null>(null)
  const [comparing, setComparing] = useState(false)
  const [devices, setDevices] = useState<AndroidDevice[]>([])
  const [refreshingDevices, setRefreshingDevices] = useState(false)
  const [uploadingApk, setUploadingApk] = useState(false)

  const backend = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '')
  const refreshDevices = async () => {
    setRefreshingDevices(true)
    setError(null)
    try {
      const response = await fetch(`${backend}/api/android/devices`)
      if (!response.ok) throw new Error(await response.text())
      const body = await response.json()
      setDevices(body.devices ?? [])
      const ready = (body.devices ?? []).filter((device: AndroidDevice) => device.status === 'device')
      if (!target.deviceSerial && ready.length === 1) setTarget(current => ({ ...current, deviceSerial: ready[0].serial }))
    } catch (e) {
      setError(`ADB device discovery failed: ${String(e)}`)
    } finally {
      setRefreshingDevices(false)
    }
  }

  useEffect(() => {
    if ((target.platform ?? 'web') === 'android') void refreshDevices()
    // Switching platform is the explicit refresh trigger; the button handles subsequent probes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target.platform])

  const uploadApk = async (file: File) => {
    setUploadingApk(true)
    setError(null)
    try {
      const data = new FormData()
      data.append('file', file)
      const response = await fetch(`${backend}/api/android/apks`, { method: 'POST', body: data })
      if (!response.ok) throw new Error(await response.text())
      const uploaded = await response.json()
      setTarget(current => ({ ...current, apkId: uploaded.apk_id, apkName: uploaded.filename, packageName: uploaded.package }))
    } catch (e) {
      setError(`APK upload failed: ${String(e)}`)
    } finally {
      setUploadingApk(false)
    }
  }

  const launch = async (body: Record<string, unknown>) => {
    setBusy(true)
    setError(null)
    setInspect(null)
    setComparison(null)
    try {
      await start(body)
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  const rememberBaseline = () => {
    if (!state.runId) return
    setBaselineId(state.runId)
    try { localStorage.setItem('pathlens-baseline-run', state.runId) } catch { /* Optional convenience only. */ }
    setComparison(null)
  }

  const compareRuns = async () => {
    if (!baselineId || !state.runId || baselineId === state.runId) return
    setComparing(true)
    setError(null)
    try {
      const response = await fetch(`${backend}/api/compare`, {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ baseline_run: baselineId, candidate_run: state.runId }),
      })
      if (!response.ok) throw new Error(await response.text())
      setComparison(await response.json())
    } catch (e) {
      setError(`Could not compare runs: ${String(e)}`)
    } finally {
      setComparing(false)
    }
  }

  return (
    <div className="app-shell flex h-screen flex-col">
      <Header
        theme={theme} onToggleTheme={() => setTheme(theme === 'light' ? 'dark' : 'light')}
        state={state} goal={target.goal} setGoal={goal => setTarget({ ...target, goal })} busy={busy}
        onLive={() => launch({
          goal: target.goal, mode: 'live', platform: target.platform ?? 'web',
          target_url: (target.platform ?? 'web') === 'web' ? target.url.trim() || null : null,
          device_serial: target.deviceSerial?.trim() || null,
          android_package: target.packageName?.trim() || null,
          android_activity: target.activity?.trim() || null,
          apk_id: target.apkId || null,
          record_video: true,
          success_url: (target.platform ?? 'web') === 'web' && target.successUrl.trim() ? [target.successUrl.trim()] : null,
          success_text: target.successText.trim() ? [target.successText.trim()] : null,
          max_steps: Number(target.maxSteps) > 0 ? Number(target.maxSteps) : null,
        })}
        onCancel={async () => {
          setError(null)
          try { await cancel() } catch (e) { setError(`Could not cancel run: ${String(e)}`) }
        }}
        onReplay={() => launch({ mode: 'replay', replay: 'golden' })}
      />
      <TargetBar target={target} setTarget={setTarget} disabled={busy || state.status === 'running' || state.status === 'connecting'}
        devices={devices} refreshingDevices={refreshingDevices} uploadingApk={uploadingApk}
        onRefreshDevices={() => void refreshDevices()} onUploadApk={file => void uploadApk(file)} />
      <ComparisonBar state={state} baselineId={baselineId} comparison={comparison} busy={comparing}
        onSetBaseline={rememberBaseline} onCompare={compareRuns} onClear={() => setComparison(null)} />
      {error && <div className="bg-red-600 px-5 py-1.5 text-sm text-white">PathLens error: {error}</div>}
      {state.status === 'disconnected' && (
        <div className="flex items-center justify-between gap-3 bg-amber-100 px-5 py-2 text-xs text-amber-900">
          <span>{state.connectionError}</span>
          <button className="secondary-action comparison-button" onClick={() => launch({ mode: 'replay', replay: 'golden' })}>Replay verified run</button>
        </div>
      )}
      <div className="workspace-intro">
        <div><div className="eyebrow">THE EXPERIENCE LAB</div><h1>See the journey. <span>Find the friction.</span></h1></div>
        <div className="workspace-status"><span className={busy || state.status === 'running' || state.status === 'connecting' ? 'status-dot active' : 'status-dot'} />{busy || state.status === 'connecting' ? `Connecting to ${(target.platform ?? 'web') === 'android' ? 'Android device' : 'browser'}` : state.status === 'running' ? `Exploring ${(state.started?.platform ?? 'web') === 'android' ? 'the Android app' : 'your experience'}` : state.status === 'disconnected' ? state.connectionError : state.status === 'completed' ? 'Journey complete' : state.status === 'failed' ? 'Run needs attention' : 'Ready to explore'}</div>
      </div>
      <main className="dashboard-grid min-h-0 flex-1">
        <BrowserPanel state={state} platform={target.platform ?? 'web'} inspect={inspect} clearInspect={() => setInspect(null)} />
        <DecisionStream state={state} onReplay={() => launch({ mode: 'replay', replay: 'golden' })} />
        <JourneyGraph state={state} onInspect={setInspect} />
        <AccessibilityPanel state={state} platform={target.platform ?? 'web'} />
      </main>
    </div>
  )
}
