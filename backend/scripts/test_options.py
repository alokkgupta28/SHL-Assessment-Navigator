from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from app.main import app
from starlette.testclient import TestClient
c = TestClient(app)
headers = {
    'Origin': 'https://example.vercel.app',
    'Access-Control-Request-Method': 'POST',
    'Access-Control-Request-Headers': 'content-type,x-request-id',
}
resp = c.options('/chat', headers=headers)
print('status', resp.status_code)
print('headers')
for k,v in resp.headers.items():
    if k.lower().startswith('access-control') or k.lower().startswith('x-'):
        print(k+':', v)
print('body:', resp.content)
