def test_recommendation_java(client):
    r = client.post("/chat", json={
        "session_id": "rec1",
        "messages": [{"role": "user", "content": "Java developer, remote, under 45 minutes"}],
        "mode": "recommend",
    })
    body = r.json()
    assert body["need_clarification"] is False
    assert len(body["recommendations"]) >= 1
    assert all(rec["duration_minutes"] <= 45 for rec in body["recommendations"])
    names = " ".join(rec["name"].lower() for rec in body["recommendations"])
    assert "java" in names
