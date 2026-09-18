import type { RunState } from '../useRun'

interface Props {
  state: RunState
  goal: string
  setGoal: (g: string) => void
  onLive: () => void
  onReplay: () => void
  busy: boolean
}

export function Header({ state, goal, setGoal, onLive, onReplay, busy }: Props) {
  const st = state.started
  const step = state.score?.step ?? state.frame?.step ?? 0
  const max = st?.max_steps ?? 12
  const progress = Math.round((state.status === 'completed' ? 1 : state.score?.goal_progress ?? 0) * 100)
  const mode = st?.mode === 'replay' ? 'REPLAY' : st?.offline_test_double ? 'TEST DOUBLE' : 'LIVE'
  const running = state.status === 'running' || state.status === 'connecting'

  return (
    <header className="flex items-center gap-4 border-b border-slate-200 bg-white px-5 py-3">
      <div className="flex items-baseline gap-2">
        <span className="text-xl font-extrabold tracking-tight text-slate-900">Path<span className="text-blue-600">Lens</span></span>
        <span className="hidden text-xs font-medium text-slate-500 xl:inline">autonomous synthetic user</span>
      </div>

      {st && (
        <span
          className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-bold tracking-wide ${
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
        disabled={running}
        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none disabled:bg-slate-50"
      />
      <button
        onClick={onLive}
        disabled={busy || running}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
      >
        ▶ Run live
      </button>
      <button
        onClick={onReplay}
        disabled={busy || running}
        className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
      >
        Replay golden run
      </button>

      <div className="flex w-56 flex-col gap-1">
        <div className="flex justify-between text-xs font-semibold text-slate-600">
          <span>STEP {step}/{max}</span>
          <span>{progress}% GOAL</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-200">
          <div
            className={`h-full rounded-full transition-all duration-500 ${state.status === 'completed' ? 'bg-emerald-500' : state.status === 'failed' ? 'bg-red-500' : 'bg-blue-600'}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </header>
  )
}
