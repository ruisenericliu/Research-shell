# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This is an Obsidian-based research library for tracking AI/ML papers, talks, and notes. The goal is an indexed, interconnected library with consistent formatting so Obsidian's graph view reveals meaningful connections across topics.

**For full repository structure, see `ARCHITECTURE.md`.** It covers the folder map, Library topic system, discovery pipeline, and launchd automation setup.

## Repository Structure (summary)

```
Library/              ← Canonical topic areas (VLA, World Models, Human-to-Robot Demonstration Transfer, Inference-Time Reasoning Algorithms, Multi-Agent Coordination, Memory & Retrieval, Humanoid Control); each topic folder has a semantic MOC.md + a machine-readable index.json of filed papers
staging/              ← Unfiled summaries, notes-to-papers output, pipeline worklists
discovery/            ← Daily paper digests written by the paper-discovery skill
scripts/              ← paper-discovery.sh + launchd plist for 8 AM automation; rebuild_index.py for the topic indexes
.claude/skills/       ← paper-discovery, huggingface-papers, arxiv-summary, notes-to-papers, library-filing, pipeline-orchestrator
Notes_2024/           ← legacy year-organized notes (migrating to Library/)
Notes_2025/           ← legacy year-organized notes (migrating to Library/)
Notes_2026/           ← legacy year-organized notes (migrating to Library/)
```

New notes go in `Library/<Topic>/`. Do not create notes in the year-based folders.

## Note Conventions

### File naming
All new notes use ISO date prefix: `YYYY-MM-DD Paper Name.md`
Example: `2026-03-16 SmolVLA.md`

### Note format (Heilmeier-style summary)
Use the `/arxiv-summary` skill when given an arxiv link or paper PDF — it generates the standard format. Every note opens with a **YAML frontmatter block** (`arxiv_id`, `title`, `authors`, `submitted`, `topic`, `blurb`) that feeds each topic's `index.json`; `arxiv-summary` writes it (minus `topic`) and `library-filing` stamps `topic`. See `ARCHITECTURE.md` → Note Format for the schema. The body template is:

```markdown
## Overview
What problem does it solve? Why does it matter now?

## Baselines & Numbers
Key quantitative comparisons with prior work.

## Contributions
- Main contribution (CLEVER: if novel framing, call it out)
- Secondary contributions
- **Ablation highlight**: what the ablations reveal

## Open Problems
What this paper leaves unresolved.

## Limitations
Stated or unstated weaknesses.

## Reproducibility
Code/data availability. Any red flags.

## Special Notes
Embedded-prompt scan result, unusual experimental choices, ethical concerns, reception in the field.

## Links
- Paper: [arxiv](url)
- Code: [GitHub](url)
```

### Linking
- Use `[[Paper Name]]` wiki links when referencing other notes
- Each topic folder has a `MOC.md` (Map of Content) — **semantic scaffolding only**: the topic's scope description plus curated `[[concept links]]`. It does not enumerate papers.
- A new note is registered in its topic's `index.json` (by `library-filing`), not by editing the MOC. Rebuild/repair the indexes with `python scripts/rebuild_index.py` (uses `researchEnv`).
- Use `[[concept]]` links for standalone concept notes (e.g., `[[RLHF]]`, `[[Diffusion Policy]]`)

### Images
Images referenced in notes live in year-specific folders: `Images_2024/`, `Images_2025/`, `Images_2026/`. Obsidian embeds them with `![[filename.png]]`.

**Moving image files is safe.** Obsidian resolves `![[filename.png]]` vault-wide by filename — path is irrelevant. Move files between image folders freely without touching any note links. Do not rename the files.

## Running Logs

`Notes_2026/Talks + Notes/GPT Tracker.md` is a reverse-chronological log of model releases and AI news — append new entries at the top with a `MM/DD:` date header, not a full note.

## Obsidian Setup

The vault is this repo root. Core plugins in use: graph view, backlinks, tag pane, daily notes, templates, canvas. Community plugins: `obsidian-importer` (for importing OneNote/other formats), `terminal`.

Do not modify `.obsidian/` config files — Obsidian manages them.

# CODE DEVELOPMENT

When writing code in this repository, follow the feature lifecycle below. Standards live in `docs/design-docs/` — read them there, do not duplicate them here.

## Standards

| Doc | Covers |
|-----|--------|
| [`docs/design-docs/DESIGN.md`](docs/design-docs/DESIGN.md) | Type hints, formatting, exceptions, layer integrity |
| [`docs/design-docs/RELIABILITY.md`](docs/design-docs/RELIABILITY.md) | Fail fast, 10s timeout, structured JSON logging, merge bar |
| [`docs/design-docs/SECURITY.md`](docs/design-docs/SECURITY.md) | Secrets in `.env`, no creds in logs, validate external data |
| [`docs/design-docs/TESTING.md`](docs/design-docs/TESTING.md) | 95% coverage target, mocking rules, fixture conventions |

## Feature Development Workflow

Do not report a task as complete until every step is done.

1. **Plan** — Write a plan before touching code. Save to `docs/exec-plans/active/<YYYY-MM-DD>-<feature-name>.md`. Include: context/motivation, implementation steps, affected files, and verification criteria.
2. **Implement** — Execute the plan, referencing the plan doc throughout.
3. **Code Review** — Review against the standards docs above. Address violations before proceeding.
4. **Review plan for completeness** — Re-read the plan doc; confirm every step is done and the doc reflects reality.
5. **Move to completed** — `docs/exec-plans/active/<name>.md` → `docs/exec-plans/completed/<name>.md`
6. **Update living docs** — Update `ARCHITECTURE.md` and any affected design docs to reflect new behavior or constraints.

## Completion Checklist

- [ ] All plan steps implemented and verified
- [ ] `ruff check src/` passes with no errors
- [ ] `mypy src/` passes with no errors
- [ ] Smoke test for the affected entry point ran successfully
- [ ] Plan doc reviewed for accuracy; updated if anything diverged
- [ ] Plan moved from `active/` → `completed/`
- [ ] Living docs updated to reflect any new conventions or interfaces

## Environment

- **Virtual environment:** `researchEnv/` (gitignored)
- **Activate:** `source researchEnv/bin/activate`

---

# EXPLORATION

Read `ARCHITECTURE.md` before making any changes to this repository. It documents the folder structure, naming conventions, linking standards, note format, and the automated discovery pipeline.
