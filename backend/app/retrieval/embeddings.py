from __future__ import annotations

from functools import lru_cache

import numpy as np


@lru_cache(maxsize=1)
def get_encoder(model_name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def encode(texts: list[str], model_name: str) -> np.ndarray:
    enc = get_encoder(model_name)
    vecs = enc.encode(texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    return vecs.astype("float32")
