# SHL Assessment Navigator

Full-stack SHL assessment recommendation system with a TanStack Start frontend
and a production FastAPI backend.

The backend turns a hiring brief into a grounded shortlist of SHL assessments
using hybrid retrieval (FAISS + BM25 + RRF + cross-encoder rerank), a
consultant-style conversation engine, and Gemini 2.5 Flash limited to
extraction, clarification, and explanation.

## Repository structure

- `backend/` FastAPI service, retrieval/ranking pipeline, tests, and evaluation harness.
- `src/` TanStack Start frontend (chat, compare, assessment browsing).

Backend architecture and deep technical notes are documented in:

- [backend/ARCHITECTURE.md](backend/ARCHITECTURE.md)

## Quickstart

### Backend (local)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Server: http://localhost:8000

### Frontend (local)

```bash
npm install
npm run dev
```

Set `VITE_API_BASE=http://localhost:8000` in the project root `.env` so the
frontend can call `POST /chat`.

## Backend API

- `GET /health` liveness + model/catalog metadata
- `GET /ready` readiness probe
- `POST /chat` conversational recommendation endpoint
- `GET /docs` OpenAPI UI

Request/response schemas are in `backend/app/schemas.py`.

## Docker

```bash
cd backend
docker compose up --build
```

## Testing

```bash
cd backend
pytest -q
python -m eval.harness --mode ablation
```

Latest backend evaluation notes are in:

- [backend/EVAL.md](backend/EVAL.md)
