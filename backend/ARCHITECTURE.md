# Architecture

Single-process FastAPI service. All long-lived collaborators are
constructed once in the lifespan and shared via dependency injection;
request handlers contain only thin wiring.

```
HTTP request
    │
    ▼
┌───────────────────────── middleware ─────────────────────────┐
│ CORS  →  TokenBucketRateLimiter  →  RequestContextMiddleware  │
│             (per-client, /chat)        (request_id, access log)│
└──────────────────────────────────────────────────────────────┘
    │  Depends(get_engine) → ConversationEngine
    ▼
┌─────────────────── ConversationEngine.handle ────────────────┐
│  Safety scan (sanitize → injection → out-of-scope)            │
│       │                                                       │
│       ▼                                                       │
│  Intent classifier (initial / refine_* / compare / …)         │
│       │                                                       │
│       ▼                                                       │
│  Slot extractor  ──▶  SessionMemory (slots + confidence)      │
│       │                                                       │
│       ▼                                                       │
│  Clarifier (≤1 question / turn, ≤2 / session, ≤8 turns)       │
│       │                                                       │
│       ▼                                                       │
│  HybridRetriever                                              │
│     ├─ FAISS dense  ─┐                                        │
│     ├─ BM25 sparse  ─┤── RRF fusion ── soft filters ──┐       │
│     │                 │                                 │       │
│     └─ Cross-encoder rerank (MS-MARCO-MiniLM)  ◀───────┘       │
│       │                                                       │
│       ▼                                                       │
│  Ranker (deterministic, slot-aware) → top-k                   │
│       │                                                       │
│       ▼                                                       │
│  Comparison engine (mode=compare)                             │
│       │                                                       │
│       ▼                                                       │
│  Gemini explainer (reasons only — never reorders)             │
│       │                                                       │
│       ▼                                                       │
│  Pydantic validator (one repair pass)                         │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
ChatResponse (frozen schema)
```

## Module map

| Layer            | Module                              | Responsibility |
| ---------------- | ----------------------------------- | -------------- |
| Entry            | `app.main`                          | `create_app`, lifespan, routes only. |
| DI               | `app.deps`                          | `Container`, `EngineDep`, `SettingsDep`. |
| Config           | `app.config`                        | Pydantic `Settings` from env / `.env`. |
| Schemas          | `app.schemas`                       | Frozen request/response models (validated). |
| Safety           | `app.safety`                        | Sanitization + injection / scope matchers. |
| Catalog          | `app.catalog.{loader,models}`       | Load + normalise SHL catalog. |
| Retrieval        | `app.retrieval.{embeddings,faiss_index,bm25,rrf,reranker,hybrid,confidence}` | Hybrid search. |
| Ranking          | `app.ranking.ranker`                | Deterministic scoring + reason synthesis. |
| Conversation     | `app.conversation.{engine,intent,extractor,clarifier,refinement,slots}` | Consultant-style orchestrator. |
| LLM              | `app.llm.{gemini,prompts,validator}` | Gemini client + prompt templates + JSON repair. |
| Observability    | `app.observability.{context,logging,errors,middleware}` | Request IDs, JSON logs, error taxonomy, rate limit. |

## Error taxonomy

Every expected error inherits `AppError` and is mapped to:

```json
{ "error": { "code": "<stable_code>", "message": "...", "request_id": "..." } }
```

| `code`               | HTTP | Meaning |
| -------------------- | ---- | ------- |
| `validation_error`   | 422  | Schema / field-level rejection (Pydantic). |
| `safety_blocked`     | 200  | Surfaced inside `ChatResponse.safety`. |
| `rate_limited`       | 429  | Token bucket exhausted; `Retry-After` set. |
| `not_ready`          | 503  | Lifespan still loading the container. |
| `catalog_unavailable`| 503  | Catalog failed to load. |
| `llm_unavailable`    | 503  | Gemini disabled / errored; engine falls back. |
| `retrieval_error`    | 500  | Retrieval pipeline crashed. |
| `internal_error`     | 500  | Unhandled exception; logged with stack. |

## Request ID

Inbound `X-Request-Id` is honoured; otherwise a 32-char hex id is
generated. The id is bound to a contextvar so it appears in every log
line emitted during the request and is echoed back as `X-Request-Id` on
the response.

## Rate limiting

In-process token bucket on `/chat` only, keyed on
`X-Forwarded-For` then remote IP. Defaults: 60 req/min sustained, burst
of 20 (`RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_BURST`). Adequate for one
Uvicorn worker; for multi-worker / horizontal scaling, swap the bucket
store for Redis.

## Prompt-injection defense

Layered:

1. **Sanitization** (`safety.sanitize`) strips control / zero-width
   characters and clamps message length before any matcher runs.
2. **Pattern matchers** block override attempts (`ignore previous`,
   fake `system:` turns, jailbreak personas) and out-of-scope topics
   (legal / medical / political / competitor catalogs).
3. **Prompt templates** (`llm.prompts`) instruct Gemini to recommend
   ONLY assessments from the supplied catalog ids; the validator
   re-checks every returned id against the in-memory catalog and drops
   hallucinations.

## Configuration

All settings come from environment variables (or `.env`). See
`.env.example`. Hot-reloadable values: none — restart on change.

## Testing

`pytest -q` runs offline. `conftest.py` points the loader at
`data/shl_catalog.sample.json` and unsets `GEMINI_API_KEY`, so tests
exercise the deterministic path. CI runs the same matrix on
Python 3.12.
