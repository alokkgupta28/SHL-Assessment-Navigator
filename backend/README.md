# SHL Conversational Assessment Recommender — Backend

Production FastAPI service that turns a hiring brief into a grounded
shortlist of SHL assessments. Hybrid retrieval (FAISS + BM25 + RRF +
cross-encoder rerank), a consultant-style conversation engine, and
Gemini 2.5 Flash strictly limited to slot extraction / clarification /
explanation. No hallucinated recommendations — every id is verified
against the in-memory catalog.

See **[ARCHITECTURE.md](./ARCHITECTURE.md)** for the system diagram,
module map, error taxonomy, and design rationale.

---

## Quickstart (local)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set GEMINI_API_KEY (optional; falls back to deterministic)
uvicorn app.main:app --reload
```

Server: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

## Building Retrieval Index (offline)

The FAISS index and precomputed embeddings must be generated offline and
committed (or provided to your container) so the API does not initialize
heavy embedding models at startup. This repository includes a helper
script that produces `data/embeddings.npy` and `data/faiss.index`.

Run locally (developer machine) once and commit the output:

```bash
python scripts/build_index.py
# or specify a different model or force rebuild
python scripts/build_index.py --model sentence-transformers/all-MiniLM-L6-v2 --force
```

Files written:

- `backend/data/embeddings.npy` — normalized float32 embedding matrix
- `backend/data/faiss.index` — FAISS index built over the embeddings

Notes:

- The application will load `faiss.index` at startup and will NOT
  instantiate `SentenceTransformer` unless the index is missing and
  you explicitly enable startup building (not recommended).
- Re-run the script whenever `backend/data/shl_catalog.json` changes.

## Quickstart (Docker)

```bash
cd backend
docker compose up --build
# or:
docker build -t shl-recommender .
docker run -p 8000:8000 -e GEMINI_API_KEY=$GEMINI_API_KEY shl-recommender
```

First boot downloads the sentence-transformers + cross-encoder weights
(~150 MB) into a cache volume; subsequent boots are warm.

## Endpoints

| Method | Path     | Description |
| ------ | -------- | ----------- |
| GET    | `/health`| Liveness, catalog size, model name. |
| GET    | `/ready` | Readiness probe — 503 until the container is warm. |
| POST   | `/chat`  | Main conversational endpoint. Schema in `app/schemas.py` (frozen). |
| GET    | `/docs`  | OpenAPI (Swagger UI). |

The TanStack Start frontend in this repo calls `POST /chat` directly; set
`VITE_API_BASE=http://localhost:8000` in the project root `.env` (see
`.env.example`).


### Request

```json
{
  "session_id": "abc-123",
  "messages": [{"role": "user", "content": "Java backend hire, 40 min, remote."}],
  "mode": "recommend",
  "compare_ids": []
}
```

### Response envelope on success — see `ChatResponse` in `app/schemas.py`.

### Error envelope

```json
{ "error": { "code": "rate_limited", "message": "...", "request_id": "..." } }
```

Full taxonomy in `ARCHITECTURE.md`.

## Configuration

| Env var                 | Default                                     | Meaning |
| ----------------------- | ------------------------------------------- | ------- |
| `GEMINI_API_KEY`        | _(empty → deterministic fallback)_          | Google AI Studio key. |
| `GEMINI_MODEL`          | `gemini-2.5-flash`                          | LLM used for extraction / clarification / explanation. |
| `CATALOG_PATH`          | `data/shl_catalog.json`                     | Path to the SHL catalog JSON. |
| `ALLOWED_ORIGINS`       | `http://localhost:5173,http://localhost:8080` | CORS allowlist. |
| `LOG_LEVEL`             | `INFO`                                      | Root log level (JSON output). |
| `RATE_LIMIT_PER_MINUTE` | `60`                                        | Per-client `/chat` rate. |
| `RATE_LIMIT_BURST`      | `20`                                        | Token-bucket burst. |
| `TOP_K_RETRIEVAL`       | `25`                                        | Candidate pool before reranking. |
| `TOP_K_FINAL`           | `10`                                        | Returned shortlist size. |

## Operations

* **Request IDs.** Inbound `X-Request-Id` is honoured; otherwise generated. Echoed on every response and present on every log line.
* **Logging.** Single-line JSON to stdout. Each line carries `request_id`, `session_id`, `level`, `msg`, plus per-event fields.
* **Rate limiting.** In-process token bucket on `/chat`. Replace with Redis for multi-worker deployments.
* **Health check.** Dockerfile + compose ship `HEALTHCHECK` against `/health`.
* **Graceful degradation.** If Gemini is unreachable, the engine returns deterministic reasons rather than failing the request.

## Testing & evaluation

```bash
pytest -q                              # 29 offline tests, ~20s
pytest -q tests/test_replay.py         # behavioural replay of every C*.md
python -m eval.harness --mode ablation # baseline vs rrf_no_rerank vs rrf
```

See [`EVAL.md`](./EVAL.md) for the latest retrieval numbers. Headline:
MRR@10 **0.740 → 0.833** (+12.6% relative) versus the v1 weighted baseline
on the full 377-assessment catalog, with R@5 +0.061 and confidence +0.077.

CI: `.github/workflows/backend-ci.yml` runs ruff + pytest on push and
builds the Docker image.


## Project layout

```
backend/
├── app/
│   ├── main.py              # create_app(), lifespan, routes
│   ├── deps.py              # Container + FastAPI Depends
│   ├── config.py            # Pydantic Settings
│   ├── schemas.py           # frozen request/response models
│   ├── safety.py            # sanitize + injection / scope matchers
│   ├── observability/       # logging, request-id, errors, middleware
│   ├── catalog/             # loader + Assessment model
│   ├── retrieval/           # FAISS, BM25, RRF, reranker, hybrid, confidence
│   ├── ranking/             # deterministic ranker + reasons
│   ├── conversation/        # engine, intent, extractor, clarifier, refinement, slots
│   └── llm/                 # Gemini client, prompts, JSON validator
├── eval/                    # retrieval ablation harness
├── tests/                   # offline pytest suite
├── data/                    # catalog JSON (full + sample)
├── Dockerfile
├── docker-compose.yml
└── ARCHITECTURE.md
```
