"""Content safety: prompt-injection, out-of-scope, and input hygiene.

Three layers, applied in order:

1. **Sanitization** — strip control characters and cap absolute length.
   This is non-blocking and runs on every message before any matcher sees
   it, so an attacker can't smuggle directives via zero-width or BOM
   characters.
2. **Prompt-injection patterns** — block obvious overrides ("ignore all
   previous instructions", fake ``system:`` turns, jailbreak personas).
3. **Out-of-scope topic patterns** — legal/medical/political/competitor
   prompts get a polite refusal. We deliberately match on the user's
   intent (e.g. "give me legal advice"), not on every keyword.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .schemas import ChatMessage

# --- limits ---------------------------------------------------------------

MAX_MESSAGE_CHARS = 4_000           # per-message cap (request schema also enforces)
MAX_TOTAL_USER_CHARS = 16_000       # aggregated across the visible history


# --- patterns -------------------------------------------------------------

INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above) (instructions|messages|prompts)",
    r"disregard (all |any |the )?(previous|prior|above)",
    r"reveal (the )?system prompt",
    r"\byou are now\b",
    r"act as (?:a |an )?(?:dan|jailbreak|developer mode)",
    r"\bsystem:\s",
    r"</?\s*system\s*>",
    r"forget everything",
    r"print your (system )?prompt",
    r"bypass (your |the )?(rules|guardrails|safety)",
]
LEGAL = [r"\blegal advice\b", r"\blawsuit\b", r"\bsue\b", r"\bcontract review\b"]
MEDICAL = [r"\bmedical advice\b", r"\bdiagnos(e|is)\b", r"\bprescribe\b",
           r"\bsymptoms?\b.*\btreatment\b"]
POLITICAL = [r"\b(vote|election|political party|democrat|republican)\b.*\b(opinion|recommend|should)\b"]
EXTERNAL = [
    r"\b(hackerrank|codility|mettl|hirevue|pymetrics|criteria corp)\b",
    r"non[- ]shl assessment",
    r"alternative to shl",
]


@dataclass
class SafetyVerdict:
    blocked: bool
    reason: str | None
    refusal: str | None


# --- API ------------------------------------------------------------------

def sanitize(text: str) -> str:
    """Strip control / formatting characters and clamp length.

    Defends against zero-width space injection (used to hide
    ``ignore previous instructions`` inside what looks like normal text).
    """
    if not text:
        return ""
    # Keep \n and \t; drop every other C-class (control) codepoint.
    cleaned = "".join(
        ch for ch in text
        if ch in ("\n", "\t") or unicodedata.category(ch)[0] != "C"
    )
    cleaned = cleaned.replace("\u200b", "").replace("\ufeff", "")
    if len(cleaned) > MAX_MESSAGE_CHARS:
        cleaned = cleaned[:MAX_MESSAGE_CHARS]
    return cleaned


def _match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def scan(messages: list[ChatMessage]) -> SafetyVerdict:
    text = "\n".join(sanitize(m.content) for m in messages if m.role == "user")
    if not text.strip():
        return SafetyVerdict(False, None, None)
    if len(text) > MAX_TOTAL_USER_CHARS:
        return SafetyVerdict(
            True, "input_too_large",
            "Your message history is too long. Please start a new session with a shorter prompt.",
        )
    if _match_any(text, INJECTION_PATTERNS):
        return SafetyVerdict(
            True, "prompt_injection",
            "I can only help recommend SHL assessments. I can't follow instructions that override my task.",
        )
    if _match_any(text, LEGAL):
        return SafetyVerdict(True, "legal", "I can't provide legal advice. I can only recommend SHL assessments.")
    if _match_any(text, MEDICAL):
        return SafetyVerdict(True, "medical", "I can't provide medical advice. I can only recommend SHL assessments.")
    if _match_any(text, POLITICAL):
        return SafetyVerdict(True, "political", "I don't discuss political topics. I can only recommend SHL assessments.")
    if _match_any(text, EXTERNAL):
        return SafetyVerdict(
            True, "external_assessments",
            "I only recommend SHL assessments from the official catalog.",
        )
    return SafetyVerdict(False, None, None)
