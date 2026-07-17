# pipeline-orchestrator evals

Regression / drift guard for the two things the cost redesign depends on:

1. **Classification stays correct and confidence-gated** — each Sonnet summary sub-agent picks the
   right topic (method-first) when the paper is in-scope, and leaves it **UNSURE** when it isn't.
   Graded here by `check_classifications.py` against `golden_set.jsonl`.
2. **The orchestrator stays cheap** — filing is mechanical, so the Opus/main-thread cost per paper
   stays near zero. Measured with `cost_report.py` (in this folder; see "Cost gate" below).

If a future edit breaks either — classification drifts, the gate stops firing, or filing/classification
slides back onto the Opus main thread — one of these catches it.

## Golden set

`golden_set.jsonl` — five papers, all confirmed present in Paperclip, chosen to cover the decision's
failure modes: an unambiguous confident call (OpenVLA), a squarely in-scope paper (WHIRL), a
border-of-two-topics paper where UNSURE is also acceptable (VINN), a split-family paper where any of
several sub-topics passes (Genie), and an **out-of-scope gate case** that MUST come back UNSURE
(*Attention Is All You Need*). Schema is documented at the top of the file.

## Running the classification eval (for a future agent)

**Safety rule: this eval never mutates the real Library.** Do not `mv` notes into `Library/`, do not
run `rebuild_index.py`, do not touch any `index.json`. You are testing the *decision*, written to a
throwaway directory.

1. Pick a scratch run dir, e.g. `RUN=.claude/skills/pipeline-orchestrator/evals/runs/$(date +%F)`
   (`runs/` is gitignored; create it). 
2. For each paper in `golden_set.jsonl`, dispatch **one** summary+classify sub-agent exactly as the
   skill's **Step 6** describes — same fetch path (Paperclip `content.lines`), same topic menu (build
   it fresh with `scripts/topic_menu.py`), same classify-and-stamp instructions — with **two changes**:
   save the note into `$RUN/` instead of `staging/`, and (belt-and-suspenders) tell the agent not to
   move the file or touch any index. The agent stamps `topic:` into the note frontmatter when
   confident and leaves it unstamped when not — identical to production.
3. Score it:
   ```bash
   researchEnv/bin/python3 .claude/skills/pipeline-orchestrator/evals/check_classifications.py --run-dir "$RUN"
   ```
   It matches each note to the golden set by `arxiv_id`, prints a PASS/FAIL line per paper, and exits
   non-zero if any case fails.

**Pass criteria:** `5/5 classifications correct`. A wrong stamped topic (worst), a leaked gate
(out-of-scope paper got a topic), or a missing note all fail. UNSURE passes only where the golden
row allows it (`unsure_ok`/`require_unsure`).

## Cost gate (drift guard)

Classification correctness says nothing about *where* the work ran. After a real pipeline run (not
this dry eval), confirm the expensive thread stayed idle:

```bash
researchEnv/bin/python3 .claude/skills/pipeline-orchestrator/evals/cost_report.py --since <run-T0> --papers N --json
```

Assert the **opus / main** bucket's cost per paper is near zero (target **< $0.20/paper** — dispatch +
one `rebuild_index.py`, no summary/MOC reads). If it spikes, classification or filing has slid back
onto the Opus orchestrator — the exact regression this design prevents. Note the measurement gotchas
in the skill's `## Benchmarking` section: sub-agent (Sonnet) cost lands in the harness `tasks/*.output`
transcripts, not the project `*.jsonl`, so a project-dir report shows the orchestrator thread only —
which is precisely the number this gate wants.

## Maintaining the golden set

- Every paper must be in Paperclip (`cat /papers/arx_<id>/meta.json`), or the eval can't fetch it.
  If Paperclip coverage changes, swap in an equivalent classic with an equally clear expected topic.
- When the Library topic set changes (a split, a new topic), re-check that each `expected_topics`
  entry still names a real topic-folder and still reflects the right method-first home.
- Keep the out-of-scope gate case: without it, a sub-agent that stamps *everything* would score 100%.
