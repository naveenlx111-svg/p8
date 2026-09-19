#!/usr/bin/env bash
# One-time (re-runnable) setup: Python env + Chromium + dashboard build + .env.
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null; then
  [ -x .venv/bin/python ] || uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python -r requirements.txt
else
  [ -x .venv/bin/python ] || python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
.venv/bin/playwright install chromium
(cd frontend && npm install && npm run build)
[ -f .env ] || cp .env.example .env

echo
echo "Setup done."
echo "  Local model:  ollama pull qwen2.5:7b   (default in .env)"
echo "  Cloud model:  set PATHLENS_PROVIDER + API key in .env"
echo "  Then run:     scripts/start.sh"
