import { BaseEdge, Controls, getSmoothStepPath, type EdgeProps, Handle, MarkerType, Position, ReactFlow, type Edge, type Node, type NodeProps, useReactFlow, ReactFlowProvider } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useEffect, useMemo } from 'react'
import { artifactBase } from '../lib'
import type { JourneyNode } from '../types'
import type { RunState } from '../useRun'

type StateNodeData = { n: JourneyNode; active: boolean; goal: boolean; selected: boolean; thumb: string | null }

function StateNode({ data }: NodeProps<Node<StateNodeData>>) {
  const { n, active, goal, selected, thumb } = data
  const issues = n.semantic_count + n.friction_count + n.accessibility_count
  const tone = n.semantic_count ? 'bad' : n.friction_count ? 'warn' : ''
  const breakdown = [n.semantic_count && `${n.semantic_count} price`, n.friction_count && `${n.friction_count} friction`, n.accessibility_count && `${n.accessibility_count} accessibility`].filter(Boolean).join(', ')
  return (
    <div className={`smap-node ${n.dialog ? 'is-dialog' : ''} ${n.semantic_count ? 'is-issue' : ''} ${active ? 'is-active' : ''} ${selected ? 'is-selected' : ''}`}>
      <Handle type="target" position={Position.Left} id="l" className="smap-handle" />
      <Handle type="source" position={Position.Right} id="r" className="smap-handle" />
      <Handle type="source" position={Position.Bottom} id="bs" className="smap-handle" />
      <Handle type="target" position={Position.Top} id="tt" className="smap-handle" />
      <Handle type="source" position={Position.Top} id="ts" className="smap-handle" style={{ left: '70%' }} />
      <Handle type="target" position={Position.Bottom} id="bt" className="smap-handle" style={{ left: '70%' }} />
      <div className="smap-thumb">{thumb && <img src={thumb} alt="" loading="lazy" />}</div>
      <div className="smap-body">
        <div className="smap-title" title={n.label}>{n.label}</div>
        <div className="smap-route" title={n.url}>{n.route || n.url}</div>
        <div className="smap-tags">
          {n.annotation && <span>{n.annotation}</span>}
          {issues > 0 && <span className={tone} title={breakdown}>{issues} {issues === 1 ? 'issue' : 'issues'}</span>}
          {n.visits > 1 && <span>visited {n.visits}×</span>}
          {goal && <span className="ok">✓ goal</span>}
        </div>
      </div>
    </div>
  )
}

// Bound labels to the available gap; separate the outbound and recovery lanes.
function ActionEdge(props: EdgeProps) {
  const [path, centerX, centerY] = getSmoothStepPath(props)
  const down = props.sourceHandleId === 'bs'
  const up = props.sourceHandleId === 'ts'
  const width = down || up ? 140 : 82
  const x = down || up ? props.sourceX : centerX
  const y = down ? props.sourceY + 38 : up ? props.sourceY - 34 : centerY
  return <>
    <BaseEdge path={path} markerEnd={props.markerEnd} style={props.style} />
    <foreignObject x={x - width / 2} y={y - 25} width={width} height={50} className="journey-action-label">
      <div title={String(props.label ?? '')}><span>{props.label}</span></div>
    </foreignObject>
  </>
}

const edgeTypes = { action: ActionEdge }
const nodeTypes = { state: StateNode }

function Graph({ state, inspect, onInspect }: { state: RunState; inspect: string | null; onInspect: (id: string) => void }) {
  const { fitView } = useReactFlow()
  const goalNode = state.status === 'completed' ? state.activeNode : null
  const base = artifactBase(state)

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
        id, type: 'state', position: { x: col[id] * 260, y: row(n) * 250 },
        data: { n, active: id === state.activeNode && state.status === 'running', goal: id === goalNode, selected: id === inspect, thumb: n.screenshot_id ? base + n.screenshot_id : null },
      }
    })
    const edges: Edge[] = state.edges
      .filter(e => e.source !== e.target && state.nodes[e.source] && state.nodes[e.target])
      .map(e => {
        const rs = row(state.nodes[e.source]), rt = row(state.nodes[e.target])
        const [sh, th] = rs < rt ? ['bs', 'tt'] : rs > rt ? ['ts', 'bt'] : ['r', 'l']
        const color = e.recovered ? '#b7791f' : e.outcome === 'success' ? '#8b8a84' : '#c0392b'
        return {
          id: e.id, source: e.source, target: e.target, sourceHandle: sh, targetHandle: th, type: 'action',
          label: `${e.step_number}. ${e.action}`, animated: e.recovered,
          style: { stroke: color, strokeWidth: 1.5, strokeDasharray: e.recovered ? '5 4' : undefined },
          markerEnd: { type: MarkerType.ArrowClosed, color, width: 14, height: 14 },
        }
      })
    return { nodes, edges }
  }, [state.nodeOrder, state.nodes, state.edges, state.activeNode, state.status, goalNode, inspect, base])

  useEffect(() => {
    const t = setTimeout(() => fitView({ padding: 0.12, duration: 300 }), 50)
    return () => clearTimeout(t)
  }, [nodes.length, fitView])

  return (
    <ReactFlow
      nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} fitView proOptions={{ hideAttribution: true }}
      nodesDraggable={false} nodesConnectable={false} onNodeClick={(_, n) => onInspect(n.id)} minZoom={0.3}
    >
      <Controls showInteractive={false} position="bottom-left" fitViewOptions={{ padding: 0.12, duration: 300 }} />
    </ReactFlow>
  )
}

export function ScreenMap({ state, inspect, onInspect }: { state: RunState; inspect: string | null; onInspect: (id: string) => void }) {
  return (
    <section className="section" aria-label="Map of screens">
      <div className="section-head">
        <h2>Map of screens</h2>
        <p>Each box is a distinct screen state; arrows are the actions between them. Click a screen to see its evidence.</p>
      </div>
      <div className="smap">
        {state.nodeOrder.length === 0 && <div className="smap-empty">Your path takes shape here as the agent moves.</div>}
        <ReactFlowProvider>
          <Graph state={state} inspect={inspect} onInspect={onInspect} />
        </ReactFlowProvider>
      </div>
    </section>
  )
}
