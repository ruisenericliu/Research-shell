# GPT-4 Technical Report

**Authors:** OpenAI (Josh Achiam, Steven Adler, Sandhini Agarwal, Sam Altman, Ilya Sutskever et al., 279 contributors)
**Date:** March 15, 2023 (v1); latest version March 4, 2024 (v6)
**arXiv:** [2303.08774](https://arxiv.org/abs/2303.08774)
**Venue:** Technical Report (not peer-reviewed)

---

## Verdict

> **Verdict:** Worth a skim for benchmark baselines and the scaling-prediction result, but the deliberate omission of all architecture, training, and dataset details makes this a product announcement masquerading as a technical report — not a paper you can build on.

---

## Overview

GPT-4 is a large multimodal model (text + image inputs, text output) trained via next-token prediction followed by RLHF alignment **(Abstract)**. It achieves human-competitive scores on a broad suite of professional and academic exams — passing the bar exam at ~90th percentile — and outperforms GPT-3.5 by wide margins across standard NLP benchmarks **(Table 1, Table 2)**. The paper's most technically substantive contribution is a scalable infrastructure for predicting final model performance from runs using 1/1,000th the compute, formalized as a power-law relationship **(Section 2)**.

---

## Current State-of-the-Art

### Academic and Professional Exams (Table 1)

| Method / Exam | GPT-3.5 percentile | GPT-4 percentile | Notes |
|---|---|---|---|
| Uniform Bar Exam | ~10th | ~90th | 298/400 raw score |
| LSAT | ~40th | ~88th | |
| SAT Evidence-Based Reading & Writing | ~87th | ~93rd | 710/800 |
| GRE Verbal | ~63rd | ~99th | 169/170 |
| USABO Semifinal | — | 99th–100th | 87/150 |
| **GPT-4 (overall)** | **~bottom 10–40th** | **~top 10–99th** | **Varies by exam** |

### Traditional NLP Benchmarks (Table 2)

| Method | MMLU | HellaSwag | HumanEval | GSM-8K | ARC | Notes |
|---|---|---|---|---|---|---|
| GPT-3.5 | 70.0% | 85.5% | 48.1% | 57.1% | 85.2% | OpenAI's prior flagship |
| **GPT-4** | **86.4%** | **95.3%** | **67.0%** | **92.0%** | **96.3%** | **All numbers from Table 2** |

The report notes GPT-4 surpasses English-language SOTA on 24 of 26 languages tested on MMLU **(Section 3.1)**. [Direct comparisons against other contemporaneous frontier models (e.g., PaLM-2, Claude) are not included; those numbers must be sourced from their respective papers.]

### Safety / Alignment Metrics

| Dimension | GPT-3.5 | GPT-4 | Notes |
|---|---|---|---|
| Toxic content rate (RealToxicityPrompts) | 6.48% | 0.73% | Section 4 |
| Human preference over ChatGPT | — | 70.2% | Appendix A |
| Disallowed-content response rate reduction | baseline | −82% vs GPT-3.5 | Section 4 |

---

## Contributions

- **CLEVER:** **Scalable performance prediction via power law.** The authors fit L(C) = aC^b + c to smaller model runs (up to 10,000× less compute) and accurately extrapolated GPT-4's final loss and per-difficulty-bucket HumanEval accuracy before training completed **(Section 2)**. This is the paper's single most technically novel and reproducible claim.

- Multimodal input capability: GPT-4 accepts images alongside text without degrading text performance **(Section 3.3)**. [Vision benchmark details are deferred to a companion paper; this report shows only qualitative examples.]

- RLHF-based alignment achieving large safety improvements (−82% disallowed-content responses, 9× reduction in toxic output) via rule-based reward models (RBRMs) used as zero-shot classifiers during fine-tuning **(Section 4)**.

- Broad multilingual generalization: state-of-the-art MMLU performance in 24/26 tested languages despite primarily English training signal **(Section 3.1)**.

- Release of **OpenAI Evals**, an open-source framework for constructing and running LLM benchmarks **(Appendix)**.

### Ablation Highlights

The paper contains no ablation study. The authors explicitly state: "This report contains no further details about the architecture (including model size), hardware, training compute, dataset construction, training method, or similar" **(Abstract / Limitations section)**. There is one partial ablation-adjacent finding:

> "The model's capabilities on exams appear to stem primarily from the pre-training process and are not significantly affected by RLHF" for multiple-choice questions, though RLHF did improve TruthfulQA performance **(Section 3)**.

This single data point is stated qualitatively, with no numbers or controls reported. The absence of ablations means the contribution of any individual component — architecture choices, RLHF formulation, data mixture, scale — cannot be assessed from this paper.

**Related work coverage:** The paper cites GPT-3 (Brown et al., 2020), InstructGPT (Ouyang et al., 2022), and a range of benchmark papers, but does not compare against PaLM 2, Chinchilla, or other frontier models that were available or imminent at submission. [This omission is likely intentional given competitive context, but it weakens the SOTA positioning.]

---

## Open Problems & Research Directions

- **Hallucination and reliability.** The authors acknowledge GPT-4 "is not fully reliable (e.g., can suffer from 'hallucinations')" but provide no quantitative analysis of hallucination rate or failure modes **(Limitations)**. Characterizing when and why the model confabulates remains open.

- **Context window scaling.** The paper tests a 32K-token variant but provides no systematic analysis of how performance degrades with context length or how retrieval interacts with long-context capability.

- **Vision-language grounding.** Multimodal results are demonstrated qualitatively; quantitative vision benchmarks and failure analysis are absent. How spatial reasoning, counting, and OCR-dependent tasks perform is unaddressed.

- **Sample efficiency and few-shot dynamics.** GPT-4's few-shot vs. zero-shot curves are not reported, leaving open how much prompt engineering accounts for the benchmark gains.

- **Instruction following vs. capability.** The paper's finding that RLHF does not improve multiple-choice accuracy but does improve TruthfulQA deserves systematic follow-up: which behaviors are capability-gated vs. alignment-gated?

- **Scaling law generalization.** The power-law extrapolation works for loss and HumanEval; whether it generalizes to reasoning-heavy benchmarks, safety metrics, or multimodal tasks is unexplored.

---

## Limitations

- **Fundamental opacity.** All architecture, training data, compute, and hyperparameter details are withheld. Independent evaluation is impossible; every claim rests entirely on OpenAI's internal evaluations.

- **Self-reported safety metrics.** Safety improvements (−82% disallowed content, 0.73% toxicity) are measured on OpenAI's own evaluation suite with no third-party auditing at time of publication. The robustness of these metrics to adversarial prompting is not assessed.

- **Benchmark saturation risk.** Several benchmarks (ARC at 96.3%, GRE Verbal at 99th percentile) are near ceiling, making further progress invisible. [Whether GPT-4 was trained with any overlap against these test sets cannot be verified.]

- **No error analysis.** The paper reports aggregate accuracy but not distribution of failure modes, systematic biases, or confidence calibration.

- **Static knowledge cutoff.** Training data ends September 2021; no mechanism for updating factual knowledge is discussed.

- **Exam performance ≠ general reasoning.** Professional exam scores are presented as the primary capability demonstration. Whether these reflect genuine reasoning or pattern matching on exam-style formatting is not disentangled **(a known critique in the field)**.

---

## Reproducibility

| Aspect | Status | Detail |
|---|---|---|
| Code / models released | ✗ | No weights, no training code. OpenAI Evals framework open-sourced (evaluation only). |
| Compute to reproduce | ✗ | Entirely withheld. Not even order-of-magnitude estimates provided. |
| Training details sufficient | ✗ | Architecture, data mixture, tokenizer, optimizer, batch size, learning rate — all absent by design. |
| Hyperparameters / stability | ✗ | Nothing disclosed. |
| Scaling-law methodology | ⚠ | Power-law formula L(C) = aC^b + c given **(Section 2)**, but the smaller runs used to fit it are not released. |
| Safety evaluation suite | ⚠ | OpenAI Evals released; specific safety eval prompts/rubrics are partially documented in the appendix but not fully reproducible without internal model access. |

This is the least reproducible class of ML paper: a closed proprietary system evaluated only by its developers, with every technical detail deliberately omitted. The scaling-prediction result is the sole contribution that could in principle be independently replicated, and even that requires reproducing the smaller training runs whose details are not given.

---

## Special Notes

- **Intentional non-disclosure policy.** The authors explicitly justify withholding all technical details on "competitive and safety" grounds **(Abstract)**. This is unusual and sets a precedent for technical reports that function more as capability demonstrations than scientific contributions.

- **Scale of authorship.** 279 contributors are listed, making attribution of specific contributions opaque. The paper reads as an organizational deliverable rather than a research paper with a core intellectual team.

- **Post-publication safety auditing.** The report commits to making technical details available "to additional third parties" for safety auditing — a transparency mechanism separate from public disclosure.

- **No embedded prompt injections detected.** The paper was scanned for prompt injection patterns directed at AI readers. None found.

- **Field reception.** The report was widely cited immediately but also widely criticized in the research community for its opacity. It accelerated public and policy discourse on AI capabilities far more than it advanced scientific understanding of how those capabilities arise.
