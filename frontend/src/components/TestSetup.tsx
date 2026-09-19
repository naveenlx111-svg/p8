import { ANDROID_PRESETS, PRESETS, type Target } from '../presets'

export interface AndroidDevice {
  serial: string
  status: string
  model: string
  product: string
}

interface Props {
  target: Target
  setTarget: (t: Target) => void
  disabled: boolean
  running: boolean
  busy: boolean
  starting: boolean
  devices: AndroidDevice[]
  refreshingDevices: boolean
  uploadingApk: boolean
  onRefreshDevices: () => void
  onUploadApk: (file: File) => void
  onLive: () => void
  onCancel: () => void
  onReplay: () => void
}

export function TestSetup(p: Props) {
  const { target, setTarget, disabled, devices } = p
  const platform = target.platform ?? 'web'
  const set = (k: keyof Target) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setTarget({ ...target, [k]: e.target.value })
  const setPlatform = (next: 'web' | 'android') => setTarget({ ...target, platform: next, successUrl: next === 'android' ? '' : target.successUrl })

  return (
    <>
      <h1>Give your product a journey.</h1>
      <p className="lede">
        PathLens drives a real browser the way a first-time visitor would, seeing only what a user or screen reader sees. Problems
        confirmed by a check in code are marked verified; the model’s own observations stay labelled as such.
      </p>

      <form className="form" onSubmit={e => e.preventDefault()}>
        <label className="field">
          <span>What should a user be able to do?</span>
          <textarea className="input" aria-label="User goal" value={target.goal} onChange={set('goal')} disabled={disabled} />
        </label>

        <div className="field">
          <span className="label">Platform</span>
          <div className="segmented" role="group" aria-label="Testing platform">
            <button type="button" className={platform === 'web' ? 'is-on' : ''} aria-pressed={platform === 'web'} disabled={disabled} onClick={() => setPlatform('web')}>Web</button>
            <button type="button" className={platform === 'android' ? 'is-on' : ''} aria-pressed={platform === 'android'} disabled={disabled} onClick={() => setPlatform('android')}>Android · ADB</button>
          </div>
        </div>

        {platform === 'web' ? <>
          <label className="field">
            <span>Target URL</span>
            <input className="input mono" aria-label="Target URL" value={target.url} onChange={set('url')} disabled={disabled} placeholder="https://…" />
          </label>
          <div className="form-row">
            <label className="field" title="Optional acceptance criteria. Leave empty to derive them from the goal.">
              <span>Done when URL contains</span>
              <input className="input" aria-label="Success URL contains" value={target.successUrl} onChange={set('successUrl')} disabled={disabled} placeholder="auto" />
            </label>
            <label className="field">
              <span>and page shows</span>
              <input className="input" aria-label="Success text" value={target.successText} onChange={set('successText')} disabled={disabled} placeholder="auto" />
            </label>
          </div>
        </> : <>
          <div className="device-row">
            <label className="field">
              <span>Device</span>
              <select className="input" aria-label="Android device" value={target.deviceSerial ?? ''} disabled={disabled || p.refreshingDevices}
                onChange={e => setTarget({ ...target, deviceSerial: e.target.value })}>
                <option value="">{devices.length === 1 ? 'Auto-select connected device' : 'Select connected device'}</option>
                {devices.map(d => <option key={d.serial} value={d.serial} disabled={d.status !== 'device'}>{d.model || d.serial} · {d.status}</option>)}
              </select>
            </label>
            <button type="button" className="btn" disabled={disabled || p.refreshingDevices} onClick={p.onRefreshDevices}>{p.refreshingDevices ? 'Checking…' : 'Refresh ADB'}</button>
          </div>
          <div className="form-hint">{devices.length ? `${devices.filter(d => d.status === 'device').length} ready` : 'No ADB device detected yet'}</div>
          <div className="form-row">
            <label className="field">
              <span>Installed package</span>
              <input className="input mono" aria-label="Installed Android package" value={target.packageName ?? ''} onChange={set('packageName')} disabled={disabled} placeholder="com.example.app" />
            </label>
            <div className="field">
              <span className="label">APK</span>
              <label className="btn" style={{ cursor: disabled || p.uploadingApk ? 'not-allowed' : 'pointer' }}>
                {p.uploadingApk ? 'Uploading…' : target.apkName ? `APK: ${target.apkName}` : 'Upload APK'}
                <input className="sr-only" type="file" accept=".apk,application/vnd.android.package-archive" disabled={disabled || p.uploadingApk}
                  onChange={e => { const file = e.target.files?.[0]; if (file) p.onUploadApk(file); e.currentTarget.value = '' }} />
              </label>
            </div>
          </div>
          <label className="field">
            <span>Android demo apps</span>
            <select className="input" aria-label="Android demo apps" disabled={disabled} value="" onChange={e => {
              const preset = ANDROID_PRESETS[Number(e.target.value)]
              if (preset) setTarget({ ...preset.t, deviceSerial: target.deviceSerial })
            }}>
              <option value="">Choose a demo…</option>
              {ANDROID_PRESETS.map((preset, i) => <option key={preset.name} value={i}>{preset.name}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Done when screen shows</span>
            <input className="input" aria-label="Success text" value={target.successText} onChange={set('successText')} disabled={disabled} placeholder="required" />
          </label>
        </>}

        <div className="form-row">
          <label className="field" title="Safety ceiling. Runs normally stop on verified success or when the agent stalls.">
            <span>Max steps</span>
            <input className="input" aria-label="Max steps" value={target.maxSteps ?? ''} onChange={set('maxSteps')} disabled={disabled} placeholder="100" inputMode="numeric" />
          </label>
          {platform === 'web' && <label className="field">
            <span>Example targets</span>
            <select className="input" aria-label="Example targets" disabled={disabled} value="" onChange={e => {
              const preset = PRESETS[Number(e.target.value)]
              if (preset) setTarget({ ...preset.t, platform: 'web' })
            }}>
              <option value="">Choose an example…</option>
              {PRESETS.map((preset, i) => <option key={preset.name} value={i}>{preset.name}</option>)}
            </select>
          </label>}
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-primary" disabled={p.busy} onClick={p.running ? p.onCancel : p.onLive}>
            {p.starting ? 'Starting…' : p.running ? 'Stop run' : 'Run live'}
          </button>
          <button type="button" className="btn" disabled={p.busy || p.running} onClick={p.onReplay}>Replay golden run</button>
          <span className="form-hint">Replays are recorded runs and are labelled as such.</span>
        </div>
      </form>
    </>
  )
}
