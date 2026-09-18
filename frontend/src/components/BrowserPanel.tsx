import type { RunState } from '../useRun'

interface Props {
  state: RunState
  inspect: string | null
  clearInspect: () => void
}

export function BrowserPanel({ state, inspect, clearInspect }: Props) {
  const backend = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '')
  const base = state.started?.artifact_base ? `${backend}${state.started.artifact_base}` : ''
  const node = inspect ? state.nodes[inspect] : null
  const image = node?.screenshot_id ?? state.frame?.image
  const url = node?.url ?? state.frame?.url

  return (
    <section className="flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
        </div>
        <div className="min-w-0 flex-1 truncate rounded-md bg-slate-100 px-2 py-1 font-mono text-xs text-slate-700">
          {url ?? 'waiting for target…'}
        </div>
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
      <div className="relative flex min-h-0 flex-1 items-center justify-center bg-slate-100">
        {image ? (
          <img src={base + image} alt="Current browser frame of the target application" className="max-h-full max-w-full object-contain" />
        ) : (
          <p className="text-sm text-slate-500">Enter a goal and press Run live. The agent receives no script, selectors or source code.</p>
        )}
      </div>
    </section>
  )
}
