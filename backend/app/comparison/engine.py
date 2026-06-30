from __future__ import annotations

from ..catalog.models import Assessment
from ..schemas import Comparison, ComparisonCell

FEATURES = [
    "duration_minutes", "remote", "adaptive", "job_levels",
    "languages", "skills", "category", "description",
]


def build(ids: list[str], catalog: list[Assessment]) -> Comparison | None:
    if not ids:
        return None
    index = {a.id: a for a in catalog}
    items: list[ComparisonCell] = []
    for i in ids:
        a = index.get(i)
        if not a:
            continue
        items.append(ComparisonCell(
            id=a.id, name=a.name, duration_minutes=a.duration_minutes,
            remote=a.remote, adaptive=a.adaptive, job_levels=a.job_levels,
            languages=a.languages, skills=a.skills, category=a.category,
            description=a.description, url=a.url,
        ))
    if not items:
        return None
    return Comparison(items=items, features=FEATURES)
