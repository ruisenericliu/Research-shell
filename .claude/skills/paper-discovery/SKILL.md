---
name: paper-discovery
description: Fetch recent HuggingFace daily papers, filter by research topics of interest, and save a curated digest to the /discovery folder. Use when the user asks to scan for new papers, run the daily paper fetch, or update the discovery feed. Accepts optional arguments: days (default 2), topics (default: all canonical Library topics, derived from the Library/<Topic>/ folders — not a fixed list).
---

# Paper Discovery Skill

Fetch HuggingFace daily papers for the last N days, filter by topic, and write a curated digest to `/discovery/YYYY-MM-DD.md`.

## Arguments

- `days` — number of days to look back (default: 2)
- `topics` — comma-separated topic names to restrict to (default: all canonical Library topics). The semantic pass auto-derives the topic set from the `Library/<Topic>/` folders (sub-topics fold into their umbrella parent); the BM25 table below should carry a keyword row for each canonical topic. When a topic has **no** BM25 row, it can never become a candidate under the both-passes merge rule (Step 5) — so adding a row is required to make a new topic discoverable.

## Steps

### 1. Determine date range

Compute today's date and the previous `days - 1` days in `YYYY-MM-DD` format. Example for `days=2` run on 2026-05-11: dates are `[2026-05-11, 2026-05-10]`.

### 2. Fetch papers for each date

For each date, run:

```bash
curl -s "https://huggingface.co/api/daily_papers?date=DATE&limit=100&sort=publishedAt"
```

Each item in the response array has this shape:
```
{
  "title": "...",          // top-level title (same as paper.title)
  "summary": "...",        // top-level abstract (same as paper.summary)
  "publishedAt": "...",    // ISO date
  "paper": {
    "id": "2605.09063",    // arXiv ID — use this for links
    "title": "...",
    "summary": "...",
    "upvotes": 42,         // upvote count is nested here
    "ai_summary": "...",   // optional AI-generated summary (may be richer than summary)
    "ai_keywords": [...]   // optional keyword list
  }
}
```
Use top-level `title` and `summary` for filtering. Use `paper.id` for arXiv links. Use `paper.upvotes` for the upvote count. Prefer `paper.ai_summary` over `summary` for the digest blurb if it is non-empty.

### 3. Deduplicate within this run

Collect all papers across all dates. Remove duplicates by `paper.id`, keeping the first occurrence.

### 4. Check against previous runs

Scan all existing files in `/Users/ruisenliu/Repositories/Research/discovery/` (excluding today's file if it exists, `.gitkeep`, and log files). Extract every arXiv ID that appears in those files by grepping for the pattern `arxiv.org/abs/` or `**arXiv:**`. Build a set of previously-seen IDs.

For each paper in today's fetch, mark it as a **prior duplicate** if its `paper.id` is in that set. Count these separately — they will not appear in any section of the digest but are reported in the summary header.

### 5. Classify papers by topic (hybrid BM25 + semantic)

For each paper that is NOT a prior duplicate, determine which topics it matches using a two-pass hybrid approach. A paper matches a topic if it passes **either** pass. A paper may match multiple topics — include it under each matched section.

Papers matching no topic go into the **Passed Over** list.

---

**Pass 1 — BM25 keyword match**

Check `paper.title` and `paper.summary` (case-insensitive) against the keyword map below.

| Topic | Keywords |
|-------|----------|
| Vision Language Action Models | `VLA`, `vision language action`, `robot policy`, `manipulation policy`, `diffusion policy`, `action chunking`, `lerobot`, `visuomotor`, `robot manipulation`, `robot learning`, `embodied manipulation` |
| World Models | `world model`, `video prediction`, `latent world`, `RSSM`, `dreamer`, `jepa world`, `dynamics model`, `environment model`, `predictive world`, `latent action`, `world simulator`, `video generation`, `text-to-video`, `interactive simulation`, `playable world`, `neural simulator`, `object-centric`, `slot attention`, `video pretraining` |
| Inference-Time Reasoning Algorithms | `decision point`, `sparse policy selection`, `test-time scaling`, `test-time compute`, `compute allocation`, `entropy-gated`, `policy selection`, `branching strategy`, `pruning strategy`, `inference-time strategy`, `tts strategy`, `thinking tokens`, `inference scaling`, `reasoning budget`, `chain-of-thought scaling` |
| Human-to-Robot Demonstration Transfer | `egocentric video`, `egocentric robot`, `exocentric`, `human video`, `human demonstration`, `first-person video`, `third-person video`, `ego4d`, `human-centric video`, `cross-embodiment`, `embodiment gap`, `imitation from observation`, `hand-object interaction`, `human data robot`, `video pretraining robot`, `embodied intelligence`, `retargeting`, `viewpoint-invariant` |
| Reward Learning from Video | `reward learning`, `learned reward`, `reward function learning`, `reward from video`, `reward from observation`, `video reward`, `reward model rl`, `reward shaping`, `inverse reinforcement`, `internet video reward`, `reward code`, `reward from human video` |
| Multi-Agent Coordination | `multi-agent`, `multi agent`, `agent coordination`, `agent collaboration`, `agent debate`, `llm debate`, `agent communication`, `agent society`, `agent team`, `cooperative agent`, `agent swarm` |
| LLM Agents & Agentic AI | `llm agent`, `ai agent`, `agentic ai`, `agentic workflow`, `tool-use agent`, `react agent`, `autonomous agent`, `long-horizon agent`, `interactive agent`, `rl for agents`, `agent fine-tuning`, `agentic trajectory`, `agency benchmark` |
| Memory & Retrieval | `agent memory`, `long-term memory`, `episodic memory`, `working memory`, `memory-augmented agent`, `agentic search`, `web search agent`, `retrieval agent`, `external memory`, `memory bank`, `skill accumulation`, `skill library`, `research automation`, `personalized research`, `agentic research` |
| Humanoid Control | `humanoid`, `whole-body control`, `whole body control`, `motion tracking`, `motion imitation`, `bipedal`, `loco-manipulation`, `loco manipulation`, `motion retargeting`, `teleoperation`, `legged robot`, `locomotion policy`, `mocap retargeting`, `humanoid robot`, `whole-body controller` |
| Joint Embedding Predictive Architectures | `jepa`, `i-jepa`, `v-jepa`, `joint embedding predictive`, `joint-embedding predictive`, `latent prediction`, `predict in latent space`, `embedding-space prediction`, `masked latent prediction`, `representation collapse`, `non-contrastive`, `self-supervised representation`, `latent dynamics` |
| Multimodal Reasoning | `visual reasoning`, `multimodal reasoning`, `spatial reasoning`, `video reasoning`, `visual question answering`, `visual chain-of-thought`, `multimodal chain-of-thought`, `visual cot`, `referring segmentation`, `grounded reasoning`, `temporal reasoning`, `multimodal benchmark`, `video understanding` |
| Open-Vocabulary Vision | `open-vocabulary`, `open vocabulary`, `open-vocab`, `open-vocabulary detection`, `open-vocabulary segmentation`, `promptable segmentation`, `grounding dino`, `zero-shot detection`, `phrase grounding`, `grounded detection`, `text-prompted detection`, `segment anything` |
| Vision-Language Navigation | `vision-language navigation`, `vision language navigation`, `vln`, `instruction-following navigation`, `object-goal navigation`, `objectnav`, `language-conditioned navigation`, `embodied navigation`, `navigation policy`, `goal-conditioned navigation`, `room-to-room` |
| Grasping & Dexterous Manipulation | `grasp synthesis`, `grasp detection`, `contact modeling`, `dexterous manipulation`, `in-hand manipulation`, `tactile sensing`, `force feedback`, `robotic assembly`, `sim-to-real assembly`, `contact-rich`, `signed distance function`, `visuotactile` |
| Robotics — Surveys & Reviews | `a survey`, `a review`, `meta-analysis`, `comprehensive survey`, `systematic review`, `literature review`, `foundation models in robotics`, `foundation models for robotics`, `robot learning survey`, `deep generative models`, `taxonomy`, `open problems`, `challenges and opportunities` |
| 3D Generation | `3d generation`, `text-to-3d`, `image-to-3d`, `mesh generation`, `cad generation`, `3d synthesis`, `scene synthesis`, `3d content generation`, `shape generation`, `image-to-world`, `3d diffusion`, `generative 3d` |
| 3D Reconstruction — Feed-Forward | `feed-forward 3d`, `feed-forward reconstruction`, `point map`, `pointmap`, `dust3r`, `mast3r`, `pose-free reconstruction`, `multi-view stereo`, `3d reconstruction`, `feed-forward gaussian`, `neural radiance field`, `nerf`, `amortized reconstruction` |
| SLAM | `slam`, `simultaneous localization and mapping`, `visual odometry`, `visual slam`, `bundle adjustment`, `loop closure`, `pose tracking`, `dense slam`, `orb-slam`, `droid-slam`, `neural slam`, `camera tracking`, `visual-inertial` |
| Semantic Mapping | `semantic mapping`, `semantic map`, `open-vocabulary map`, `bird's-eye-view`, `bev mapping`, `semantic occupancy`, `scene graph`, `occupancy mapping`, `language-queryable map`, `feature field`, `distilled features`, `semantic slam`, `3d scene graph` |

---

**Pass 2 — Semantic match via local embedding model**

Build a JSON array of all non-duplicate papers in the form `[{"id": "...", "title": "...", "abstract": "..."}]` where `abstract` is the paper's `summary` field. Pipe it to the classifier bundled with this skill:

```bash
echo '<JSON_ARRAY>' | /Users/ruisenliu/Repositories/Research/researchEnv/bin/python /Users/ruisenliu/Repositories/Research/.claude/skills/paper-discovery/semantic_classify.py
```

The script reads each `Library/<Topic>/MOC.md` as the semantic specification for that topic, embeds both the MOC text and each paper's title+abstract using `all-MiniLM-L6-v2`, and returns a JSON object mapping `paper_id → {topic_name: score}` for all topics that exceeded the threshold. Default similarity threshold is 0.50.

**Discovery classifies at *parent* granularity.** A topic that has been split into sub-topic folders (`<Parent> — <Child>`, e.g. `World Models — Object-Centric`, or the `VLA — …` family under the canonical `Vision Language Action Models` parent) is **folded back into its parent** by the classifier: the parent's semantic spec is the concatenation of the umbrella MOC plus all its sub-topic MOCs, and the script only ever emits the canonical parent topic names. This keeps the daily digest a readable broad-triage feed and leaves the fine sub-topic placement to the `library-filing` skill. The fold (and the `VLA → Vision Language Action Models` alias) lives in `semantic_classify.py`'s `load_topics`; the BM25 keyword rows above are likewise keyed by parent.

If `sentence-transformers` is not installed or the script fails, skip this pass gracefully and rely on BM25 results only.

---

**Merge and best-fit assignment:**

1. A paper is a **candidate** for a topic only if it passed **both** BM25 AND semantic for that topic.
2. Each paper is placed in exactly **one** topic — the topic with the highest semantic similarity score among its candidates. If semantic scores are unavailable (BM25-only fallback), use keyword match count as the tiebreaker.
3. Papers with no candidate topics go into the **Passed Over** list.

### 6. Build the digest

Construct the output Markdown in this order:

**Header block:**
```markdown
# Paper Discovery — YYYY-MM-DD
> **Fetched:** FETCH_DATE · **Window:** DATE_START → DATE_END
> **Candidates:** N total · **Prior duplicates skipped:** D · **Passed over:** P · **Matched:** M across T topics
```

**Topic sections** (one per topic with matches, sorted by match score descending):
```markdown
## Vision Language Action Models (N)

### Paper Title
**arXiv:** [PAPER_ID](https://arxiv.org/abs/PAPER_ID) | **Match:** 0.XX | **▲ Upvotes:** N | **Published:** YYYY-MM-DD
> Abstract truncated to 2 sentences.

```

- `Match` is the cosine similarity score (0.00–1.00) from the semantic classifier for this topic. If semantic scores were unavailable, omit the Match field.
- `▲ Upvotes` is the HuggingFace crowd-interest count, sourced from `paper.upvotes` (default `0` when absent). It is a display-only signal — entries stay sorted by `Match`, not by upvotes.
- Do NOT include a HuggingFace link for each paper — arXiv only.
- Omit any topic section with 0 matches.

**Passed Over section** (arXiv link + a one-sentence blurb each):
```markdown
## Passed Over (P)
- [Paper Title One](https://arxiv.org/abs/PAPER_ID) — Abstract truncated to 1 sentence.
- [Paper Title Two](https://arxiv.org/abs/PAPER_ID) — Abstract truncated to 1 sentence.
- ...
```
If a paper has no usable abstract, write just `- [Paper Title](https://arxiv.org/abs/PAPER_ID)` (drop the ` — blurb`).

**Footer:**
```markdown
---
*Generated by paper-discovery skill · [HuggingFace Daily Papers](https://huggingface.co/papers)*
```

If all topics have 0 matches, replace topic sections with: `> No papers matched today's topics.`

### 7. Write output

Write the digest to:
```
/Users/ruisenliu/Repositories/Research/discovery/YYYY-MM-DD.md
```

Using today's date as the filename. Overwrite if the file already exists (runs are idempotent).

### 8. Confirm

Report to the user: total candidates, prior duplicates skipped, passed over, matched per topic, and the output path.
