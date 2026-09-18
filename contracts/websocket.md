# PathLens WebSocket event contract (frozen)

Source of truth: `backend/schemas.py` (`Event`, payload models). Mirror: `frontend/src/types.ts`.
Live runs and replays emit the **identical** contract; only `run_started.payload.mode` differs (`live` | `replay`).

Endpoint: `ws://<host>/ws/runs/{run_id}?after=<last_sequence>`. The server sends every event with
`sequence > after`, then streams live events. After a disconnect, the client reconnects with its last sequence.
REST equivalent: `GET /api/runs/{run_id}/events?after=N`.

## Envelope

```json
{ "run_id": "abc", "sequence": 18, "timestamp": "ISO-8601", "offset_ms": 3840, "type": "finding", "payload": {} }
```

`offset_ms` is the time since run start. Replay uses it to reproduce the original timing.

## Types

| type | payload (key fields) |
|---|---|
| `run_started` | mode, goal (GoalSpec), target_url, provider, model, offline_test_double, vision_mode, max_steps, artifact_base, replay_name? |
| `browser_frame` | image (file name under artifact_base), url, step, state_id |
| `observation` | observation_id, route, heading, dialog_open, dialog_name, element_count, state_id, elements[] — or `{verification: {completed, evidence[]}}` |
| `decision` | step, observed (page summary), goal_progress, facts[] (grounded), facts_rejected[], action, label, text, rationale, confidence, latency_ms, vision, attempts |
| `action_started` | step, action, label, text, target (semantic descriptor role/name — never a selector) |
| `action_completed` | step, action, label, outcome (success/stale/blocked/failed/rejected), duration_ms, error, recovery |
| `axe_update` | final, state_id, violations[], new_rules[], score, counts |
| `finding` | CriticFinding: code, category, severity, title, evidence, recommendation, step_number, state_id, screenshot_id, source (deterministic/model/axe), verified, data |
| `journey_node` | JourneyNode (upsert by id): id=state fingerprint, label, route, page_type, annotation, dialog, counts, visits, active? |
| `journey_edge` | JourneyEdge: id, source, target, action, step_number, duration_ms, outcome, recovered |
| `score_update` | accessibility_score, accessibility_counts, disclaimer, findings_by_category, friction{}, friction_score, goal_progress, step, max_steps, final |
| `run_completed` / `run_failed` | summary: status, actions, recoveries, findings_by_category, accessibility_score, runtime_s, model stats, report_url, reason?, fallback_available? |

Screenshots are **never** base64 in events or in JSONL. Frames are files at `artifact_base + image`.
