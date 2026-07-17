#!/bin/bash
# Daily paper discovery — invoked by launchd.
# Fires at 06:00 (primary) plus catch-up slots at 09/12/15/18:00 so a run
# missed because the Mac was asleep at 06:00 still happens the next time the
# machine is awake. This script is idempotent: only the first slot that lands
# while awake does work; later slots no-op once today's digest exists.
# Fetches HuggingFace daily papers for the last 2 days, filters by topic,
# and writes a digest to /discovery/YYYY-MM-DD.md
set -euo pipefail

REPO="/Users/ruisenliu/Repositories/Research"
LOG="$REPO/discovery/last-run.log"
CLAUDE="/Users/ruisenliu/.local/bin/claude"
TODAY=$(date '+%Y-%m-%d')
HOUR=$(date '+%H')
DIGEST="$REPO/discovery/$TODAY.md"
MAX_RETRIES=3

cd "$REPO"

# Idempotency guard: if today's digest already exists, a primary or earlier
# catch-up slot already did the work. Skip without calling claude.
if [ -f "$DIGEST" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Digest already exists ($TODAY.md) — already complete, skipping" >> "$LOG"
  exit 0
fi

if [ "$HOUR" = "06" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting paper discovery" >> "$LOG"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting paper discovery (catch-up run — 06:00 slot was missed, likely asleep)" >> "$LOG"
fi

for attempt in $(seq 1 $MAX_RETRIES); do
  [ -f "$DIGEST" ] && break

  if [ $attempt -gt 1 ]; then
    backoff=$(( (attempt - 1) * 60 ))
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Attempt $attempt/$MAX_RETRIES after ${backoff}s backoff..." >> "$LOG"
    sleep $backoff
  fi

  "$CLAUDE" \
    --print \
    --dangerously-skip-permissions \
    "Run the paper-discovery skill with days=2" \
    >> "$LOG" 2>&1 || true
done

if [ ! -f "$DIGEST" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: digest not created after $MAX_RETRIES attempts" >> "$LOG"
  exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done" >> "$LOG"
