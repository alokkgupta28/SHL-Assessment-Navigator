"""HTTP middleware: request IDs, structured access logs, token-bucket rate limit."""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .context import set_request_id, set_session_id
from .errors import RateLimited
from .logging import get_logger

log = get_logger("http")

REQUEST_ID_HEADER = "x-request-id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign / propagate ``x-request-id`` and emit a single access log line."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        set_request_id(rid)
        set_session_id("-")  # cleared per request; populated by handler if known
        start = time.perf_counter()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = rid
            return response
        finally:
            dur_ms = (time.perf_counter() - start) * 1000.0
            log.info(
                "http_request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": round(dur_ms, 2),
                    "client": request.client.host if request.client else "-",
                },
            )


@dataclass
class _Bucket:
    tokens: float
    updated: float


class TokenBucketRateLimiter(BaseHTTPMiddleware):
    """Per-client token bucket. In-process only — adequate for a single
    Uvicorn worker; swap for Redis if you horizontally scale.

    Defaults: 60 req/min sustained, burst of 20.
    """

    def __init__(
        self,
        app,
        *,
        rate_per_minute: int = 60,
        burst: int = 20,
        paths: tuple[str, ...] = ("/chat",),
    ) -> None:
        super().__init__(app)
        self.rate = rate_per_minute / 60.0
        self.burst = float(burst)
        self.paths = paths
        self.buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(tokens=self.burst, updated=time.monotonic())
        )

    def _client_key(self, request: Request) -> str:
        # Prefer the session id from the JSON body if available without
        # consuming the stream; otherwise fall back to remote IP.
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "anon"

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in self.paths:
            return await call_next(request)
        key = self._client_key(request)
        now = time.monotonic()
        b = self.buckets[key]
        elapsed = now - b.updated
        b.tokens = min(self.burst, b.tokens + elapsed * self.rate)
        b.updated = now
        if b.tokens < 1.0:
            retry = max(1, int((1.0 - b.tokens) / self.rate))
            log.warning("rate_limited", extra={"client": key, "retry_after_s": retry})
            err = RateLimited(retry_after_s=retry)
            return JSONResponse(
                status_code=429,
                headers={"retry-after": str(retry)},
                content={
                    "error": {
                        "code": err.code,
                        "message": err.message,
                        "details": {"retry_after_s": retry},
                    }
                },
            )
        b.tokens -= 1.0
        return await call_next(request)


def install(app: FastAPI, *, rate_per_minute: int = 60, burst: int = 20) -> None:
    # Order matters: RequestContext must be OUTERMOST so the rate-limit
    # rejection still carries a request_id header.
    if rate_per_minute > 0:
        app.add_middleware(TokenBucketRateLimiter, rate_per_minute=rate_per_minute, burst=burst)
    app.add_middleware(RequestContextMiddleware)

