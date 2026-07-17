# LoRA: Low-Rank Adaptation of Large Language Models

**Authors:** Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang, Weizhu Chen (Microsoft)
**Date:** June 17, 2021 (revised October 16, 2021)
**arXiv:** https://arxiv.org/abs/2106.09685
**Venue:** ICLR 2022

---

## Verdict

> **Verdict:** Worth a deep read — LoRA is a foundational PEFT technique that matches full fine-tuning quality at 10,000× fewer trainable parameters and has become the dominant approach for adapting LLMs in production; the ablation study substantiates the core claim empirically, and the deployed code made it immediately reproducible.

---

## Overview

Fine-tuning large language models for downstream tasks requires updating and storing a full copy of all parameters per task, which becomes prohibitively expensive at GPT-3 scale (175B parameters = 350GB per checkpoint). LoRA freezes the pre-trained weights and injects trainable low-rank decomposition matrices (W₀ + ΔW = W₀ + BA, where r ≪ min(d,k)) into each Transformer layer, so only A and B are trained. On GPT-3 175B, LoRA matches or beats full fine-tuning across WikiSQL, MNLI, and SAMSum while using 4.7M–37.7M trainable parameters versus 175B, with no added inference latency because the adapter matrices can be merged back into W before deployment **(Abstract, Section 4)**.

---

## Current State-of-the-Art

The paper benchmarks on three model families. Tables below use the numbers as reported **(Tables 2, 3, 4)**.

### RoBERTa / DeBERTa — GLUE Average Score (Table 2)

| Method | Params (trainable) | RoBERTa-Base | RoBERTa-Large | DeBERTa-XXL | Notes |
|--------|-------------------|--------------|---------------|-------------|-------|
| Full Fine-Tune | ~125M / ~355M / ~1.5B | 86.4 | 88.9 | 91.1 | Separate checkpoint per task |
| BitFit | ~0.1M | 85.2 | — | — | Bias-only tuning |
| AdapterD | 0.9M | 85.4 | — | — | |
| AdapterP | 0.8M | — | 87.9 | — | |
| AdapterH | 0.8M | — | 86.4 | — | |
| **LoRA** | **0.3M / 0.8M / 4.7M** | **87.2** | **89.0** | **91.3** | Matches or exceeds FFT |

### GPT-2 Medium/Large — E2E NLG Challenge BLEU (Table 3)

| Method | Params (trainable) | BLEU | NIST | ROUGE-L | Notes |
|--------|-------------------|------|------|---------|-------|
| Full Fine-Tune (Med) | 354.9M | 68.2 | 8.62 | 71.0 | |
| AdapterH (Med) | 11.09M | 67.3 | 8.83 | 71.0 | |
| PreLayer (Med) | 0.35M | 69.7 | 8.81 | 71.4 | Prefix tuning |
| **LoRA (Med)** | **0.35M** | **70.4** | **8.85** | **71.8** | Beats FFT with 1000× fewer params |
| Full Fine-Tune (Large) | 774.0M | 68.5 | 8.78 | 71.4 | |
| PreLayer (Large) | 0.77M | 70.3 | 8.85 | 71.7 | |
| **LoRA (Large)** | **0.77M** | **70.4** | **8.89** | **71.8** | |

### GPT-3 175B (Table 4)

| Method | Params (trainable) | WikiSQL | MNLI-m | SAMSum R1 | Notes |
|--------|-------------------|---------|--------|-----------|-------|
| Full Fine-Tune | 175B | 73.8 | 89.5 | 52.0 | |
| BitFit | 14.2M | 71.3 | 91.0 | 51.3 | |
| PreEmbed | 3.2M | 63.1 | 88.6 | 48.3 | |
| PreLayer | 20.2M | 70.1 | 89.5 | 50.8 | |
| AdapterH (7.1M) | 7.1M | 71.9 | 89.8 | 53.0 | |
| AdapterH (40.1M) | 40.1M | 73.2 | 91.5 | 53.2 | |
| **LoRA (4.7M)** | **4.7M** | **73.4** | **91.7** | **53.8** | Best overall efficiency |
| **LoRA (37.7M)** | **37.7M** | **74.0** | **91.6** | **53.4** | More params, marginal gains |

Prior methods that matter but aren't directly head-to-head comparable: **Adapter** variants (Houlsby et al., 2019; Pfeiffer et al., 2021) suffer sequential bottleneck latency at low batch sizes; **prefix/prompt tuning** (Li & Liang, 2021; Lester et al., 2021) reduces usable sequence length and shows non-monotonic behavior with more tokens. LoRA specifically targets the inference-latency problem of adapters and the sequence-length reduction problem of prefix tuning.

---

## Contributions

- **CLEVER:** The core insight that weight update matrices during fine-tuning have low intrinsic rank — formalized as ΔW = BA with r as small as 1 — is non-obvious and supported both empirically (Tables 5–6) and via subspace analysis (Figures 3–4). The reformulation is elegant: it turns a high-rank gradient update into a structured low-rank product, requiring no change to the Transformer architecture.

- **CLEVER:** Merging LoRA weights back into W at inference time (W' = W₀ + BA) eliminates all inference overhead — unlike adapter layers which insert sequential computation bottlenecks. This makes LoRA uniquely suited to production deployment where batch size fluctuates **(Section 3, Table 1)**.

- Demonstrated that a fixed 18M parameter budget is better spent adapting multiple weight matrices at low rank than a single matrix at high rank — e.g., Wq+Wv at r=4 outperforms Wq-only at r=8 on GPT-3 **(Table 5)**.

- Provided practical 3× VRAM reduction during training on GPT-3 175B (1.2TB → 350GB) and 25% throughput improvement (32.5 → 43.1 tokens/s), making 175B-class training feasible on fewer GPUs **(Section 3)**.

- Theoretical grounding via connection to prior work on intrinsic dimensionality of neural networks (Aghajanyan et al., 2021; Li et al., 2018), though the paper notes this as motivating rather than formally proven **(Section 7)**.

### Ablation Highlights

#### Which Weight Matrices to Adapt? (Table 5, GPT-3 175B, 18M param budget)

| Configuration | WikiSQL | MNLI-m | What it means |
|---------------|---------|--------|---------------|
| Wq only (r=8) | 70.4 | 91.0 | Query alone is the weakest single choice |
| Wk only (r=8) | 70.0 | 90.8 | Key alone is weakest of all; often skipped in practice |
| Wv only (r=8) | 73.0 | 91.0 | Value is more important than Q or K individually |
| Wo only (r=8) | 73.2 | 91.3 | Output projection rivals value alone |
| **Wq+Wv (r=4)** | **73.7** | **91.3** | Splitting budget across Q+V beats single-matrix high-rank |
| Wq+Wk (r=4) | 71.4 | 91.3 | Q+K underperforms Q+V, confirming value > key |
| All four (r=2) | 73.7 | 91.7 | MNLI benefit from all four; marginal on WikiSQL |

**Takeaway:** The gain from spreading rank across more matrices (r=4 each on two vs. r=8 on one) is real but small (~0.5–3 pts). The practical default of Wq+Wv at low rank comes from this table. [Note: this ablation only tests attention matrices — MLP layers are never adapted and remain uncharacterized.]

#### Rank Sensitivity (Table 6, GPT-3 175B)

| Rank r | Wq only (WikiSQL) | Wq+Wv (WikiSQL) | All four (WikiSQL) | Wq only (MNLI) |
|--------|-------------------|-----------------|-------------------|----------------|
| 1 | 68.8 | 73.4 | 74.1 | 90.7 |
| 2 | 69.6 | 73.3 | 73.7 | 90.9 |
| 4 | 70.5 | 73.7 | 74.0 | 91.1 |
| 8 | 70.4 | 73.8 | 74.0 | 90.7 |
| 64 | 70.0 | 73.5 | 73.9 | 90.7 |

**Takeaway:** Performance plateaus at r=1 for multi-matrix settings and r=4 for single-matrix — striking evidence for the low-rank hypothesis. Higher rank does not help and sometimes slightly hurts (possibly noise or optimization difficulty). [This is the ablation's strongest finding for the central claim: the task-specific update subspace is genuinely low-dimensional.]

#### Subspace Analysis (Figures 3–4, Section 7.3)

The paper measures normalized subspace similarity between Ar=8 and Ar=64 top singular vectors. The top direction has >0.5 overlap, while other directions approach zero — confirming that larger r simply adds noise dimensions. Random Gaussian matrices serve as a control and show near-zero overlap. [This analysis is qualitative and limited to one layer (layer 48 of GPT-3) but is directionally convincing.]

#### ΔW Amplification Analysis (Table 7)

| Projection basis | ‖projected Wq‖_F | Interpretation |
|-----------------|-----------------|----------------|
| ΔWq singular vectors (r=4) | 0.32 | ΔW does NOT repeat the top directions of W |
| Top directions of Wq itself | 21.67 | W's top directions are NOT what ΔW enhances |
| Random matrix control | 0.02 | Baseline |
| ‖Wq‖_F | 61.95 | Full magnitude |
| ‖ΔWq‖_F | 6.91 | ΔW is ~11% the size of W |

**Takeaway:** ΔW enhances directions in W that are underemphasized (not the dominant ones), amplifying them by ~21.67/0.32 ≈ 67×. This suggests LoRA is not merely memorizing but refocusing attention capacity toward task-relevant features. [This is an interesting mechanistic finding but the analysis is localized to one layer and one task; generalizability is unverified.]

### Related Work Coverage

Key citations are present and appropriate: Li et al. (2018) intrinsic dimensionality, Aghajanyan et al. (2021) fine-tuning intrinsic dimensionality, Houlsby et al. (2019) adapters, Pfeiffer et al. (2021) AdapterFusion, Li & Liang (2021) prefix tuning, Lester et al. (2021) prompt tuning. [One notable gap: **Diff-Pruning** (Guo et al., 2021) is not cited, which also constrains fine-tuning updates to a low-dimensional subspace via masking. The connection would sharpen the motivation section.]

---

## Open Problems & Research Directions

- **MLP and LayerNorm adaptation:** The paper applies LoRA only to attention projection matrices. Whether MLP weights benefit from low-rank adaptation — and what the optimal layer-type budget allocation is — is entirely unaddressed **(Section 7, Future Work)**.

- **Automated rank and matrix selection:** The choice of r and which matrices to adapt is empirical and task-specific. A principled or learned selection criterion (e.g., sensitivity-based allocation of rank budget across layers) would be a clear extension.

- **Multi-task batching:** When A and B differ per task, batched inference requires separate forward passes per task. The paper acknowledges this but provides no solution **(Section 6)**. This limits LoRA in serving architectures that need to handle many tasks simultaneously.

- **Dynamic rank during training:** The paper uses a fixed r throughout; progressive rank pruning or growth during training could recover additional efficiency or quality.

- **Theoretical lower bounds:** Why does r=1 suffice? The low-intrinsic-dimensionality hypothesis is borrowed but not proven for the adaptation setting. A formal result connecting model scale, task complexity, and minimum sufficient rank would be valuable.

- **Vision and multimodal models:** The paper focuses entirely on NLP. [LoRA for ViTs and diffusion models has since been demonstrated by the community, but this is outside the original paper's scope.]

---

## Limitations

- **Attention-only evaluation:** All ablations are on attention weight matrices. MLP layers, layer norms, and biases are excluded from adaptation without justification beyond compute budget. This leaves open whether the low-rank hypothesis holds for other parameter types **(Section 4.2)**.

- **Batch size sensitivity for latency claims:** The adapter latency comparison (Table 1) is measured at batch size 1. At larger batch sizes, adapter overhead amortizes and the latency advantage of LoRA narrows; this is acknowledged but not quantified **(Section 2)**.

- **Rank selection is empirical and task-dependent:** There is no principled method to choose r before training. The paper tests a limited grid (r ∈ {1, 2, 4, 8, 64}) and relies on validation performance, which requires access to labeled data for each new task.

- **Benchmark diversity is limited:** GPT-3 ablations cover only WikiSQL, MNLI, and SAMSum — three quite different tasks, but not a broad evaluation. Generation tasks like code, reasoning chains, or structured prediction are not tested at 175B scale.

- **Statistical reporting is inconsistent:** GPT-2 results include ±0.1 confidence intervals; GPT-3 ablation tables note ±0.5% / ±0.1% uncertainty for WikiSQL/MNLI. Full fine-tuning and adapter baselines on GPT-3 are single-run numbers, making the comparison asymmetric.

- **No catastrophic forgetting analysis:** LoRA freezes the base model, which should reduce forgetting — but no multi-task or sequential adaptation experiments test this claim.

---

## Reproducibility

| Aspect | Status | Detail |
|--------|--------|--------|
| Code / models released | ✓ | https://github.com/microsoft/LoRA — includes RoBERTa, DeBERTa, GPT-2 checkpoints and PyTorch package |
| Compute to reproduce | ⚠ | GPT-3 175B requires 350GB VRAM (LoRA) vs. 1.2TB (full FT) — multi-node A100 setup, exact hardware not specified. RoBERTa/GPT-2 experiments are small-scale and reproducible on a single GPU. |
| Training details sufficient | ✓ | Tables 9–12 give optimizer (AdamW), LR, warmup ratio, epochs, batch size, sequence length, and LoRA rank/α per model family and task. Enough to reimplement from scratch. |
| Hyperparameter / stability notes | ⚠ | Rank and α are reported as final values; search range not stated. GPT-2 results include standard deviation (±0.1 BLEU), but GPT-3 baselines do not. No instability or sensitivity warnings reported — likely stable given frozen base, but not verified. |
| Data splits / preprocessing | ✓ | Standard public benchmarks (GLUE, E2E NLG, WikiSQL, MNLI, SAMSum) with standard preprocessing; no custom splits. |

The code release substantially lowers the barrier to reproduction. The main gap is that the 175B experiments require infrastructure not accessible to most academic labs, and the exact cluster configuration is not described.

---

## Special Notes

- **Field reception:** LoRA became the de facto standard PEFT method for LLMs and diffusion models within 1–2 years of release. As of mid-2025, the paper has >10,000 citations and the technique is integrated into HuggingFace PEFT, diffusers, and most major LLM fine-tuning frameworks. This is one of the few recent ML papers with genuine infrastructural impact.

- **Naming and scope:** The paper's framing is for large language models, but the technique is architecture-agnostic. The community rapidly extended it to ViTs (LoRA for vision), diffusion U-Nets, and multimodal models — none of which are discussed here.

- **No embedded prompt injections detected** in the HTML version of the paper.

- **Initialization choice:** Zeroing B at init (so ΔW = BA = 0 at step 0) is a small but important detail that ensures training starts from the pretrained model's behavior. The paper mentions it **(Section 4.1)** but does not ablate whether random init for B would hurt — [a useful sanity check that is absent].

- **α/r scaling:** The authors fix α (a constant) and vary r, rather than tuning α independently. In practice α is set equal to r (α=r), effectively making the scaling factor 1. [This detail trips up many reimplementations; the paper's notation could be clearer.]
