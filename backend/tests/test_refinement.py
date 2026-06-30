def test_refinement_shortens(client):
    sid = "ref1"
    r1 = client.post("/chat", json={
        "session_id": sid,
        "messages": [{"role": "user", "content": "Python developer, remote"}],
        "mode": "recommend",
    })
    first = r1.json()["recommendations"]
    assert len(first) >= 1

    r2 = client.post("/chat", json={
        "session_id": sid,
        "messages": [
            {"role": "user", "content": "Python developer, remote"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "make it shorter, under 20 minutes"},
        ],
        "mode": "refine",
    })
    second = r2.json()["recommendations"]
    assert all(rec["duration_minutes"] <= 20 for rec in second)
