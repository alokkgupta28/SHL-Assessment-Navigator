"""Confidence-based clarification gate.

Rules enforced here:
- At most ONE question per turn (single `?`).
- At most TWO clarifications per session.
- Never ask within the last turn before the 8-turn cap.
- Never ask the same slot-group twice in a row.
- Only ask if a decision-critical slot is missing or below confidence.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..schemas import ConversationState
from .slots import CLARIFYING_QUESTIONS, SlotMeta, critical_gap

MAX_CLARIFICATIONS = 2
TURN_HARD_CAP = 8
CONFIDENCE_THRESHOLD = 0.5


@dataclass
class Clarification:
    need: bool
    question: str | None = None
    slot_key: str | None = None


def decide(
    state: ConversationState,
    meta: SlotMeta,
    *,
    turn_count: int,
    clarifications_asked: int,
    last_question_slot: str | None,
    has_any_recommendations: bool,
) -> Clarification:
    # Budget exhausted
    if clarifications_asked >= MAX_CLARIFICATIONS:
        return Clarification(False)
    # Don't ask on the final allowed turn — commit instead.
    if turn_count >= TURN_HARD_CAP - 1 and has_any_recommendations:
        return Clarification(False)

    gap = critical_gap(state, meta, threshold=CONFIDENCE_THRESHOLD)
    if gap is None:
        return Clarification(False)
    if gap == last_question_slot:
        # Asked already — don't loop.
        return Clarification(False)
    q = CLARIFYING_QUESTIONS.get(gap)
    if not q:
        return Clarification(False)
    # Enforce single-question rule defensively.
    if q.count("?") != 1:
        q = q.split("?")[0].strip() + "?"
    return Clarification(True, q, gap)
