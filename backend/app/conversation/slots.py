"""Internal slot tracking with confidence + provenance.

The public `ConversationState` schema must not change (assignment contract),
so confidence metadata lives here, in session memory, alongside the state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..schemas import ConversationState

# Slot names we track. Mirrors ConversationState fields a clarifier may probe.
SLOT_NAMES = (
    "role",
    "experience",
    "industry",
    "programming_language",
    "technical_skills",
    "assessment_types",
    "leadership",
    "communication",
    "personality",
    "duration_max",
    "remote",
    "adaptive",
    "languages",
    "job_levels",
)

Source = Literal["empty", "regex", "llm", "user_confirmed"]

# Confidence map per provenance — used to gate clarification.
SOURCE_CONF: dict[Source, float] = {
    "empty": 0.0,
    "regex": 0.55,
    "llm": 0.75,
    "user_confirmed": 0.95,
}

# Decision-critical slots — the consultant must know at least ONE of these
# before recommending. Asking about anything else is noise.
CRITICAL_SLOT_GROUPS: tuple[tuple[str, ...], ...] = (
    ("role", "industry"),                                    # who is this for
    ("technical_skills", "programming_language", "assessment_types"),  # what to measure
)


@dataclass
class SlotMeta:
    """Per-slot confidence + last-source map for the active session."""

    confidence: dict[str, float] = field(
        default_factory=lambda: {n: 0.0 for n in SLOT_NAMES}
    )
    source: dict[str, Source] = field(
        default_factory=lambda: {n: "empty" for n in SLOT_NAMES}
    )

    def bump(self, slot: str, src: Source) -> None:
        new = SOURCE_CONF[src]
        if new > self.confidence.get(slot, 0.0):
            self.confidence[slot] = new
            self.source[slot] = src


def _present(state: ConversationState, slot: str) -> bool:
    """Is this slot populated on the public state?"""
    c = state.constraints
    if slot == "duration_max":
        return c.duration_max is not None
    if slot == "remote":
        return c.remote is not None
    if slot == "adaptive":
        return c.adaptive is not None
    if slot == "languages":
        return bool(c.languages)
    if slot == "job_levels":
        return bool(c.job_levels)
    val = getattr(state, slot, None)
    if isinstance(val, list):
        return bool(val)
    return val is not None


def critical_gap(state: ConversationState, meta: SlotMeta, threshold: float = 0.5) -> str | None:
    """Return the slot-group label needing clarification, or None.

    A group "needs" clarification when NONE of its slots are present with
    confidence >= threshold. Returns a stable key for the question selector.
    """
    for group in CRITICAL_SLOT_GROUPS:
        ok = any(_present(state, s) and meta.confidence.get(s, 0.0) >= threshold for s in group)
        if not ok:
            return group[0]  # canonical key for this gap
    return None


# Canonical clarifying questions, one per critical-slot group.
CLARIFYING_QUESTIONS: dict[str, str] = {
    "role": "Who is this assessment for — what role, level, or candidate pool?",
    "technical_skills": "What capabilities should the assessment measure — specific skills, tools, or competencies?",
}
