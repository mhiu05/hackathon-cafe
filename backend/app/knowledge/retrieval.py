"""Knowledge retrieval: Voyage query embedding + NumPy cosine search, FTS5 keyword fallback.

Usage (agent tool `search_cafe_knowledge` in the app phase):

    index = KnowledgeIndex.load(conn)                      # once at startup
    result = await asearch_knowledge(conn, index, embedder, "quán có chỗ đỗ xe không?")
    result.hits  -> list[KnowledgeHit] with content + source attribution

Prices, availability and order status must NOT be answered from this module; they come from SQL.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np

from app.knowledge.embeddings import EmbeddingError, VoyageEmbedder, blob_to_vector
from app.knowledge.text import fts_query, normalize_text

MAX_QUERY_CHARS = 500
DEFAULT_TOP_K = 5
# Cosine floor for voyage-4-lite@512 on this corpus; calibrated by scripts/knowledge/verify.py.
DEFAULT_MIN_SCORE = 0.30

SearchMode = Literal["vector", "keyword_fallback", "empty"]


@dataclass(frozen=True)
class KnowledgeHit:
    chunk_id: str
    document_id: str
    title: str
    category: str
    content_kind: str
    verification_status: str
    source_id: str
    source_type: str
    source_title: str
    source_url: str | None
    retrieved_at: str
    content: str
    score: float
    match: Literal["vector", "keyword"]
    citations: tuple[str, ...] = ()   # source ids cited by synthesis documents (src-kb-curation)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    mode: SearchMode
    hits: list[KnowledgeHit]
    error: str | None = None

    def to_dict(self) -> dict:
        return {"query": self.query, "mode": self.mode, "error": self.error, "hits": [h.to_dict() for h in self.hits]}


_META_SQL = """
SELECT c.id AS chunk_id, c.document_id, c.content, d.title, d.category, d.content_kind,
       d.verification_status, d.source_id, d.retrieved_at,
       COALESCE(d.source_url, s.url) AS source_url, s.source_type, s.title AS source_title,
       d.metadata_json
FROM kb_chunks c
JOIN kb_documents d ON d.id = c.document_id
JOIN kb_sources s ON s.id = d.source_id
"""


def _hit(row: sqlite3.Row, score: float, match: Literal["vector", "keyword"]) -> KnowledgeHit:
    return KnowledgeHit(
        chunk_id=row["chunk_id"], document_id=row["document_id"], title=row["title"], category=row["category"],
        content_kind=row["content_kind"], verification_status=row["verification_status"], source_id=row["source_id"],
        source_type=row["source_type"], source_title=row["source_title"], source_url=row["source_url"],
        retrieved_at=row["retrieved_at"], content=row["content"], score=round(float(score), 4), match=match,
        citations=tuple(json.loads(row["metadata_json"] or "{}").get("citations") or ()),
    )


class KnowledgeIndex:
    """In-memory matrix of all chunk vectors (single café => a few hundred rows at most)."""

    def __init__(self, chunk_ids: list[str], matrix: np.ndarray, rows: dict[str, sqlite3.Row], model: str, dimension: int):
        self.chunk_ids = chunk_ids
        self.matrix = matrix
        self.rows = rows
        self.model = model
        self.dimension = dimension

    @classmethod
    def load(cls, conn: sqlite3.Connection) -> "KnowledgeIndex":
        meta = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM kb_meta")}
        model = meta.get("embedding_model", "")
        dimension = int(meta.get("embedding_dimension", "0") or 0)
        rows = {r["chunk_id"]: r for r in conn.execute(_META_SQL)}
        ids: list[str] = []
        vectors: list[np.ndarray] = []
        for r in conn.execute(
            "SELECT e.chunk_id, e.vector, e.dimension FROM kb_embeddings e "
            "JOIN kb_chunks c ON c.id = e.chunk_id AND c.content_hash = e.content_hash "
            "WHERE e.model = ? ORDER BY e.chunk_id",
            (model,),
        ):
            if r["chunk_id"] in rows:
                ids.append(r["chunk_id"])
                vectors.append(blob_to_vector(r["vector"], r["dimension"]))
        matrix = np.vstack(vectors) if vectors else np.zeros((0, max(dimension, 1)), dtype=np.float32)
        return cls(ids, matrix, rows, model, dimension)

    def __len__(self) -> int:
        return len(self.chunk_ids)

    def search(
        self,
        query_vector: np.ndarray,
        *,
        top_k: int = DEFAULT_TOP_K,
        categories: set[str] | None = None,
        exclude_kinds: set[str] | None = None,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> list[KnowledgeHit]:
        if not len(self):
            return []
        scores = self.matrix @ np.asarray(query_vector, dtype=np.float32)
        hits: list[KnowledgeHit] = []
        seen_docs: set[str] = set()
        for idx in np.argsort(-scores):
            score = float(scores[idx])
            if score < min_score:
                break
            row = self.rows[self.chunk_ids[idx]]
            if categories and row["category"] not in categories:
                continue
            if exclude_kinds and row["content_kind"] in exclude_kinds:
                continue
            if row["document_id"] in seen_docs:  # one (best) chunk per document keeps top-k diverse
                continue
            seen_docs.add(row["document_id"])
            hits.append(_hit(row, score, "vector"))
            if len(hits) >= top_k:
                break
        return hits


def keyword_search(
    conn: sqlite3.Connection, query: str, *, top_k: int = DEFAULT_TOP_K, categories: set[str] | None = None
) -> list[KnowledgeHit]:
    match = fts_query(query)
    if not match:
        return []
    fts_rows = conn.execute(
        "SELECT chunk_id, bm25(kb_chunks_fts) AS rank FROM kb_chunks_fts WHERE kb_chunks_fts MATCH ? ORDER BY rank LIMIT ?",
        (match, top_k * 4),
    ).fetchall()
    if not fts_rows:
        return []
    ranks = {r["chunk_id"]: float(r["rank"]) for r in fts_rows}
    placeholders = ",".join("?" for _ in ranks)
    meta = {r["chunk_id"]: r for r in conn.execute(f"{_META_SQL} WHERE c.id IN ({placeholders})", list(ranks))}
    hits: list[KnowledgeHit] = []
    seen_docs: set[str] = set()
    for chunk_id, rank in sorted(ranks.items(), key=lambda kv: kv[1]):
        row = meta.get(chunk_id)
        if row is None or (categories and row["category"] not in categories) or row["document_id"] in seen_docs:
            continue
        seen_docs.add(row["document_id"])
        hits.append(_hit(row, -rank, "keyword"))  # bm25: lower is better -> negate
        if len(hits) >= top_k:
            break
    return hits


def _prepare(query: str) -> str:
    return normalize_text(query, max_len=MAX_QUERY_CHARS)


def search_knowledge(
    conn: sqlite3.Connection,
    index: KnowledgeIndex,
    embedder: VoyageEmbedder | None,
    query: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    categories: set[str] | None = None,
    exclude_kinds: set[str] | None = None,
    min_score: float = DEFAULT_MIN_SCORE,
) -> RetrievalResult:
    """Synchronous retrieval (scripts/tests). Vector first; FTS fallback on embedding failure."""
    q = _prepare(query)
    if not q:
        return RetrievalResult(query=q, mode="empty", hits=[], error="empty_query")
    if embedder is not None and len(index):
        try:
            qvec = embedder.embed_query(q)
            hits = index.search(qvec, top_k=top_k, categories=categories, exclude_kinds=exclude_kinds, min_score=min_score)
            return RetrievalResult(query=q, mode="vector" if hits else "empty", hits=hits)
        except EmbeddingError as exc:
            hits = keyword_search(conn, q, top_k=top_k, categories=categories)
            return RetrievalResult(query=q, mode="keyword_fallback" if hits else "empty", hits=hits, error=str(exc)[:200])
    hits = keyword_search(conn, q, top_k=top_k, categories=categories)
    return RetrievalResult(query=q, mode="keyword_fallback" if hits else "empty", hits=hits, error="embedder_unavailable")


async def asearch_knowledge(
    conn: sqlite3.Connection,
    index: KnowledgeIndex,
    embedder: VoyageEmbedder | None,
    query: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    categories: set[str] | None = None,
    exclude_kinds: set[str] | None = None,
    min_score: float = DEFAULT_MIN_SCORE,
) -> RetrievalResult:
    """Async variant for FastAPI/agent tools (uses VoyageEmbedder.aembed_query, fail-fast)."""
    q = _prepare(query)
    if not q:
        return RetrievalResult(query=q, mode="empty", hits=[], error="empty_query")
    if embedder is not None and len(index):
        try:
            qvec = await embedder.aembed_query(q)
            hits = index.search(qvec, top_k=top_k, categories=categories, exclude_kinds=exclude_kinds, min_score=min_score)
            return RetrievalResult(query=q, mode="vector" if hits else "empty", hits=hits)
        except EmbeddingError as exc:
            hits = keyword_search(conn, q, top_k=top_k, categories=categories)
            return RetrievalResult(query=q, mode="keyword_fallback" if hits else "empty", hits=hits, error=str(exc)[:200])
    hits = keyword_search(conn, q, top_k=top_k, categories=categories)
    return RetrievalResult(query=q, mode="keyword_fallback" if hits else "empty", hits=hits, error="embedder_unavailable")


def hits_as_json(result: RetrievalResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False)
