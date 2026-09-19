import { useEffect, useState } from 'react'
import { ActionTimeline } from './components/ActionTimeline'
import { AppHeader, type View } from './components/AppHeader'
import { BrowserFrame } from './components/BrowserFrame'
import { ComparisonBar } from './components/ComparisonBar'
import { FindingList } from './components/FindingList'
import { LogView } from './components/LogView'
import { MetricStrip } from './components/MetricStrip'
import { ReportPanel } from './components/ReportPanel'
import { RunHeader, type Tab } from './components/RunHeader'
import { ScreenMap } from './components/ScreenMap'
import { TestSetup, type AndroidDevice } from './components/TestSetup'
import { isLive } from './lib'
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
  const [view, setView] = useState<View>('test')
  const [tab, setTab] = useState<Tab>('watch')
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
      setView('run')
      setTab('watch')
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

  const platform = target.platform ?? 'web'
  const running = isLive(state)
  const liveBody = () => ({
    goal: target.goal, mode: 'live', platform,
    target_url: platform === 'web' ? target.url.trim() || null : null,
    device_serial: target.deviceSerial?.trim() || null,
    android_package: target.packageName?.trim() || null,
    android_activity: target.activity?.trim() || null,
    apk_id: target.apkId || null,
    record_video: true,
    success_url: platform === 'web' && target.successUrl.trim() ? [target.successUrl.trim()] : null,
    success_text: target.successText.trim() ? [target.successText.trim()] : null,
    max_steps: Number(target.maxSteps) > 0 ? Number(target.maxSteps) : null,
  })
  const replay = () => launch({ mode: 'replay', replay: 'golden' })
  const stop = async () => {
    setError(null)
    try { await cancel() } catch (e) { setError(`Could not cancel run: ${String(e)}`) }
  }
  const showRun = view === 'run' && !!state.runId
  const viewInEvidence = (id: string) => {
    setInspect(id)
    setTab('watch')
    setTimeout(() => document.getElementById('watch-workspace')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
  }
  const progress = Math.round((state.status === 'completed' ? 1 : state.score?.goal_progress ?? 0) * 100)
  const step = state.score?.step ?? state.frame?.step ?? 0

  return (
    <div className="app-shell">
      <AppHeader view={showRun ? 'run' : 'test'} setView={setView} hasRun={!!state.runId} state={state}
        theme={theme} onToggleTheme={() => setTheme(theme === 'light' ? 'dark' : 'light')} />
      <main className="page" style={{ paddingBottom: 96 }}>
        {error && <div className="banner banner-bad" role="alert">PathLens error: {error}</div>}

        {!showRun && (
          <div className="setup">
            <div>
              <TestSetup target={target} setTarget={setTarget} disabled={busy || running} running={running} busy={busy} starting={busy || state.status === 'connecting'}
                devices={devices} refreshingDevices={refreshingDevices} uploadingApk={uploadingApk}
                onRefreshDevices={() => void refreshDevices()} onUploadApk={file => void uploadApk(file)}
                onLive={() => launch(liveBody())} onCancel={() => void stop()} onReplay={() => void replay()} />
            </div>
            <div className="setup-preview">
              <BrowserFrame state={state} platform={platform} inspect={inspect} clearInspect={() => setInspect(null)} />
            </div>
          </div>
        )}

        {showRun && (
          <>
            <RunHeader key={state.runId} state={state} tab={tab} setTab={setTab} onBack={() => setView('test')} onCancel={() => void stop()} onReplay={() => void replay()} busy={busy} />

            {tab === 'watch' && (
              <>
                <div className="workspace" id="watch-workspace">
                  <BrowserFrame state={state} platform={platform} inspect={inspect} clearInspect={() => setInspect(null)} onInspect={setInspect} thumbnails />
                  <div>
                    <div className="pane-head">
                      <span className={`badge badge-${state.status === 'completed' ? 'ok' : state.status === 'failed' ? 'bad' : 'run'}`}>
                        <i />{state.status === 'completed' ? (state.summary?.goal_completed ? (state.summary.completion_mode === 'model_judged' ? 'Goal judged' : 'Goal reached') : 'Finished') : state.status === 'failed' ? 'Not completed' : running ? 'Exploring' : 'Stopped'}
                      </span>
                      <span className="fill">{state.started?.model} · {state.started?.platform === 'android' ? 'Android' : 'Web'}</span>
                      {state.started && <span>step {step}/{state.started.max_steps} · {progress}%{state.status === 'completed' ? ' verified' : ' AI est.'}</span>}
                    </div>
                    <div className={`progress ${state.status === 'completed' ? 'is-done' : state.status === 'failed' ? 'is-failed' : ''}`}><i style={{ width: `${progress}%` }} /></div>
                    <ActionTimeline state={state} onReplay={() => void replay()} />
                  </div>
                </div>
                <MetricStrip state={state} />
                <ScreenMap state={state} inspect={inspect} onInspect={id => setInspect(inspect === id ? null : id)} />
                <FindingList state={state} onInspect={viewInEvidence} />
              </>
            )}

            {tab === 'actions' && <div style={{ marginTop: 28 }}><ActionTimeline state={state} detailed onReplay={() => void replay()} /></div>}

            {tab === 'report' && (
              <>
                <FindingList state={state} onInspect={viewInEvidence} />
                <ReportPanel state={state} platform={platform} onInspect={viewInEvidence} />
                <ComparisonBar state={state} baselineId={baselineId} comparison={comparison} busy={comparing}
                  onSetBaseline={rememberBaseline} onCompare={compareRuns} onClear={() => setComparison(null)} />
              </>
            )}

            {tab === 'log' && <LogView state={state} />}
          </>
        )}
      </main>
    </div>
  )
}
