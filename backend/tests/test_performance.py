import time


def test_performance_warm(client):
    # warm-up
    client.post("/chat", json={
        "session_id": "perf0",
        "messages": [{"role": "user", "content": "Java developer remote 40 min"}],
        "mode": "recommend",
    })
    t0 = time.perf_counter()
    r = client.post("/chat", json={
        "session_id": "perf1",
        "messages": [{"role": "user", "content": "Python developer remote 30 min"}],
        "mode": "recommend",
    })
    dt = time.perf_counter() - t0
    assert r.status_code == 200
    assert dt < 2.5, f"warm /chat took {dt:.2f}s"
