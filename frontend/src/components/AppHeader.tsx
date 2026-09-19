import type { RunState } from '../useRun'

export type View = 'test' | 'run'

interface Props {
  view: View
  setView: (v: View) => void
  hasRun: boolean
  state: RunState
  theme: 'light' | 'dark'
  onToggleTheme: () => void
}

export function AppHeader({ view, setView, hasRun, state, theme, onToggleTheme }: Props) {
  const st = state.started
  return (
    <header className="nav">
      <div className="page">
        <div className="brand"><span className="brand-name">PathLens</span><span className="brand-sub">Experience intelligence</span></div>
        <nav className="nav-tabs" aria-label="Primary">
          <button className={`nav-tab ${view === 'test' ? 'is-active' : ''}`} aria-current={view === 'test' ? 'page' : undefined} onClick={() => setView('test')}>Test</button>
          <button className={`nav-tab ${view === 'run' ? 'is-active' : ''}`} aria-current={view === 'run' ? 'page' : undefined} disabled={!hasRun} onClick={() => setView('run')}>Run</button>
        </nav>
        <div className="nav-right">
          {st && <span className="nav-model" title={st.offline_test_double ? 'Offline heuristic test double — not AI' : undefined}>
            <i />{st.model}, {st.provider}{st.offline_test_double ? ' (test double)' : ''}
          </span>}
          <button className="text-btn" onClick={onToggleTheme} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
            {theme === 'light' ? 'Dark mode' : 'Light mode'}
          </button>
        </div>
      </div>
    </header>
  )
}
