"""Apply structural refinements (add / drop / replace) to a pinned shortlist."""
from __future__ import annotations

import re

from ..catalog.models import Assessment


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def _tokens(s: str) -> set[str]:
    return {t for t in _norm(s).split() if len(t) > 2}


def _score_match(term: str, a: Assessment) -> float:
    tt = _tokens(term)
    if not tt:
        return 0.0
    name_tokens = _tokens(a.name)
    skill_tokens = _tokens(" ".join(a.skills))
    cat_tokens = _tokens(a.category)
    inter_name = len(tt & name_tokens) / max(len(tt), 1)
    inter_skill = len(tt & skill_tokens) / max(len(tt), 1)
    inter_cat = len(tt & cat_tokens) / max(len(tt), 1)
    return 0.7 * inter_name + 0.2 * inter_skill + 0.1 * inter_cat


def resolve_term(term: str, pool: list[Assessment]) -> Assessment | None:
    """Find the catalog assessment that best matches a free-text term."""
    if not term or not pool:
        return None
    best, best_s = None, 0.0
    for a in pool:
        s = _score_match(term, a)
        if s > best_s:
            best, best_s = a, s
    return best if best_s >= 0.34 else None


def drop_from(pinned: list[str], terms: list[str], catalog: list[Assessment]) -> list[str]:
    by_id = {a.id: a for a in catalog}
    current = [by_id[i] for i in pinned if i in by_id]
    out_ids = list(pinned)
    for term in terms:
        target = resolve_term(term, current)
        if target and target.id in out_ids:
            out_ids.remove(target.id)
            current = [a for a in current if a.id != target.id]
    return out_ids


def add_to(
    pinned: list[str],
    terms: list[str],
    catalog: list[Assessment],
    max_size: int = 10,
) -> list[str]:
    by_id = {a.id: a for a in catalog}
    out = list(pinned)
    for term in terms:
        # Prefer items NOT already pinned
        pool = [a for a in catalog if a.id not in out]
        target = resolve_term(term, pool) or resolve_term(term, list(by_id.values()))
        if target and target.id not in out:
            out.append(target.id)
            if len(out) >= max_size:
                break
    return out


def replace_in(
    pinned: list[str],
    pairs: list[tuple[str, str]],
    catalog: list[Assessment],
) -> list[str]:
    by_id = {a.id: a for a in catalog}
    out = list(pinned)
    for old_term, new_term in pairs:
        current = [by_id[i] for i in out if i in by_id]
        old = resolve_term(old_term, current)
        pool = [a for a in catalog if a.id not in out]
        new = resolve_term(new_term, pool)
        if old and new:
            idx = out.index(old.id)
            out[idx] = new.id
        elif new and new.id not in out:
            out.append(new.id)
        elif old and old.id in out:
            out.remove(old.id)
    return out
