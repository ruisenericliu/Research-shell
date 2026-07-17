# Local Discovery Review Website

## Context

The discovery pipeline writes daily digests to `discovery/YYYY-MM-DD.md` (46 of them,
just re-classified against the 15-topic set). Today the only way to triage them is to
open each markdown file by hand. We want a **local web UI** to visually review matched
papers, filter by category, and check off the ones worth pursuing — writing those
selections to a `staging/` file that the existing `pipeline-orchestrator` skill can
ingest for summarization + filing into the Library.

Per user decisions:
- **Selections → dated file** `staging/selected-YYYY-MM-DD.md`, one `Title — https://arxiv.org/abs/ID`
  line per pick (the exact format `notes-to-papers`/`unsorted.txt` use, so the
  orchestrator reads it natively). Append + dedup on write.
- **Dedup awareness** — papers whose `arxiv_id` is already in any `Library/*/index.json`
  are dimmed ("filed"); papers already in today's selection file are badged ("selected").

## Stack (no new dependencies)

Python **3.14**, stdlib `http.server` only — no Flask/FastAPI (house rule: prefer stdlib;
a new dep needs a rationale doc). Frontend is a **single self-contained HTML file** with
inline CSS + vanilla JS (no CDN, fully offline), per the `docs/design-docs/FRONTEND.md`
precedent ("single self-contained `.html`, no build tools"). `Jinja2` is available but not
needed — the page is static and pulls data from a JSON endpoint.

## Components (all new files)

### `scripts/review_server.py` — backend + digest parser
`ThreadingHTTPServer` bound to **127.0.0.1** (localhost only, never the network),
`BaseHTTPRequestHandler` subclass. Repo root via `Path(__file__).resolve().parent.parent`
(matches `backfill_discovery.py`). `logging` module, no `print()`. Routes:

- `GET /` → serve `scripts/review_ui.html`.
- `GET /api/papers` → JSON `{topics: [...], papers: [Paper...]}`. Parse every
  `discovery/*.md` for **matched** papers (Passed-Over entries are titles-only / no
  arxiv link, so they're excluded — they can't be summarized without an ID). Each
  `Paper` is a typed `@dataclass`: `date, topic, title, arxiv_id, match, published,
  blurb, filed: bool, selected: bool`.
- `POST /api/select` → body `{papers: [{title, arxiv_id}]}`; validate JSON + arxiv-ID
  shape before use (SECURITY.md boundary rule); append new lines to
  `staging/selected-<today>.md` (create with a `# Selected from discovery review — DATE`
  header if absent), dedup against IDs already in that file; return the updated selected
  set.

**Parser** (the logic-heavy, test-worthy part): walk each digest's lines tracking the
current `## <Topic> (N)` heading (skip `## Passed Over`); on `### <Title>` start a paper;
parse the following `**arXiv:** [ID](url) | **Match:** X | **Published:** date` line with
one regex; capture the `> blurb`. `filed` = ID present in any `Library/*/index.json`
(reuse the same `cat Library/*/index.json` dedup source the orchestrator uses);
`selected` = ID present in today's selection file.

### `scripts/review_ui.html` — frontend
Vanilla JS, inline styles. On load `fetch('/api/papers')`. Default view: cards **grouped
by date, newest first**. Toolbar: a **category filter** dropdown (topics + "All"), a live
selected-count, and a **Save selections** button. Each card: checkbox, title linked to
arxiv, topic badge, match score, published date, blurb. Filed papers render dimmed;
already-selected papers render checked + badged. Category filter shows/hides client-side.
Save → `POST /api/select` → update badges + a confirmation toast.

### `scripts/launch_review.sh` — launcher
`#!/bin/bash`, `set -euo pipefail`, `REPO="/Users/ruisenliu/Repositories/Research"`,
optional `$1` port (default 8000). Starts `"$REPO/researchEnv/bin/python"
scripts/review_server.py --port "$PORT"`, `open http://localhost:$PORT`, and `trap`s
INT/TERM to kill the server on Ctrl-C. Matches the absolute-path style of
`scripts/paper-discovery.sh`.

### `scripts/test_review_server.py` — focused tests
pytest for the two risky pure functions: digest parsing (a fixture digest → expected
`Paper` list, incl. em-dash topic + Passed-Over exclusion) and the selection writer
(append + dedup, header creation) against a tmp dir. (If `pytest` isn't in `researchEnv`,
note it and provide a `__main__` self-check instead.)

## Reuse / integration points

- Selection-file format & path conventions: `staging/unsorted.txt` /
  `notes-to-papers` SKILL (`Title — https://arxiv.org/abs/ID`).
- Consumer: `pipeline-orchestrator` LIST mode — accepts `staging/selected-*.md` directly
  (`'process staging/selected-2026-06-25.md'`).
- Filed-dedup source: `Library/*/index.json` `arxiv_id` fields (same source as
  orchestrator Step 3).
- Digest format reference: `discovery/2026-06-24.md`; parser mirrors the writer in
  `scripts/backfill_discovery.py::build_digest`.

## Standards (per CLAUDE.md CODE DEVELOPMENT)

Full type hints, `X | None` not `Optional`, ruff-clean at **≤80 cols**, mypy zero errors,
`logging` (no `print`), validate the POST body at the boundary, bind localhost-only. Save
this plan to `docs/exec-plans/active/2026-06-25-discovery-review-ui.md` at start; move to
`completed/` when done; add the three scripts to `ARCHITECTURE.md`'s `scripts/` map and a
short "Review UI" note in the discovery-pipeline section.

## Verification

1. `source researchEnv/bin/activate && ruff check scripts/review_server.py` and
   `mypy scripts/review_server.py` → zero errors; `pytest scripts/test_review_server.py`
   passes.
2. `bash scripts/launch_review.sh` → browser opens `http://localhost:8000`; the page lists
   matched papers grouped by date.
3. `curl -s localhost:8000/api/papers | python -m json.tool | head` → well-formed JSON with
   topic, arxiv_id, match, filed/selected flags.
4. In the UI: filter to one category (e.g. "Vision Language Action Models") → only those
   cards show. Check 2 papers, click Save.
5. Confirm `staging/selected-2026-06-25.md` now holds those 2 `Title — https://arxiv.org/abs/ID`
   lines; re-saving the same picks does not duplicate them; reload shows them badged
   "selected". A paper with an ID already in a `Library/*/index.json` shows dimmed/"filed".
6. Sanity: `pipeline-orchestrator` would accept the file — lines match the
   `Title — URL` grammar it parses.
7. `git status` shows only the new scripts + exec-plan + ARCHITECTURE.md edit.

---

## Addendum — two-pane revision (post-review feedback)

Initial single-list + Save UI had no way to de-select. Revised to a picklist:
- **Available** pane (grouped by date, category filter, filed papers dimmed) and a
  **Selected** pane. Click a paper → moves to Selected; `×` / **Clear** returns it.
- Moves persist **live** to `staging/selected-YYYY-MM-DD.md` (the file is source of
  truth; Clear deletes it). No Save button.
- Endpoints: `GET /api/papers` now also returns the current `selected` list;
  `POST /api/select | /api/deselect | /api/clear` (replacing the old batch
  `append_selections`). `read/write_selection_entries` round-trip the file.
- Tests updated: `test_selection_roundtrip` covers add/dedup/deselect/clear.

---

## Addendum 2 — equal panes, stats bar, passed-over page

- **50/50 layout**: Available and Selected are now equal-width panes, each
  scrolling independently with full cards (blurb shown in both).
- **Stats bar** (header): aggregate counts across all digests — candidates,
  matched, passed over, selected, days — parsed from each digest's summary
  line via `parse_header_stats` / `compute_stats`. Surfaced on `GET /api/papers`
  (and `/api/passed`) as a `stats` object.
- **Passed-over page** `scripts/passed_over.html`, served at `/passed`, data
  from `GET /api/passed` (`collect_passed_over` + `parse_passed_over`). Lists
  passed-over titles grouped by date with a client-side title filter;
  reference-only (no arXiv ids recorded for these).
- Tests added: `test_parse_passed_over`, `test_parse_header_stats`.

---

---

## Addendum 3 — left nav rail (Discovery / Passed over tabs)

Reworked navigation into a **left sidebar table of contents** with two tabs that
switch full-page views in the main area:
- **Discovery** — the 50/50 picklist (Available / Selected) + stats bar.
- **Passed over** — full-page list of passed-over papers grouped by date with a
  title filter; lazy-loaded from `GET /api/passed` on first visit.

Single-page app: the server serves one HTML (`review_ui.html`). Removed the
interim standalone `passed_over.html`, its `/passed` route, the `PASSED_HTML`
constant, and the earlier collapsible drawer. `GET /api/passed` is the data
source. Tab labels show the matched / passed-over counts from `stats`.
