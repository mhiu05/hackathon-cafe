"""Vietnamese-aware text helpers shared by ingestion, menu search and retrieval."""
from __future__ import annotations

import hashlib
import re
import unicodedata

_WS = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_text(text: str, *, max_len: int | None = None) -> str:
    """NFC-normalise, collapse whitespace, trim; optionally truncate."""
    out = _WS.sub(" ", unicodedata.normalize("NFC", text or "")).strip()
    return out[:max_len] if max_len else out


def fold_vi(text: str) -> str:
    """Lowercase and strip Vietnamese diacritics ('Cà phê đen' -> 'ca phe den')."""
    decomposed = unicodedata.normalize("NFD", (text or "").lower())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return normalize_text(stripped.replace("đ", "d"))


def fts_query(text: str) -> str:
    """Build a safe FTS5 OR-query of quoted folded tokens (len >= 2). Empty string if none."""
    tokens = [t for t in _NON_WORD.sub(" ", fold_vi(text)).split() if len(t) >= 2]
    seen: list[str] = []
    for tok in tokens:
        if tok not in seen:
            seen.append(tok)
    return " OR ".join(f'"{t}"' for t in seen[:16])


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    """Cheap token estimate for Vietnamese text (~1 token per 3 chars)."""
    return max(1, len(text) // 3)
