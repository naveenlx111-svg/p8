import { Background, Handle, MarkerType, Position, ReactFlow, type Edge, type Node, type NodeProps, useReactFlow, ReactFlowProvider } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useEffect, useMemo } from 'react'
import type { JourneyNode } from '../types'
import type { RunState } from '../useRun'

type StateNodeData = { n: JourneyNode; active: boolean; goal: boolean }

function StateNode({ data }: NodeProps<Node<StateNodeData>>) {
  const { n, active, goal } = data
  const border = goal ? 'border-emerald-500' : n.semantic_count ? 'border-red-500' : n.friction_count ? 'border-amber-500' : 'border-slate-300'
  const hidden = '!h-1 !w-1 !min-w-0 !border-0 !bg-transparent'
  return (
    <div className={`w-40 cursor-pointer rounded-lg border-2 bg-white px-2 py-1.5 shadow-sm ${border} ${active ? 'node-active' : ''}`}>
      <Handle type="target" position={Position.Left} id="l" className={hidden} />
      <Handle type="source" position={Position.Right} id="r" className={hidden} />
      <Handle type="source" position={Position.Bottom} id="bs" className={hidden} />
      <Handle type="target" position={Position.Top} id="tt" className={hidden} />
      <Handle type="source" position={Position.Top} id="ts" className={hidden} style={{ left: '70%' }} />
      <Handle type="target" position={Position.Bottom} id="bt" className={hidden} style={{ left: '70%' }} />
      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{n.page_type}{n.visits > 1 ? ` · visited ×${n.visits}` : ''}</div>
      <div className="truncate text-xs font-bold text-slate-900" title={n.label}>{n.label}</div>
      <div className="mt-0.5 flex flex-wrap items-center gap-1 text-[10px] font-semibold">
        {n.annotation && <span className="rounded bg-slate-100 px-1 text-slate-800">{n.annotation}</span>}
        {n.semantic_count > 0 && <span className="rounded bg-red-100 px-1 text-red-700">⚠ price</span>}
        {n.friction_count > 0 && <span className="rounded bg-amber-100 px-1 text-amber-800">⚠ friction</span>}
        {n.accessibility_count > 0 && <span className="rounded bg-violet-100 px-1 text-violet-800">⚠ a11y {n.accessibility_count}</span>}
        {goal && <span className="rounded bg-emerald-100 px-1 text-emerald-800">✓ goal</span>}
      </div>
    </div>
  )
}

const nodeTypes = { state: StateNode }

function Graph({ state, onInspect }: { state: RunState; onInspect: (id: string) => void }) {
  const { fitView } = useReactFlow()
  const goalNode = state.status === 'completed' ? state.activeNode : null

  const { nodes, edges } = useMemo(() => {
    const row = (n: JourneyNode) => (n.dialog ? 1 : 0)
    // Page states advance left-to-right; dialog/overlay states hang below the state they interrupted,
    // so a detour + recovery reads as a loop instead of forward progress.
    const col: Record<string, number> = {}
    let next = 0
    for (const id of state.nodeOrder) if (!state.nodes[id].dialog) col[id] = next++
    for (const id of state.nodeOrder) {
      if (!state.nodes[id].dialog) continue
      const parent = state.edges.find(e => e.target === id && e.source in col)?.source
      col[id] = parent ? col[parent] + 0.45 : next++
    }
    const nodes: Node<StateNodeData>[] = state.nodeOrder.map(id => {
      const n = state.nodes[id]
      return {
        id, type: 'state', position: { x: col[id] * 250, y: row(n) * 120 },
        data: { n, active: id === state.activeNode && state.status === 'running', goal: id === goalNode },
      }
    })
    const edges: Edge[] = state.edges
      .filter(e => e.source !== e.target && state.nodes[e.source] && state.nodes[e.target])
      .map(e => {
        const rs = row(state.nodes[e.source]), rt = row(state.nodes[e.target])
        const [sh, th] = rs < rt ? ['bs', 'tt'] : rs > rt ? ['ts', 'bt'] : ['r', 'l']
        const color = e.recovered ? '#d97706' : e.outcome === 'success' ? '#64748b' : '#dc2626'
        return {
          id: e.id, source: e.source, target: e.target, sourceHandle: sh, targetHandle: th, type: 'smoothstep',
          label: `${e.step_number}. ${e.action.length > 22 ? e.action.slice(0, 21) + '…' : e.action}`, animated: e.recovered,
          style: { stroke: color, strokeWidth: 2, strokeDasharray: e.recovered ? '5 4' : undefined },
          labelStyle: { fontSize: 10, fontWeight: 600, fill: '#334155' },
          labelBgStyle: { fill: '#fff' },
          markerEnd: { type: MarkerType.ArrowClosed, color },
        }
      })
    return { nodes, edges }
  }, [state.nodeOrder, state.nodes, state.edges, state.activeNode, state.status, goalNode])

  useEffect(() => {
    const t = setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 50)
    return () => clearTimeout(t)
  }, [nodes.length, fitView])

  return (
    <ReactFlow
      nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView proOptions={{ hideAttribution: true }}
      nodesDraggable={false} nodesConnectable={false} onNodeClick={(_, n) => onInspect(n.id)} minZoom={0.3}
    >
      <Background gap={20} color="#e2e8f0" />
    </ReactFlow>
  )
}

export function JourneyGraph({ state, onInspect }: { state: RunState; onInspect: (id: string) => void }) {
  return (
    <section className="flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white">
      <h2 className="flex items-center border-b border-slate-200 px-3 py-2 text-xs font-bold tracking-widest text-slate-500">
        JOURNEY GRAPH
        <span className="ml-auto font-medium normal-case tracking-normal text-slate-400">
          {state.nodeOrder.length} states · {state.edges.length} actions · click a state for its evidence
        </span>
      </h2>
      <div className="min-h-0 flex-1">
        <ReactFlowProvider>
          <Graph state={state} onInspect={onInspect} />
        </ReactFlowProvider>
      </div>
    </section>
  )
}
