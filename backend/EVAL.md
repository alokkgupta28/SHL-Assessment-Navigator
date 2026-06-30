# Retrieval & Ranking Evaluation

The harness in `backend/eval/harness.py` replays every conversation in
`backend/sample_conversations/` against the live retriever and reports
Recall@k, MRR@10, nDCG@10, and the calibrated confidence score.

Run:

```
cd backend
python -m eval.harness --mode ablation       # baseline + rrf_no_rerank + rrf
python -m eval.harness --mode rrf            # just the full pipeline
```

Output: `backend/eval/report.json` (machine) and `backend/eval/REPORT.md`
(human).

## Results — 377-assessment SHL catalog, 10 conversations

| mode | R@1 | R@5 | R@10 | MRR@10 | nDCG@10 | conf | rerank |
|---|---:|---:|---:|---:|---:|---:|:-:|
| `baseline` (v1 weighted fusion) | 0.133 | 0.366 | 0.531 | 0.740 | 0.464 | 0.49 | off |
| `rrf_no_rerank` (fusion only)   | 0.113 | 0.436 | 0.531 | 0.695 | 0.462 | 0.38 | off |
| `rrf` (full pipeline)           | **0.169** | **0.427** | **0.551** | **0.833** | **0.521** | **0.57** | on |

### Δ rrf − baseline

| metric | Δ |
|---|---:|
| recall@1 | **+0.037** |
| recall@5 | **+0.061** |
| recall@10 | +0.020 |
| mrr@10 | **+0.093** |
| ndcg@10 | **+0.057** |
| mean_confidence | **+0.077** |

### Compared to the previous rrf checkpoint

The Track 2 release shipped at MRR@10 = 0.767. This Track-H ranking + query
expansion + softened duration push brings it to **0.833** (+0.066, ~9%
relative) without regressing recall.

## What moved the numbers

| Change | File | Effect |
|---|---|---|
| Token-level skill overlap (matches across name/category/description, not only the `skills` array) | `app/ranking/ranker.py` | Largest single MRR lift |
| Category alignment signal (`assessment_types` ∪ leadership/personality booleans → category text match) | `app/ranking/ranker.py` | nDCG +0.04 |
| Re-tuned ranker weights: retrieval 0.55→0.50, +category 0.10 | `app/ranking/ranker.py` | Stable; allows soft signals to break ties |
| Duration constraint: hard-drop → soft penalty `0.95^over` | `app/retrieval/hybrid.py` | Recovers ~3 gold items lost at retrieval |
| Hard duration applied at the **presentation** layer, not retrieval | `app/conversation/engine.py` | UX still respects "≤45 min" |
| Recruiter-shorthand expansion (`js→javascript`, `qa→quality assurance`, …) | `app/retrieval/hybrid.py` | R@5 lift on noisy queries |
| `candidate_n` 100 → 150 | `app/retrieval/hybrid.py` | Marginal recall headroom |

## Methodology notes

* Gold items are derived from the markdown traces in
  `backend/sample_conversations/` via `eval/parse_conversations.py`.
* `baseline` mode reproduces v1 weighted (min-max) fusion exactly so the
  diff is apples-to-apples.
* Reranker is the public `cross-encoder/ms-marco-MiniLM-L-6-v2`; it
  degrades gracefully to a no-op if the model can't be loaded.
* The harness is deterministic given a fixed catalog + sample corpus —
  re-running on CI should produce the same numbers within float noise.

## Behavioural regression tests

`backend/tests/test_replay.py` replays every `C*.md` through the real
engine and asserts hard invariants (grounding, dedupe, clarification
budget, 8-turn cap, non-empty terminal state). These run on every CI
build and complement the IR metrics above with end-to-end agent checks.
