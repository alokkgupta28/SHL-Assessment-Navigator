def test_comparison(client):
    r = client.post("/chat", json={
        "session_id": "cmp1",
        "messages": [{"role": "user", "content": "compare these"}],
        "mode": "compare",
        "compare_ids": ["java-dev-8-0", "frontend-react"],
    })
    body = r.json()
    assert body["comparison"] is not None
    assert len(body["comparison"]["items"]) == 2
    assert "duration_minutes" in body["comparison"]["features"]
