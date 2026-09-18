#!/usr/bin/env bash
# One-time setup: Python env + Chromium + frontend build.
set -euo pipefail
cd "$(dirname "$0")/.."
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/playwright install chromium
(cd frontend && npm install && npm run build)
[ -f .env ] || cp .env.example .env
echo "Setup done. Put an API key in .env, then run scripts/start.sh"
