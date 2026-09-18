import type { RunState } from '../useRun'

interface Props {
  state: RunState
  goal: string
  setGoal: (g: string) => void
  onLive: () => void
  onReplay: () => void
  theme: 'light' | 'dark'
  onToggleTheme: () => void
  busy: boolean
}

export function Header({ state, goal, setGoal, onLive, onReplay, busy, theme, onToggleTheme }: Props) {
  const st = state.started
  const step = state.score?.step ?? state.frame?.step ?? 0
  const max = st?.max_steps ?? 12
  const progress = Math.round((state.status === 'completed' ? 1 : state.score?.goal_progress ?? 0) * 100)
  const mode = st?.mode === 'replay' ? 'REPLAY' : st?.offline_test_double ? 'TEST DOUBLE' : 'LIVE'
  const running = state.status === 'running' || state.status === 'connecting'

  return (
    <header className="mission-header flex items-center gap-3 px-4 py-2">
      <div className="header-brand flex min-w-[150px] items-center gap-2">
        <span className="brand-mark" aria-hidden="true"><span /></span>
        <div>
          <div className="brand-title">PathLens</div>
          <div className="brand-caption">Experience intelligence</div>
        </div>
      </div>

      {st && (
        <span
          className={`mode-pill flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-bold tracking-wide ${
            mode === 'LIVE' ? 'bg-red-50 text-red-700' : mode === 'REPLAY' ? 'bg-violet-50 text-violet-700' : 'bg-slate-100 text-slate-700'
          }`}
          title={mode === 'REPLAY' ? 'Recorded run of the identical workflow — not live' : mode === 'TEST DOUBLE' ? 'Offline heuristic test double — not AI' : 'Live autonomous run'}
        >
          <span className={`h-2 w-2 rounded-full ${mode === 'LIVE' ? 'bg-red-600' : mode === 'REPLAY' ? 'bg-violet-600' : 'bg-slate-500'} ${running ? 'animate-pulse' : ''}`} />
          {mode}
        </span>
      )}

      <input
        aria-label="User goal"
        value={goal}
        onChange={e => setGoal(e.target.value)}
        disabled={busy || running}
        className="header-goal goal-input min-w-0 flex-1 rounded-lg px-3 py-2 text-sm text-slate-100 focus:border-blue-400 focus:outline-none"
      />
      <button
        onClick={onLive}
        disabled={busy || running}
        className="header-live primary-action"
      >
        <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M5 3.8a.8.8 0 0 1 1.2-.7l10 6.2a.8.8 0 0 1 0 1.4l-10 6.2a.8.8 0 0 1-1.2-.7Z" /></svg>
        <span>{busy || state.status === 'connecting' ? 'Starting…' : running ? 'Running' : 'Run live'}</span>
      </button>
      <button
        onClick={onReplay}
        disabled={busy || running}
        className="header-replay secondary-action"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 10a9 9 0 1 1 2.7 8.5M3 4v6h6" /></svg>
        <span>Replay golden run</span>
      </button>

      <button className="theme-toggle" onClick={onToggleTheme} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
          {theme === 'light' ? <path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z" /> : <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></>}
        </svg>
        <span>{theme === 'light' ? 'Dark' : 'Light'}</span>
      </button>
      <div className="header-progress flex w-56 flex-col gap-1">
        <div className="flex justify-between text-xs font-semibold text-slate-400">
          <span>STEP {step}/{max}</span>
          <span>{progress}% GOAL</span>
        </div>
        <div className="progress-track h-2 overflow-hidden rounded-full">
          <div
            className={`h-full rounded-full transition-all duration-500 ${state.status === 'completed' ? 'bg-emerald-500' : state.status === 'failed' ? 'bg-red-500' : 'bg-blue-600'}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </header>
  )
}
