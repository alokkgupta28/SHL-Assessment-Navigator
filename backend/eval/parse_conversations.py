"""Parse sample conversations into evaluation cases.

Each ``.md`` file under ``backend/sample_conversations`` looks like a
multi-turn agent transcript. We need two things per file:

1. ``query`` — what the user asked. We concatenate every ``User`` turn so
   the retriever has full context (the engine in production builds a
   slot summary; for an offline eval we use the raw text — same input
   for both baseline and the new pipeline, so the comparison is fair).
2. ``gold_urls`` — the assessment URLs the agent eventually recommended.
   We take the final markdown table in the file. URLs are wrapped in
   angle brackets (``<https://...>``) so we strip those.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

USER_BLOCK = re.compile(r"\*\*User\*\*\s*\n+>\s*(.+?)(?=\n\n|\Z)", re.DOTALL)
URL_RE = re.compile(r"<(https?://[^>]+)>")
TABLE_ROW = re.compile(r"^\|.*\|$", re.MULTILINE)


@dataclass
class EvalCase:
    name: str
    query: str
    gold_urls: list[str]


def parse_conversation(path: Path) -> EvalCase | None:
    text = path.read_text(encoding="utf-8")
    # Collect user utterances (preserve order, drop duplicates).
    seen: set[str] = set()
    user_turns: list[str] = []
    for m in USER_BLOCK.finditer(text):
        u = re.sub(r"\s+", " ", m.group(1)).strip()
        if u and u not in seen:
            seen.add(u)
            user_turns.append(u)
    # Gold = URLs in the LAST markdown table in the file.
    tables = re.findall(r"((?:^\|.*\|\n)+)", text, flags=re.MULTILINE)
    if not tables or not user_turns:
        return None
    last_table = tables[-1]
    urls = [u.rstrip("/") for u in URL_RE.findall(last_table)]
    if not urls:
        return None
    return EvalCase(
        name=path.stem,
        query=" ".join(user_turns),
        gold_urls=urls,
    )


def load_eval_cases(folder: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for p in sorted(folder.glob("*.md")):
        c = parse_conversation(p)
        if c:
            cases.append(c)
    return cases
