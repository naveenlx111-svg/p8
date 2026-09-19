import { artifactBase } from '../lib'
import type { RunState } from '../useRun'

interface Props {
  state: RunState
  platform: 'web' | 'android'
  inspect: string | null
  clearInspect: () => void
  onInspect?: (id: string) => void
  thumbnails?: boolean
}

export function BrowserFrame({ state, platform, inspect, clearInspect, onInspect, thumbnails }: Props) {
  const base = artifactBase(state)
  const node = inspect ? state.nodes[inspect] : null
  const image = node?.screenshot_id ?? state.frame?.image
  const url = node?.url ?? state.frame?.url
  const tree = node?.accessibility_tree_id ?? state.frame?.accessibilityTree
  const android = (state.started?.platform ?? platform) === 'android'
  const waiting = state.status === 'connecting' || state.status === 'running'
  const live = state.status === 'running' && !node
  const replay = state.started?.mode === 'replay'

  return (
    <div className="frame">
      <div className="frame-bar">
        <div className="frame-dots" aria-hidden="true"><i /><i /><i /></div>
        <div className="frame-url">{url ?? (waiting ? `Waiting for the ${android ? 'device' : 'browser'}` : `${android ? 'Android device' : 'Browser'} preview`)}</div>
        {tree && <a className="frame-chip" href={base + tree} target="_blank" rel="noreferrer" title="Captured platform accessibility hierarchy">Accessibility tree</a>}
        {node
          ? <button className="frame-chip is-evidence" onClick={clearInspect}>Evidence: {node.label} · back to live ✕</button>
          : state.pendingAction
            ? <span className="frame-chip is-live">acting: {state.pendingAction}</span>
            : live && <span className="frame-chip is-live">{replay ? 'Replay' : 'Live'}</span>}
      </div>
      <div className={`frame-view ${android ? 'is-android' : ''}`}>
        {image
          ? <img src={base + image} alt={`Current ${android ? 'Android device' : 'browser'} frame of the target application`} />
          : <div className="frame-empty">
              {waiting ? <><div className="spinner" />The first screenshot appears within a few seconds.</> : 'The browser session appears here once a run starts.'}
            </div>}
      </div>
      {thumbnails && state.nodeOrder.length > 0 && (
        <div className="thumbs" aria-label="Screens visited">
          {state.nodeOrder.map((id, i) => {
            const n = state.nodes[id]
            return (
              <button key={id} className={`thumb ${inspect === id ? 'is-on' : ''}`} title={n.label} onClick={() => onInspect?.(id)}>
                {n.screenshot_id && <img src={base + n.screenshot_id} alt={n.label} loading="lazy" />}<b>{i + 1}</b>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
