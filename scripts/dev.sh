#!/usr/bin/env bash
# Start the API on :8741 and the terminal on :4317.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8741 --reload &
API_PID=$!

cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
npm run dev &
WEB_PID=$!

trap 'kill "$API_PID" "$WEB_PID"' INT TERM EXIT
wait
