from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..schemas import ChatResponse


def coerce_response(payload: dict[str, Any]) -> ChatResponse:
    try:
        return ChatResponse.model_validate(payload)
    except ValidationError:
        # Repair: drop unknown keys, fill required defaults.
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
        return ChatResponse.model_validate(safe)
