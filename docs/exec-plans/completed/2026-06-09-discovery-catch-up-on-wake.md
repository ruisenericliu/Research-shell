# Discovery: run on next wake if 6 AM was missed

## Context / motivation

On 2026-06-08 the daily discovery job never ran. Root cause: the Mac was in
deep sleep at the scheduled 06:00 (no full wake until 12:18 PM), and macOS
`launchd` does not wake the machine for a `StartCalendarInterval` job. The
missed run was eventually coalesced and fired at 05:00 on 2026-06-09 during a
maintenance dark-wake — but notably it did **not** fire at the 12:18 PM full
wake on the 8th, so launchd's built-in coalescing is too unreliable to treat as
"run on next wake."

The fix should make the job run at the next opportunity the machine is awake,
without requiring `sudo`/`pmset` (the user declined waking the machine) and
without third-party tools (sleepwatcher/Homebrew).

## Approach

Give `launchd` **multiple calendar slots** through the day and make the script
**idempotent**:

- The plist fires at 06:00 (primary) plus catch-up slots at 09:00, 12:00,
  15:00, 18:00.
- The script exits early if today's digest already exists, so only the first
  slot that lands while the Mac is awake does work; later slots no-op.

This is a fully-native "run at next opportunity if missed" with no machine
wake and no external deps. The 2-day fetch window means a later-in-day catch-up
still captures the missed day's papers.

## Implementation steps

1. `scripts/paper-discovery.sh` — add an early idempotency guard: if
   `$DIGEST` already exists, log "already complete, skipping" and exit 0.
   Annotate runs that fire outside the 06:00 primary slot as catch-up runs in
   the log.
2. `scripts/com.research.paper-discovery.plist` — replace the single
   `StartCalendarInterval` dict with an array of dicts (06/09/12/15/18:00).
3. Reinstall + reload the agent: copy plist to `~/Library/LaunchAgents/`,
   `launchctl bootout` the old instance, `bootstrap` the new one.
4. Verify: `bash -n` the script; dry-run the idempotency guard with an existing
   digest; confirm `launchctl print` shows the 5 calendar intervals.
5. Update `ARCHITECTURE.md` (discovery pipeline section; also fix the stale
   "8:07 AM"/"8 AM" mentions that contradict the 6 AM plist).

## Affected files

- `scripts/paper-discovery.sh`
- `scripts/com.research.paper-discovery.plist`
- `~/Library/LaunchAgents/com.research.paper-discovery.plist` (installed copy)
- `ARCHITECTURE.md`

## Verification criteria

- [x] `bash -n scripts/paper-discovery.sh` passes.
- [x] Running the script when today's digest exists logs "already complete" and
      makes no `claude` call (exit 0). Verified: logged
      `Digest already exists (2026-06-09.md) — already complete, skipping`.
- [x] `plutil -lint` passes on the plist; `launchctl print` shows 5 intervals
      (06/09/12/15/18:00), agent reloaded via bootout/bootstrap.
- [x] ARCHITECTURE.md reflects the multi-slot catch-up schedule (and stale
      "8:07 AM"/"8 AM" mentions corrected to 6 AM).

Note: repo `ruff`/`mypy` checklist items are N/A — this change touches only a
shell script, a launchd plist, and Markdown docs.
