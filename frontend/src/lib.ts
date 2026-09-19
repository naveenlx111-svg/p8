import type { RunState } from './useRun'

export const backendUrl = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '')

/** Base URL that artifact paths (screenshots, accessibility trees) are relative to for this run. */
export const artifactBase = (state: RunState) => (state.started?.artifact_base ? `${backendUrl}${state.started.artifact_base}` : '')

const SYMBOL: Record<string, string> = { INR: '₹', USD: '$', EUR: '€', GBP: '£' }
export const money = (v: number, cur = 'INR') =>
  cur === 'INR'
    ? '₹' + Math.round(v).toLocaleString('en-IN')
    : (SYMBOL[cur] ?? cur + ' ') + v.toLocaleString('en-US', { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 })

export const duration = (s: number) => (s >= 60 ? `${Math.floor(s / 60)} m ${String(Math.round(s % 60)).padStart(2, '0')} s` : `${Math.round(s)} s`)

export const isLive = (state: RunState) => state.status === 'running' || state.status === 'connecting'

export const VERBS: Record<string, string> = {
  click: 'Clicks', type: 'Types', scroll: 'Scrolls', back: 'Goes back', wait: 'Waits', done: 'Marks the goal done',
}

export const SEVERITY_RANK: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 }
