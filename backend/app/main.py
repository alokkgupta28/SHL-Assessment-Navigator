"""FastAPI application entry-point.

Wiring only — no business logic lives here. The conversation engine and
its collaborators are constructed once in the lifespan and resolved via
``app/deps.py``.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .deps import EngineDep, build_container, get_container
from .llm.validator import coerce_response
from .observability import middleware as obs_middleware
from .observability.context import set_session_id
from .observability.errors import install_handlers
from .observability.logging import configure as configure_logging, get_logger
from .schemas import ChatRequest, ChatResponse, HealthResponse

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import time as _t
    configure_logging()
    app.state.started_at = _t.monotonic()
    app.state.container = build_container()
    try:
        yield
    finally:
        log.info("shutdown")
        app.state.container = None


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()


    app = FastAPI(
        title="SHL Assessment Recommender",
        version="1.1.0",
        lifespan=lifespan,
        # Tight default body cap; chat payloads are conversational, not bulk.
        openapi_url="/openapi.json",
    )
    # Temporary early middleware: log incoming Origin and whether it's allowed.
    # This runs before CORSMiddleware so we can observe the raw header the app sees.
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    class OriginLoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            try:
                origin = request.headers.get("origin")
                allowed = origin in settings.origins if origin else False
                log.info("origin_seen", extra={"origin": origin, "allowed": allowed})
            except Exception:
                log.exception("origin_logging_failed")
            return await call_next(request)

    app.add_middleware(OriginLoggingMiddleware)

    # CORS: explicit allow-list only. Refuse to fall back to "*" — that would
    # break the published-site security model and allow any origin to call /chat.
    if not settings.origins:
        log.warning("cors_no_origins_configured")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type", "x-request-id"],
        expose_headers=["x-request-id"],
        allow_credentials=False,
        max_age=600,
    )
    # Diagnostic startup log for CORS settings (temporary)
    try:
        log.info(
            "CORS CONFIG",
            extra={
                "allowed_origins_raw": settings.allowed_origins,
                "allowed_origins_parsed": settings.origins,
                "allowed_methods": ["GET", "POST", "OPTIONS"],
                "allowed_headers": ["content-type", "x-request-id"],
            },
        )
    except Exception:
        log.exception("cors_config_log_failed")
    obs_middleware.install(app, rate_per_minute=settings.rate_limit_per_minute,
                           burst=settings.rate_limit_burst)
    install_handlers(app)

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        import time as _t
        container = getattr(app.state, "container", None)
        started = getattr(app.state, "started_at", None)
        uptime = round(_t.monotonic() - started, 2) if started else 0.0
        return HealthResponse(
            status="ok" if container else "starting",
            catalog_size=container.catalog_size if container else 0,
            model=settings.gemini_model,
            uptime_seconds=uptime,
        )

    @app.get("/ready", tags=["meta"])
    def ready():
        """Kubernetes-style readiness probe — 503 until the container is built."""
        container = getattr(app.state, "container", None)
        if container is None or container.catalog_size == 0:
            from fastapi.responses import JSONResponse
            return JSONResponse({"ready": False}, status_code=503)
        return {"ready": True, "catalog_size": container.catalog_size}

    @app.get("/metrics", tags=["meta"])
    def metrics():
        """Lightweight operational metrics. Not Prometheus — small JSON for
        debugging and dashboards. Swap for prometheus_client when scaling out.
        """
        import time as _t
        container = getattr(app.state, "container", None)
        started = getattr(app.state, "started_at", None)
        sessions = 0
        if container is not None:
            store = getattr(container.engine, "sessions", None)
            sessions = len(store) if store is not None else 0
        return {
            "uptime_seconds": round(_t.monotonic() - started, 2) if started else 0.0,
            "catalog_size": container.catalog_size if container else 0,
            "active_sessions": sessions,
            "llm_enabled": bool(container and container.llm is not None),
            "version": "1.1.0",
        }


    @app.post("/chat", response_model=ChatResponse, tags=["chat"])
    async def chat(req: ChatRequest, engine: EngineDep) -> ChatResponse:
        # The conversation engine and the underlying Gemini SDK are
        # synchronous and CPU/IO-bound; running them on the event loop
        # would block every other request. Offload to the threadpool.
        from starlette.concurrency import run_in_threadpool
        import traceback
        import sys as _sys
        import os as _os

        pid_before = _os.getpid()
        log.info("chat_invoke", extra={"session_id": req.session_id, "pid_before": pid_before})

        set_session_id(req.session_id)
        try:
            log.info("before_engine_handle", extra={"session_id": req.session_id})
            pid_mid_before = _os.getpid()
            log.info("pid_before_handle", extra={"pid": pid_mid_before})
            raw = await run_in_threadpool(engine.handle, req)
            pid_mid_after = _os.getpid()
            log.info("after_engine_handle", extra={"session_id": req.session_id, "pid_after": pid_mid_after, "raw_type": type(raw).__name__})
        except Exception as exc:  # noqa: BLE001 - we need to log then re-raise
            log.exception("engine_handle_exception", extra={"session_id": req.session_id, "pid": _os.getpid()})
            # log full traceback
            tb = traceback.format_exc()
            log.error("engine_handle_traceback", extra={"traceback": tb})
            raise

        # 3) Before raw.model_dump()
        try:
            log.info("before_model_dump", extra={"session_id": req.session_id})
            dumped = raw.model_dump()
            log.info("after_model_dump", extra={"session_id": req.session_id, "dump_keys": list(dumped.keys())})
        except Exception:
            log.exception("model_dump_exception", extra={"session_id": req.session_id})
            raise

        # 5) Before coerce_response()
        try:
            log.info("before_coerce_response", extra={"session_id": req.session_id})
            final = coerce_response(dumped)
            log.info("after_coerce_response", extra={"session_id": req.session_id, "final_type": type(final).__name__})
        except Exception:
            log.exception("coerce_response_exception", extra={"session_id": req.session_id})
            # re-raise so FastAPI can surface 500/502 as appropriate
            raise

        try:
            pid_after = _os.getpid()
            log.info("before_return", extra={"session_id": req.session_id, "pid_after": pid_after})
            return final
        except Exception:
            log.exception("return_exception", extra={"session_id": req.session_id})
            raise


    # Temporary diagnostic endpoint to inspect CORS runtime configuration.
    @app.get("/debug/cors")
    def debug_cors():
        return {
            "allowed_origins_raw": settings.allowed_origins,
            "allowed_origins_parsed": settings.origins,
            "allowed_methods": ["GET", "POST", "OPTIONS"],
            "allowed_headers": ["content-type", "x-request-id"],
        }


    return app


app = create_app()


# Re-export for backwards compatibility with anything reaching for `state`.
def _legacy_state_proxy():  # pragma: no cover - thin shim
    return get_container  # type: ignore[return-value]
