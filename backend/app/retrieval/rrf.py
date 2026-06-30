"""Reciprocal Rank Fusion.

RRF is the de-facto baseline for combining heterogeneous ranked lists
(Cormack, Clarke & Buettcher, SIGIR 2009). Unlike weighted score fusion it
is **score-agnostic**: only positions matter, so it is robust to the very
different score distributions of FAISS cosine similarity (≈0–1) and BM25
(unbounded). It also degrades gracefully when one ranker is silent for a
document (the missing list contributes 0 instead of corrupting the fusion).

``k`` controls how aggressively low ranks are discounted. The original
paper recommends ``k=60`` and that value is reproduced across the IR
literature; we expose it for tuning but default to 60.
"""
from __future__ import annotations

from collections.abc import Iterable


def reciprocal_rank_fusion(
    ranked_lists: Iterable[list[int]],
    k: int = 60,
) -> dict[int, float]:
    """Fuse multiple ranked lists of document indices.

    Parameters
    ----------
    ranked_lists:
        Each inner list is an ordered sequence of doc indices, best first.
    k:
        Smoothing constant — higher values flatten the contribution of
        rank position. 60 is the standard.

    Returns
    -------
    dict mapping doc index -> fused RRF score (higher = better).
    """
    fused: dict[int, float] = {}
    for ranking in ranked_lists:
        for rank, doc_id in enumerate(ranking):
            if doc_id < 0:
                continue
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return fused
