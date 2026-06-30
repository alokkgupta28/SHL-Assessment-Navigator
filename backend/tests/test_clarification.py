def test_clarification_required(client):
    r = client.post("/chat", json={
        "session_id": "clar1",
        "messages": [{"role": "user", "content": "I need an assessment"}],
        "mode": "recommend",
    })
    body = r.json()
    assert body["need_clarification"] is True
    assert body["clarifying_question"]
    assert "?" in body["clarifying_question"]
    # exactly one question
    assert body["clarifying_question"].count("?") == 1
    assert body["recommendations"] == []
