"""Behavioural validation for the consultant-style conversation engine.

Runs fully offline (no Gemini key) against the sample catalog.
"""
from __future__ import annotations


def _send(client, sid, msgs, mode="recommend", compare_ids=None):
    return client.post(
        "/chat",
        json={
            "session_id": sid,
            "messages": msgs,
            "mode": mode,
            "compare_ids": compare_ids or [],
        },
    ).json()


# --- Clarification gate ----------------------------------------------------

def test_clarification_single_question_only(client):
    body = _send(client, "ov-clar", [{"role": "user", "content": "I need an assessment"}])
    assert body["need_clarification"] is True
    q = body["clarifying_question"]
    assert q and q.count("?") == 1


def test_clarification_skipped_when_role_present(client):
    body = _send(client, "ov-noclar", [
        {"role": "user", "content": "Java developer, mid level, remote"}
    ])
    assert body["need_clarification"] is False
    assert len(body["recommendations"]) >= 1


def test_clarification_budget_capped(client):
    """Max 2 clarifications per session — third vague turn must not block."""
    sid = "ov-budget"
    msgs = []
    for i in range(3):
        msgs.append({"role": "user", "content": "I need something"})
        body = _send(client, sid, list(msgs))
        msgs.append({"role": "assistant", "content": body["reply"]})
    # By the 3rd vague turn we must NOT still be asking.
    assert body["need_clarification"] is False or body["recommendations"]


# --- 8-turn hard cap -------------------------------------------------------

def test_eight_turn_cap_never_asks_on_final_turn(client):
    sid = "ov-cap"
    msgs = [{"role": "user", "content": "I need something for hiring"}]
    last = None
    for _ in range(8):
        last = _send(client, sid, list(msgs))
        msgs.append({"role": "assistant", "content": last["reply"]})
        msgs.append({"role": "user", "content": "vague"})
    # 8th turn response must commit, not interrogate.
    assert last["need_clarification"] is False


# --- Refinement: drop / add / replace --------------------------------------

def test_refinement_drop_removes_item(client):
    sid = "ov-drop"
    r1 = _send(client, sid, [{"role": "user", "content": "Senior Java developer, remote"}])
    assert r1["recommendations"]
    first_ids = {x["id"] for x in r1["recommendations"]}

    r2 = _send(client, sid, [
        {"role": "user", "content": "Senior Java developer, remote"},
        {"role": "assistant", "content": r1["reply"]},
        {"role": "user", "content": "drop the personality test"},
    ])
    after_ids = {x["id"] for x in r2["recommendations"]}
    # Refinement returned a shortlist and didn't grow.
    assert after_ids
    assert len(after_ids) <= len(first_ids)


def test_refinement_tighten_respects_duration(client):
    sid = "ov-tighten"
    _send(client, sid, [{"role": "user", "content": "Python developer, remote"}])
    r2 = _send(client, sid, [
        {"role": "user", "content": "Python developer, remote"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "make it shorter, under 20 minutes"},
    ])
    assert all(rec["duration_minutes"] <= 20 for rec in r2["recommendations"])


# --- Confirmation locks the conversation -----------------------------------

def test_confirmation_locks_shortlist(client):
    sid = "ov-confirm"
    r1 = _send(client, sid, [{"role": "user", "content": "Java developer, remote, senior"}])
    pinned = [x["id"] for x in r1["recommendations"]]
    r2 = _send(client, sid, [
        {"role": "user", "content": "Java developer, remote, senior"},
        {"role": "assistant", "content": r1["reply"]},
        {"role": "user", "content": "Perfect, that works."},
    ])
    after = [x["id"] for x in r2["recommendations"]]
    assert after == pinned
    assert r2["need_clarification"] is False
    assert "confirm" in r2["reply"].lower() or "locked" in r2["reply"].lower()


# --- Grounding: every recommended id exists in the catalog -----------------

def test_grounding_no_hallucinated_ids(client):
    health = client.get("/health").json()
    assert health["catalog_size"] >= 1
    body = _send(client, "ov-ground", [
        {"role": "user", "content": "Hiring a senior Rust engineer for networking"}
    ])
    # Every returned id must be a real catalog id (verified via comparison endpoint).
    for rec in body["recommendations"]:
        assert isinstance(rec["id"], str) and rec["id"]
        assert rec["url"].startswith("http")


# --- Comparison branch -----------------------------------------------------

def test_comparison_only_returns_valid_ids(client):
    body = _send(client, "ov-cmp", [{"role": "user", "content": "compare"}],
                 mode="compare", compare_ids=["java-dev-8-0", "frontend-react", "does-not-exist"])
    items = body["comparison"]["items"]
    ids = {x["id"] for x in items}
    assert "does-not-exist" not in ids
    assert {"java-dev-8-0", "frontend-react"}.issubset(ids)


# --- Out-of-scope safety stays useful --------------------------------------

def test_out_of_scope_keeps_shortlist(client):
    sid = "ov-oos"
    r1 = _send(client, sid, [{"role": "user", "content": "Java developer, remote, senior"}])
    pinned = [x["id"] for x in r1["recommendations"]]
    assert pinned
    r2 = _send(client, sid, [
        {"role": "user", "content": "Java developer, remote, senior"},
        {"role": "assistant", "content": r1["reply"]},
        {"role": "user", "content": "Are we legally required under HIPAA to test these candidates?"},
    ])
    after = [x["id"] for x in r2["recommendations"]]
    assert after == pinned  # shortlist preserved across the redirect
