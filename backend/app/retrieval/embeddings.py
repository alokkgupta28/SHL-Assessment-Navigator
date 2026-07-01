from __future__ import annotations

import numpy as np
from typing import Optional

# Global encoder instance. Intentionally not initialized on import to
# avoid pulling heavy models into request workers. Call
# `initialize_encoder(model_name)` in offline scripts or at startup if
# you accept the memory cost.
_encoder: Optional[object] = None


def initialize_encoder(model_name: str):
    """Initialize the sentence-transformers encoder.

    This must be called explicitly by offline scripts that need to
    generate embeddings (e.g. `scripts/build_index.py`). Runtime
    request handlers MUST NOT call this to avoid loading the model on
    first user request.
    """
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer(model_name)
    return _encoder


def has_encoder() -> bool:
    return _encoder is not None


def encode(texts: list[str], model_name: str) -> np.ndarray:
    """Encode texts using a pre-initialized encoder.

    Raises RuntimeError if the encoder has not been initialized. Call
    `initialize_encoder` from offline tooling (or explicit startup
    warmup) to populate the encoder.
    """
    if _encoder is None:
        raise RuntimeError("Encoder not initialized")
    vecs = _encoder.encode(texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    return vecs.astype("float32")
