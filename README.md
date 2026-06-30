# SHL Conversational Assessment Recommender

A production-grade AI hiring assistant for SHL Labs that turns a recruiter's brief into a grounded, explainable shortlist of SHL assessments through natural conversation.
Built as a **dark-mode-first enterprise AI product** with a TanStack Start/React frontend and a **FastAPI + RAG backend** that does not hallucinate — every recommendation is verified against the SHL catalog.
> Live demo 
---
## What it does
- **Conversational discovery:** asks up to 2 focused clarifying questions, then recommends assessments from the SHL catalog.
- **Hybrid retrieval:** dense (FAISS `all-MiniLM-L6-v2`) + sparse (domain-aware BM25) + RRF fusion + cross-encoder rerank.
- **Consultant-style agent:** intent routing, slot-confidence tracking, refinement, and comparison modes.
- **Grounded explanations:** LLM (Gemini 2.5 Flash) is only allowed to explain and reason about IDs already retrieved and verified.
- **Compare & save:** side-by-side comparison table with shareable URLs and persistent local selections.
- **Production-ready:** structured JSON logging, request IDs, rate limiting, error taxonomy, Docker, CI/CD, prompt-injection defense.
---
## Tech stack
| Layer | Tech |
| --- | --- |
| Frontend | React 19, TypeScript, TanStack Start/Router, Tailwind CSS v4, shadcn/ui, Framer Motion, Lucide |
| Backend | Python 3.12, FastAPI, Pydantic v2, Uvicorn |
| Retrieval | FAISS-CPU, sentence-transformers, BM25 (rank-bm25), RRF, cross-encoder reranker (MS-MARCO-MiniLM) |
| LLM | Google Gemini 2.5 Flash via `google-generativeai` (extraction / clarification / explanation only) |
| Scraping | Playwright + BeautifulSoup (one-shot catalog build) |
| Testing | pytest, pytest-asyncio, behavioral replay tests |
| Ops | Docker + Docker Compose, GitHub Actions CI, JSON logging, token-bucket rate limiting |
---
## Quick start
### 1. Clone & run the backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Optional: add GEMINI_API_KEY for LLM explanations; otherwise deterministic fallback
uvicorn app.main:app --reload
```
Backend runs at `http://localhost:8000` with docs at `/docs`.
### 2. Run the frontend
In a new terminal from the project root:
```bash
bun install
cp .env.example .env
# Set VITE_API_BASE=http://localhost:8000
bun dev
```
Frontend runs at `http://localhost:8080`.
### 3. Try it
Send a message like: *“I need a Java backend assessment, 40 minutes, remote.”* The assistant will clarify, retrieve, rank, and explain.
---
## Architecture overview
```
Frontend (React + TanStack Start)
        │ POST /chat
        ▼
FastAPI
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│  CORS → Rate limiter → Request ID middleware                   │
└──────────────────────────────────────────────────────────────┘
        │  Depends(get_engine)
        ▼
┌──────────────────────────────────────────────────────────────┐
│  ConversationEngine.handle                                     │
│    • Safety scan (sanitize + injection + scope matchers)       │
│    • Intent classifier (initial / refine / compare / …)        │
│    • Slot extractor → SessionMemory                            │
│    • Clarifier (≤1 question/turn, ≤2/session, ≤8 turns)       │
│    • HybridRetriever (FAISS + BM25 + RRF + rerank)            │
│    • Ranker (deterministic, slot-aware)                        │
│    • Gemini explainer (reasons only, never reorders)           │
│    • JSON validator + one repair pass                          │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
ChatResponse (frozen Pydantic schema)
```
Full system diagram, module map, error taxonomy, and design rationale are in [`backend/ARCHITECTURE.md`](./backend/ARCHITECTURE.md).
---
## API example
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-1",
    "messages": [{"role": "user", "content": "Senior Java backend engineer, 45 min max, remote friendly."}],
    "mode": "recommend",
    "compare_ids": []
  }'
```
Response includes `reply`, `recommendations`, `safety` flags, `can_compare`, and `session_id`.
---
## Evaluation
The retrieval pipeline was evaluated on the full 377-assessment SHL catalog against 10 sample hiring conversations.
| Metric | v1 Baseline | v2 Full Pipeline | Δ |
| --- | --- | --- | --- |
| MRR@10 | 0.740 | **0.833** | +12.6% |
| Recall@5 | 0.366 | **0.427** | +0.061 |
| Confidence | 0.493 | **0.570** | +0.077 |
Ablation and methodology are in [`backend/EVAL.md`](./backend/EVAL.md).
---
## Testing
```bash
# Backend — 29 offline tests (includes all 10 conversation replays)
cd backend
pytest -q
# Retrieval ablation
cd backend
python -m eval.harness --mode ablation
# Frontend typecheck
bun run build
```
---
## Deployment
### Frontend
Deploy via Lovable: click **Publish** in the editor. The published site can be pointed to a custom domain.
### Backend
Deploy the `backend` folder to any container host. Example for Render:
1. Push the repo to GitHub.
2. Create a new **Web Service** on Render, connect the repo.
3. Set **Root Directory** to `backend`.
4. Use **Docker** runtime (the included `Dockerfile` handles everything).
5. Set environment variables in Render:
   - `GEMINI_API_KEY`
   - `ALLOWED_ORIGINS=https://your-frontend-domain.com`
A `render.yaml` blueprint can be added if you want one-click provisioning.
---
## Project structure
```
.
├── src/                      # TanStack Start frontend
│   ├── components/           # UI components (chat, assessments, layout)
│   ├── hooks/                # useChat, useLocalSet, theme, mobile
│   ├── routes/               # File-based routes
│   ├── services/             # API clients (chat-api, assessments)
│   └── styles.css            # Tailwind v4 theme + glass utilities
├── backend/                  # FastAPI backend
│   ├── app/                  # Main application
│   ├── tests/                # pytest suite
│   ├── eval/                 # Retrieval evaluation harness
│   ├── data/                 # SHL catalog JSON
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── ARCHITECTURE.md
│   ├── EVAL.md
│   └── README.md
├── .github/workflows/        # CI/CD
└── README.md
```
---

## License
Internal submission for SHL Labs internship evaluation. Not open-source licensed.
