# Iteration 3+ — the 8 standalone areas (top-down creation)

**Part of:** the Library-population effort (master plan decomposed into per-iteration plans). Runs after Iteration 2 (World Models). Depends on the refined `library-filing` from Iterations 1–2.

## Context / motivation

The remaining 8 temp.md clusters have **no existing parent topic**, so they don't stress the split path — they exercise topic *creation* and the confidence gate against a now-crowded topic field (post-VLA, post-World-Models). Each becomes a new top-level `Library/<Area>/` created top-down (MOC first), then filled.

## The 8 areas (temp.md lines 177–end)

| Area | temp.md heading | approx N |
|------|-----------------|----------|
| 3D Generation | `## 3D Generation` | ~ |
| 3D Reconstruction (Feed-Forward) | `## 3D Reconstruction - Feed-Forward Methods` | ~ |
| Semantic Mapping | `## Semantic Mapping` | ~ |
| Joint Embedding Predictive Architectures | `## Joint Embedding Predictive Architectures` | ~ |
| Multimodal Reasoning | `## Multimodal Reasoning` | ~ |
| Open-Vocabulary Vision | `## Open-Vocabulary Vision` | ~ |
| SLAM | `## SLAM (Simultaneous Localization and Mapping)` | ~ |
| Vision-Language Navigation | `## Vision-Language Navigation` | ~ |

(Counts to be filled when each is picked up — read the heading's bullet block from temp.md.)

## Implementation steps (per area)

1. **Create the topic** — `Library/<Area>/MOC.md` (scope paragraph + curated `[[concept links]]`; link from related existing MOCs, e.g. VLN ↔ `VLA — Spatial Grounding & Embodiment`, 3D Reconstruction ↔ same).
2. **Summarize** — orchestrate sub-agents over the area's arxiv links (Paperclip ≤2603 / arxiv 2604+), notes to `staging/`.
3. **File** — bulk path (`mv` + `rebuild_index.py`) into the new topic. These land well under 20, so no split expected.
4. **Verify** — `--check` exit 0; index count matches; spot-check.

## Sequencing

Batch or chunk across turns as quota allows. Natural pairing: the 3D/SLAM/mapping areas (3D Generation, 3D Reconstruction, Semantic Mapping, SLAM) share concept vocabulary and cross-link heavily; the reasoning/vision areas (JEPA, Multimodal Reasoning, Open-Vocab Vision) form a second group; VLN bridges into the VLA family. Consider one turn per group.

## Watch for

- **Confidence-gate cross-pulls** now that the topic field is crowded — e.g. a VLN paper that reads as `VLA — Spatial`, or an Open-Vocab paper that reads as Multimodal Reasoning. Apply method-first/domain-second (memory: [[feedback-library-split-method-first]]).
- Whether any area itself approaches 20 (unlikely from temp.md sizes) — if so, the split path applies again.

## Affected files

- `Library/<Area>/` × 8 (new), each with MOC + index.json
- `staging/worklist-2026-06-24-<area>.md` per batch
- `ARCHITECTURE.md` topic table (add 8 rows)
- `staging/iteration-findings.md` (append per-area notes)
