"""Cross-encoder reranker.

A bi-encoder (FAISS over MiniLM embeddings) is fast but lossy — it
projects query and document into independent vectors. A *cross-encoder*
re-scores each (query, doc) pair jointly with full self-attention, which
is the single biggest precision lever in modern retrieval pipelines.

We only rerank the top ``N`` candidates produced by hybrid fusion (default
40). That keeps latency bounded (one forward pass per candidate) while
recovering most of the precision lift seen in MS-MARCO style benchmarks.

The reranker is **lazy** and **optional**: if ``sentence-transformers`` or
the model cannot be loaded (offline CI), :meth:`rerank` becomes an
identity pass-through. Pipelines that depend on it must handle the
no-op case (they always do — we return the same candidates in the same
order with their fused score preserved).
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_MODELS: dict[str, Any] = {}


def _load(model_name: str):
    try:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder(model_name)
        _MODELS[model_name] = model
        return model
    except Exception as exc:  # network / disk / missing model
        log.warning("cross-encoder unavailable (%s); reranking disabled", exc)
        return None


class CrossEncoderReranker:
    """Wrap a sentence-transformers ``CrossEncoder`` with safe fallback."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name

    @property
    def available(self) -> bool:
        return self.model_name in _MODELS

    def warmup(self) -> bool:
        return _load(self.model_name) is not None

    def rerank(
        self,
        query: str,
        candidates: list[tuple[int, float]],
        texts: list[str],
        top_n: int = 40,
        blend_alpha: float = 0.5,
    ) -> list[tuple[int, float]]:
        """Re-score the top ``top_n`` candidates and return them sorted.

        ``candidates`` is a list of ``(doc_idx, prior_score)`` pairs in
        the order produced by fusion. ``texts`` is the corpus indexed
        by ``doc_idx``. Returns a new list of ``(doc_idx, blended_score)``
        ordered best first; the tail beyond ``top_n`` is appended
        untouched so callers never lose candidates.

        We **blend** rather than overwrite: a cross-encoder is much
        stronger than a bi-encoder on short MS-MARCO style queries but
        can mis-rank long conversational queries. Blending with the
        fusion prior (``blend_alpha`` controls the CE weight) gives us
        the precision lift without throwing away the recall signal that
        BM25 + dense already agreed on.
        """
        model = _load(self.model_name)
        if model is None or not candidates:
            return candidates
        head = candidates[:top_n]
        tail = candidates[top_n:]
        pairs = [(query, texts[idx]) for idx, _ in head]
        try:
            scores = model.predict(pairs, show_progress_bar=False)
        except Exception as exc:
            log.warning("cross-encoder predict failed (%s); keeping prior order", exc)
            return candidates
        # Min-max normalise both signals over the head, then blend.
        prior = [p for _, p in head]
        ce = [float(s) for s in scores]
        def _mm(xs: list[float]) -> list[float]:
            lo, hi = min(xs), max(xs)
            if hi - lo < 1e-9:
                return [0.0 for _ in xs]
            return [(x - lo) / (hi - lo) for x in xs]
        prior_n = _mm(prior)
        ce_n = _mm(ce)
        blended = [
            (head[i][0], blend_alpha * ce_n[i] + (1 - blend_alpha) * prior_n[i])
            for i in range(len(head))
        ]
        blended.sort(key=lambda x: x[1], reverse=True)
        return blended + tail

