# Fold classification into the summary sub-agent to cut pipeline Opus cost

**Status:** completed (2026-07-06)

## Context / motivation

A prior session's `/usage` showed the pipeline's cost heavily skewed to Opus over Sonnet.
Transcript measurement confirmed cost was ~97% Opus even though summary sub-agents run on Sonnet.
Root cause: `library-filing` runs serially in the **Opus orchestrator** and, per paper, re-reads
the Sonnet-written summary plus every MOC intro to pick a topic — duplicating context for what is
an **i.i.d.** per-paper decision (depends only on the paper + the topic menu, not on the batch).

Lever: move topic judgment to the Sonnet sub-agent that already holds the paper, and reduce filing
to a mechanical, frontmatter-driven end-of-batch step. Fetch/paperclip micro-optimization is a
rounding error by comparison.

### Measurement gotchas discovered (2026-07-06)
- Sub-agent transcripts land in the harness **task-output** files (session scratchpad `tasks/*.output`),
  **not** the project `*.jsonl`. A project-dir measurement captures the orchestrator thread only.
- `model: opus` on a `general-purpose` sub-agent is **silently ignored** — they run Sonnet. So you
  cannot A/B "Opus filing" via a sub-agent; reprice the filing token-volume at the Opus rate instead.

## Implementation steps

1. `scripts/topic_menu.py` — emit a compact `Topic — one-line scope` menu from each MOC intro
   (~26 rows, ~2k tokens) so the orchestrator hands sub-agents a small menu instead of reading MOCs.
2. `pipeline-orchestrator/SKILL.md`:
   - Rewrite intro + "why this split" rationale (orchestrator stays cheap; concurrency hazard gone).
   - Fix Step 2 paperclip search: `search -s arxiv "QUERY"` (source flag required).
   - New Step 5: build the topic menu once via `topic_menu.py`.
   - Step 6 sub-agent prompt: summarize **and** classify (method-first + confidence gate per
     `library-filing` Steps 2–3), stamp `topic:` into frontmatter when confident, else report UNSURE.
   - New Step 7: mechanical batch filing — `mv` confident notes → `Library/<topic>/`, one
     `rebuild_index.py` (+ `--check`), one cap/split check, stragglers stay in `staging/`.
   - Renumber report (Step 8) + teardown (Step 9); update straggler vocabulary.
   - New `## Benchmarking` section documenting the drift guard + A/B procedure + gotchas.
3. `library-filing/SKILL.md` — note the interactive-vs-pipeline division of labor (still source of truth).
4. `pipeline-orchestrator/evals/` — committed drift guard: `cost_report.py` (cost aggregator),
   `check_classifications.py` + `golden_set.jsonl` (classification correctness), `README.md`.
   (`topic_menu.py` stays in `scripts/` — it's a runtime dependency the skill calls each run, not an eval.)

## Affected files
- `scripts/topic_menu.py` (new — runtime helper)
- `.claude/skills/pipeline-orchestrator/SKILL.md`
- `.claude/skills/pipeline-orchestrator/evals/` (new — cost_report.py, check_classifications.py, golden_set.jsonl, README.md)
- `.claude/skills/library-filing/SKILL.md`

## Verification criteria
- `ruff check` + `mypy` pass on new Python.
- `topic_menu.py` emits one row per Library topic; `rebuild_index.py --check` still exits 0.
- A/B cost (2-paper sample, priced from task-output transcripts): OLD end-to-end on an Opus
  orchestrator vs NEW (summary+classify on Sonnet + mechanical filing) — confirm the Opus/main
  per-paper cost collapses.
- Functional: new sub-agent writes the staging note AND stamps a correct `topic:` (or reports UNSURE);
  mechanical filing lands the note in the right `index.json`.

## Results (2026-07-06)

A/B measured from real sub-agent task-output transcripts (2-paper sample: WHIRL 2207.09450,
VINN 2112.01511), priced with `cost_report.py`'s rate table.

| Per paper | OLD | NEW |
|---|---|---|
| Summary (Sonnet) | $0.576 | — |
| Summary + classify (Sonnet) | — | $0.654 (classify increment +$0.078) |
| Filing on the Opus orchestrator (summary + 26 MOC intros; 1.2M cache-read/2 papers) | $3.936 | — |
| Filing: mechanical `mv` + one `rebuild_index.py` (main thread) | — | ~$0 |
| **End-to-end / paper** | **~$4.51** | **~$0.65** (~85% ↓) |

Opus/main-thread per-paper cost: **$3.94 → ~$0**. Structural win beyond the number: the
orchestrator never reads a summary or MOC, so its context stays flat as the batch grows (the old
long-lived-Opus-context cost the original investigation flagged is eliminated, not just amortized).

**Functional checks passed:** both sub-agents wrote the staging note AND stamped a correct,
confident `topic:` (Human-to-Robot Demonstration Transfer) without touching any index; mechanical
filing moved both notes, one `rebuild_index.py` rebuilt the index (18 papers, under the 20 cap),
`--check` exited 0, both IDs present in `index.json`.

**Two measurement gotchas discovered (now documented in the skill's `## Benchmarking`):**
sub-agent cost lives in `tasks/*.output` not the project `*.jsonl`; and `model: opus` on a
general-purpose sub-agent is silently ignored (they run Sonnet). The first invalidated an earlier
"$1.77 all-Opus filing" baseline (it was measuring polluted main-session context); corrected above.

Completion checklist: ruff ✓, mypy ✓, `rebuild_index.py --check` exit 0 ✓, functional smoke ✓.
