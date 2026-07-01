from pathlib import Path
import sys
sys.path.insert(0, str(Path('.').resolve()))
from app.main import app
from starlette.testclient import TestClient
import os

# set up a minimal POST to /chat using test fixtures from tests
c = TestClient(app)
# construct a minimal valid request
payload = {
    "session_id": "diag-1",
    "messages": [{"role": "user", "content": "Hello"}],
    "mode": "recommend"
}
print('PID before request', os.getpid())
resp = c.post('/chat', json=payload)
print('status', resp.status_code)
print('resp body', resp.text)
