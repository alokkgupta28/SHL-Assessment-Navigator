from __future__ import annotations

import numpy as np


class FaissIndex:
    def __init__(self, vectors: np.ndarray):
        import faiss
        self.dim = vectors.shape[1]
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(vectors)

    def search(self, query: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        if query.ndim == 1:
            query = query.reshape(1, -1)
        k = min(k, self.index.ntotal)
        scores, idx = self.index.search(query.astype("float32"), k)
        return scores[0], idx[0]
