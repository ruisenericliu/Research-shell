---
name: notes-to-papers
description: "Extract paper references from scribbled notes and find their arXiv links. Use this skill when the user shares a document, file, or paste of notes that mentions research papers—even casually (e.g., 'the diffusion policy thing from chi', 'Hafner world models', 'RT-2 paper'). Identifies paper candidates, searches for their arXiv IDs, and appends results to a staging file. Trigger any time the user wants to turn notes or references into linked arXiv entries."
---

# Notes-to-Papers

Turn messy research notes into a list of titled arXiv links, saved to a staging file for later processing.

## Step 1: Read the Notes

Accept input in either form:
- **File path**: read the file directly
- **Pasted inline**: the notes are already in context

If neither is obvious, ask the user for the notes before proceeding.

## Step 2: Extract Paper Candidates

Scan the notes for anything that looks like a reference to a research paper:
- Named papers ("Attention Is All You Need", "CLIP", "RT-2")
- Author + year patterns ("chi et al. 2023", "Hafner 2023")
- Informal references ("the visuomotor diffusion thing", "that world model paper from Dreamer")
- Acronyms that are likely papers ("RLHF", "DreamerV3", "VPT")
- Conference/workshop references ("the NeurIPS 2023 paper on...")

Deduplicate — if the same paper is mentioned multiple times in different ways, treat it as one candidate. List all candidates before searching.

## Step 3: Search for Each Paper

Run all searches in parallel — issue every candidate's search call in the same message.

### Before searching: flag edge cases

Before issuing any search, scan each candidate for these signals that make keyword/semantic search unreliable:

- **Special characters in the name**: `+`, `~`, `*`, `π`, `₀`, symbols (e.g. "R+X", "π₀")
- **Very short or opaque names**: single letters, abbreviations under 3 characters
- **A project URL is present in the notes** alongside the paper name

For candidates with any of these signals, **use URL resolution instead of search** (see below). Do not waste a search call on a name that can't be tokenized.

### Route A: URL resolution (for edge cases)

When the notes include a project URL for a paper, fetch it with the `WebFetch` tool. Scan the returned HTML for:
1. A direct `arxiv.org/abs/XXXXXXXXX` link — use that ID immediately
2. The canonical paper title (usually in `<title>`, `<h1>`, or a "Paper" link) — use it to run a targeted paperclip search

Project pages almost always embed the arXiv link. This is the most reliable path for papers whose names are unsearchable.

### Route B: paperclip (semantic search)

Use the `mcp__paperclip__paperclip` tool for all other candidates:

```
search "QUERY" -n 5
```

Build the query from the most specific signal available. For vague references, include descriptive terms from the notes (e.g., "shadows human motion cross-embodiment robot" rather than just "Shadow"). For acronyms, expand them if you know what they stand for.

**Parsing paperclip results:**
- Results appear as numbered entries with an ID in the form `arx_XXXXXXX`, `bio_XXXX`, `med_XXXX`, or `PMCXXXXXX`
- **Only arXiv papers are usable** — skip any result whose ID starts with `bio_`, `med_`, or `PMC`
- Strip the `arx_` prefix from arXiv IDs to get the raw arXiv ID (e.g., `arx_2403.10506` → `2403.10506`)

### Route C: HuggingFace API (fallback)

Use when paperclip is unavailable (no MCP connection) or returns no arXiv results with high confidence:

```bash
curl -s "https://huggingface.co/api/papers/search?q=QUERY&limit=5"
```

URL-encode the query (spaces → `%20`). Parse the JSON: each result has `.paper.id` (the arXiv ID) and `.paper.title`.

### Confidence assessment

After getting results, judge whether the top arXiv hit is a real match:
- **High confidence**: title closely matches — overlapping key words, same acronym, same authors
- **Low confidence**: result title looks like a different paper, or no arXiv results returned

For low-confidence results from Route B, try Route A if a project URL is available, or rephrase the query once. If still uncertain, note it for the Step 5 report.

## Step 4: Write to the Staging File

Default output file: `staging/unsorted.txt`, relative to the repo root.

If the user specified a different target in their prompt, use that instead.

Append one line per confirmed paper in this format:
```
Paper Title — https://arxiv.org/abs/PAPER_ID
```

Use the official title returned by the search tool (not the user's informal phrasing), and the exact arXiv ID. Open in append mode — do not overwrite existing content.

## Step 5: Report Results

After writing, summarize:
- **Written**: list of papers successfully added with their links
- **Skipped / uncertain**: candidates where search came back empty or confidence was too low — list what was searched so the user can follow up manually

Keep the report tight. The user cares about what made it in and what didn't.
