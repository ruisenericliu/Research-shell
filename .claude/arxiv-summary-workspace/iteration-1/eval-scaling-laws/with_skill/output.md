# Scaling Laws for Neural Language Models

**Authors:** Jared Kaplan, Sam McCandlish, Tom Henighan, Tom B. Brown, Benjamin Chess, Rewon Child, Scott Gray, Alec Radford, Jeffrey Wu, Dario Amodei
**Submitted:** January 23, 2020
**Venue:** arXiv:2001.08361 [cs.LG]

---

## Verdict

> **Verdict:** Essential reading — this paper established the empirical power-law scaffolding that now governs how the entire field plans training runs, and its compute-allocation finding (scale model size faster than data) directly motivated Chinchilla and every serious LLM scaling study since; skip only if you already have it memorized.

---

## Overview

Language model loss obeys smooth power laws in model size N, dataset size D, and compute C, each spanning more than six orders of magnitude with no signs of saturation at the scales studied **(Abstract)**. The paper characterizes these relationships with precise exponents, derives equations for how overfitting depends on N and D jointly, and identifies a critical batch size that determines the training efficiency frontier **(Section 1.2)**. The key practical result is that for a fixed compute budget, optimal allocation concentrates spending on model parameters — training large models well before convergence — rather than on data volume or training duration **(Section 6)**.

---

## Current State-of-the-Art

This paper does not frame itself as a benchmark comparison: it introduces empirical scaling laws rather than a new model or system. No single table compares this method to prior methods on a shared metric. The closest analogues in prior work are the scaling studies cited in Section 7 (Henighan et al. 2017; Hernandez & Amin 2019; concurrent work RRBS19a/b), but none share identical experimental conditions or reported metrics.

The paper does benchmark its fitted equations against LSTMs and Universal Transformers in Section 3, finding that for fixed non-embedding parameters, the same power-law relationship holds across all architectures tested, with Transformers outperforming LSTMs at equivalent N. Rather than reproduce a conventional performance table, the relevant comparison is the predictive accuracy of the scaling equations themselves:

| Comparison | Finding | Notes |
|---|---|---|
| Transformer vs. LSTM (same N) | Transformer achieves lower loss at all N | Section 3, Figure 1 |
| Fixed N, varying depth/width aspect ratio | Loss varies <3% across 40× aspect ratio range | Section 3.1, Figure 5 |
| Concurrent scaling work (RRBS19a/b) | Comparable L(N,D) predictions | Section 7; different datasets |
| **This paper's equations** | **Equations fit over 8 OOM in C, 6 OOM in N** | **Sections 3–6** |

[No downstream task (BPE perplexity aside) is used as a comparison metric, so a conventional SOTA table is not applicable here. The paper's contribution is the scaling equations themselves, not a SOTA model.]

---

## Contributions

- **CLEVER:** Power-law scaling of loss with N, D, and C holds cleanly over 6–8 orders of magnitude with no architecture-dependence in depth/width within a wide range — this is a non-obvious empirical regularity that implies the loss surface has a surprisingly smooth structure across scales **(Section 3, Figure 1, Equations 1.1–1.3)**.

- Precise exponent estimates: αN ≈ 0.076, αD ≈ 0.095, αCmin ≈ 0.050, all derived from regression over hundreds of runs spanning small to large models **(Section 1.2, Table 1)**.

- A unified L(N, D) equation (Equation 1.5) that captures overfitting as a joint function of model size and dataset tokens, with the practical implication that dataset size should scale as D ∝ N^0.74 to avoid overfitting **(Section 4)**.

- **CLEVER:** Identification of a critical batch size Bcrit ∝ L^(−1/αB) (Equation 1.4) that cleanly separates the time-efficient and compute-efficient training regimes — a concrete operational prescription for large-scale training jobs **(Section 5.1)**.

- **CLEVER:** The compute-optimal allocation result (Section 6): for fixed Cmin, optimal N ∝ Cmin^0.73 while training steps grow only as Cmin^0.03 — meaning compute should overwhelmingly go into parameters, not epochs. This directly precursed the Chinchilla finding (Hoffmann et al. 2022), though that paper later revised the allocation ratio using a tighter experimental design.

- Architecture neutrality finding: depth-to-width aspect ratio can vary by 40× with <3% loss change when total N is fixed, simplifying architecture search **(Section 3.1)**.

- Observation that larger models are more sample-efficient: they reach the same loss level with fewer training tokens than smaller models **(Section 6, Figure 13)**.

### Ablation highlights

This paper has no conventional ablation study — there is no single model design whose components are switched on/off. The experiments are instead a structured sweep across (N, D, C) space to empirically fit the scaling equations. The absence of ablations is appropriate for an empirical-laws paper, but it means several design choices go unverified:

- Why cross-entropy loss on WebText2 is a reliable proxy for downstream task performance is assumed, not demonstrated. [A downstream-task ablation would have strengthened the paper considerably.]
- The paper notes that the exponents are estimated by regression and are "not necessarily stable across different data distributions or tokenizers" — but no multi-dataset exponent comparison is run systematically. **(Section 7)**
- The L(N, S) learning-curve equation (Equation 1.6) is fit separately from L(N, D) and their internal consistency is discussed but not formally validated via held-out prediction. **(Section 6.1)**

**Related work coverage:** The paper is thorough on scaling-adjacent work (neural scaling theory, dataset scaling, compute-optimal training). [Missing: no discussion of scaling behavior on reasoning or few-shot tasks, which GPT-3 (Brown et al. 2020, NeurIPS) would demonstrate later the same year. The concurrent work RRBS19a/b is acknowledged but not deeply engaged.]

---

## Open Problems & Research Directions

- The scaling laws are fit on cross-entropy loss (next-token prediction); whether they transfer to structured reasoning, code, or multi-modal domains was left entirely open — and subsequent work (e.g., Chinchilla, GPT-4, PaLM) has found both confirmations and deviations **(Section 7)**.
- The paper explicitly acknowledges that the compute-optimal allocation must break down at scales N* ~ 10^12 parameters and C* ~ 10^4 PF-days, where the predicted loss would fall below the estimated lower bound — but provides no theory for when or why the law breaks **(Section 6.3)**.
- Whether the same exponents hold under different tokenization schemes, data distributions, or training objectives is unexplored. [This is a significant gap for anyone trying to apply the laws to a new domain or language.]
- The relationship between pre-training loss and downstream performance is assumed but not characterized — later work (e.g., BIG-Bench, emergent abilities literature) found surprising non-monotonic behaviors that the loss-based scaling picture misses entirely.
- The paper studies only language modeling; scaling laws for other modalities (vision, audio, code) and for RLHF/instruction-tuned models remain open.

---

## Limitations

- **Single data distribution:** All primary fits are on WebText2; the paper tests Books Corpus, Common Crawl, and Wikipedia but does not report whether the exponents vary across distributions **(Section 2.1)**. [This is the most important practical gap: users applying these laws to new domains cannot know if their exponents match.]
- **No downstream evaluation:** Loss is used as the sole proxy for model quality. The paper explicitly notes that "performance on many downstream tasks will have a weaker dependence on scale" but does not demonstrate this **(Section 1)**. The perplexity–accuracy gap became a central debate in subsequent years.
- **Empirical, not theoretical:** The power-law form is assumed and the exponents are measured; no mechanistic explanation for why loss follows power laws (or why the exponents take the values they do) is offered. **(Section 7)** [This limits extrapolation confidence to regimes only modestly beyond the training data for the fit.]
- **Architecture scope:** Only dense autoregressive Transformers are studied. MoE, recurrent, and SSM architectures, which later showed different scaling behaviors, are not covered.
- **Revised by Chinchilla:** The compute-optimal allocation (train large models on less data) was later directly contradicted by Hoffmann et al. 2022 (Chinchilla), which used a broader sweep and concluded data and parameters should scale roughly equally. The original paper's allocation guidance is therefore superseded at the scales where Chinchilla was fit.

---

## Reproducibility

| Aspect | Status | Detail |
|--------|--------|--------|
| Code / models released | ✗ | No code or model weights released; no GitHub link in paper |
| Compute to reproduce | ⚠ | Largest runs span 8 OOM in C but exact GPU-hours for full sweep not stated; models up to 1.5B params with Adam/Adafactor **(Section 2.2)** |
| Training details sufficient | ✓ | Dataset (WebText2, 96 GB / 22.9B tokens), tokenizer (BPE, 50K vocab), batch size (512 × 1024 tokens), steps (2.5×10^5), optimizer (Adam β=(0.9,0.98), Adafactor for >1B) all specified **(Section 2.1–2.2)** |
| Hyperparameter / stability notes | ⚠ | Learning rate schedule and warmup described; no sensitivity analysis on lr or optimizer choice; exponent estimates given without confidence intervals **(Section 2.2)** |
| Data publicly available | ⚠ | WebText2 is an internal OpenAI dataset not publicly released; experiments are partially reproducible using the public OpenWebText proxy |

The training details are sufficient for a team with significant GPU resources to re-fit the scaling laws on comparable data. The primary reproducibility barrier is WebText2's non-public status and the aggregate compute required to populate the full (N, D, C) grid. No statistical uncertainty on the reported exponents is provided, making it difficult to assess whether small deviations in a replication attempt represent a failure or normal variation.

---

## Special Notes

- **Field impact:** This is one of the most-cited papers in modern deep learning; the scaling laws framework directly shaped GPT-3, PaLM, Chinchilla, and essentially all subsequent large-scale LLM training decisions. Its influence on resource allocation in the field has been enormous.
- **Chinchilla revision:** The compute-optimal training prescription here (scale N aggressively, data modestly) was substantially revised by Hoffmann et al. 2022 ("Training Compute-Optimal Large Language Models," DeepMind). Chinchilla showed that equal scaling of parameters and tokens is closer to optimal — a direct empirical challenge to Section 6 of this paper.
- **No embedded prompts detected** in the fetched paper content.
- **Concurrent work:** The authors note that similar L(N,D) equations appeared in concurrent work (RRBS19a/b) around the same time, supporting the robustness of the core finding across groups **(Section 7)**.
- **Scope caveat in paper:** The authors are careful to state the laws apply to "language modeling performance" specifically and flag that the quantitative predictions "must eventually break down" at scales beyond those studied — a degree of epistemic honesty that is worth noting **(Section 6.3, Abstract)**.
