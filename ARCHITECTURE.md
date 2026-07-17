# Repository Architecture

An Obsidian-based research library for AI/ML papers, talks, and notes. This document is the canonical reference for structure, conventions, and automation.

---

## Folder Map

```
Research/
├── Library/                    ← Canonical topic areas (primary knowledge base)
│   ├── Vision Language Action Models/
│   │   ├── MOC.md              ← Map of Content — topic scope + curated [[concept links]] (semantic only)
│   │   ├── index.json          ← Machine-readable list of filed papers (dedup + ~30 cap); every topic folder has one
│   │   └── 2025-10-15 VLA-0.md ← Paper note: YAML frontmatter + Heilmeier body
│   ├── World Models/
│   │   └── MOC.md
│   ├── Human-to-Robot Demonstration Transfer/
│   │   └── MOC.md
│   ├── Inference-Time Reasoning Algorithms/
│   │   └── MOC.md
│   ├── Multi-Agent Coordination/
│   │   └── MOC.md
│   ├── LLM Agents & Agentic AI/
│   │   └── MOC.md
│   ├── Reward Learning from Video/
│   │   └── MOC.md
│   ├── Memory & Retrieval/
│   │   └── MOC.md
│   ├── Humanoid Control/
│   │   └── MOC.md
│   ├── 3D Generation/
│   │   └── MOC.md
│   ├── 3D Reconstruction — Feed-Forward/
│   │   └── MOC.md
│   ├── Semantic Mapping/
│   │   └── MOC.md
│   ├── SLAM/
│   │   └── MOC.md
│   ├── Joint Embedding Predictive Architectures/
│   │   └── MOC.md
│   ├── Multimodal Reasoning/
│   │   └── MOC.md
│   ├── Open-Vocabulary Vision/
│   │   └── MOC.md
│   ├── Vision-Language Navigation/
│   │   └── MOC.md
│   └── Robotics — Surveys & Reviews/
│       └── MOC.md
│
├── discovery/                  ← Daily paper digests (auto-generated)
│   ├── 2026-05-11.md           ← One file per day, written by paper-discovery skill
│   └── last-run.log            ← Log from the launchd daily job
│
├── Images/                     ← Images embedded in notes via ![[filename]]
│   (Images_2024/, Images_2025/, Images_2026/ are legacy equivalents)
│
├── Notes_2024/                 ← Legacy year-organized notes (migrating to Library/)
├── Notes_2025/                 ← Legacy year-organized notes (migrating to Library/)
├── Notes_2026/                 ← Legacy year-organized notes (migrating to Library/)
│
├── staging/                    ← Unfiled summaries + notes-to-papers output + active pipeline worklists + input lists; iteration-findings.md (persistent log) lives here
│   └── archive/                 ← Completed worklists, moved here by pipeline-orchestrator teardown (Step 9)
│
├── scripts/                    ← Automation scripts
│   ├── paper-discovery.sh      ← Shell script run by launchd daily at 6:00 AM (+ catch-up slots)
│   ├── com.research.paper-discovery.plist  ← launchd plist (install to ~/Library/LaunchAgents/)
│   ├── rebuild_index.py        ← Rebuilds every Library/<Topic>/index.json from note frontmatter + regenerates README's auto-managed library-overview block
│   ├── topic_menu.py           ← Emits a compact `Topic — one-line scope` menu from each MOC intro (fed to pipeline-orchestrator's summary sub-agents for in-agent classification)
│   ├── backfill_discovery.py   ← Regenerates discovery/ digests over a date range against the current topic set (per-day, no dedup); reuses the skill's BM25 table + semantic_classify
│   ├── review_server.py        ← Local-only (127.0.0.1) stdlib HTTP server for the review UI: parses discovery/*.md, serves matched papers as JSON, writes picks to staging/selected-<date>.md; also serves the filed Library (taxonomy, search, note bodies) from Library/*/index.json + MOC.md
│   ├── review_ui.html          ← Single-file frontend (vanilla JS) for review_server.py; includes a scoped markdown renderer for reading filed summaries in-page
│   └── launch_review.sh        ← Launches the review site on localhost and opens the browser (default port 8000)
│
├── tests/                      ← Self-checking test scripts (no pytest dep), one per scripts/ module
│   ├── test_rebuild_index.py   ← Covers the README library-overview generation
│   └── test_review_server.py   ← Covers digest parsing + the selection writer
│
├── .claude/
│   ├── skills/
│   │   ├── huggingface-papers/ ← HF Papers API skill (fetch paper metadata)
│   │   ├── paper-discovery/    ← Daily topic-filtered paper digest skill
│   │   ├── arxiv-summary/      ← Generates a Heilmeier-style summary (+ frontmatter) from an arxiv link/PDF
│   │   ├── notes-to-papers/    ← Extracts paper refs from notes → arXiv links in staging/
│   │   ├── library-filing/     ← Files a generated summary into Library/<Topic>/ + updates index.json
│   │   └── pipeline-orchestrator/ ← Conducts discovery→summary→filing across many papers in parallel (+ evals/: check_classifications.py, cost_report.py, golden_set — the committed classification + cost drift guard)
│   └── settings.json           ← Project-level tool permissions
│
├── docs/                       ← Code development standards and execution plans
│   ├── design-docs/            ← DESIGN, RELIABILITY, SECURITY, TESTING, FRONTEND
│   └── exec-plans/             ← active/ and completed/ feature plans
│
├── ARCHITECTURE.md             ← This file
├── AGENTS.md                   ← Entry point for non-Claude agents
├── CLAUDE.md                   ← Claude Code-specific guidance
└── researchEnv/                ← Python venv (gitignored)
```

---

## Library System

`Library/` is the canonical knowledge base, organized by topic rather than by year. Each topic folder contains:

- **`MOC.md`** — Map of Content: **semantic only**. Holds the topic's scope description (matched against when classifying a paper) plus hand-curated `[[concept links]]` organized into subtopic sections. It does **not** enumerate the filed papers.
- **`index.json`** — the machine-readable enumeration of filed papers for this topic (a JSON array, newest first). This is the source of dedup and the ~30-paper cap. Generated/repaired by `scripts/rebuild_index.py` and updated incrementally by `library-filing`.
- **Individual paper notes** — one file per paper, named `YYYY-MM-DD Paper Name.md`, each carrying YAML frontmatter (see Note Format).

### Topics

| Topic | Focus |
|-------|-------|
| `Vision Language Action Models` | Umbrella hub for the VLA family (split 2026-06-24 along a method-first axis; Post-Training & Data spun out of Foundations 2026-06-30); no papers filed directly — see the five `VLA — …` sub-topics |
| `VLA — Foundations & Training` | Generalist VLA foundation models + policy architectures: the base policies themselves (π-series, Octo, RT-1/2, CogACT, ACT, Diffusion Policy) |
| `VLA — Post-Training & Data` | RL post-training, self-improvement, reward design/search, and demonstration synthesis/augmentation/annotation (Pi-star, LWD, GigaBrain, Eureka, DexMimicGen) |
| `VLA — Reasoning, Planning & Inference` | CoT/latent reasoning, test-time search, world-model planning, policy steering, inference-time efficiency |
| `VLA — Spatial Grounding & Embodiment` | 3D grounding, spatio-semantic memory, navigation, whole-body control (method-first; domain neighbors linked via MOC `## Related Topics`) |
| `VLA — Evaluation, Benchmarks & Safety` | VLA benchmarks, evaluation harnesses, leaderboards, safety/threat analyses |
| `World Models` | Umbrella hub for the World Models family (split 2026-06-24 along a method × interaction-modality axis); no papers filed directly — see the four `World Models — …` sub-topics |
| `World Models — Control & Decision-Making` | Model-based RL agents/planners acting inside a learned world model (Dreamer/TD-MPC lineage, latent/diffusion world models for control, multi-agent, real-robot) |
| `World Models — Video Generation` | Generative video/image diffusion as world models: VAEs, DiT backbones, text/image-to-video systems, inference acceleration, "is video generation a world model?" surveys |
| `World Models — Interactive Simulation` | Action-conditioned interactive simulators (games, driving, cities), multi-agent/multi-view simulation, interactive-world-model benchmarks |
| `World Models — Object-Centric` | Slot-, object-, and point-flow-structured world models that factor dynamics over entities rather than whole frames |
| `Human-to-Robot Demonstration Transfer` | Learning robot policies from human demonstrations (egocentric + exocentric video, teleop, mocap/retargeting) instead of expensive robot data; cross-embodiment transfer, embodiment gap, datasets (Ego4D, HumanNet) |
| `Inference-Time Reasoning Algorithms` | Mechanistic understanding of how LLMs reason at inference + automated discovery of compute-allocation strategies (branching, pruning, stopping) — not training methods or speed optimization |
| `Multi-Agent Coordination` | Agent debate, collaboration, role assignment, swarm architectures |
| `LLM Agents & Agentic AI` | Single LLM agents: tool-use/ReAct loops, RL for interactive agents, data-efficient agency fine-tuning, agents on real control stacks (ROS), agent-vs-agentic taxonomy — the single-agent counterpart to Multi-Agent Coordination |
| `Reward Learning from Video` | Learning RL reward functions/signals from internet + human video: video-language contrastive rewards (MINECLIP), VLM/LLM reward-code synthesis, reward from observation — the learned artifact is the reward, not the policy |
| `Memory & Retrieval` | Agent memory (episodic, working, long-term), agentic search, retrieval-augmented agents |
| `Humanoid Control` | Whole-body control of bipedal/legged humanoids; motion tracking & retargeting, RL locomotion + sim2real, loco-manipulation, zero-shot motion tracking |
| `3D Generation` | Synthesizing 3D content (meshes, CAD, Gaussian-splat scenes, navigable worlds) from images/text; diffusion-based mesh/CAD/scene synthesis, image-to-world (created top-down 2026-06-24) |
| `3D Reconstruction — Feed-Forward` | Recovering observed 3D geometry in a single/few forward pass without per-scene optimization; DUSt3R/MASt3R point-map lineage, feed-forward Gaussian-splat reconstructors, amortized neural fields (created top-down 2026-06-24) |
| `Semantic Mapping` | Spatial maps carrying meaning — open-vocabulary labels, BEV layouts, semantic occupancy, scene-language; foundation-model fusion, queryable semantic representations for agents (created top-down 2026-06-24) |
| `SLAM` | Simultaneous Localization and Mapping — joint sequential pose tracking + map building; classical (ORB/DROID), learned point-map (MASt3R-SLAM/SLAM3R), Gaussian-splat/neural-field SLAM, GPU/real-time systems (created top-down 2026-06-24) |
| `Joint Embedding Predictive Architectures` | Self-supervised representation learning that predicts in a learned latent/embedding space (LeCun's JEPA program); image/video/3D/action-conditioned variants (I-JEPA → V-JEPA 2), collapse-avoidance theory, latent world models for control (created top-down 2026-06-25) |
| `Multimodal Reasoning` | Reasoning over visual/video input — spatial reasoning, multi-hop VQA, visual/video chain-of-thought, referring/grounded reasoning, retrieval-augmented video reasoning, and the spatial/video reasoning benchmarks (created top-down 2026-06-25) |
| `Open-Vocabulary Vision` | Detection/segmentation from arbitrary text queries rather than a fixed label set; grounded-pretraining lineage (GLIP/DetCLIP), real-time open-vocab detectors (YOLO-World/OmDet-Turbo), promptable segmentation (SAM 3 + text variants), unified detection (created top-down 2026-06-25) |
| `Vision-Language Navigation` | Embodied agents moving to satisfy a language goal — instruction following, object-goal navigation, navigation map/memory (VLMaps/ReMEmbR), and test-time adaptation for unseen scenes (NavMorph/RAVEN); bridges into the VLA family (created top-down 2026-06-25) |
| `Grasping & Dexterous Manipulation` | Grasp synthesis, contact-rich manipulation, and dexterous in-hand control — grasp detection surveys, contact modeling (ContactSDF, SDF-based), tactile/force sensing, sim-to-real assembly (IndustReal, Factory, AutoMate), and LLM-guided adaptive grasping (created bottom-up 2026-06-30) |
| `Robotics — Surveys & Reviews` | Artifact-type topic for broad robot-learning surveys, reviews, and meta-analyses (not single-method papers) — foundation-model-in-robotics surveys, deep-generative-model-in-robotics survey, taxonomies, deployment-challenge syntheses (created bottom-up 2026-07-06) |

Topic classification uses a hybrid approach: BM25 keyword matching plus semantic similarity between paper abstracts and each topic's `MOC.md` content (via `sentence-transformers` in `.claude/skills/paper-discovery/semantic_classify.py`). Classification runs at **parent granularity**: a split topic's sub-topic folders (`<Parent> — <Child>`, plus the `VLA → Vision Language Action Models` alias) are folded back into their parent — the parent's semantic spec is the umbrella MOC concatenated with all its sub-topic MOCs — so the digest stays a broad-triage feed and fine sub-topic placement is left to `library-filing`.

To add a new topic: create a folder under `Library/`, add a `MOC.md`, and link it from related existing MOC files.

---

## Note Format

### File naming
All new notes: `YYYY-MM-DD Paper Name.md`
Example: `2026-03-16 SmolVLA.md`

### Frontmatter
Every paper note begins with a YAML frontmatter block (Obsidian renders these as Properties). It is the source of truth that `scripts/rebuild_index.py` reads to build each topic's `index.json`:

```yaml
---
arxiv_id: "2510.13054"    # quoted, preserves the dotted form
title: "VLA-0: Building State-of-the-Art VLAs with Zero Modification"
authors: ["Ankit Goyal", "Hugo Hadfield"]
submitted: 2025-10-15     # ISO date, unquoted (Obsidian date property)
topic: Vision Language Action Models   # added by library-filing at filing time
blurb: text-action VLA, zero VLM modification   # one-line description for the index
---
```

`arxiv-summary` emits everything except `topic` (unknown until filing); `library-filing` stamps `topic`. For older notes lacking frontmatter, `rebuild_index.py` backfills it by parsing the `# Title`, `**Authors:**`, `**Submitted:**`, and `**Paper:**` lines.

### Note body (Heilmeier-style)
Use the `/arxiv-summary` skill when given an arxiv link — it generates the standard format:

```
## Overview
## Baselines & Numbers
## Contributions
## Open Problems
## Limitations
## Reproducibility
## Links
```

### Linking conventions
- Use `[[Paper Name]]` to link to another note from within any note.
- Use `[[concept]]` for concept notes (e.g., `[[Diffusion Policy]]`, `[[RLHF]]`).
- A new note is registered in its topic's `index.json` (by `library-filing`), not by hand-editing the MOC.

### Filing a summary into the Library
The `library-filing` skill is the canonical step that moves a generated summary from `staging/` into the right `Library/<Topic>/`, stamps the note's `topic` frontmatter, and registers it in that topic's `index.json`. It only files when confident about the topic (otherwise it leaves the file in `staging/` and reports candidates), counts a topic's papers from `index.json`, keeps a topic under ~30 papers, and proposes (never auto-runs) a split when a topic reaches the limit. Split *proposals* cluster method-first (domain-second), may spin out an artifact-type "Evaluation/Benchmarks" sub-topic when those accumulate, resolve seam papers in mixed method × interaction-modality splits by primary contribution (the World Models split, 2026-06-24), and are emitted once (debounced). Split *execution* (skill Step 8) is user-approved: create top-level sub-topic folders + MOCs, convert the parent to an umbrella hub, move notes, **re-stamp `topic:`** (rebuild won't overwrite an existing value), then `rebuild_index.py`. The `MOC.md` is left untouched during normal filing — it is semantic scaffolding only and does not enumerate papers.

### Index maintenance
`scripts/rebuild_index.py` (run with `researchEnv`) regenerates every `Library/<Topic>/index.json` from note frontmatter and backfills frontmatter on notes that lack it. It also regenerates the auto-managed "What's in the library" block in `README.md` (between the `<!-- BEGIN/END library-overview -->` markers) from the live per-topic counts, so the README snapshot never drifts from the indexes — the topic→family grouping is editorial config at the top of the script, but any unlisted topic still surfaces so a new topic can't silently vanish. `library-filing` updates the index incrementally on each file; the rebuild script is the source of truth that repairs drift. `python scripts/rebuild_index.py --check` reports drift without writing (exit 1 if any) — useful for verification, and now also catches a stale README overview.

### Images
Embedded with `![[filename.png]]`. Images live in year-specific folders: `Images_2024/`, `Images_2025/`, `Images_2026/`.

**Moving image files:** Obsidian resolves `![[filename.png]]` by searching the entire vault for a matching filename — the path does not matter. You can move image files between folders without updating any wiki links in notes, as long as you do not rename the files. This means "Pasted image …" files that land at the repo root can be moved to the appropriate `Images_YYYY/` folder freely.

---

## Discovery Pipeline

An automated daily job fetches recent HuggingFace daily papers and filters them by the Library topics (each topic's `MOC.md` scope).

### How it works

1. **launchd** fires `scripts/paper-discovery.sh` at 6:00 AM (primary) plus catch-up slots at 9/12/15/18:00.
2. The script is **idempotent**: it exits early if today's `discovery/YYYY-MM-DD.md` already exists. So the primary 6 AM slot normally does the work, and the catch-up slots no-op — *unless* the Mac was asleep at 6 AM (launchd does not wake the machine and does not reliably run a sleep-missed `StartCalendarInterval`), in which case the first catch-up slot that lands while the Mac is awake does the work instead. Catch-up runs are labeled as such in `last-run.log`.
3. The script calls `claude --print "Run the paper-discovery skill with days=2"`.
4. The `paper-discovery` skill hits the HF daily papers API, filters by topic keywords, and writes a digest to `discovery/YYYY-MM-DD.md`. The 2-day window means a later-in-day catch-up still captures the missed day's papers.

### Manual run
```bash
# Inside a Claude Code session:
/paper-discovery

# Or with arguments:
/paper-discovery days=3
```

### Install the launchd job (one-time setup)
```bash
cp scripts/com.research.paper-discovery.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.research.paper-discovery.plist
# If updating an already-installed agent, reload it:
#   launchctl bootout gui/$(id -u)/com.research.paper-discovery
#   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.research.paper-discovery.plist
# Test immediately (without waiting for a scheduled slot):
launchctl start com.research.paper-discovery
```

### Classification: two passes, both required
A paper is matched to a topic only if it passes **both** a BM25 keyword filter (Pass 1, a hand-curated keyword table in `paper-discovery/SKILL.md`) **and** a semantic filter (Pass 2, `semantic_classify.py` cosine-scoring the paper against each topic's `MOC.md`, threshold 0.50). The semantic pass auto-derives its topic set from the `Library/<Topic>/` folders — sub-topics fold into their umbrella parent (only toward a parent folder that actually exists; a standalone em-dash topic like `3D Reconstruction — Feed-Forward` keeps its own name), with `VLA → Vision Language Action Models` aliased. The BM25 table does **not** auto-update.

### New-topic rule (keep discovery and the Library in sync)
Because the merge requires **both** passes, **a new canonical (top-level, non-folding) topic is invisible to discovery until it has a BM25 keyword row** — the semantic pass alone is not enough. So whenever a standalone topic is created (a top-down new topic, or a split spinning out a non-folding parent — *not* ordinary split sub-topics, which fold into a retained umbrella that already has a row), propose a BM25 keyword row and **have the user review it before adding it** to the table. Keyword rows are user-reviewed artifacts. This obligation is recorded in `library-filing` Step 8.

### Discovery output format
Each `discovery/YYYY-MM-DD.md` contains paper titles, HF links, arXiv IDs, upvote counts, and 1-2 sentence summaries, organized by matched topic.

### Review UI (visual triage)
`bash scripts/launch_review.sh [port]` starts a local-only review site (`scripts/review_server.py` + `review_ui.html`, stdlib `http.server`, bound to `127.0.0.1`). It parses the **matched** papers from every `discovery/*.md` (Passed-Over entries are surfaced separately in their own view, not the picklist). The page is a **50/50 two-pane picklist** under a stats bar: an **Available** pane (papers grouped by date, with a category filter; papers already filed in `Library/*/index.json` are dimmed and non-selectable) and an equal-width **Selected** pane, each scrolling independently with full cards. Clicking a paper moves it to Selected (it leaves Available); the `×` on a selected card or the **Clear** button returns papers to Available. Every move is persisted **live** to `staging/selected-YYYY-MM-DD.md` as `Title — https://arxiv.org/abs/ID` lines (the file is the source of truth — `Clear` deletes it). A **left navigation rail** under a **Research Library** brand groups the pages — a **Home** landing at the top, a **Library** group (Taxonomy, Browse), then a **Discovery** group (the Discovery picklist, Passed over) — and the app opens on Home. The top **stats bar** reports aggregate counts across all digests (candidates · matched · passed over · selected · days), parsed from each digest's summary line, and the rail tabs show the matched / passed-over counts. The **Passed over** view (lazy-loaded on first visit) lists the passed-over papers grouped by date with a title filter; each carries a linked title (arXiv) and a one-sentence blurb, useful for spotting category gaps. (The parser also tolerates legacy digests that recorded bare titles only.) It's a single-page app (one served HTML); endpoints: `GET /api/papers` (papers + topics + current selection + stats), `GET /api/passed` (passed-over list + stats), `POST /api/select|/api/deselect|/api/clear`. The line grammar is exactly what `pipeline-orchestrator` ingests, so a review session feeds straight into `process staging/selected-<date>.md`.

The **Home** landing (default view, `GET /api/taxonomy` + `/api/library`, both eager-loaded on launch so the nav badges populate immediately) shows library totals (filed papers · topics · discovery matches · passed over), navigation cards to each section, and a **Recently filed** list (newest notes, each opening straight into Browse). The same page also browses the **filed Library** through the Library-group tabs. **Taxonomy** (`GET /api/taxonomy`) renders the topic tree as a table of contents: umbrella hubs (parsed from each hub MOC's `## Sub-Topics` `[[wikilinks]]`) expand to their sub-topics, every topic shows its paper count and its MOC scope blurb (the MOC's first prose paragraph), and clicking a topic jumps into the browse view filtered to it. **Browse** (`GET /api/library`) is a topic-dropdown + keyword + sort toolbar over paper cards drawn from every `Library/*/index.json`; clicking a card fetches that note's body (`GET /api/note?topic=&path=`) and renders it in a reading pane via an inline scoped markdown renderer (headings, GFM tables, lists, blockquotes, code, bold/italic, links, wiki-links). `/api/note` validates the `(topic, path)` pair against the index entries before reading, so it can't be used to read files outside the Library. When these tabs are active the stats bar switches to Library totals (papers · topics).

---

## Pipeline Orchestration

The `pipeline-orchestrator` skill conducts the other skills end-to-end across **many** papers from one prompt. Given a list (arxiv links, a notes file, a `discovery/` digest) or a generic ask ("build a literature review on X"), it:

1. Builds a candidate list — reusing `notes-to-papers` for messy refs, or `paperclip`/HF/web search for generic asks (the generic path confirms the list with the user first).
2. Dedups against `Library/*/index.json` so already-filed papers are skipped.
3. Writes a `staging/worklist-YYYY-MM-DD.md` status table (cross-turn source of truth).
4. Builds a compact **topic menu** once via `scripts/topic_menu.py` (one `Topic — one-line scope` row per MOC intro), so it never reads MOC bodies into its own thread.
5. Fans out **summary + classification** to a bounded FIFO pool of up to 10 background sub-agents on Sonnet. Each runs `arxiv-summary`, then classifies its paper against the passed menu (method-first + confidence gate, `library-filing` Steps 2–3) and **stamps `topic:` into its own note's frontmatter** when confident — an isolated `staging/` write, safe in parallel. Low-confidence papers are left unstamped with candidate topics.
6. **Files the batch mechanically** (no per-paper reads): `mv` each confident note into `Library/<topic>/`, run `scripts/rebuild_index.py` once to rebuild every `index.json` from frontmatter (`+ --check`), then do a single cap/split check. Unsure stragglers stay in `staging/` for a review pass.
7. Reports Filed / Left-in-staging (UNSURE) / Failed / Skipped.
8. **Tears down** (Step 9): once every worklist row is terminal, finalizes the worklist, archives it to `staging/archive/`, and reconciles the run's input lists against the Library — deleting a fully-consumed list (e.g. `temp.md`) and pruning only the filed entries from a partial one (e.g. `unsorted.txt`). Unsure stragglers and `iteration-findings.md` are left untouched.

The load-bearing design choice is that topic classification — an **i.i.d. per-paper decision** — lives in the Sonnet sub-agent that already holds the paper, not in a long-lived Opus orchestrator that re-reads each summary to file it. Because topics ride in per-note frontmatter, filing is a single-writer mechanical step (`mv` + one `rebuild_index.py`), which also removes the concurrent-`index.json`-write hazard that used to justify serial Opus filing. This keeps the orchestrator's context flat regardless of batch size; measured ~85% cheaper per paper than the old Opus-filing design (see `pipeline-orchestrator/evals/cost_report.py` and the skill's `## Benchmarking` section, the committed drift guard). For a single paper, skip the orchestrator and use `arxiv-summary` + `library-filing` directly.

**Fetch source for background sub-agents:** non-interactive sub-agents can't answer a permission prompt, so `WebFetch` is auto-denied unless its domain is allowlisted. Sub-agents therefore fetch paper text from **Paperclip** (the `mcp__paperclip__paperclip` MCP tool is allowlisted and mirrors arXiv full text at `/papers/arx_<id>/`), with `WebFetch(domain:arxiv.org)` as an allowlisted fallback for papers Paperclip lacks. Both rules live in `.claude/settings.json`.

---

## Legacy Content

`Notes_2024/`, `Notes_2025/`, and `Notes_2026/` contain older notes in various formats. These are being migrated to `Library/` topic folders incrementally. Do not create new notes in the year-based folders — put new content in `Library/`.

`Research_OneNotes/` is a OneNote import archive and is gitignored.

---

## Code Development

All code development in this repository follows the standards and workflow documented in `docs/`. These were copied from the Stock project and may diverge over time — edit them here to reflect Research-specific needs.

```
docs/
├── design-docs/
│   ├── DESIGN.md        ← Type hints, formatting, exceptions, dependency rules, layer integrity
│   ├── RELIABILITY.md   ← Fail fast, 10s timeout, structured JSON logging, merge bar
│   ├── SECURITY.md      ← Secrets in .env, no creds in logs, validate all external data
│   ├── TESTING.md       ← 95% coverage target, mocking rules, fixture conventions
│   ├── FRONTEND.md      ← Self-contained HTML, no build tools, CDN-only
│   └── core-beliefs.md  ← Foundational engineering principles
└── exec-plans/
    ├── active/          ← In-progress feature plans (one file per feature)
    └── completed/       ← Finished feature plans (moved here when done)
```

Feature plans are named `<YYYY-MM-DD>-<feature-name>.md`. See `CLAUDE.md` for the full feature development workflow and completion checklist.
