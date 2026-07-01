from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
sys.path.insert(0, str(BACKEND))

# Construct container like the app lifespan does
from app.deps import build_container
from app.schemas import ChatRequest, ChatMessage
from app.config import get_settings

settings = get_settings()
container = build_container(settings)
engine = container.engine

text = Path(BACKEND / 'sample_conversations' / 'C1.md').read_text(encoding='utf-8')
# extract first user turn as tests do
lines = [l.strip() for l in text.splitlines() if l.strip()]
user_turns = [l for l in lines if l.startswith('User:')]
if not user_turns:
    user_turns = [l for l in lines if not l.startswith('Assistant:')]
first = user_turns[0].replace('User:','').strip()
print('User turn:', first)
req = ChatRequest(session_id='replay-C1', messages=[ChatMessage(role='user', content=first)], mode='recommend')
resp = engine.handle(req)
print('Response:', resp)
print('Recommendations:', resp.recommendations)
print('Need clarification:', resp.need_clarification)
print('Safety:', resp.safety)
