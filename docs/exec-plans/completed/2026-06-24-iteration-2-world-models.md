# Iteration 2 — World Models split-path test

**Part of:** the Library-population / library-filing growth-path refinement effort (master plan `~/.claude/plans/ok-give-me-a-graceful-hennessy.md`, now decomposed into per-iteration plans). Iteration 1 (VLA) is complete — see `docs/exec-plans/completed/` once moved, and `staging/iteration-findings.md`.

## Context / motivation

Validate the **refined** `library-filing` split logic (method-first/domain-second clustering, artifact-type eval sub-topic, propose-once debounce, Step 8 execute-split) at greater width than VLA: World Models is a **4-way** split over ~40 papers vs. VLA's 3+1 over 33. temp.md is the ground-truth answer key.

## Papers (38 new + 2 existing = 40)

From `staging/temp.md` lines 77–176. Existing in `Library/World Models/index.json`: DINO-WM, DreamerV3 (no collisions).

- **Control & Decision-Making (12):** HWM 2604.03208, dWorldEval 2604.22152, InteractiveWorldSim 2603.08546, DreamDojo 2602.06949, LAWM 2512.10016, Dreamer4 2509.24527, DiWA 2508.03645, MATWM 2506.18537, DIAMOND 2405.12399, TDMPC2 2310.16828, IRIS 2209.00588, Daydreamer 2206.14176
- **Video Generation (10):** PVVAE 2605.02134, WorldR1 2604.24764, EvolvingVisualGeneration 2604.28185, OpenWorldLib 2604.04707, AgenticWorldModeling 2604.22748, WorldCache 2603.22286, OpenSora 2412.20404, CogVideoX 2408.06072, SoraWorldModelSurvey 2403.05131, DiT 2212.09748
- **Interactive Simulation (10):** iWorldBench 2605.03941, WorldMark 2604.21686, World2Minecraft 2604.27578, MultiWorld 2604.18564, HERMESPP 2604.28196, WorldCam 2603.16871, WildWorld 2603.23497, SeoulWorldModel 2603.15583, CosmosPredict2_5 2511.00062, NWM 2412.03572
- **Object-Centric (6):** PointWorld 2601.03782, DexWM 2512.13644, STICA 2511.14262, Dream2Flow 2512.24766, OCSTORM 2501.16443, FOCUS 2307.02427

**Fetch routing:** `2604`/`2605` (12 papers) → WebFetch arxiv.org; `≤2603` (26) → Paperclip-first with arxiv.org fallback. Sub-agent prompts self-heal on 404.

## Implementation steps (the iteration loop)

1. **Summarize** — orchestrate ≤10 concurrent background Sonnet sub-agents over the 38, writing notes to `staging/`. Track in `staging/worklist-2026-06-24-world-models.md`.
2. **File** — bulk path (Finding F7): `mv` all summaries into flat `Library/World Models/`, then one `rebuild_index.py`. Drives the topic to 40, past the cap.
3. **Observe** — generate the split proposal from the 40-paper index (blurb-clustered).
4. **Compare** — diff against temp.md's 4-way clustering; log divergences in `iteration-findings.md`.
5. **Refine** — fold any new gaps into `library-filing/SKILL.md`.
6. **Execute split** (Step 8) — 4 sub-topic folders + MOCs, umbrella-hub parent, move + re-stamp `topic:`, rebuild, `--check`.
7. **Verify** — `--check` exit 0; each sub-topic under 20; spot-check notes.

## Affected files

- `staging/worklist-2026-06-24-world-models.md` (new), `staging/iteration-findings.md` (append Iteration 2)
- `Library/World Models/` → dissolved into 4 `World Models — …` sub-topics + umbrella hub
- `.claude/skills/library-filing/SKILL.md` (only if new gaps surface)
- `ARCHITECTURE.md` topic table

## Verification criteria

- All 38 summarized (0 true losses after retries); reconcile failures against `ls staging/` before retrying (Finding F6).
- `rebuild_index.py --check` exit 0 after filing and after the split.
- 4 sub-topics, each `index.json` count under 20, summing to 40.
- Split proposal recorded and diffed against temp.md.
