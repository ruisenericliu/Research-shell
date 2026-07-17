---
name: library-filing
description: "File a generated paper summary into the correct Library topic and update that topic's MOC, applying the library's organization rules. Use when the user wants to file, shelve, categorize, or add a generated arxiv-summary into the Library (e.g. 'file this into the library', 'add this summary to the library', 'categorize and shelve this paper'), or as the filing step right after the arxiv-summary skill produces a summary. Only files when confident about the topic; keeps each topic under ~30 papers and proposes a split when one gets too large."
---

# Library Filing

Take a generated paper summary (the markdown file the `arxiv-summary` skill produces) and file it into the right `Library/<Topic>/` folder, registering it in that topic's `index.json`. Keep the library organized with three rules:

1. **Only file when confident** about the topic. When unsure, leave it in `staging/` and report — never guess.
2. **Keep each topic under ~30 papers** (counted from the topic's `index.json` — the JSON array of filed papers).
3. **Propose a split** when a topic reaches the limit — propose only, never restructure automatically.

**The `MOC.md` is semantic only** — a topic's scope description plus hand-curated `[[concept links]]`. It does **not** enumerate the filed papers; that enumeration lives in `index.json`. Never add a `## Papers` section to a MOC.

All paths are relative to the Research repo root: `/Users/ruisenliu/Repositories/Research/`.

**This skill is the source of truth for classification (Steps 2–3) and split clustering (Step 4).** It runs two ways. **Interactive/single-paper:** you do every step below yourself. **Pipeline mode** (`pipeline-orchestrator`): the classification decision (Steps 2–3, method-first + confidence gate) is made inside each Sonnet summary sub-agent, which stamps `topic:` into the note's frontmatter; the orchestrator then files the whole batch mechanically via the Step 6 bulk shortcut (one `mv` pass + a single `rebuild_index.py`), and runs the Step 4 cap/split check once at the end. Same rules, cheaper thread — don't restate the rules in the orchestrator, reference them.

## Step 1: Locate the Summary

Determine which summary file to file:
- If the user just generated one (or names a path), use that.
- Otherwise scan `staging/` for unfiled summary files (e.g. `staging/2025_10_VLA-0.md`) and confirm which one with the user if there is more than one.

Read the file. A summary follows the arxiv-summary template. It carries **YAML frontmatter** (`arxiv_id`, `title`, `authors`, `submitted`, `blurb`; `topic` not yet set) — read those fields directly. Also skim the **Overview / Contributions** body to understand the paper's subject. If the frontmatter is missing (an older note), fall back to the `**Authors:** / **Submitted:** / **Paper:**` meta lines.

## Step 2: Read the Library's Topic Scopes

List the topics: each `Library/<Topic>/MOC.md` is one topic. Read the **intro of every MOC** — the title plus the description paragraph directly under it defines that topic's scope. That description is what you match against; do **not** match against the `[[concept links]]` lower in the MOC (those are hand-curated concept scaffolding, not papers).

## Step 3: Confidence Gate (Rule 1)

Judge which single topic best fits the paper, based on the MOC scope descriptions.

- **Confident** — one topic is a clear best fit: continue to Step 4.
- **Not confident** — the paper is ambiguous, plausibly spans several topics, or fits none well: **STOP. Write nothing. Move nothing.** Leave the file in `staging/` and report:
  - why you're unsure (one or two sentences), and
  - the top 2–3 candidate topics, each with a short reason.

  Then end. Filing the wrong paper is worse than not filing.

## Step 4: Size Check (Rules 2 & 3)

Open the chosen topic's `index.json` and count its entries (zero if the file doesn't exist yet). This array is the topic's paper count.

- **Under 30 after adding this one:** proceed normally.
- **Reaches 30 or more after adding this one:** still file the paper (Steps 5–6), then in your report emit a **split proposal** — do not restructure anything yourself. The proposal should name:
  - the set of new sub-topics (and the dissolved/slimmed parent), grounded in the actual clustering of papers currently in `index.json`,
  - which existing papers move to each sub-topic,
  - a one-line scope description for each new sub-topic's MOC.

  Leave it to the user to approve and run the split (Step 8).

### Clustering rules for the split proposal

Cluster from each paper's `title` + `blurb` in `index.json` (don't re-read note bodies — the blurb is the signal the index layer exists to provide). Apply these rules, learned from the VLA split (2026-06-24):

- **Method-first, domain-second.** Group by what the paper *does* (its method/contribution), not the application domain it happens to target. A paper that is a VLA *by method* stays in the VLA family even when its subject overlaps another Library topic (navigation, humanoid control, memory, 3D). Preserve the domain link in the sub-topic MOC's `## Related Topics` (`[[wikilinks]]`) rather than filing the paper out of the family. Only route a paper *out* to another existing topic when its method — not just its application — clearly belongs there.
- **Artifact-type sub-topics are legitimate when they accumulate.** Benchmarks, evaluation harnesses, and surveys share vocabulary and cluster together regardless of the domain they measure. When several pile up (≈4+), a dedicated "Evaluation, Benchmarks & Safety" sub-topic is correct — don't scatter them across the method axes. Below that threshold, leave them with the method topic they evaluate.
- **Watch the blurb-vs-intent gap.** A paper's blurb may read as one axis ("VLM family", "world-model RL") while the user considers it another. When method-first and the blurb agree, trust them; surface the few genuine ambiguities in the proposal rather than silently picking.
- **Mixed-axis splits: resolve seam papers by primary contribution, not mechanism.** A topic's natural sub-axes are not always parallel. The World Models split (2026-06-24) mixed *method* axes (Control & Decision-Making, Video Generation, Object-Centric) with one *interaction-modality* axis (Interactive Simulation). A paper can satisfy a method axis *and* the modality axis at once (e.g. an action-conditioned video simulator whose actual contribution is policy-evaluation data), so it sits on the seam and method-first alone can't place it. Resolve such papers by their **primary contribution / intended use**, not their underlying mechanism — the policy-eval simulator files under Control (decision-making), not Interactive Simulation, despite being mechanically a simulator. Name the seam papers explicitly in the proposal.

### Propose once, not per-paper (debounce)

Emit the split proposal **once**, when a topic first crosses the cap. Do not re-propose on every subsequent filing into an already-over-cap topic — that is noise. If the user has seen the proposal and not yet acted, keep filing silently (a one-line "still over cap (N); split proposal pending" is enough). Re-propose only if the clustering has materially changed since the last proposal.

## Step 5: File the Note

Build the canonical filename: `YYYY-MM-DD <Name>.md`
- **Date** = the paper's submission date from the summary's `Submitted:` line (e.g. `October 15, 2025` → `2025-10-15`).
- **`<Name>`** = the model/method/system name — the same short name practitioners use, already the suffix of the staging filename (e.g. `VLA-0`).

Move the file (don't copy) from `staging/` into `Library/<Topic>/` under that name. A freshly-generated staging note is **untracked**, so use plain `mv` — `git mv` errors with "not under version control" on a new note:

```bash
mv "staging/2025_10_VLA-0.md" "Library/Vision Language Action Models/2025-10-15 VLA-0.md"
```

Reserve `git mv` for moving an **already-committed** note (e.g. relocating a note between topics during a split, Step 8). When git later commits the new note, rename detection is irrelevant — there's no prior history to follow.

Then **stamp the `topic` into the note's YAML frontmatter** — add `topic: <Topic>` (the exact topic-folder name) to the frontmatter block. If the note has no frontmatter (an older note), leave it; the `scripts/rebuild_index.py` backfill will add it.

## Step 6: Register in `index.json`

Add the paper to the topic's `index.json` — the JSON array of filed papers, kept **newest first** (descending `submitted`). Each entry:

```json
{
  "arxiv_id": "2510.13054",
  "name": "VLA-0",
  "title": "VLA-0: Building State-of-the-Art VLAs with Zero Modification",
  "path": "2025-10-15 VLA-0.md",
  "submitted": "2025-10-15",
  "blurb": "text-action VLA that beats action-token/head designs, zero VLM modification"
}
```

- Pull `arxiv_id`, `title`, `submitted`, and `blurb` straight from the note's frontmatter; `name` is the model name (the filename suffix); `path` is the note's basename (it lives in the same folder as `index.json`).
- Insert the new entry so the array stays sorted newest-first by `submitted`. If `index.json` doesn't exist, create it as a one-element array.
- **Do not touch `MOC.md`** — its concept scaffolding is hand-curated and the enumeration belongs in `index.json`.
- The canonical rebuild is `researchEnv/bin/python3 scripts/rebuild_index.py`, which regenerates every `index.json` from note frontmatter. Your incremental edit should already match what it would produce.

**Bulk filing into a known topic (shortcut).** When filing a *batch* of notes that all go to the same already-decided topic (e.g. the pipeline-orchestrator handing you a pre-clustered worklist), skip the per-note `index.json` edits entirely: `mv` all the notes into the topic folder, stamp each note's `topic:`, then run `rebuild_index.py` **once** — it builds the index from frontmatter and backfills `topic:` from the folder name for any note that lacks it. One rebuild replaces N manual index edits and is correct by construction.

**Reconcile frontmatter drift at batch end, not per-note.** Freshly-generated notes carry compact YAML (`arxiv-summary`'s style); `rebuild_index.py` re-emits canonical block YAML. The difference is cosmetic but trips `--check`. Run `rebuild_index.py` (no flag) **once after a batch finishes** to canonicalize every newly-filed note, then `--check` exits 0. Do not rebuild after each individual filing.

## Step 7: Report

Summarize tightly:
- **Filed:** `<Name>` → `<Topic>` (now N papers), and the new note path.
- **Index:** the entry added to `index.json`.
- **Split proposal** (only if the topic reached the limit): the proposed sub-topics, which papers move, and that it awaits the user's approval.
- If you stopped at the confidence gate, report that instead (per Step 3) — nothing was filed.

## Step 8: Execute an approved split

Run this only when the user approves a proposal from Step 4. `rebuild_index.py` discovers topics from **top-level** `Library/` folders only (non-recursive), so each sub-topic is its own top-level folder whose name equals the `topic:` value.

1. **Create each sub-topic folder + `MOC.md`.** The MOC is semantic-only (scope paragraph + curated `[[concept links]]`, plus a `## Related Topics` section linking domain neighbors for method-first papers). Have each sub-topic MOC link back to the parent as `[[<Parent Topic>]]`.
2. **Convert the parent into an umbrella hub** (don't delete it): rewrite its `MOC.md` to a short scope paragraph + a `## Sub-Topics` list of `[[wikilinks]]` to the new folders. Its `index.json` becomes `[]` after the notes move (rebuild handles this). Keeping the parent preserves the `[[<Parent Topic>]]` backlinks as a hub node in the graph.
3. **Move each note** into its sub-topic folder. `git mv` for already-committed notes (history follows); plain `mv` for any still-untracked note (see Step 5).
4. **Re-stamp `topic:` on every moved note** to the new folder name. ⚠️ This is mandatory and easy to miss: `rebuild_index.py`'s `normalize_frontmatter` uses `setdefault`, so it will **not** overwrite an existing `topic:` value — a stale parent topic survives a rebuild untouched. Edit the `topic:` line yourself (or strip it and let the rebuild backfill from the folder name).
5. **Rebuild + verify:** `researchEnv/bin/python3 scripts/rebuild_index.py` to build each sub-topic's `index.json` and empty the parent's, then `... --check` (exit 0 = no drift). Confirm each sub-topic's count matches the proposal and sits under 30.
6. **Update `ARCHITECTURE.md`** Library topic list to reflect the new sub-topics and dissolved parent.
7. **Register any new *standalone* topic with discovery.** A new canonical (top-level, non-folding) topic is invisible to the `paper-discovery` pipeline until it has a BM25 keyword row — the both-passes merge rule drops topics with no keywords (see that skill's Step 5). This applies whenever a **standalone** topic is created: a top-down new topic, or a split that spins out a parent that does *not* fold into an existing umbrella. **It does not apply to ordinary split sub-topics** — those fold back into their retained umbrella parent for discovery, which already has a row. For each genuinely new standalone topic, **propose a BM25 keyword row (~10–13 lowercase terms drawn from the new MOC's scope paragraph) and let the user review/edit it before you add it** to the keyword table in `paper-discovery/SKILL.md`. Keyword rows are user-reviewed artifacts, not silent edits.

A scripted move that sets `topic:` during the move (then one rebuild to canonicalize) is the cleanest way to do steps 3–5 atomically for a large split.
