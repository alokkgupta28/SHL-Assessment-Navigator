#!/usr/bin/env python3
"""Build FAISS index and embeddings.npy for offline retrieval.

Usage:
  python scripts/build_index.py [--force] [--model MODEL]

This script is idempotent by default: if `data/faiss.index` and
`data/embeddings.npy` exist it will skip work unless `--force` is
provided.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import numpy as np

# Make backend importable
# If this script lives at `backend/scripts/build_index.py` then:
#   HERE    -> <repo>/backend/scripts
#   BACKEND -> <repo>/backend
#   REPO    -> <repo>
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.catalog.loader import load_catalog
from app.retrieval.embeddings import encode
from app.retrieval.faiss_index import FaissIndex
from app.retrieval.hybrid import HybridRetriever
from app.config import get_settings


def build(catalog_path: Path, out_dir: Path, model_name: str, force: bool = False):
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "faiss.index"
    emb_path = out_dir / "embeddings.npy"
    if index_path.exists() and emb_path.exists() and not force:
        print("faiss.index and embeddings.npy already exist — use --force to rebuild")
        return

    print(f"Loading catalog from {catalog_path}")
    catalog = load_catalog(catalog_path)
    # Reuse the same corpus text formatting as the runtime retriever to
    # guarantee identical embeddings.
    corpus = [HybridRetriever._corpus_text(a) for a in catalog]
    if not corpus:
        raise SystemExit("Catalog empty or not found — aborting")

    print(f"Encoding {len(corpus)} documents with model {model_name}")
    vecs = encode(corpus, model_name)
    vecs = vecs.astype("float32")

    print(f"Saving embeddings to {emb_path}")
    np.save(str(emb_path), vecs)

    print("Building FAISS index")
    idx = FaissIndex(vecs)
    try:
        import faiss

        faiss.write_index(idx.index, str(index_path))
        print(f"Wrote FAISS index to {index_path}")
    except Exception as e:
        print("Warning: failed to write FAISS index:", e)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="Rebuild index even if files exist")
    p.add_argument("--model", type=str, default=None, help="Embedding model name (overrides settings)")
    args = p.parse_args()

    settings = get_settings()
    model = args.model or settings.embedding_model
    catalog_path = (BACKEND / settings.catalog_path).resolve()
    out_dir = (BACKEND / "data").resolve()
    build(catalog_path, out_dir, model, force=args.force)


if __name__ == "__main__":
    main()
