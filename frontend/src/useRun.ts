import { useCallback, useEffect, useReducer, useRef } from 'react'
import type {
  ActionCompleted, AxeViolation, Decision, Finding, JourneyEdge, JourneyNode, RunEvent, RunStarted, RunSummary,
  ScoreUpdate,
} from './types'

export type StreamItem =
  | { kind: 'decision'; seq: number; d: Decision; outcome?: ActionCompleted }
  | { kind: 'finding'; seq: number; f: Finding }
  | { kind: 'verified'; seq: number; evidence: string[] }
  | { kind: 'rejected'; seq: number; a: ActionCompleted }

export interface RunState {
  runId: string | null
  status: 'idle' | 'connecting' | 'running' | 'completed' | 'failed'
  started: RunStarted | null
  frame: { image: string; url: string; step: number } | null
  stream: StreamItem[]
  nodes: Record<string, JourneyNode>
  nodeOrder: string[]
  edges: JourneyEdge[]
  activeNode: string | null
  findings: Finding[]
  violations: AxeViolation[]
  score: ScoreUpdate | null
  summary: RunSummary | null
  lastSeq: number
  pendingAction: string | null
}

const initial: RunState = {
  runId: null, status: 'idle', started: null, frame: null, stream: [], nodes: {}, nodeOrder: [], edges: [],
  activeNode: null, findings: [], violations: [], score: null, summary: null, lastSeq: 0, pendingAction: null,
}

type Action = { type: 'reset'; runId: string } | { type: 'event'; ev: RunEvent } | { type: 'ws_error' }

function reduce(s: RunState, a: Action): RunState {
  if (a.type === 'reset') return { ...initial, runId: a.runId, status: 'connecting' }
  if (a.type === 'ws_error') return s
  const ev = a.ev
  if (ev.sequence <= s.lastSeq) return s // idempotent on reconnect
  const p = ev.payload
  const next: RunState = { ...s, lastSeq: ev.sequence, status: s.status === 'connecting' ? 'running' : s.status }
  switch (ev.type) {
    case 'run_started':
      return { ...next, started: p as RunStarted, status: 'running' }
    case 'browser_frame':
      return { ...next, frame: { image: p.image, url: p.url, step: p.step } }
    case 'observation':
      if (p.verification) return { ...next, stream: [...s.stream, { kind: 'verified', seq: ev.sequence, evidence: p.verification.evidence }] }
      return next
    case 'decision':
      return { ...next, stream: [...s.stream, { kind: 'decision', seq: ev.sequence, d: p as Decision }] }
    case 'action_started':
      return { ...next, pendingAction: p.label || p.action }
    case 'action_completed': {
      const ac = p as ActionCompleted
      const stream = [...s.stream]
      for (let i = stream.length - 1; i >= 0; i--) {
        const it = stream[i]
        if (it.kind === 'decision' && it.d.step === ac.step) {
          stream[i] = { ...it, outcome: ac }
          break
        }
      }
      if (ac.outcome === 'rejected') stream.push({ kind: 'rejected', seq: ev.sequence, a: ac })
      return { ...next, stream, pendingAction: null }
    }
    case 'finding':
      return { ...next, findings: [...s.findings, p as Finding], stream: [...s.stream, { kind: 'finding', seq: ev.sequence, f: p as Finding }] }
    case 'journey_node': {
      const n = p as JourneyNode
      const known = n.id in s.nodes
      return {
        ...next,
        nodes: { ...s.nodes, [n.id]: { ...s.nodes[n.id], ...n } },
        nodeOrder: known ? s.nodeOrder : [...s.nodeOrder, n.id],
        activeNode: n.active ? n.id : s.activeNode,
      }
    }
    case 'journey_edge':
      return { ...next, edges: [...s.edges, p as JourneyEdge] }
    case 'axe_update': {
      if (!p.violations) return next
      const known = new Set(s.violations.map(v => v.id))
      return { ...next, violations: [...s.violations, ...(p.violations as AxeViolation[]).filter(v => !known.has(v.id))] }
    }
    case 'score_update':
      return { ...next, score: p as ScoreUpdate }
    case 'run_completed':
      return { ...next, status: 'completed', summary: p as RunSummary, pendingAction: null }
    case 'run_failed':
      return { ...next, status: 'failed', summary: p as RunSummary, pendingAction: null }
  }
  return next
}

export function useRun() {
  const [state, dispatch] = useReducer(reduce, initial)
  const wsRef = useRef<WebSocket | null>(null)
  const seqRef = useRef(0)
  const doneRef = useRef(false)
  seqRef.current = state.lastSeq
  doneRef.current = state.status === 'completed' || state.status === 'failed'

  const connect = useCallback((runId: string, attempt = 0) => {
    const defaultProto = location.protocol === 'https:' ? 'wss' : 'ws'
    const backend = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '')
    const wsBase = import.meta.env.VITE_WS_URL || (backend ? backend.replace(/^http/, 'ws') : `${defaultProto}://${location.host}`)
    const ws = new WebSocket(`${wsBase}/ws/runs/${runId}?after=${seqRef.current}`)
    wsRef.current = ws
    ws.onmessage = m => dispatch({ type: 'event', ev: JSON.parse(m.data) })
    ws.onclose = () => {
      if (wsRef.current !== ws || doneRef.current || attempt > 20) return
      setTimeout(() => connect(runId, attempt + 1), 800) // reconnect, resuming after the last sequence
    }
  }, [])

  useEffect(() => () => { wsRef.current?.close() }, [])

  const start = useCallback(async (body: Record<string, unknown>) => {
    wsRef.current?.close()
    wsRef.current = null
    const backend = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '')
    const r = await fetch(`${backend}/api/runs`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
    if (!r.ok) throw new Error(await r.text())
    const { run_id } = await r.json()
    seqRef.current = 0
    doneRef.current = false
    dispatch({ type: 'reset', runId: run_id })
    connect(run_id)
  }, [connect])

  return { state, start }
}

