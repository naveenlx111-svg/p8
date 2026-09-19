#!/usr/bin/env bash
# Start PathLens locally: demo target app (:4173) + backend API and built dashboard (:8000).
# Rebuilds the dashboard if its sources changed, checks the model backend, and prints a health summary.
# Stop with Ctrl+C (or scripts/stop.sh if they were started elsewhere).
set -euo pipefail
cd "$(dirname "$0")/.."

DEMO_PORT=4173
API_PORT=8000
LOG_DIR="${TMPDIR:-/tmp}/pathlens"
mkdir -p "$LOG_DIR"

port_busy() { ss -ltn "sport = :$1" 2>/dev/null | grep -q LISTEN; }
env_get() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' || true; }

# 1. Python environment
if [ ! -x .venv/bin/python ]; then
  echo "✗ No .venv found. Run scripts/setup.sh first."; exit 1
fi
[ -f .env ] || { cp .env.example .env; echo "• Created .env from .env.example"; }

# 2. Dashboard build: rebuild when missing or when any frontend source is newer than the build
if [ ! -f frontend/dist/index.html ] || [ -n "$(find frontend/src frontend/index.html frontend/vite.config.ts frontend/package.json -newer frontend/dist/index.html -print -quit 2>/dev/null)" ]; then
  echo "• Building dashboard (sources changed)…"
  if ! (cd frontend && { [ -d node_modules ] || npm install; } && npm run build) >"$LOG_DIR/build.log" 2>&1; then
    echo "✗ Dashboard build failed:"; tail -20 "$LOG_DIR/build.log"; exit 1
  fi
fi

# 3. Model backend
PROVIDER="$(env_get PATHLENS_PROVIDER)"; PROVIDER="${PROVIDER:-gemini}"
MODEL="$(env_get PATHLENS_MODEL)"
if [ "$PROVIDER" = "ollama" ]; then
  OLLAMA_URL="$(env_get PATHLENS_OLLAMA_BASE_URL)"; OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
  MODEL="${MODEL:-qwen2.5:7b}"
  if ! curl -sf --max-time 3 "$OLLAMA_URL/api/version" >/dev/null; then
    echo "✗ Ollama is not reachable at $OLLAMA_URL. Start it (e.g. 'ollama serve' or 'systemctl start ollama')."; exit 1
  fi
  if ! curl -sf --max-time 5 "$OLLAMA_URL/api/tags" | grep -q "\"name\":\"$MODEL\""; then
    echo "✗ Ollama model '$MODEL' is not pulled. Run: ollama pull $MODEL"; exit 1
  fi
  echo "• Model: ollama/$MODEL"
else
  echo "• Model: $PROVIDER/${MODEL:-default} (API key read from .env)"
fi

# 4. Ports
if port_busy "$API_PORT"; then
  echo "✗ Port $API_PORT is already in use (PathLens already running?). Run scripts/stop.sh, then retry."; exit 1
fi
PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

if port_busy "$DEMO_PORT"; then
  echo "• Demo app already running on :$DEMO_PORT (reusing it)"
else
  .venv/bin/python -m http.server "$DEMO_PORT" -d demo_app --bind 127.0.0.1 >"$LOG_DIR/demo.log" 2>&1 &
  PIDS+=($!)
fi

.venv/bin/uvicorn backend.api.app:app --host 127.0.0.1 --port "$API_PORT" >"$LOG_DIR/api.log" 2>&1 &
API_PID=$!
PIDS+=($API_PID)

# 5. Wait for the API, then show the health summary
for _ in $(seq 1 40); do
  curl -sf --max-time 2 "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1 && break
  kill -0 "$API_PID" 2>/dev/null || { echo "✗ Backend exited. Log:"; tail -20 "$LOG_DIR/api.log"; exit 1; }
  sleep 0.5
done
curl -s --max-time 120 "http://127.0.0.1:$API_PORT/health?deep=true" | .venv/bin/python -c '
import sys, json
d = json.load(sys.stdin)
for k, v in d["details"].items():
    mark = "✓" if d[k] else "✗"
    print(f"  {mark} {k:<11} {v}")
print("  ALL GREEN" if d["all_green"] else "  ⚠ some checks failed (see above)")
' || echo "  (health check unavailable)"

echo
echo "  demo app  → http://127.0.0.1:$DEMO_PORT"
echo "  dashboard → http://127.0.0.1:$API_PORT"
echo "  logs      → $LOG_DIR/{api,demo}.log     (Ctrl+C to stop)"
wait "$API_PID"
