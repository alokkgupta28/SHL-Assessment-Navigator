"""Hybrid retrieval: FAISS (dense) + BM25 (sparse) + RRF + cross-encoder.

Pipeline (per query):

    state ──► query string (slot-aware) ─┐
                                         ├─► FAISS top-N  ┐
                                         │                ├─► RRF fuse ─► metadata
                                         └─► BM25  top-N  ┘                 (soft penalty)
                                                                              │
                                                                              ▼
                                                                      cross-encoder
                                                                       rerank top-N
                                                                              │
                                                                              ▼
                                                                       (item, score)

Design choices, in order of impact:

* **RRF over weighted score fusion.** Dense and sparse scores live on
  incompatible scales (cosine sim vs unbounded BM25). Min-max normalising
  per query is fragile — a single outlier collapses the whole list to ~0.
  RRF only needs ranks, so it survives missing entries and score skew.
* **Soft metadata filters.** Hard-filtering on a constraint the user
  *mentioned* (e.g. "≤30 min") drops legitimate near-misses (a 31-minute
  assessment). We penalise instead and let ranking break ties. Hard
  filters are reserved for *contradictions* (wrong language family).
* **Cross-encoder rerank.** The biggest single precision lever; only run
  on the top ``rerank_n`` to keep latency O(N) in a small constant.
  Optional — pipeline degrades to fusion-only if the model isn't
  reachable.
* **Slot-aware query string.** A bare list of skill words misses the
  *type* signal ("personality", "cognitive", "leadership"). We add a
  small canonical phrase per slot so BM25 can light up category text
  even when the user never typed the category name.
* **Confidence as a first-class output.** Downstream code uses it to
  gate clarification. Built from score gap + ranker agreement +
  cross-encoder absolute score.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from ..catalog.models import Assessment
from ..config import Settings
from ..schemas import ConversationState
from .bm25 import BM25
from .confidence import (
    agreement_confidence,
    aggregate,
    cross_encoder_confidence,
    score_gap_confidence,
)
from .embeddings import encode, has_encoder
import traceback
from .faiss_index import FaissIndex
from .reranker import CrossEncoderReranker
from .rrf import reciprocal_rank_fusion
from pathlib import Path
import os
import time
from ..observability.logging import get_logger

log = get_logger("shl.retriever")

# Low-memory production mode disables dense retrieval and the reranker.
LOW_MEMORY_MODE = os.environ.get("LOW_MEMORY_MODE", "").lower() in ("1", "true", "yes")
if LOW_MEMORY_MODE:
    log.info("Running in LOW_MEMORY_MODE: dense retrieval and reranker disabled.")

# Canonical phrases injected when a slot is present — boosts BM25 recall
# on the assessment *type*, which assessment descriptions almost always
# use verbatim (e.g. "Personality & Behavior", "Cognitive Ability").
_SLOT_PHRASES = {
    "leadership": "leadership executive director manager",
    "communication": "communication interpersonal verbal",
    "personality": "personality behavior occupational opq",
    "cognitive": "cognitive ability aptitude verify reasoning",
    "knowledge": "knowledge skills technical",
}

# Lightweight, lossless query expansion. Keys are matched case-insensitively
# as whole tokens; the value is appended (not substituted) so original terms
# keep their IDF weight. Synonyms here are the ones that show up repeatedly
# in real recruiter language but mismatch the catalog wording.
_QUERY_SYNONYMS = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "qa": "quality assurance testing",
    "sre": "site reliability engineering devops",
    "fe": "frontend",
    "be": "backend",
    "ic": "individual contributor",
    "sde": "software developer engineer",
    "pm": "product manager",
    "tpm": "technical program manager",
}

# Common duration ceilings mentioned in natural language.
_DURATION_RE = re.compile(
    r"(?:under|less than|<=?|max|maximum|no more than|within)\s*(\d{1,3})\s*(?:min|mins|minutes)?",
    re.IGNORECASE,
)


def _expand_query(q: str) -> str:
    extras: list[str] = []
    for tok in re.findall(r"[A-Za-z]+", q):
        syn = _QUERY_SYNONYMS.get(tok.lower())
        if syn:
            extras.append(syn)
    return (q + " " + " ".join(extras)).strip() if extras else q



@dataclass
class RetrievalDiagnostics:
    """Per-query telemetry. Helpful for eval, logs, debugging UI."""

    query: str
    dense_top: list[int] = field(default_factory=list)
    sparse_top: list[int] = field(default_factory=list)
    fused_top: list[int] = field(default_factory=list)
    reranked_top: list[int] = field(default_factory=list)
    confidence: float = 0.0
    cross_encoder_used: bool = False


@dataclass
class RetrievedItem:
    assessment: Assessment
    score: float
    rank_dense: int | None = None
    rank_sparse: int | None = None
    rerank_score: float | None = None


class HybridRetriever:
    """Hybrid retriever with RRF fusion and cross-encoder reranking."""

    def __init__(
        self,
        catalog: list[Assessment],
        settings: Settings,
        *,
        enable_reranker: bool = True,
        rrf_k: int = 60,
        rerank_n: int = 40,
        candidate_n: int = 150,
    ):
        self.catalog = catalog
        self.settings = settings
        self.rrf_k = rrf_k
        self.rerank_n = rerank_n
        self.candidate_n = candidate_n
        self.corpus = [self._corpus_text(a) for a in catalog]
        # Compact text used by the cross-encoder. Cross-encoders are
        # trained on short MS-MARCO style "passages"; feeding them the
        # full BM25 corpus_text (which repeats fields and runs to ~500
        # chars) skews their scores. A focused "card" form gives much
        # better rerank precision.
        self.rerank_corpus = [self._rerank_text(a) for a in catalog]
        self.reranker = CrossEncoderReranker() if enable_reranker else None
        if not catalog:
            self.faiss = None
            self.bm25 = None
            return
        # Prefer a pre-built FAISS index to avoid heavy model initialization
        # at startup. The index and embeddings are expected at
        # `<repo>/backend/data/faiss.index` and `.../embeddings.npy`.
        backend_data = Path(__file__).resolve().parents[2] / "data"
        index_path = backend_data / "faiss.index"
        embeddings_path = backend_data / "embeddings.npy"

        # Try loading a matching prebuilt FAISS index first.
        if index_path.exists():
            try:
                candidate = FaissIndex.load(str(index_path))
                ntotal = getattr(candidate.index, "ntotal", None)
                if ntotal is not None and int(ntotal) == len(catalog):
                    self.faiss = candidate
                else:
                    # index doesn't match this catalog; ignore it and
                    # fall back to embeddings or building.
                    self.faiss = None
            except Exception:
                # If loading fails, continue to other fallback paths.
                self.faiss = None

        # If we didn't get a usable index, try embeddings or build.
        if getattr(self, "faiss", None) is None:
            # If precomputed embeddings exist, build the FaissIndex quickly
            if embeddings_path.exists():
                vecs = np.load(str(embeddings_path)).astype("float32")
                # Validate embeddings shape matches catalog
                if vecs.shape[0] != len(catalog):
                    # Mismatch — do not use these embeddings.
                    self.faiss = None
                else:
                    self.faiss = FaissIndex(vecs)
                    # persist index for future boots if possible
                    try:
                        import faiss

                        faiss.write_index(self.faiss.index, str(index_path))
                    except Exception:
                        pass
            else:
                # Building embeddings at startup is potentially memory-heavy.
                # Only allow it when explicitly enabled in local development
                # via the `BUILD_FAISS_INDEX_AT_STARTUP` env var.
                if os.environ.get("BUILD_FAISS_INDEX_AT_STARTUP", "").lower() in (
                    "1",
                    "true",
                    "yes",
                ):
                    vecs = encode(self.corpus, settings.embedding_model)
                    np.save(str(embeddings_path), vecs)
                    self.faiss = FaissIndex(vecs)
                    try:
                        import faiss

                        faiss.write_index(self.faiss.index, str(index_path))
                    except Exception:
                        pass
                else:
                    raise RuntimeError(
                        f"FAISS index not found at {index_path}. Run scripts/build_index.py to generate it."
                    )
        self.bm25 = BM25(self.corpus)


    # ------------------------------------------------------------------
    # Query construction
    # ------------------------------------------------------------------
    @staticmethod
    def _corpus_text(a: Assessment) -> str:
        """Indexed text for one assessment.

        Repeat the name (acts as a soft boost without abusing BM25 IDF)
        and include languages so a query like "Portuguese personality"
        can route by language even without a hard filter.
        """
        return " ".join([
            a.name, a.name,           # gentle name boost
            a.category,
            a.description,
            " ".join(a.skills),
            " ".join(a.job_levels),
            " ".join(a.languages),
        ])

    @staticmethod
    def _rerank_text(a: Assessment) -> str:
        """Compact, MS-MARCO style passage for the cross-encoder."""
        skills = ", ".join(a.skills[:8])
        desc = (a.description or "").strip()
        if len(desc) > 280:
            desc = desc[:277].rsplit(" ", 1)[0] + "…"
        return f"{a.name} — {a.category}. Skills: {skills}. {desc}".strip()



    @classmethod
    def _state_to_query(cls, state: ConversationState) -> str:
        parts: list[str] = []
        if state.role:
            parts.append(state.role)
        if state.experience:
            parts.append(state.experience)
        if state.industry:
            parts.append(state.industry)
        parts.extend(state.programming_language)
        parts.extend(state.technical_skills)
        parts.extend(state.assessment_types)
        if state.leadership:
            parts.append(_SLOT_PHRASES["leadership"])
        if state.communication:
            parts.append(_SLOT_PHRASES["communication"])
        if state.personality:
            parts.append(_SLOT_PHRASES["personality"])
        # Job levels matter for ranking *and* for retrieval (the catalog
        # text mentions them, e.g. "for Executive and Director roles").
        parts.extend(state.constraints.job_levels)
        return " ".join(p for p in parts if p).strip() or "assessment"

    # ------------------------------------------------------------------
    # Metadata filtering — *soft*, score-based
    # ------------------------------------------------------------------
    @staticmethod
    def _filter_penalty(a: Assessment, state: ConversationState) -> tuple[float, bool]:
        """Return ``(multiplier, hard_drop)``.

        Hard drops are reserved for *contradictions* — language mismatch when
        both sides are non-empty. Duration is treated as a **soft** budget
        (penalty that grows with the overshoot) rather than a guillotine,
        because a 32-minute assessment is usually fine for a "≤30 min"
        request and culling it costs recall — see the eval harness
        before/after for measured impact.
        """
        c = state.constraints
        mult = 1.0
        if c.duration_max and a.duration_minutes:
            over = a.duration_minutes - c.duration_max
            if over > 0:
                # 1-min over → 0.95, 10-min over → ~0.60, 30-min over → ~0.22
                mult *= max(0.2, 0.95 ** over)
        if c.remote is True and not a.remote:
            mult *= 0.7
        if c.adaptive is True and not a.adaptive:
            mult *= 0.85
        if c.languages and a.languages:
            wanted = {l.lower() for l in c.languages}
            have = {l.lower() for l in a.languages}
            if not (wanted & have):
                # No language overlap and we know what they want — hard drop.
                return 0.0, True
        if c.job_levels and a.job_levels:
            wanted = {l.lower() for l in c.job_levels}
            have = {l.lower() for l in a.job_levels}
            if not (wanted & have):
                mult *= 0.8
        return mult, False


    @classmethod
    def _infer_query_constraints(cls, raw_query: str, state: ConversationState) -> None:
        """Cheap regex extraction so the eval harness (which has no LLM)
        still benefits from constraint-aware filtering.

        Mutates ``state.constraints`` in place — only fills *unset* fields.
        """
        if state.constraints.duration_max is None:
            m = _DURATION_RE.search(raw_query or "")
            if m:
                try:
                    state.constraints.duration_max = int(m.group(1))
                except ValueError:
                    pass

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(
        self,
        state: ConversationState,
        k: int | None = None,
        *,
        raw_query: str | None = None,
        mode: str = "rrf",
        return_diagnostics: bool = False,
    ):
        if not self.catalog or self.faiss is None or self.bm25 is None:
            return ([], RetrievalDiagnostics(query="")) if return_diagnostics else []
        k = k or self.settings.top_k_retrieval
        if raw_query:
            self._infer_query_constraints(raw_query, state)
        query = raw_query or self._state_to_query(state)
        # Lossless synonym expansion (recruiter shorthand → catalog wording).
        query = _expand_query(query)


        n = len(self.catalog)
        candidate_n = min(self.candidate_n, n)

        # 1. Dense
        qvec = None
        d_scores = []
        d_idx = []
        dense_ranked = []
        dense_score_map = {}
        # Attempt dense retrieval only if an encoder has been initialized.
        if has_encoder():
            try:
                log.info("encode_before", extra={"query_len": len(query), "model": self.settings.embedding_model})
                t0_encode = time.perf_counter()
                qvec = encode([query], self.settings.embedding_model)[0]
                t1_encode = time.perf_counter()
                log.info("encode_after", extra={"elapsed_ms": int((t1_encode - t0_encode) * 1000)})
            except Exception as exc:  # noqa: BLE001
                tb = traceback.format_exc()
                log.error("encode_exception", extra={"type": type(exc).__name__, "repr": repr(exc), "traceback": tb})
                log.warning("Dense retrieval disabled because encoder unavailable.")
                qvec = None
        else:
            log.info("dense_disabled_no_encoder", extra={"reason": "encoder_not_initialized"})
            log.warning("Dense retrieval disabled because encoder unavailable.")

        if qvec is not None and getattr(self, "faiss", None) is not None:
            try:
                log.info("faiss_search_before", extra={"candidate_n": candidate_n})
                t0_faiss = time.perf_counter()
                d_scores, d_idx = self.faiss.search(qvec, candidate_n)
                t1_faiss = time.perf_counter()
                log.info("faiss_search_after", extra={"elapsed_ms": int((t1_faiss - t0_faiss) * 1000)})
                dense_ranked = [int(i) for i in d_idx if i >= 0]
                dense_score_map = {int(i): float(s) for s, i in zip(d_scores, d_idx) if i >= 0}
            except Exception as exc:  # noqa: BLE001
                tb = traceback.format_exc()
                log.error("faiss_search_exception", extra={"type": type(exc).__name__, "repr": repr(exc), "traceback": tb})
                log.warning("Dense retrieval disabled because faiss search failed.")
                dense_ranked = []
                dense_score_map = {}
        else:
            # No dense results; continue with BM25-only.
            dense_ranked = []
            dense_score_map = {}
        # dense_ranked and dense_score_map populated above when available

        # 2. Sparse
        bm25_scores = np.asarray(self.bm25.scores(query), dtype="float32")
        sparse_ranked = np.argsort(-bm25_scores)[:candidate_n].tolist()

        # 3. Fuse
        if mode == "weighted":
            fused_scores = self._weighted_fuse(dense_score_map, bm25_scores, n)
        else:
            fused_scores = reciprocal_rank_fusion(
                [dense_ranked, sparse_ranked], k=self.rrf_k
            )
        fused_ranked = sorted(fused_scores.keys(), key=lambda i: -fused_scores[i])

        # 4. Soft metadata filter
        filtered: list[tuple[int, float]] = []
        for doc_id in fused_ranked:
            mult, drop = self._filter_penalty(self.catalog[doc_id], state)
            if drop:
                continue
            filtered.append((doc_id, fused_scores[doc_id] * mult))
        filtered.sort(key=lambda x: -x[1])

        # Safety: never return an empty list when the unfiltered fusion
        # had hits. The conversation engine surfaces "no exact match"
        # commentary downstream.
        if not filtered:
            filtered = [(i, fused_scores[i]) for i in fused_ranked]

        # 5. Cross-encoder rerank (top-N only)
        cross_used = False
        cross_top_score: float | None = None
        if self.reranker and self.reranker.available:
            reranked = self.reranker.rerank(
                query, filtered, self.rerank_corpus, top_n=self.rerank_n,
                blend_alpha=0.4,
            )
            if reranked is not filtered:
                cross_used = True
                cross_top_score = reranked[0][1] if reranked else None
                filtered = reranked

        # 6. Confidence
        head_scores = [s for _, s in filtered[:5]]
        gap = score_gap_confidence(head_scores)
        agree = agreement_confidence(dense_ranked[:10], sparse_ranked[:10])
        ce_conf = cross_encoder_confidence(cross_top_score) if cross_used else None
        confidence = aggregate(gap, agree, ce_conf)

        top = filtered[:k]
        items = [(self.catalog[i], float(s)) for i, s in top]

        if return_diagnostics:
            diag = RetrievalDiagnostics(
                query=query,
                dense_top=dense_ranked[:k],
                sparse_top=sparse_ranked[:k],
                fused_top=[i for i, _ in filtered[:k]],
                reranked_top=[i for i, _ in top],
                confidence=confidence,
                cross_encoder_used=cross_used,
            )
            return items, diag
        return items

    # ------------------------------------------------------------------
    # Baseline fusion kept for A/B evaluation
    # ------------------------------------------------------------------
    @staticmethod
    def _weighted_fuse(
        dense_score_map: dict[int, float],
        bm25_scores: np.ndarray,
        n: int,
        alpha: float = 0.6,
    ) -> dict[int, float]:
        dense = np.zeros(n, dtype="float32")
        for i, s in dense_score_map.items():
            dense[i] = s
        lo, hi = float(dense.min()), float(dense.max())
        dense_n = (dense - lo) / (hi - lo) if hi - lo > 1e-9 else np.zeros_like(dense)
        lo, hi = float(bm25_scores.min()), float(bm25_scores.max())
        bm_n = (
            (bm25_scores - lo) / (hi - lo)
            if hi - lo > 1e-9
            else np.zeros_like(bm25_scores)
        )
        fused = alpha * dense_n + (1 - alpha) * bm_n
        return {int(i): float(fused[i]) for i in range(n)}

    def confidence(self, state: ConversationState, raw_query: str | None = None) -> float:
        """Public helper for the conversation engine."""
        _, diag = self.search(state, return_diagnostics=True, raw_query=raw_query)
        return diag.confidence
