from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..schemas import ChatResponse
import traceback
from ..observability.logging import get_logger

log = get_logger("llm.validator")


def coerce_response(payload: dict[str, Any]) -> ChatResponse:
    try:
        log.info("coerce_attempt", extra={"payload_keys": list(payload.keys())})
        return ChatResponse.model_validate(payload)
    except ValidationError:
        # Repair: drop unknown keys, fill required defaults.
        log.warning("coerce_validation_error", extra={"errors": True})
        tb = traceback.format_exc()
        log.error("coerce_validation_traceback", extra={"traceback": tb})
        safe = {
            "session_id": str(payload.get("session_id", "")),
            "reply": str(payload.get("reply", "")),
            "need_clarification": bool(payload.get("need_clarification", False)),
            "clarifying_question": payload.get("clarifying_question"),
            "recommendations": payload.get("recommendations") or [],
            "comparison": payload.get("comparison"),
            "state": payload.get("state") or {},
            "safety": payload.get("safety") or {"blocked": False, "reason": None},
        }
        log.info("coerce_repair", extra={"safe_keys": list(safe.keys())})
        return ChatResponse.model_validate(safe)
