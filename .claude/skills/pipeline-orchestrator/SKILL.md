---
name: pipeline-orchestrator
description: "Conduct the full research pipeline (discovery → summary → filing) across many papers from a single prompt. Use when the user wants to process, triage, or bulk-ingest a LIST of papers into the Library (e.g. 'summarize and file these arxiv links', 'run the pipeline on this discovery digest', 'process my staging list into the library'), or when they ask for something GENERIC that implies assembling and ingesting many papers (e.g. 'build a literature review on X', 'survey recent work on Y and file it'). This is the multi-paper orchestrator — for a single paper, use arxiv-summary (+ library-filing) directly instead."
---

# Pipeline Orchestrator

Drive many papers through the existing single-purpose skills from one request. You (the main agent) are the **orchestrator**: you build a worklist and a topic menu, fan out **summary + classification** work to parallel sub-agents, then **file mechanically** at the end of the batch. You never read a paper's body or its summary into your own context — the sub-agents summarize *and* pick the topic; you only move files, run one index rebuild, and resolve the few papers they were unsure about.

All paths are relative to the Research repo root: `/Users/ruisenliu/Repositories/Research/`. The Python interpreter for any script is `researchEnv/bin/python3`.

**Why this split (and why the orchestrator stays cheap):** per-paper topic choice is an i.i.d. decision — it depends only on (this paper, the topic menu), not on the other papers in the batch. So it belongs in the Sonnet sub-agent that already has the paper in context, not in a long-lived Opus thread that re-reads every summary to file it. Each sub-agent writes an **isolated** staging note and stamps `topic:` into its own frontmatter; it never touches shared `index.json`. That removes the concurrency hazard that used to justify serial Opus filing: with topics living in per-note frontmatter, the batch is filed by one `mv` pass + a single `rebuild_index.py` that reconstructs every `index.json` from frontmatter (correct by construction, `library-filing` Step 6). The orchestrator's only judgment work is the end-of-batch cap/split check and the handful of low-confidence stragglers. See `## Benchmarking` for the cost rationale and the drift guard that keeps classification on Sonnet.

If unsure how to manage the parallel pool mechanically, consult `superpowers:dispatching-parallel-agents`.

## Step 1: Classify the input

Decide which intake mode you're in:

- **LIST mode** — the prompt names or points at concrete papers: arxiv URLs/IDs, a file of notes, a pasted reference list, a `discovery/YYYY-MM-DD.md` digest, or `staging/unsorted.txt`.
- **GENERIC mode** — the ask is a topic or goal with no explicit list ("literature review on world models for manipulation", "survey recent VLA papers").

When both are present (a topic *and* some seed links), treat it as GENERIC seeded by the given links.

## Step 2: Build the candidate list

Produce a flat list of `Title — https://arxiv.org/abs/ID` candidates.

- **LIST mode**:
  - If the input is already clean arxiv URLs/IDs, parse them directly.
  - If it's messy notes or informal references, **delegate to the `notes-to-papers` skill** to resolve titles → arxiv IDs (it writes `staging/unsorted.txt`), then read that file back. Do not re-implement its search logic.
- **GENERIC mode**:
  - Assemble candidates with `mcp__paperclip__paperclip` semantic search (`search -s arxiv "QUERY" -n 10` — the `-s arxiv` source flag is required), expanding to a few queries to cover the topic's facets. Fall back to the HF papers API / web search the way `notes-to-papers` Routes B/C describe. You may also seed from a recent `discovery/` digest when the topic matches.
  - **Mandatory checkpoint:** present the assembled list to the user and get explicit confirmation (let them prune/add) **before** spawning any sub-agent. This is the one required human gate.

In LIST mode, only pause for confirmation if extraction was fuzzy or low-confidence; clean explicit links can proceed.

## Step 3: Dedup against the Library index

Before queueing, read every `Library/*/index.json` (each is a small JSON array) and collect the set of already-filed `arxiv_id`s. Drop any candidate whose ID is already filed. This is the cheap, indexed dedup the index layer exists for — do not scan note bodies.

```bash
cat Library/*/index.json
```

Report skipped (already-filed) papers in the final summary.

## Step 4: Write the worklist file

Create `staging/worklist-YYYY-MM-DD.md` (append a short slug if one already exists for today). This table is the **single source of truth** across turns, so a session reset can resume from it:

```markdown
# Pipeline Worklist — 2026-06-07 — <source description>

| # | Name | arxiv | summary | filed |
|---|------|-------|---------|-------|
| 1 | VLA-0 | 2510.13054 | queued | — |
| 2 | (tbd) | 2505.01234 | queued | — |
```

Status vocabulary:
- **summary**: `queued` → `summarizing` → `summarized` | `failed(<reason>)`
- **filed**: `—` → `<Topic> (N)` | `declined(staging; candidates: A/B)` | `failed(<reason>)`

Update the relevant row every time a sub-agent reports or you file at the end.

## Step 5: Build the topic menu once (for in-agent classification)

Each summary sub-agent will also **classify** its paper, so it needs the list of Library topics and their scopes. Materialize this menu **to a file once** and have each sub-agent read it — do **not** capture it into your own context and paste it into prompts. **Redirect the script straight to a file so the menu never passes through your generation** (it is derived from the MOCs by the script, so there is nothing for you to author):

```bash
researchEnv/bin/python3 scripts/topic_menu.py > staging/topic-menu.txt
```

This writes one `Topic name — one-line scope` row per `Library/<Topic>/MOC.md` intro (~26 rows, ~1.7k tokens) to `staging/topic-menu.txt`. Each sub-agent will `Read` that path itself (Step 6), so the menu lands in the cheap Sonnet contexts as tool output, never in your (opus) output or re-read prefix. Do **not** `cat` the file into your own thread, and do **not** read the MOC bodies — the whole point is to keep topic scopes out of the orchestrator's context entirely. If a brand-new topic folder lacks an intro paragraph its row will be name-only; that is fine. (Teardown deletes `staging/topic-menu.txt`; it is regenerated each run.)

## Step 6: Run the summary + classify pool (bounded FIFO, parallel)

Maintain a FIFO queue of `queued` papers and a pool of **at most 10 concurrent** sub-agents.

- Spawn each via the **Agent tool** with `subagent_type: general-purpose`, `model: sonnet`, `run_in_background: true`.
- **Fetch source — this matters.** Background sub-agents run non-interactively, so any tool that would normally prompt for permission is **auto-denied** — `WebFetch` (which `arxiv-summary` Step 1 reaches for by default) fails outright unless its domain is allowlisted. Direct each sub-agent to a fetch path that is allowlisted for non-interactive use:
  - **Preferred: Paperclip.** It mirrors arXiv full text. First check coverage yourself (orchestrator) with `mcp__paperclip__paperclip` — `ls /papers/arx_<id>` — and pass the agent the exact path. The agent reads `cat /papers/arx_<id>/meta.json` (metadata) and `cat /papers/arx_<id>/content.lines` (body), then runs the rest of `arxiv-summary` on that text (skipping its Step 1 fetch). The `mcp__paperclip__paperclip` tool is allowlisted, so this works in background.
  - **Fallback (papers paperclip lacks): `WebFetch(domain:arxiv.org)`** — allowlisted in `.claude/settings.json`, so it also works non-interactively. Tell the agent to fetch `https://arxiv.org/abs/<id>` then `https://arxiv.org/html/<id>`.
- Sub-agent task prompt (one paper each — fill in the fetch source per above; the sub-agent reads the Step 5 **topic menu** file itself rather than you pasting it):
  > The paper `<Name>` (arxiv `<id>`) is available full-text in Paperclip at `/papers/arx_<id>/`. Fetch it using ONLY the `mcp__paperclip__paperclip` tool (`cat /papers/arx_<id>/meta.json` for metadata, `cat /papers/arx_<id>/content.lines` for the body) — do NOT use WebFetch/Bash curl, they are denied in your non-interactive context. Then run the `arxiv-summary` skill's analysis and "Saving to File" rules on that text (skip its Step 1 fetch; include the full header — YAML frontmatter **and** the `# Title` + `**Authors:**/**Submitted:**/**Paper:**` meta lines). Save it to `staging/` under its **canonical filename** `YYYY-MM-DD <Name>.md` (date = the paper's `submitted` date).
  >
  > Then **classify** the paper into exactly one Library topic, using the `library-filing` skill's rules (its Step 2 topic-scope match and Step 3 confidence gate — read that skill for the rules; do not guess your own). Match **method-first**: what the paper *does* (its contribution/method), not the application domain it happens to target. **`Read` the file `staging/topic-menu.txt` for the list of allowed topics and their scopes, and choose exactly one topic from it** (only those topics; if the file is missing, run `researchEnv/bin/python3 scripts/topic_menu.py` yourself and use its output).
  >
  > - If **one topic is a clear best fit** (confident): add a line `topic: <exact Topic name>` to the note's YAML frontmatter.
  > - If the paper is **ambiguous, spans several topics, or fits none well** (not confident): do NOT add a `topic:` line. Leave it unstamped.
  >
  > **Do not move the file out of `staging/` and do not touch any `index.json` or `MOC.md`** — filing is the orchestrator's job. Report back exactly, on one line: the saved staging path, `<Name>`, `arxiv_id`, `submitted`, and either `topic: <Topic>` (if you stamped one) or `UNSURE(candidates: <A> / <B>[ / <C>])` with a ≤10-word reason. If you could not complete, give a one-line failure reason instead. Do not block on anything.
- On each completion notification: set the `summary` cell to `summarized` (capture the staging path) or `failed(...)`, and record the returned topic in the `filed` cell as `ready:<Topic>` or `unsure(candidates: …)` — these are provisional until the Step 7 file pass. Then **pull the next `queued` paper into the freed slot**. A failed sub-agent simply frees its slot — it never blocks the others or the run.
- Keep spawning until the queue drains and all in-flight agents have reported.

## Step 7: File the batch mechanically (you, once — no per-paper reads)

Once the pool has drained and every row is `summarized` or `failed`, file the whole batch in one mechanical pass. You do **not** re-read any summary — the topic is already in each note's frontmatter.

1. **Move the confident notes.** For each row whose sub-agent returned a `topic:` (`ready:<Topic>`), `mv` its staging note into `Library/<Topic>/` (the canonical filename `YYYY-MM-DD <Name>.md` is already set — do not rename). Use plain `mv` (the notes are untracked). Do this for every confident note; leave `unsure(...)` notes in `staging/`.
2. **Rebuild the indexes once.** `researchEnv/bin/python3 scripts/rebuild_index.py` — it reconstructs every `index.json` from note frontmatter (`library-filing` Step 6's bulk shortcut) and backfills `topic:` from the folder for any note missing it. Then `researchEnv/bin/python3 scripts/rebuild_index.py --check` must exit 0 (no drift). Update each filed row to `filed: <Topic> (N)` from the rebuilt index.
3. **Cap / split check, once.** From the rebuilt `index.json` files, flag any topic now at ≥30 papers and emit a split proposal using `library-filing` Step 4's clustering rules (cluster from the `title`+`blurb` in `index.json`, not the note bodies). Debounce per its "propose once" rule — do not re-propose an already-pending split.
4. **Stragglers stay put.** Every `unsure(...)` note remains unstamped in `staging/`; it is surfaced in the report for the review pass. Nothing about a straggler is a failure.

Because sub-agents wrote isolated frontmatter and never touched `index.json`, there is no concurrent-write hazard here and nothing to serialize — the single `rebuild_index.py` is the only writer of shared state.

## Step 8: Final report

From the worklist, summarize tightly:

- **Filed** — grouped by topic (from the rebuilt indexes), with new note paths and any cap/split proposals.
- **Left in staging (UNSURE stragglers)** — papers + the sub-agent's candidate topics, for the review pass / manual filing.
- **Failed** — papers + one-line reasons, so the user can retry or follow up.
- **Skipped (already filed)** — from the Step 3 dedup.
- The worklist's disposition — it is archived in Step 9 (teardown), so give the archived path there.

Keep it scannable: the user cares about what landed, what needs a human, and what broke.

After the report, if there are any UNSURE stragglers, **ask the user to work through them** — don't close the run. They are the expected manual-filing handoff (resolve each by stamping `topic:` and re-running `rebuild_index.py`), not a footnote to end on.

## Step 9: Teardown — clean up the run's staging artifacts

The pipeline leaves transient files in `staging/`; an unattended run otherwise piles up stale worklists and dead input lists. Run teardown **only once every worklist row is terminal** (`filed` / `declined` / `failed`) — a run with rows still `queued`/`summarizing` is not finished, so do not clean up.

1. **Finalize the worklist first.** Make every row's `summary` and `filed` cell reflect its terminal state and confirm the `STATUS: COMPLETE` header line. The archived copy is the run's audit record, so correct any stale `queued`/`—` cells before moving it — do not rely on the header alone.
2. **Archive the worklist; delete the topic-menu scratch file.** `mkdir -p staging/archive` then `mv staging/worklist-*.md staging/archive/` (move only *this run's* worklist if several exist). The active `staging/` view should hold no completed worklists. Also `rm -f staging/topic-menu.txt` — it is a per-run scratch file regenerated by Step 5, never an audit record.
3. **Reconcile input lists against the Library.** For each source list this run drew from (`staging/temp.md`, `staging/unsorted.txt`, or a passed-in file), parse its arxiv IDs and check each against the filed set across `Library/*/index.json` — match by `arxiv_id`, never by mnemonic:
   - **Fully consumed** (every ID now filed) → delete the list; it has no remaining pipeline function (e.g. `temp.md` once all its sections are filed).
   - **Partially consumed** → remove only the lines whose ID is now filed, leaving the un-ingested backlog intact (e.g. `unsorted.txt`).
   - **Never** delete a list that still has un-ingested entries, and never touch `staging/iteration-findings.md` (persistent findings log) or anything under `Library/`.
4. **Leave UNSURE stragglers in place.** Low-confidence notes (no `topic:` stamped) stay in `staging/` by design (they await the review pass / manual filing) — teardown must not remove loose `*.md` summaries.
5. **Report the disposition:** which worklist was archived and to where, and which input lists were deleted or pruned.

**Why archive the worklist but delete consumed input lists:** the worklist is the only per-run record of routing, retries, and session-cap recoveries — worth keeping out-of-the-way rather than discarding (durable cross-run learnings still go in `staging/iteration-findings.md`). Input lists are pure inputs: once their papers are in the Library, a fully-consumed list is dead weight and a partial one should shrink to just its backlog.

## Benchmarking (efficiency + drift guard)

This design exists to keep the **expensive orchestrator thread cheap**. Summarization and classification both run on Sonnet sub-agents that already hold the paper; the orchestrator only dispatches, moves files, runs one `rebuild_index.py`, and resolves stragglers — so its per-paper cost should be near-zero and roughly flat as batches grow. If a future edit slides classification or per-paper summary re-reads back onto the (Opus) main thread, per-paper cost spikes. `cost_report.py` is the guard against that regression.

**The metric that matters:** *cost attributable to the main orchestrator thread, per paper.* In production the orchestrator is the main session (its transcript is `~/.claude/projects/-Users-ruisenliu-Repositories-Research/*.jsonl`, `isSidechain:false`); each Sonnet sub-agent's cost lands in its own sidechain/task transcript. A healthy run shows the main thread doing dispatch + one rebuild and little else.

**Run the report:**

```bash
# Whole run since a start time, per-paper over an N-paper batch
researchEnv/bin/python3 .claude/skills/pipeline-orchestrator/evals/cost_report.py --since <T0-iso> --papers N
```

It aggregates tokens by model family (opus/sonnet/haiku) × thread (main vs sub) and applies a directional rate table (cache-read ~0.1× input, cache-creation ~1.25× input). It is a cost *proxy*, not a bill.

**Measurement gotchas (learned 2026-07-06 — read before trusting numbers):**
- **Per-turn usage is logged once per content block — dedup by `message.id` or you multiply parallel turns.** A single assistant turn writes one JSONL line per block (thinking + text + each `tool_use`), each carrying the *same* `usage`. Summing per line counts a turn's cost by its block count, which hits the parallel-tool-call turns (10 `Agent` spawns, N parallel Paperclip `ls`) hardest — inflating a run ~4× and making the drift guard cry regression falsely (learned 2026-07-09). `cost_report.py` now dedups by `message.id`; any ad-hoc analysis of the JSONL must do the same.
- **Sub-agent cost is not in the project `*.jsonl`.** Background sub-agent transcripts are written to the harness's task-output files (e.g. the session scratchpad's `tasks/*.output`), not the project dir. A project-dir-only measurement captures the **orchestrator thread only** — which is exactly the drift-guard metric, but means it will *not* show the Sonnet summary cost. To price a sub-agent, point the aggregator at its task-output transcript.
- **`model: opus` on a `general-purpose` sub-agent is silently ignored** — sub-agents ran on Sonnet regardless. So you cannot A/B "Opus filing" by dispatching a filing sub-agent; that measures Sonnet. To represent the *production* orchestrator (which the user runs on Opus), reprice the filing token-volume at the Opus rate, or measure the main thread directly.

**A/B procedure for a skill change:** pick a fixed paper set **of a fixed size** (per-paper cache-read grows with batch position, so batch size must match across A and B), run it through the old skill and record `cost_report.py --papers N`, `git restore` the Library + `staging`, apply the edit, run the same set, and compare. Watch the **opus/main per-paper** line specifically — it should stay low.

**Trustworthy baseline:** ~**$0.76/paper** orchestrator cost for a **10-paper** batch (2026-07-09, fixed dedup-by-`message.id` script, post-redesign design with inline menu). Compare future runs against this at the same batch size.

**Retired numbers — do not cite.** Earlier figures ("~$4.5→~$0.65/paper" redesign win; "$3.9/paper OLD filing" 2-paper sample) predate the dedup fix and were inflated by the per-line double-count (see gotcha above) by an unknown, run-specific factor. Since inflation scales with a run's parallel/multi-block turns, it also distorted the before/after *ratio*, not just the absolutes — so the advertised redesign multiple is not trustworthy, and the old windows weren't recorded to re-measure cleanly. The redesign's *direction* (classification off the Opus thread onto Sonnet, filing → mechanical `mv` + one rebuild) is still sound; only the magnitudes are void.
