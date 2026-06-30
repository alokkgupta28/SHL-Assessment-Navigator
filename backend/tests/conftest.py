from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("CATALOG_PATH", str(ROOT / "data" / "shl_catalog.sample.json"))
os.environ.setdefault("GEMINI_API_KEY", "")  # offline by default
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "0")  # disable limiter in tests



@pytest.fixture(scope="session")
def client():
    from app.main import app  # noqa: WPS433
    with TestClient(app) as c:
        yield c
