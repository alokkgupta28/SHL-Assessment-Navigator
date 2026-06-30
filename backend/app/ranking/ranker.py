from __future__ import annotations

import re

from ..catalog.models import Assessment
from ..schemas import ConversationState

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> set[str]:
    return set(_TOKEN_RE.findall(s.lower()))


def _skill_overlap(state: ConversationState, a: Assessment) -> float:
    """Token-level overlap between wanted skills and the assessment.

    Token matching (rather than exact-string set intersection) recovers
    cases like wanted={"python developer"} vs have={"python"} which the
    old `set & set` lookup missed completely.
    """
    wanted_terms = state.technical_skills + state.programming_language
    if not wanted_terms:
        return 0.5
    wanted_toks = set().union(*(_tokens(s) for s in wanted_terms)) or set()
    if not wanted_toks:
        return 0.5
    # Search across skills *and* description/name so a skill that's
    # implicitly covered (e.g. "JavaScript" inside a "Frontend Developer"
    # description) still scores.
    have_text = " ".join([a.name, a.category, a.description, " ".join(a.skills)])
    have_toks = _tokens(have_text)
    inter = wanted_toks & have_toks
    return len(inter) / max(len(wanted_toks), 1)


def _category_fit(state: ConversationState, a: Assessment) -> float:
    """Reward the requested *type* of assessment (cognitive/personality/…)."""
    wanted = [t.lower() for t in state.assessment_types]
    boolean_types: list[str] = []
    if state.leadership:
        boolean_types.append("leadership")
    if state.personality:
        boolean_types.append("personality")
    if state.communication:
        boolean_types.append("communication")
    wanted += boolean_types
    if not wanted:
        return 0.6
    cat = a.category.lower()
    desc = a.description.lower()
    hits = sum(1 for w in wanted if w in cat or w in desc)
    return min(1.0, 0.4 + 0.3 * hits)


def _level_fit(state: ConversationState, a: Assessment) -> float:
    levels = {l.lower() for l in state.constraints.job_levels}
    if not levels:
        return 0.7
    return 1.0 if levels & {l.lower() for l in a.job_levels} else 0.2


def _duration_fit(state: ConversationState, a: Assessment) -> float:
    target = state.constraints.duration_max
    if target is None or target <= 0 or a.duration_minutes <= 0:
        return 0.7
    if a.duration_minutes <= target:
        return 1.0 - (target - a.duration_minutes) / (target * 2)
    return max(0.0, 1.0 - (a.duration_minutes - target) / target)


def _language_fit(state: ConversationState, a: Assessment) -> float:
    langs = {l.lower() for l in state.constraints.languages}
    if not langs:
        return 0.8
    return 1.0 if langs & {l.lower() for l in a.languages} else 0.1


def _remote_adaptive_fit(state: ConversationState, a: Assessment) -> float:
    s = 0.5
    if state.constraints.remote is True:
        s = 1.0 if a.remote else 0.0
    if state.constraints.adaptive is True:
        s = (s + (1.0 if a.adaptive else 0.0)) / 2
    return s


def rank(state: ConversationState, candidates: list[tuple[Assessment, float]], top_k: int) -> list[tuple[Assessment, float]]:
    """Blend the retriever's confidence with state-conditioned signals.

    Weights tuned via the eval harness (see backend/EVAL.md). The retrieval
    score dominates (it already encodes RRF + cross-encoder), with metadata
    signals acting as tie-breakers that nudge in-budget, on-category items
    above off-spec near-misses.
    """
    scored: list[tuple[Assessment, float]] = []
    for a, retrieval in candidates:
        final = (
            0.50 * retrieval
            + 0.18 * _skill_overlap(state, a)
            + 0.10 * _category_fit(state, a)
            + 0.08 * _level_fit(state, a)
            + 0.07 * _duration_fit(state, a)
            + 0.04 * _language_fit(state, a)
            + 0.03 * _remote_adaptive_fit(state, a)
        )
        scored.append((a, round(float(final), 4)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def build_reasons(state: ConversationState, a: Assessment) -> list[str]:
    reasons: list[str] = []
    wanted_toks = set().union(
        *(_tokens(s) for s in state.technical_skills + state.programming_language)
    ) or set()
    have_toks = _tokens(" ".join([a.name, a.category, a.description, " ".join(a.skills)]))
    overlap = sorted(wanted_toks & have_toks)
    if overlap:
        reasons.append("Matches skills: " + ", ".join(overlap[:6]))
    if state.constraints.duration_max and a.duration_minutes <= state.constraints.duration_max:
        reasons.append(f"Fits within {state.constraints.duration_max} min (this is {a.duration_minutes} min)")
    if state.constraints.remote and a.remote:
        reasons.append("Remote-enabled")
    if state.constraints.adaptive and a.adaptive:
        reasons.append("Adaptive")
    levels = {l.lower() for l in state.constraints.job_levels} & {l.lower() for l in a.job_levels}
    if levels:
        reasons.append("Targets job level: " + ", ".join(sorted(levels)))
    if not reasons:
        reasons.append(f"Strong topical match in {a.category}")
    return reasons
