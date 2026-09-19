import type { RunState } from '../useRun'

interface Props {
  state: RunState
  platform: 'web' | 'android'
  inspect: string | null
  clearInspect: () => void
}

export function BrowserPanel({ state, platform, inspect, clearInspect }: Props) {
  const backend = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '')
  const base = state.started?.artifact_base ? `${backend}${state.started.artifact_base}` : ''
  const node = inspect ? state.nodes[inspect] : null
  const image = node?.screenshot_id ?? state.frame?.image
  const url = node?.url ?? state.frame?.url
  const tree = node?.accessibility_tree_id ?? state.frame?.accessibilityTree
  const android = (state.started?.platform ?? platform) === 'android'

  return (
    <section className="workspace-panel flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
        </div>
        <div className="min-w-0 flex-1 truncate rounded-md bg-slate-100 px-2 py-1 font-mono text-xs text-slate-700">
          {url ?? `${android ? 'Android device' : 'Browser'} preview · waiting for a run`}
        </div>
        {tree && <a href={base + tree} target="_blank" rel="noreferrer"
          className="rounded-md bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700" title="Captured platform accessibility hierarchy">
          Accessibility tree
        </a>}
        {node ? (
          <button onClick={clearInspect} className="rounded-md bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">
            Evidence: {node.label} · back to live ✕
          </button>
        ) : (
          state.pendingAction && (
            <span className="animate-pulse rounded-md bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">
              acting: {state.pendingAction}
            </span>
          )
        )}
      </div>
      <div className="browser-viewport relative flex min-h-0 flex-1 items-center justify-center bg-slate-100">
        {image ? (
          <img src={base + image} alt={`Current ${android ? 'Android device' : 'browser'} frame of the target application`} className="max-h-full max-w-full object-contain" />
        ) : (
          <div className="browser-empty">
            <div className="browser-sculpture" aria-hidden="true">
              <div className="sculpture-scene">
              <div className="sculpture-back" />
              <div className="sculpture-window"><div className="sculpture-toolbar"><i /><i /><i /><span /></div><div className="sculpture-content"><div className="sculpture-sidebar" /><div className="sculpture-lines"><b /><i /><i /><div><span /><span /></div></div></div></div>
              <div className="sculpture-cursor"><svg viewBox="0 0 32 36" fill="currentColor"><path d="M4 2l23 19-11 1-5 10z" /></svg></div>
              <div className="sculpture-check">✓</div>
              </div>
            </div>
            <h2>A fresh pair of eyes for your product.</h2>
            <p>Give the agent a goal. Watch it navigate your site,<br className="desktop-break" /> spot friction, and follow the evidence.</p>
            <div className="empty-caption"><span /> YOUR NEXT JOURNEY STARTS ABOVE</div>
          </div>
        )}
      </div>
    </section>
  )
}
