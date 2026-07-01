# syntax=docker/dockerfile:1.7
# ----- builder ------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ----- runtime ------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    HF_HOME=/app/data/.cache/hf \
    SENTENCE_TRANSFORMERS_HOME=/app/data/.cache/st

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 ca-certificates curl tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app
COPY --from=builder /install /usr/local
## Prefer explicit copy of prebuilt retrieval artifacts if present so
## the runtime image does not attempt to build them.
COPY --chown=app:app data/faiss.index /app/data/faiss.index
COPY --chown=app:app data/embeddings.npy /app/data/embeddings.npy
COPY --chown=app:app . /app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers"]
