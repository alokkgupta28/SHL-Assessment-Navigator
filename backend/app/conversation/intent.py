"""Per-turn intent classification.

Deterministic-first so the system works fully offline. Used to route the
turn into the right branch of the engine (refine vs. fresh retrieve vs.
compare vs. confirm) instead of always re-running retrieval.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

Intent = Literal[
    "initial",          # first substantive ask, run full retrieval
    "refine_add",       # add X to the shortlist
    "refine_drop",      # drop / remove X from the shortlist
    "refine_replace",   # swap X for Y
    "refine_tighten",   # change constraints (shorter, remote, language)
    "explain_diff",     # "what's the difference between X and Y"
    "compare",          # explicit comparison request / mode
    "confirm",          # "perfect", "go with that", "locked", "thanks"
    "meta_question",    # asks about the assessments themselves, not changes
    "out_of_scope",     # legal/medical/regulatory advice etc.
]


@dataclass
class IntentResult:
    intent: Intent
    add_terms: list[str] = field(default_factory=list)
    drop_terms: list[str] = field(default_factory=list)
    replace_pairs: list[tuple[str, str]] = field(default_factory=list)


CONFIRM_PAT = re.compile(
    r"\b(perfect|great|sounds good|that works|confirmed|lock(?:ed|ing)? it in|"
    r"go ahead|go with (?:that|this|it)|use (?:that|this|it)|"
    r"final(?:ize|ised|ized)?|that(?:'s| is) (?:it|good|fine)|"
    r"thanks(?: a lot)?|thank you|all set|we're done)\b",
    re.IGNORECASE,
)
COMPARE_PAT = re.compile(r"\bcompare\b|\bside[- ]by[- ]side\b", re.IGNORECASE)
DIFF_PAT = re.compile(
    r"\b(what(?:'s| is) the difference|how (?:do|does) .{1,60}\s(?:differ|compare)|"
    r"difference between|vs\.?|versus)\b",
    re.IGNORECASE,
)
OUT_OF_SCOPE_PAT = re.compile(
    r"\b(legal(?:ly)? (?:required|obligat\w+)|regulatory|comply with .* law|"
    r"HIPAA (?:require|obligat)|GDPR (?:require|obligat)|medical advice|"
    r"diagnos\w+ )",
    re.IGNORECASE,
)
DROP_PAT = re.compile(
    r"\b(drop|remove|exclude|take out|get rid of|skip|without)\s+(?:the\s+)?([^.,;]+?)(?:[.,;]|$)",
    re.IGNORECASE,
)
ADD_PAT = re.compile(
    r"\b(add|include|also (?:add|include|consider)|throw in|toss in)\s+(?:the\s+)?([^.,;]+?)(?:[.,;]|$)",
    re.IGNORECASE,
)
REPLACE_PAT = re.compile(
    r"\b(replace|swap)\s+([^.,;]+?)\s+with\s+([^.,;]+?)(?:[.,;]|$)",
    re.IGNORECASE,
)
TIGHTEN_PAT = re.compile(
    r"\b(shorter|under\s+\d+\s*min|less than\s+\d+\s*min|remote only|"
    r"in\s+(?:spanish|french|german|portuguese|italian|chinese|japanese|hindi)|"
    r"adaptive|untimed)\b",
    re.IGNORECASE,
)
META_PAT = re.compile(
    r"\b(why|what does|what is|is .* the right|do (?:we|i) (?:really )?need|"
    r"is this (?:redundant|necessary)|how long|how much|tell me more)\b",
    re.IGNORECASE,
)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip(" .,:;-")


def classify(
    text: str,
    *,
    has_pinned: bool,
    mode_hint: str | None = None,
    compare_ids: list[str] | None = None,
) -> IntentResult:
    t = (text or "").strip()
    if not t:
        return IntentResult("initial")

    # Explicit comparison short-circuit
    if mode_hint == "compare" or (compare_ids and len(compare_ids) >= 2):
        return IntentResult("compare")
    if COMPARE_PAT.search(t):
        return IntentResult("compare")

    if OUT_OF_SCOPE_PAT.search(t):
        return IntentResult("out_of_scope")

    if DIFF_PAT.search(t):
        return IntentResult("explain_diff")

    # Structural refinements
    replaces = [(_clean(m.group(2)), _clean(m.group(3))) for m in REPLACE_PAT.finditer(t)]
    if replaces:
        return IntentResult("refine_replace", replace_pairs=replaces)

    drops = [_clean(m.group(2)) for m in DROP_PAT.finditer(t)]
    adds = [_clean(m.group(2)) for m in ADD_PAT.finditer(t)]
    if drops and adds:
        return IntentResult("refine_replace", replace_pairs=list(zip(drops, adds)))
    if drops:
        return IntentResult("refine_drop", drop_terms=drops)
    if adds:
        return IntentResult("refine_add", add_terms=adds)

    if has_pinned and TIGHTEN_PAT.search(t):
        return IntentResult("refine_tighten")

    # Short confirmation (only meaningful once we've shown a shortlist)
    if has_pinned and len(t) <= 80 and CONFIRM_PAT.search(t):
        return IntentResult("confirm")

    if has_pinned and META_PAT.search(t):
        return IntentResult("meta_question")

    return IntentResult("initial")
