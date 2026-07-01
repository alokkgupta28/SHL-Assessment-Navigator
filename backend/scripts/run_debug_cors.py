from pathlib import Path
import sys
sys.path.insert(0, str(Path('.').resolve()))
from app.main import app
from starlette.testclient import TestClient
import os

print('ENV ALLOWED_ORIGINS=', os.environ.get('ALLOWED_ORIGINS'))

c = TestClient(app)
resp = c.get('/debug/cors')
print('status', resp.status_code)
print(resp.json())
