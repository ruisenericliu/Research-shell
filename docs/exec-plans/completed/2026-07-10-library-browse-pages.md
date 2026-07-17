# Plan: Add Taxonomy + Library browse pages to the review web app

## Context

The local review web app (`scripts/launch_review.sh` → `scripts/review_server.py` → static
`scripts/review_ui.html`) today only triages **incoming discovery** papers (Discovery + Passed-over
tabs). There is no way to browse the **already-filed** Library — ~376 papers across 28 topic folders,
each with an `index.json` (metadata) and a rendered Heilmeier-style summary note.

We want two new sidebar tabs that turn the same single-page app into a reading tool for the Library:

1. **Taxonomy** — an overview of how the Library is organized: the topic hierarchy (umbrella hubs
   expanding to their sub-topics) with per-topic paper counts and each topic's MOC scope blurb. Reads
   like a table of contents for the whole library.
2. **Library** — a search view with a toolbar (topic dropdown + keyword box + sort) whose results are
   paper cards; clicking a card renders that paper's full summary in-page.

The app stays a single self-contained `review_ui.html` served by a stdlib-only Python server (its
stated design constraint — "no web framework, no new dependencies"). Markdown is rendered by a small
**scoped inline JS renderer** in the HTML, keeping both the server dependency-free and the whole UI in
one file.

Design decisions already confirmed with the user: two new sidebar tabs; taxonomy shows hierarchy +
counts + MOC scope blurb; search toolbar has topic + keyword (+ sort); summaries render in-page.

## Repo code-development process (per CLAUDE.md)

This is a code change, so follow the feature lifecycle:
- **Step 0**: copy this plan into `docs/exec-plans/active/2026-07-10-library-browse-pages.md`.
- On completion: `ruff check src/` (note: code lives in `scripts/`, so run `ruff check scripts/` and
  `mypy scripts/review_server.py`), smoke-test the server, move the exec-plan `active/ → completed/`,
  and update `ARCHITECTURE.md` (discovery-pipeline / review-tool section) to document the two new tabs
  and endpoints.

## Implementation

### 1. Server: data-loading helpers (`scripts/review_server.py`)

Add near the existing `load_filed_ids()` (which already globs `Library/*/index.json`):

- `load_library() -> list[dict]` — iterate `LIBRARY_DIR.glob("*/index.json")`; for each entry add a
  `topic` field (the parent folder name) and pass through `arxiv_id, name, title, path, submitted,
  blurb`. Reuse the same tolerant JSON-load + `isinstance` guards as `load_filed_ids()`. Skip the two
  empty umbrella folders naturally (their `index.json` is `[]`).
- `read_moc_scope(topic: str) -> str` — read `Library/<topic>/MOC.md`; return the first non-empty
  paragraph after the `# Title` line (stop at the first blank line following it, or at the first `##`).
  Return `""` if missing.
- `parse_subtopics(topic: str) -> list[str]` — from an umbrella `MOC.md`, parse the `## Sub-Topics`
  section's `- [[Child Topic]] — …` lines (regex `\[\[([^\]]+)\]\]`), returning child folder names in
  order. Empty list when there is no such section.
- `build_taxonomy() -> list[dict]` — build the tree:
  - Load all topic folders that have an `index.json`; `count` = number of entries.
  - Umbrellas = folders whose own count is 0 **and** whose MOC has a non-empty `parse_subtopics`.
  - Each umbrella node: `{name, scope, is_umbrella: true, count: <sum of child counts>,
    children: [{name, scope, count}]}`; children are pulled from the standalone pool.
  - Remaining standalone topics: `{name, scope, count, is_umbrella: false, children: []}`.
  - Sort children by MOC order (from `parse_subtopics`); sort top-level nodes by count desc (umbrellas
    included via their summed count). Return the list.
- `read_note(topic: str, path: str) -> str | None` — **validated** file read for `/api/note`:
  build the allowed `(topic, path)` set from `load_library()`; if the requested pair is not in it,
  return `None` (defends against path traversal — never trust the raw `path`). Otherwise read
  `Library/<topic>/<path>`, strip the leading YAML frontmatter (`---` … `---`), and return the body
  markdown (the body already opens with `# Title` + authors/links, so no separate header needed).

### 2. Server: new GET endpoints (`ReviewHandler.do_GET`)

Add three branches alongside the existing `/api/papers` / `/api/passed`:

- `GET /api/taxonomy` → `{"taxonomy": build_taxonomy(), "topics_total": N, "papers_total": M}`.
- `GET /api/library` → `{"papers": load_library(), "topics": <sorted distinct topic names>}`.
- `GET /api/note?topic=<t>&path=<p>` → parse the query with `urllib.parse.urlparse` +
  `parse_qs`; call `read_note`; return `{"markdown": <body>}` or `send_error(404)` when `None`.
  (Add `from urllib.parse import urlparse, parse_qs`.) Match on `urlparse(self.path).path` for this
  route so the query string doesn't break the existing exact-string comparisons — keep the other
  routes as-is.

Follow existing conventions: `@dataclass` is optional here (dicts are fine and match `load_filed_ids`
style); keep type hints, `logger.warning` on skips, and the `_send_json` helper.

### 3. UI: two new sidebar tabs + views (`scripts/review_ui.html`)

- **Sidebar**: after the existing two `.tab` buttons, add a divider and `Taxonomy` + `Library` tabs
  (`data-view="taxonomy"`, `data-view="library"`). The existing `showView()` already toggles any
  `.tab`/`.view` by name — extend it to toggle the two new `<section class="view">` blocks and
  lazy-load each (`loadTaxonomy()` / `loadLibrary()` on first show, mirroring `loadPassed()`).
- **Topbar**: make it contextual — on taxonomy/library show library stats (`topics_total`,
  `papers_total`) instead of the discovery stats; small tweak in `showView`.
- **`#taxonomyView`**: single scrolling column. Render each top-level node as a section: topic name +
  count badge + scope blurb; umbrella nodes render an indented child list (name + count + blurb).
  Clicking any leaf topic switches to the Library tab with that topic pre-selected in the dropdown
  (`showView('library')` + set `#libTopic` value + `renderLibrary()`).
- **`#libraryView`**: a toolbar (`.topbar`-styled row) with `#libTopic` `<select>` (All + every topic),
  `#libSearch` keyword `<input type="search">`, and `#libSort` `<select>` (Newest / Oldest / Title).
  Below it a two-pane split reusing the existing `.pane` styles: left = results list of paper cards
  (title, `topic` badge, `submitted`, blurb), right = `#reader` rendered-summary pane. Filtering =
  topic match AND keyword substring over `title`+`blurb`; sort per `#libSort`. Clicking a card calls
  `openNote(topic, path)` → `fetch('/api/note?…')` → `reader.innerHTML = renderMarkdown(md)`.
  Reuse `esc()` and the existing card/badge CSS; add minimal CSS for `.reader` typography (h1–h3,
  tables, code, blockquote, hr) using the existing CSS variables.

### 4. UI: scoped markdown renderer (`scripts/review_ui.html` `<script>`)

Add `renderMarkdown(md) -> htmlString` handling exactly the note template: HTML-escape first, then
transform fenced code blocks, GFM pipe tables (header row + `---|---` separator → `<table>`), `#`/`##`/
`###` headings, `---` horizontal rules, `- ` unordered lists, `>` blockquotes, `**bold**`, `*italic*`,
`` `code` ``, `[text](url)` links (open in new tab), `[[wikilink]]` → styled non-link span, `![[img]]`
→ dropped/placeholder, and blank-line-separated paragraphs. ~100 lines, self-contained; no external
library, no CDN, no build step. This is the only rendering path — verify against a table-heavy note.

## Affected files

- `scripts/review_server.py` — 5 helpers + 3 GET routes + `urllib.parse` import.
- `scripts/review_ui.html` — 2 sidebar tabs, 2 view sections, toolbar, reader pane, `renderMarkdown`,
  `loadTaxonomy`/`loadLibrary`/`openNote`, reader CSS.
- `docs/exec-plans/active/2026-07-10-library-browse-pages.md` — exec-plan copy (Step 0).
- `ARCHITECTURE.md` — document the new tabs/endpoints (completion step).

## Reuse

- `load_filed_ids()` (`review_server.py:181`) — copy its `Library/*/index.json` glob + tolerant-load
  pattern for `load_library()`.
- `_send_json()` (`review_server.py:323`) and the `do_GET` routing block (`:331`) — extend, don't
  rewrite.
- `showView()` (`review_ui.html:241`), `loadPassed()` (`:250`), `card()`/`esc()`/`toast()` — the new
  views follow these exact patterns; `.tab`/`.view`/`.pane`/`.card`/`.badge` CSS is reused as-is.

## Verification

1. `source researchEnv/bin/activate` then `ruff check scripts/` and `mypy scripts/review_server.py` —
   both clean.
2. Start the server: `python scripts/review_server.py --port 8765` (background). `curl -s
   localhost:8765/api/taxonomy | python -m json.tool` — confirm umbrellas (Vision Language Action
   Models, World Models) show their sub-topics with summed counts and scope blurbs, and standalone
   topics (Grasping &c.) appear top-level. `curl -s 'localhost:8765/api/library'` — confirm ~376
   papers each with a `topic`. `curl -s 'localhost:8765/api/note?topic=VLA%20%E2%80%94%20Foundations%20%26%20Training&path=2024-10-31%20pi0.md'`
   — confirm the note body comes back frontmatter-stripped. `curl -s 'localhost:8765/api/note?topic=x&path=../../etc/passwd'`
   — confirm a 404 (traversal blocked).
3. Full run: `bash scripts/launch_review.sh 8765`, open in browser. Manually check: Taxonomy tab shows
   the tree; clicking a topic jumps to Library filtered to it; toolbar topic/keyword/sort all filter;
   clicking a paper renders its summary (headings, **a table**, bold, links) correctly in the reader
   pane; Discovery/Passed-over tabs still work unchanged.
4. Move exec-plan `active/ → completed/`; update `ARCHITECTURE.md`.

---

## Completion note (2026-07-10)

Implemented as planned. All steps done and verified:
- Server: `load_library`, `read_moc_scope`, `parse_subtopics`, `build_taxonomy`,
  `read_note` + `/api/taxonomy`, `/api/library`, `/api/note` routes.
- UI: Taxonomy + Browse tabs, search toolbar (topic/keyword/sort), reader pane,
  scoped `renderMarkdown`, contextual topbar stats.
- **Added beyond the plan**: `test_library` in `tests/test_review_server.py`
  covering the five new helpers incl. the `/api/note` traversal guard.
- Verified: `ruff`/`mypy` clean; `python tests/test_review_server.py` passes;
  all four endpoints return correct status codes (traversal → 404); markdown
  renderer produces correct HTML for a real table-heavy note (h1/h2/h3, GFM
  table, bold, links, hr, list, wiki-links).
- `ARCHITECTURE.md` updated (folder map + review-tool paragraph).

## Follow-up refinements (2026-07-10, post-review)

From user feedback after the first pass:
- Nav badges no longer read 0 on launch — `/api/taxonomy` + `/api/library`
  are eager-loaded in `load()`.
- Taxonomy list spans the full content width (dropped the `max-width`).
- Sidebar rebranded to **Research Library** (centered); rail regrouped so the
  Library tabs sit above the Discovery tabs.
- Added a **Home** landing view (now the default): library totals, navigation
  cards, and a Recently-filed list (each item opens in Browse). Topbar is
  hidden on Home. `ARCHITECTURE.md` updated to match.
