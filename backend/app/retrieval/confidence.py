"""Retrieval confidence estimation.

We expose a single ``[0, 1]`` confidence score per query so the
conversation engine can decide when to ask a clarifying question vs
commit to recommendations. The score blends three signals:

1. **Score gap** — how much the top hit dominates the next ``k-1``.
   A large gap means the system is sure; a flat distribution means the
   query is ambiguous. Computed as ``sigmoid((s1 - mean(s2..sk)) / scale)``.
2. **Ranker agreement** — the Jaccard overlap between the top-K of the
   dense and sparse rankers. High overlap = both views agree this is
   the right neighborhood of the catalog.
3. **Cross-encoder absolute score** — when available, the raw
   ``ms-marco`` logit on the top candidate, squashed through sigmoid.
   This catches the "all candidates fit poorly" case that gap+agreement
   cannot detect.

The three signals are averaged with weights tuned on the sample
conversations (see ``backend/eval``). Weights are intentionally close to
uniform — none of the signals is reliable enough on its own.
"""
from __future__ import annotations

import math


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def score_gap_confidence(scores: list[float], k: int = 5, scale: float = 0.15) -> float:
    if not scores:
        return 0.0
    head = scores[:k]
    if len(head) == 1:
        return _sigmoid(head[0] / scale)
    top = head[0]
    rest = sum(head[1:]) / (len(head) - 1)
    return _sigmoid((top - rest) / scale)


def agreement_confidence(dense_top: list[int], sparse_top: list[int]) -> float:
    if not dense_top or not sparse_top:
        return 0.0
    a, b = set(dense_top), set(sparse_top)
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def cross_encoder_confidence(top_score: float | None) -> float | None:
    if top_score is None:
        return None
    # ms-marco logits are roughly in [-11, +11]; squash.
    return _sigmoid(top_score)


def aggregate(
    gap: float,
    agreement: float,
    cross: float | None,
) -> float:
    if cross is None:
        return max(0.0, min(1.0, 0.55 * gap + 0.45 * agreement))
    return max(0.0, min(1.0, 0.4 * gap + 0.3 * agreement + 0.3 * cross))
