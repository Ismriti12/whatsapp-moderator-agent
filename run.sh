#!/usr/bin/env bash
# Launches the API/listener and the Streamlit dashboard in the background.
# Usage: bash scripts/run.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "Virtual environment not found. Run scripts/setup.sh first." >&2
  exit 1
fi

echo "==> Starting API/listener (logs: $ROOT/data/api.log)"
"$PY" -m app.main > "$ROOT/data/api.log" 2>&1 &
echo "    PID $!"

echo "==> Starting dashboard (logs: $ROOT/data/dashboard.log)"
"$ROOT/venv/bin/streamlit" run "$ROOT/dashboard/dashboard.py" > "$ROOT/data/dashboard.log" 2>&1 &
echo "    PID $!"

echo "Both processes started. Use 'kill <PID>' to stop them."
