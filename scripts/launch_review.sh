#!/bin/bash
# Launch the local discovery review website on localhost.
# Usage: bash scripts/launch_review.sh [port]   (default port: 8000)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-8000}"
PY="$REPO/researchEnv/bin/python"

if [ ! -x "$PY" ]; then
  echo "error: no interpreter at $PY — create the virtualenv first (see README → Environment)" >&2
  exit 1
fi

cd "$REPO"

"$PY" "$REPO/scripts/review_server.py" --port "$PORT" &
SERVER_PID=$!

# Stop the server on Ctrl-C / termination.
trap 'kill "$SERVER_PID" 2>/dev/null || true' INT TERM EXIT

# Give the server a moment to bind, then open the browser.
sleep 1
open "http://localhost:$PORT" 2>/dev/null || true

wait "$SERVER_PID"
