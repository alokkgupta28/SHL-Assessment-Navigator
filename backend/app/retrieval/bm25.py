"""Sparse retrieval (BM25) with a tokenizer tuned for SHL catalog text.

Improvements over a naïve word split:

- Split on whitespace AND camelCase / kebab-case / slash so that
  ``ASP.NET``, ``Front-End``, ``Verify-G+``, ``react/typescript`` all break
  into searchable units while preserving the original token as well
  (we want both ``front-end`` and {``front``, ``end``} in the index).
- Lowercase, strip a small English stoplist — SHL catalog descriptions are
  saturated with words like *the/and/of* that wash out IDF.
- Light suffix stripping (Porter-ish) for plurals/-ing/-ed only. We avoid a
  full stemmer because over-stemming hurts exact technical matches
  ("Java" vs "Javanese").
- Domain synonym expansion: ``exec → executive``, ``cxo → executive``,
  ``ic → individual contributor`` etc. Keeps recall high when users
  speak in shorthand.
"""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

# Keep + # . inside tokens so C++, C#, Node.js, .NET survive intact.
_TOKEN = re.compile(r"[A-Za-z0-9+#\.]+")
_SPLIT_INNER = re.compile(r"[-/_]")
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")

_STOP = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with",
    "is", "are", "be", "this", "that", "as", "by", "at", "from", "it",
    "we", "i", "you", "our", "your", "their", "them",
    # SHL catalog filler
    "assessment", "test", "tests", "candidate", "candidates", "report",
    "designed", "individuals", "across",
}

_SYNONYMS: dict[str, list[str]] = {
    "cxo": ["executive", "leadership"],
    "exec": ["executive"],
    "execs": ["executive"],
    "ceo": ["executive", "leadership"],
    "cto": ["executive", "leadership", "technology"],
    "cfo": ["executive", "leadership", "finance"],
    "vp": ["executive", "leadership"],
    "ic": ["individual", "contributor"],
    "swe": ["software", "engineer", "developer"],
    "dev": ["developer", "engineer"],
    "devs": ["developer", "engineer"],
    "fe": ["frontend", "front", "end"],
    "be": ["backend", "back", "end"],
    "ml": ["machine", "learning"],
    "ai": ["artificial", "intelligence"],
    "qa": ["quality", "assurance", "testing"],
    "pm": ["product", "manager"],
    "ux": ["user", "experience", "design"],
    "js": ["javascript"],
    "ts": ["typescript"],
    "py": ["python"],
    "k8s": ["kubernetes"],
    "db": ["database"],
    "sql": ["database"],
    "cog": ["cognitive"],
    "psych": ["personality", "psychometric"],
}


def _strip_suffix(t: str) -> str:
    if len(t) <= 4:
        return t
    for suf in ("ings", "ing", "edly", "edly", "ies", "ied", "ed", "es", "ly", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)]
    return t


def tokenize(text: str) -> list[str]:
    """Return BM25 tokens for a piece of free text.

    The same function is used for both indexing and querying so the
    statistics stay aligned.
    """
    if not text:
        return []
    out: list[str] = []
    # Split camelCase first so "FrontEnd" -> "Front End".
    text = _CAMEL.sub(" ", text)
    for raw in _TOKEN.findall(text):
        low = raw.lower()
        # Keep the compound form as a token (good for exact match on ".net").
        if low not in _STOP:
            out.append(_strip_suffix(low))
        # Also break compounds like "front-end" or "react/typescript".
        for part in _SPLIT_INNER.split(low):
            if not part or part == low or part in _STOP:
                continue
            out.append(_strip_suffix(part))
        # Synonym expansion.
        for extra in _SYNONYMS.get(low, ()):
            out.append(extra)
    return out


class BM25:
    """Thin wrapper around ``rank_bm25.BM25Okapi`` with our tokenizer."""

    def __init__(self, corpus: list[str]):
        self.tokens = [tokenize(c) for c in corpus]
        self.model = BM25Okapi(self.tokens)

    def scores(self, query: str):
        return self.model.get_scores(tokenize(query))
