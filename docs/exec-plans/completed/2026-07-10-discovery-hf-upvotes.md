# Restore HuggingFace Upvotes into the Discovery Digest

## Context

Over a ~2-month window the discovery pipeline produced **381 matches and 1571 declines** — far
more than one person can read. The front-end triage needs a cheap *early* importance signal to
prioritize, and one is already being thrown away.

The HuggingFace daily-papers API returns `paper.upvotes` for every paper, and the discovery skill
already fetches it (`.claude/skills/paper-discovery/SKILL.md` lines 39, 45). But the digest
template never renders it — the current entry format was deliberately upvotes-free (see
`docs/exec-plans/completed/2026-06-25-backfill-discovery.md` line 55, "No upvotes field (current
format dropped it)"). Restoring it costs nothing at fetch time and gives the reader a crowd-interest
signal alongside the existing semantic `Match:` score.

This is the **front-end / ingest-time** half of the impact-filtering effort. Citation-based signals
are retrospective (a 2-month-old paper has ~0 citations) and are handled separately in
`2026-07-10-impact-supersession-scan.md`. Upvotes are the one strong signal available *at
discovery time*.

Scope decision: display upvotes on **matched** entries only for this pass. Sorting within a topic
stays by semantic match score; upvotes are shown, not yet used to re-rank. (Surfacing upvotes on
Passed-Over entries to rescue high-interest papers the topic filter dropped is a deliberate future
extension, not built here.)

## Approach

The digest entry line is rendered in **two independent places** that must stay in sync — the skill
template (used by the live daily run via `claude --print`) and the Python backfill driver. Update
both, then confirm the review UI tolerates the new field.

### 1. `.claude/skills/paper-discovery/SKILL.md` — Step 6 template

Change the matched-entry meta line (~line 131) to add upvotes between `Match` and `Published`:

```
**arXiv:** [PAPER_ID](https://arxiv.org/abs/PAPER_ID) | **Match:** 0.XX | **▲ Upvotes:** N | **Published:** YYYY-MM-DD
```

Add a one-line note near line 136 documenting the field: sourced from `paper.upvotes`, default `0`
when absent. Leave the Passed-Over format (line ~143) unchanged.

### 2. `scripts/backfill_discovery.py` — entry render (~lines 186–189)

Mirror the same `▲ Upvotes:` field in the f-string that builds each matched entry. Confirm the
paper dict this script assembles from the HF response carries `upvotes` (from `paper.upvotes`); add
it to the parse step if it is not already threaded through.

### 3. `scripts/review_server.py` — review UI

The server already references `upvote`. Verify it reads the new entry field (or at minimum does not
break parsing the changed meta line). Adjust the line parser/regex if it keys on the old
`Match | Published` shape.

## Critical files

- **Edit** `.claude/skills/paper-discovery/SKILL.md` — Step 6 matched-entry template + field note.
- **Edit** `scripts/backfill_discovery.py` — mirror upvotes in the entry render; thread `upvotes`
  through the paper dict.
- **Verify/Edit** `scripts/review_server.py` — review UI tolerates/uses the new field.
- **Reference format** `discovery/2026-07-10.md` — current entry shape to diff against.

## Code-development lifecycle (per CLAUDE.md)

- This plan lives in `docs/exec-plans/active/`; move to `completed/` when done.
- `ruff check` + `mypy` any edited `.py`; no creds involved (public API).
- Update `ARCHITECTURE.md` if it documents the digest entry format.

## Verification

1. Run the discovery skill for `days=2` (or `python scripts/backfill_discovery.py` on one date)
   and confirm matched entries render `▲ Upvotes: N` with real, non-zero values on popular papers.
2. Diff a regenerated digest against a prior one (`discovery/2026-07-10.md`) — only the added
   upvotes field differs; `Match:`, `Published:`, blurb, section ordering, footer all unchanged.
3. Load a regenerated digest in `review_server.py`'s UI — confirm no parse break and, if the UI
   surfaces upvotes, that the value displays.
4. `ruff check` and `mypy` pass on `scripts/backfill_discovery.py` (and `review_server.py` if
   touched).
5. `git status` shows only the intended files changed — no stray edits to MOCs or `.obsidian/`.
