"""Gemini wrapper with timeout, structured logging, and bounded retry."""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

from ..config import get_settings
from ..observability.logging import get_logger

log = get_logger(__name__)

DEFAULT_TIMEOUT_S = 12.0
MAX_ATTEMPTS = 2


class GeminiClient:
    """Thin wrapper around google-generativeai with JSON mode + retry.

    Failures are logged with structured context and raised so callers can
    degrade deterministically — they never silently return empty payloads.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ):
        s = get_settings()
        self.api_key = api_key or s.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model or s.gemini_model
        self.timeout_s = timeout_s
        self._client = None

    def _ensure(self):
        if self._client is not None:
            return
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        self._client = genai.GenerativeModel(
            self.model_name,
            generation_config={"response_mime_type": "application/json", "temperature": 0.2},
        )

    def json(self, system: str, user: str) -> dict[str, Any]:
        import time as _time
        self._ensure()
        prompt = f"{system}\n\n---\n{user}"
        prompt_chars = len(prompt)
        last_err: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            start = _time.perf_counter()
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self._client.generate_content,
                        prompt,
                        request_options={"timeout": self.timeout_s},
                    )
                    try:
                        resp = future.result(timeout=self.timeout_s)
                    except FuturesTimeoutError as e:
                        future.cancel()
                        raise TimeoutError(
                            f"Gemini request timed out after {self.timeout_s}s"
                        ) from e
                text = (resp.text or "").strip()
                if text.startswith("```"):
                    text = text.strip("`")
                    if text.lower().startswith("json"):
                        text = text[4:]
                latency_ms = round((_time.perf_counter() - start) * 1000, 2)
                log.info(
                    "gemini_call_ok",
                    extra={
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                        "prompt_chars": prompt_chars,
                        "response_chars": len(text),
                        "model": self.model_name,
                    },
                )
                return json.loads(text)
            except Exception as e:  # noqa: BLE001
                last_err = e
                latency_ms = round((_time.perf_counter() - start) * 1000, 2)
                log.warning(
                    "gemini_call_failed",
                    extra={
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                        "error": type(e).__name__,
                        "msg": str(e)[:200],
                    },
                )
        raise RuntimeError(f"Gemini call failed after {MAX_ATTEMPTS} attempts: {last_err}")

