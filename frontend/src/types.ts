// Mirror of backend/schemas.py + contracts/websocket.md. Do not add event shapes here that the backend does not emit.

export type EventType =
  | 'run_started' | 'browser_frame' | 'observation' | 'decision'
  | 'action_started' | 'action_completed' | 'axe_update' | 'finding'
  | 'journey_node' | 'journey_edge' | 'score_update' | 'run_completed' | 'run_failed'

export interface RunEvent<P = any> {
  run_id: string
  sequence: number
  timestamp: string
  offset_ms: number
  type: EventType
  payload: P
}

export type Severity = 'info' | 'low' | 'medium' | 'high' | 'critical'
export type Outcome = 'success' | 'stale' | 'blocked' | 'failed' | 'rejected'

export interface RunStarted {
  mode: 'live' | 'replay'
  goal: { raw: string; objective: string; constraints: Record<string, unknown> }
  target_url: string
  provider: string
  model: string
  offline_test_double: boolean
  vision_mode: string
  max_steps: number
  artifact_base: string
  replay_name?: string
  platform: 'web' | 'android'
  device_serial?: string | null
  android_package?: string | null
  record_video: boolean
}

export interface Fact { kind: string; entity: string; value: number; currency: string; context: string }

export interface Decision {
  step: number
  state_id: string
  observed: string
  goal_progress: number
  facts: Fact[]
  facts_rejected: Fact[]
  action: string
  label: string | null
  text: string | null
  rationale: string
  confidence: number
  latency_ms: number
  vision: boolean
  attempts: number
}

export interface ActionCompleted {
  step: number
  action: string
  label: string | null
  outcome: Outcome
  duration_ms: number
  error: string | null
  recovery: boolean
}

export interface Finding {
  finding_id: string
  code: string
  category: string
  severity: Severity
  title: string
  evidence: string
  recommendation: string | null
  step_number: number
  state_id: string | null
  screenshot_id: string | null
  source: 'deterministic' | 'model' | 'axe'
  verified: boolean
  data: Record<string, any>
}

export interface JourneyNode {
  id: string
  label: string
  url: string
  route: string
  step_number: number
  page_type: string | null
  annotation: string | null
  dialog: boolean
  screenshot_id: string | null
  accessibility_tree_id: string | null
  friction_count: number
  semantic_count: number
  accessibility_count: number
  visits: number
  active?: boolean
}

export interface JourneyEdge {
  id: string
  source: string
  target: string
  action: string
  step_number: number
  duration_ms: number
  outcome: Outcome
  recovered: boolean
}

export interface AxeViolation {
  id: string
  impact: 'minor' | 'moderate' | 'serious' | 'critical' | null
  description: string
  help: string
}

export interface ScoreUpdate {
  accessibility_score: number
  accessibility_counts: Record<string, number>
  disclaimer: string
  findings_by_category: Record<string, number>
  friction: Record<string, number>
  friction_score: number
  goal_progress: number
  step: number
  max_steps: number
  final: boolean
}

export interface RunSummary {
  status: string
  goal_completed: boolean
  completion_mode?: 'verified' | 'model_judged' | null
  actions: number
  recoveries: number
  findings_by_category: Record<string, number>
  accessibility_score: number
  runtime_s: number
  model_calls: number
  model_latency_p50_ms: number | null
  report_url?: string
  reason?: string
  error?: string | null
  platform?: 'web' | 'android'
  video_path?: string | null
  video_url?: string
  accessibility_trees?: number
  action_loops?: number
}

export interface RunComparison {
  verdict: 'regression' | 'improvement' | 'no_material_change'
  severity: 'none' | 'medium' | 'high' | 'critical'
  comparable_goal: boolean
  baseline: { run_id: string; target_url: string; goal_completed: boolean; actions: number; runtime_s: number; friction_score: number; accessibility_score: number }
  candidate: { run_id: string; target_url: string; goal_completed: boolean; actions: number; runtime_s: number; friction_score: number; accessibility_score: number }
  deltas: { actions: number; runtime_s: number; friction_score: number; accessibility_score: number }
  reasons: string[]
  improvements: string[]
  new_findings: Finding[]
  resolved_findings: Finding[]
  milestones: { baseline: Array<{ milestone: string; label: string; step: number }>; candidate: Array<{ milestone: string; label: string; step: number }>; added: string[]; missing: string[] }
  method: string
}
