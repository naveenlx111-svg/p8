import { PRESETS, type Target } from '../presets'

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
  devices: AndroidDevice[]
  refreshingDevices: boolean
  uploadingApk: boolean
  onRefreshDevices: () => void
  onUploadApk: (file: File) => void
}

const input = 'rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none disabled:bg-slate-50'

export function TargetBar({ target, setTarget, disabled, devices, refreshingDevices, uploadingApk, onRefreshDevices, onUploadApk }: Props) {
  const platform = target.platform ?? 'web'
  const set = (k: keyof Target) => (e: React.ChangeEvent<HTMLInputElement>) => setTarget({ ...target, [k]: e.target.value })
  return (
    <div className="target-bar flex flex-wrap items-center gap-2 px-5 py-2 text-xs text-slate-300">
      <label className="flex items-center gap-1.5 font-semibold">
        Platform
        <select aria-label="Testing platform" value={platform} disabled={disabled} onChange={e => setTarget({
          ...target, platform: e.target.value as 'web' | 'android',
          successUrl: e.target.value === 'android' ? '' : target.successUrl,
        })} className={input}>
          <option value="web">Web</option>
          <option value="android">Android · ADB</option>
        </select>
      </label>

      {platform === 'web' ? <>
        <label className="flex items-center gap-1.5 font-semibold">
          Target URL
          <input aria-label="Target URL" value={target.url} onChange={set('url')} disabled={disabled} placeholder="https://…" className={`${input} w-72 font-mono`} />
        </label>
        <label className="flex items-center gap-1.5 font-semibold" title="Optional acceptance criteria. Leave empty to derive them from the goal.">
          Done when URL contains
          <input aria-label="Success URL contains" value={target.successUrl} onChange={set('successUrl')} disabled={disabled} placeholder="auto" className={`${input} w-40`} />
        </label>
      </> : <>
        <label className="flex items-center gap-1.5 font-semibold">
          Device
          <select aria-label="Android device" value={target.deviceSerial ?? ''} disabled={disabled || refreshingDevices}
            onChange={e => setTarget({ ...target, deviceSerial: e.target.value })} className={`${input} w-52`}>
            <option value="">{devices.length === 1 ? 'Auto-select connected device' : 'Select connected device'}</option>
            {devices.map(device => <option key={device.serial} value={device.serial} disabled={device.status !== 'device'}>
              {device.model || device.serial} · {device.status}
            </option>)}
          </select>
        </label>
        <button type="button" disabled={disabled || refreshingDevices} onClick={onRefreshDevices} className="secondary-action comparison-button">
          {refreshingDevices ? 'Checking…' : '↻ ADB'}
        </button>
        <label className="secondary-action comparison-button cursor-pointer">
          {uploadingApk ? 'Uploading…' : target.apkName ? `APK: ${target.apkName}` : 'Upload APK'}
          <input className="sr-only" type="file" accept=".apk,application/vnd.android.package-archive" disabled={disabled || uploadingApk}
            onChange={e => { const file = e.target.files?.[0]; if (file) onUploadApk(file); e.currentTarget.value = '' }} />
        </label>
        <label className="flex items-center gap-1.5 font-semibold">
          Package
          <input aria-label="Installed Android package" value={target.packageName ?? ''} onChange={set('packageName')} disabled={disabled}
            placeholder="com.example.app" className={`${input} w-52 font-mono`} />
        </label>
      </>}

      <label className="flex items-center gap-1.5 font-semibold">
        {platform === 'android' ? 'Done when screen shows' : 'and page shows'}
        <input aria-label="Success text" value={target.successText} onChange={set('successText')} disabled={disabled}
          placeholder={platform === 'android' ? 'required' : 'auto'} className={`${input} w-40`} />
      </label>
      <label className="flex items-center gap-1.5 font-semibold" title="Safety ceiling. Runs normally stop on verified success or when the agent stalls.">
        Max steps
        <input aria-label="Max steps" value={target.maxSteps ?? ''} onChange={set('maxSteps')} disabled={disabled} placeholder="100" inputMode="numeric" className={`${input} w-16`} />
      </label>
      {platform === 'web' && <select aria-label="Example targets" disabled={disabled} value="" onChange={e => {
        const preset = PRESETS[Number(e.target.value)]
        if (preset) setTarget({ ...preset.t, platform: 'web' })
      }} className="target-examples rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800">
        <option value="">Examples…</option>
        {PRESETS.map((preset, index) => <option key={preset.name} value={index}>{preset.name}</option>)}
      </select>}
      {platform === 'android' && <span className="text-[10px] text-slate-400">{devices.length ? `${devices.filter(d => d.status === 'device').length} ready` : 'No ADB device detected yet'}</span>}
    </div>
  )
}
