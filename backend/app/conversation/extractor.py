"""Slot extractor — produces a state update *and* per-slot provenance.

Deterministic regex always runs; the LLM (if configured) augments but never
replaces it. Returns both the new state and the set of slots that were
populated this turn (so the engine can bump confidence accordingly).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..llm.gemini import GeminiClient
from ..llm.prompts import EXTRACTOR_SYSTEM
from ..schemas import Constraints, ConversationState
from .slots import SlotMeta, Source
from .state import merge

LANG_KEYWORDS = ["java", "python", "javascript", "typescript", "go", "rust",
                 "c#", "c++", "ruby", "php", "kotlin", "swift", "scala", "sql"]
SKILL_KEYWORDS = ["react", "angular", "vue", "spring", "django", "node",
                  "aws", "azure", "gcp", "kubernetes", "docker", "linux",
                  "networking", "ml", "data", "excel", "word", "powerpoint",
                  "accounting", "statistics", "hipaa", "selling"]
LEVEL_MAP = {
    "entry": "Entry", "graduate": "Entry", "junior": "Entry", "trainee": "Entry",
    "mid": "Mid", "intermediate": "Mid",
    "senior": "Senior", "lead": "Senior", "principal": "Senior",
    "manager": "Manager", "director": "Executive",
    "executive": "Executive", "cxo": "Executive", "vp": "Executive",
}
ASSESSMENT_TYPES = {
    "cognitive": "Cognitive", "reasoning": "Cognitive", "aptitude": "Cognitive",
    "personality": "Personality", "behavioural": "Personality", "behavioral": "Personality",
    "technical": "Technical", "coding": "Technical", "knowledge": "Technical",
    "leadership": "Leadership", "sales": "Sales",
    "situational": "Situational", "scenarios": "Situational",
    "simulation": "Simulation", "simulations": "Simulation",
    "numerical": "Numerical",
}
ROLE_PAT = re.compile(
    r"\b(engineer|developer|analyst|manager|designer|consultant|representative|"
    r"agent|operator|administrator|admin(?:istrator|istrative)?|assistant|nurse|"
    r"technician|accountant|recruiter|teacher|trainee)\b",
    re.IGNORECASE,
)


@dataclass
class ExtractionResult:
    state: ConversationState
    touched: dict[str, Source]  # slot -> source provenance for THIS turn


def _regex_extract(text: str) -> ExtractionResult:
    t = text.lower()
    state = ConversationState()
    touched: dict[str, Source] = {}

    m = re.search(r"(?:under|less than|within|max(?:imum)?)\s*(\d+)\s*(?:min|minute|minutes)\b", t)
    if not m:
        m = re.search(r"(\d+)\s*(?:min|minute|minutes)\b", t)
    if m:
        state.constraints.duration_max = int(m.group(1))
        touched["duration_max"] = "regex"

    if re.search(r"\bremote\b|\bwfh\b|\bonline\b", t):
        state.constraints.remote = True
        touched["remote"] = "regex"
    if re.search(r"\badaptive\b", t):
        state.constraints.adaptive = True
        touched["adaptive"] = "regex"

    langs = []
    for l in LANG_KEYWORDS:
        if re.search(rf"\b{re.escape(l)}\b", t):
            label = "C++" if l == "c++" else "C#" if l == "c#" else "SQL" if l == "sql" else l.title()
            if label not in langs:
                langs.append(label)
    if langs:
        state.programming_language = langs
        touched["programming_language"] = "regex"

    skills = [s.title() for s in SKILL_KEYWORDS if re.search(rf"\b{re.escape(s)}\b", t)]
    if skills:
        state.technical_skills = skills
        touched["technical_skills"] = "regex"

    levels: list[str] = []
    for k, v in LEVEL_MAP.items():
        if re.search(rf"\b{k}\b", t) and v not in levels:
            levels.append(v)
    if levels:
        state.constraints.job_levels = levels
        touched["job_levels"] = "regex"

    types: list[str] = []
    for k, v in ASSESSMENT_TYPES.items():
        if re.search(rf"\b{k}\b", t) and v not in types:
            types.append(v)
    if types:
        state.assessment_types = types
        touched["assessment_types"] = "regex"

    if re.search(r"\bleadership\b", t):
        state.leadership = True
        touched["leadership"] = "regex"
    if re.search(r"\bcommunication\b", t):
        state.communication = True
        touched["communication"] = "regex"
    if re.search(r"\bpersonality\b", t):
        state.personality = True
        touched["personality"] = "regex"

    rm = ROLE_PAT.search(t)
    if rm:
        state.role = rm.group(1).title()
        touched["role"] = "regex"

    # Industry hints
    for kw, ind in [
        ("contact centre", "Contact Center"), ("contact center", "Contact Center"),
        ("call centre", "Contact Center"), ("call center", "Contact Center"),
        ("healthcare", "Healthcare"), ("hospital", "Healthcare"),
        ("manufactur", "Manufacturing"), ("industrial", "Manufacturing"),
        ("chemical", "Manufacturing"), ("plant operator", "Manufacturing"),
        ("retail", "Retail"), ("financial", "Finance"), ("bank", "Finance"),
        ("sales", "Sales"),
    ]:
        if kw in t:
            state.industry = ind
            touched["industry"] = "regex"
            break

    # Spoken languages (constraints.languages)
    for lang_kw, label in [
        ("english", "English"), ("spanish", "Spanish"), ("french", "French"),
        ("german", "German"), ("portuguese", "Portuguese"), ("italian", "Italian"),
        ("chinese", "Chinese"), ("japanese", "Japanese"), ("hindi", "Hindi"),
    ]:
        if re.search(rf"\bin\s+{lang_kw}\b|\b{lang_kw}\s+(?:speaking|language)\b", t):
            if label not in state.constraints.languages:
                state.constraints.languages.append(label)
                touched["languages"] = "regex"

    return ExtractionResult(state, touched)


def _from_llm_dict(d: dict) -> ConversationState:
    c = d.get("constraints") or {}
    return ConversationState(
        role=d.get("role"),
        experience=d.get("experience"),
        industry=d.get("industry"),
        programming_language=list(d.get("programming_language") or []),
        leadership=d.get("leadership"),
        communication=d.get("communication"),
        technical_skills=list(d.get("technical_skills") or []),
        personality=d.get("personality"),
        assessment_types=list(d.get("assessment_types") or []),
        constraints=Constraints(
            duration_max=c.get("duration_max"),
            remote=c.get("remote"),
            adaptive=c.get("adaptive"),
            languages=list(c.get("languages") or []),
            job_levels=list(c.get("job_levels") or []),
        ),
    )


def _touched_from_llm(s: ConversationState) -> dict[str, Source]:
    out: dict[str, Source] = {}
    if s.role: out["role"] = "llm"
    if s.industry: out["industry"] = "llm"
    if s.programming_language: out["programming_language"] = "llm"
    if s.technical_skills: out["technical_skills"] = "llm"
    if s.assessment_types: out["assessment_types"] = "llm"
    if s.leadership is not None: out["leadership"] = "llm"
    if s.communication is not None: out["communication"] = "llm"
    if s.personality is not None: out["personality"] = "llm"
    c = s.constraints
    if c.duration_max is not None: out["duration_max"] = "llm"
    if c.remote is not None: out["remote"] = "llm"
    if c.adaptive is not None: out["adaptive"] = "llm"
    if c.languages: out["languages"] = "llm"
    if c.job_levels: out["job_levels"] = "llm"
    return out


def extract(
    prev_state: ConversationState,
    user_message: str,
    client: GeminiClient | None,
    meta: SlotMeta,
) -> ConversationState:
    """Update prev_state from user_message; mutate `meta` confidences in place."""
    base = _regex_extract(user_message)
    for slot, src in base.touched.items():
        meta.bump(slot, src)
    merged = merge(prev_state, base.state)

    if client is not None:
        try:
            payload = client.json(
                EXTRACTOR_SYSTEM,
                json.dumps({"prior_state": prev_state.model_dump(), "message": user_message}),
            )
            llm_state = _from_llm_dict(payload)
            for slot, src in _touched_from_llm(llm_state).items():
                meta.bump(slot, src)
            merged = merge(merged, llm_state)
        except Exception:
            pass
    return merged
