# Retrieval evaluation

Catalog: **377** assessments · Cases: **10**

| mode | R@1 | R@5 | R@10 | MRR@10 | nDCG@10 | conf | rerank |
|---|---:|---:|---:|---:|---:|---:|:-:|
| `baseline` | 0.133 | 0.366 | 0.531 | 0.740 | 0.464 | 0.49 | off |
| `rrf_no_rerank` | 0.113 | 0.436 | 0.531 | 0.695 | 0.462 | 0.38 | off |
| `rrf` | 0.169 | 0.427 | 0.551 | 0.833 | 0.521 | 0.57 | on |

## Δ (rrf − baseline)

| metric | Δ |
|---|---:|
| recall@1 | +0.037 |
| recall@5 | +0.061 |
| recall@10 | +0.020 |
| mrr@10 | +0.093 |
| ndcg@10 | +0.057 |
| mean_confidence | +0.077 |
