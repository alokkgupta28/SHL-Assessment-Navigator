from __future__ import annotations

import json
import re
from pathlib import Path

from .models import Assessment


def _parse_duration(item: dict) -> int:
    for key in ("duration_minutes", "durationMinutes"):
        v = item.get(key)
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.strip().isdigit():
            return int(v.strip())
    raw = item.get("duration") or item.get("duration_raw") or ""
    if isinstance(raw, int):
        return raw
    m = re.search(r"(\d+)", str(raw))
    return int(m.group(1)) if m else 0


def _parse_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"yes", "true", "y", "1"}
    return False


def _coerce(item: dict) -> Assessment:
    id_ = str(item.get("id") or item.get("entity_id") or "")
    url = str(item.get("url") or item.get("link") or item.get("officialUrl") or "")
    keys = list(item.get("keys") or [])
    category = str(item.get("category") or (keys[0] if keys else ""))
    skills = list(item.get("skills") or keys)
    return Assessment(
        id=id_,
        name=str(item.get("name", "")),
        url=url,
        description=str(item.get("description", "")),
        category=category,
        duration_minutes=_parse_duration(item),
        remote=_parse_bool(item.get("remote", False)),
        adaptive=_parse_bool(item.get("adaptive", False)),
        job_levels=list(item.get("job_levels") or item.get("jobLevels") or []),
        languages=list(item.get("languages") or []),
        skills=skills,
    )


def load_catalog(path: Path) -> list[Assessment]:
    if not path.exists():
        sample = path.parent / "shl_catalog.sample.json"
        if sample.exists():
            path = sample
        else:
            return []
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "assessments" in raw:
        raw = raw["assessments"]
    out: list[Assessment] = []
    for x in raw:
        a = _coerce(x)
        if a.id and a.name:
            out.append(a)
    return out
