"""Regression replay across every sample conversation.

Runs the user turns of each ``backend/sample_conversations/C*.md`` through the
real engine and asserts hard behavioural invariants:

* No recommendation id is hallucinated (every id resolves in the catalog).
* No duplicate ids inside a single response (schema dedupe).
* Clarification budget honoured (≤2 questions per session, 1 per turn).
* The 8-turn hard cap is respected (engine never asks on the final turn).
* By the end of the trace the engine has either produced a non-empty
  shortlist or returned a safety/clarification reason — it never silently
  returns an empty response.

These tests are deliberately behavioural (not gold-pinning) because the
public gold sets in the markdown traces exceed our test catalog slice.
The full retrieval-quality numbers live in ``backend/eval/harness.py``.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.deps import build_container
from app.schemas import ChatMessage, ChatRequest, ChatResponse

SAMPLES = Path(__file__).resolve().parent.parent / "sample_conversations"
USER_RE = re.compile(r"^\s*(?:\*\*)?(?:User|HM|Hiring Manager)(?:\*\*)?\s*[:\-]\s*(.+)$",
                     re.IGNORECASE)


def _extract_user_turns(md: str) -> list[str]:
    turns: list[str] = []
    lines = md.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*\*\*(User|HM|Hiring Manager)\*\*\s*$", line, re.IGNORECASE):
            buf: list[str] = []
            for j in range(i + 1, min(i + 12, len(lines))):
                nxt = lines[j].strip()
                if nxt.startswith(">"):
                    buf.append(nxt.lstrip(">").strip())
                elif buf:
                    break
            if buf:
                turns.append(" ".join(buf))
        else:
            m = USER_RE.match(line)
            if m:
                turns.append(m.group(1).strip())
    return turns


@pytest.fixture(scope="module")
def engine():
    return build_container().engine


def _all_traces() -> list[Path]:
    return sorted(SAMPLES.glob("C*.md"))


@pytest.mark.parametrize("path", _all_traces(), ids=lambda p: p.stem)
def test_replay_invariants(engine, path: Path):
    turns = _extract_user_turns(path.read_text(encoding="utf-8"))
    if not turns:
        pytest.skip(f"no user turns parsed from {path.name}")
    session_id = f"replay-{path.stem}"
    catalog_ids = {a.id for a in engine.catalog}
    clarifications = 0
    last_resp: ChatResponse | None = None
    asked_on_final = False

    for i, text in enumerate(turns[:8], start=1):
        req = ChatRequest(
            session_id=session_id,
            messages=[ChatMessage(role="user", content=text)],
            mode="recommend",
        )
        resp = engine.handle(req)
        last_resp = resp

        # Grounding: every id resolves.
        for rec in resp.recommendations:
            assert rec.id in catalog_ids, (
                f"{path.stem} turn {i}: hallucinated id {rec.id!r}"
            )
        # No duplicate ids in one response.
        ids = [r.id for r in resp.recommendations]
        assert len(ids) == len(set(ids)), f"{path.stem} turn {i}: duplicate ids in response"

        if resp.need_clarification:
            clarifications += 1
            assert resp.clarifying_question, "need_clarification with no question"
            if i == min(len(turns), 8):
                asked_on_final = True

    assert last_resp is not None
    assert clarifications <= 2, f"{path.stem}: too many clarifications: {clarifications}"
    # 8-turn cap: engine must never end the session asking another question.
    assert not (asked_on_final and i >= 8), (
        f"{path.stem}: clarification asked on the final allowed turn"
    )
    # End-state must be informative — recs, or a safety/clarification reason.
    assert (
        last_resp.recommendations
        or last_resp.safety.blocked
        or last_resp.need_clarification
    ), f"{path.stem}: empty terminal response with no reason"


def test_replay_corpus_present():
    """The eval corpus itself must exist — guards against accidental deletion."""
    assert _all_traces(), "no sample conversations found"
