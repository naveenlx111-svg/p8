#!/usr/bin/env bash
# Start the demo target app (:4173) and the PathLens backend + built dashboard (:8000).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d frontend/dist ] || (cd frontend && npm install && npm run build)
.venv/bin/python -m http.server 4173 -d demo_app --bind 127.0.0.1 >/tmp/pathlens-demo.log 2>&1 &
DEMO=$!
trap 'kill $DEMO 2>/dev/null' EXIT
echo "demo app  → http://127.0.0.1:4173"
echo "dashboard → http://127.0.0.1:8000"
.venv/bin/uvicorn backend.api.app:app --host 127.0.0.1 --port 8000
