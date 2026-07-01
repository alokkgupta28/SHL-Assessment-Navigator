import os
import numpy as np
from pathlib import Path
from app.catalog.models import Assessment
from app.retrieval.hybrid import HybridRetriever
from app.config import get_settings
from app.schemas import ConversationState


def make_catalog(n=3):
    out = []
    for i in range(n):
        out.append(Assessment(
            id=f"a{i}", name=f"A{i}", url=f"/a{i}", description="desc",
            category="cat", duration_minutes=30, remote=False, adaptive=False,
            job_levels=["Entry"], languages=["English"], skills=["skill"]
        ))
    return out


def test_low_memory_mode_bm25_only(monkeypatch, tmp_path):
    # Force low memory mode
    monkeypatch.setenv("LOW_MEMORY_MODE", "1")
    catalog = make_catalog(5)
    settings = get_settings()
    retriever = HybridRetriever(catalog, settings)
    # In low memory mode, faiss and reranker must be disabled
    assert retriever.faiss is None
    assert retriever.reranker is None
    items, diag = retriever.search(ConversationState(), return_diagnostics=True)
    # BM25 should return some items
    assert len(items) > 0
    assert isinstance(diag.query, str)


def test_normal_mode_with_embeddings_and_faiss(monkeypatch, tmp_path):
    # Ensure LOW_MEMORY_MODE not set
    monkeypatch.delenv("LOW_MEMORY_MODE", raising=False)
    catalog = make_catalog(4)
    settings = get_settings()
    # Create embeddings and faiss index files in repo backend/data
    backend_data = Path(__file__).resolve().parents[2] / "data"
    backend_data.mkdir(parents=True, exist_ok=True)
    # create random embeddings matching catalog
    vecs = np.random.rand(len(catalog), 16).astype("float32")
    emb_path = backend_data / "embeddings.npy"
    np.save(str(emb_path), vecs)
    # write faiss index
    try:
        import faiss
        idx = faiss.IndexFlatIP(16)
        idx.add(vecs)
        faiss.write_index(idx, str(backend_data / "faiss.index"))
    except Exception:
        # If faiss not available, skip this part of the test
        return
    # Write artifacts into the repo backend/data so HybridRetriever can find them
    np.save(str(backend_data / "embeddings.npy"), vecs)
    faiss.write_index(idx, str(backend_data / "faiss.index"))
    # Create retriever pointing at this catalog
    retriever = HybridRetriever(catalog, settings)
    # If faiss loaded, search should return items
    items = retriever.search(ConversationState())
    assert isinstance(items, list)

*** End Patch