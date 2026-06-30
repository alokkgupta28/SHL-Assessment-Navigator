from app.schemas import ChatResponse


def test_schema_validates(client):
    r = client.post("/chat", json={
        "session_id": "s1",
        "messages": [{"role": "user", "content": "I need a Java developer assessment, remote, 40 min."}],
        "mode": "recommend",
    })
    assert r.status_code == 200
    ChatResponse.model_validate(r.json())
