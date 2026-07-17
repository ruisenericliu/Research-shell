# Retrospective Impact & Supersession Scan (`scripts/impact_scan.py`)

## Context

Over a ~2-month window the discovery pipeline produced **381 matches and 1571 declines**. The
Library already holds **355 notes across 27 topics**, and ingestion costs **~$0.76/paper**, so
ingesting all 381 would ~double the library and cost ~$290 before a single paper is read. Raw
match/decline gives no notion of which filed papers actually *advance the field*, nor which have
been superseded by newer work.

There is no citation or impact data anywhere in the repo today — but every note carries an
`arxiv_id`, which is the join key to free external impact data. **One enrichment layer yields three
signals:** citation count + velocity, the citation graph (supersession), and reference overlap
(novelty-vs-library).

Two findings from investigation shape the design:

- **Semantic Scholar is the reliable source, not OpenAlex.** A live test on RT-1 (`2212.06817`)
  showed OpenAlex's arXiv-DOI join returning a *stub* record (39 citations, 0 references) — the
  canonical RSS'23 version is a separate un-merged work. Semantic Scholar's native
  `paper/arXiv:{id}` path returned the correct merged record: **2492 citations, 193 influential,
  72 references**. These exact numbers are the smoke-test ground truth below.
- **Citation signals are retrospective.** A 2-month-old paper has ~0 citations, so this scan is a
  periodic **T+3–6mo** job over *already-filed* papers — the back-end complement to the ingest-time
  upvotes signal in `2026-07-10-discovery-hf-upvotes.md`.

The scan **evaluates and reports — it does not auto-delete.** It produces a ranked review report;
whether to archive/prune any paper stays a human decision (the prune-action policy is intentionally
deferred).

## Approach

A new standalone script `scripts/impact_scan.py` following the conventions of
`scripts/rebuild_index.py` (stdlib + PyYAML, `argparse`, `logging`,
`REPO_ROOT = Path(__file__).resolve().parent.parent`, run under `researchEnv`). Adheres to
`docs/design-docs/RELIABILITY.md` (fail fast, 10s HTTP timeout, structured logging) and
`SECURITY.md` (optional S2 API key from `.env`, never logged).

### 1. Enrichment layer (Semantic Scholar, cached)

- Read every `Library/*/index.json` → the full set of filed `arxiv_id`s (reuse the existing index
  files; **no new frontmatter fields** on the 355 notes).
- Call the S2 **batch** endpoint (≤500 ids/request), one request for the whole library:
  `POST /graph/v1/paper/batch?fields=externalIds,citationCount,influentialCitationCount,referenceCount,publicationDate`
  with body `{"ids": ["arXiv:<id>", ...]}`.
- Write a **sidecar cache** `data/impact_cache.json` keyed by `arxiv_id` (storing `CorpusId`,
  the returned fields, and a `fetched_at` timestamp). Citation data is never written into note
  frontmatter — it goes stale; the cache refreshes without git-churning 355 notes.
- Flags: `--refresh` forces re-fetch; default reuses cache entries newer than N days. Backoff on
  HTTP 429 (unauthenticated S2 is ~1 req/s; the batch endpoint sidesteps per-paper throttling).

### 2. Three derived signals

1. **Citation count + velocity** — from the batch fields: `citationCount`,
   `influentialCitationCount` (S2's "meaningfully built-upon" subset, the sharper
   advances-the-field proxy), and `velocity = citationCount / age_in_months` (age from the note's
   `submitted` date).
2. **Supersession (citation graph)** — for each filed paper A,
   `GET /paper/arXiv:{id}/citations?fields=externalIds,publicationDate&limit=1000` (in-edges: who
   cites A). Intersect the citing set with library `arxiv_id`s **in the same topic** that are
   **newer** than A → candidate supersessors B. Confirm "B beats A" by parsing the local
   `## Baselines & Numbers` GFM tables from both notes and checking dominance on a shared benchmark
   column. Emit two tiers:
   - **Confirmed**: citation edge **and** a benchmark win → `A superseded_by B (benchmark, Δ)`.
   - **Likely**: citation edge only, no shared benchmark to confirm.
3. **Novelty-vs-library** — for a paper, `?fields=references.externalIds`; count how many of its
   references are already-filed `arxiv_id`s. High reference-overlap **and** holds no benchmark
   record → low-novelty / incremental flag.

Benchmark-table parsing: a small GFM-table extractor over the note body between the
`## Baselines & Numbers` heading and the next `##`. Column headers are paper-specific, so match
benchmarks by normalized header string; a table is usable only when a shared benchmark column
exists across A and B. Where none exists, fall back to the citation-edge-only ("Likely") tier.

### 3. Output: ranked review report (no auto-prune)

Write `staging/impact-report-YYYY-MM-DD.md`:
- **Top movers** — filed papers ranked by influential-citation count / velocity (the load-bearing
  papers to prioritize reading).
- **Supersession candidates** — `A superseded_by B` pairs, Confirmed vs Likely tiers, so the user
  can decide whether to archive A.
- **Low-novelty flags** — high reference-overlap papers holding no benchmark record.

`--check` mode: refresh nothing, re-render the report from the cache (fast, offline, no network).

## Critical files

- **Create** `scripts/impact_scan.py` — the enrichment + 3-signal + report driver.
- **Create** `data/impact_cache.json` — sidecar cache (new `data/` dir; likely gitignored — see
  open decision).
- **Create (output)** `staging/impact-report-YYYY-MM-DD.md` — the ranked review report.
- **Reuse** `scripts/rebuild_index.py` — index.json enumeration + frontmatter/YAML parsing patterns.
- **Read-only** `Library/*/index.json` (filed `arxiv_id`s) and note bodies (`## Baselines & Numbers`
  tables).

## Open decision (resolve at implementation)

Whether `data/impact_cache.json` is git-tracked (shareable across machines, but churns on refresh)
or gitignored (clean history, re-fetched per machine). **Lean: gitignore the cache, commit the
report.** Add `data/impact_cache.json` to `.gitignore` if so.

## Code-development lifecycle (per CLAUDE.md)

- This plan lives in `docs/exec-plans/active/`; move to `completed/` when done.
- `ruff check scripts/impact_scan.py` + `mypy scripts/impact_scan.py` clean; type hints throughout;
  fail-fast with clear messages on fetch errors; 10s HTTP timeout; structured JSON logging.
- Optional S2 API key read from `.env`; never logged, never committed.
- Update `ARCHITECTURE.md` to document the new impact layer + sidecar cache after implementation.

## Verification

1. **Enrichment ground truth** — run enrichment on RT-1 (`2212.06817`); assert the cache shows
   `citationCount ≈ 2492` and `influentialCitationCount ≈ 193` (live-verified). Confirms the arXiv
   join resolves the correct merged S2 record.
2. **Batch coverage** — run over all `Library/*/index.json`; confirm the cache covers all filed
   `arxiv_id`s (report any misses), via ≤1 batch request per 500 papers.
3. **Supersession sanity** — run on the VLA topic (e.g. RT-1 → OpenVLA / newer VLA notes); confirm
   at least one plausible `superseded_by` pair surfaces with a benchmark delta, and eyeball it.
4. **Offline `--check`** — renders `staging/impact-report-*.md` from cache with zero network calls.
5. `ruff check` and `mypy` pass on the new script.
6. **Security** — grep the run logs and the committed cache/report: no S2 API key or secret present.
