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

    @classmethod
    def load(cls, path: str | "os.PathLike[str]") -> "FaissIndex":
        """Load a FAISS index from disk without requiring the original vectors.

        This avoids instantiating heavy embedding models at startup — the
        index is read directly with `faiss.read_index` and wrapped in the
        same `FaissIndex` interface.
        """
        import faiss
        import os

        idx = faiss.read_index(str(path))
        inst = cls.__new__(cls)
        inst.index = idx
        # IndexFlat stores its dimension as attribute `d`.
        dim = getattr(idx, "d", None)
        try:
            inst.dim = int(dim) if dim is not None else 0
        except Exception:
            inst.dim = 0
        return inst
