"""Offline tests for the knowledge layer: migrations, text folding, chunking, retrieval ranking and fallback."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

from app.db.connection import transaction
from app.db.migrate import apply_migrations
from app.knowledge.embeddings import EmbeddingError, blob_to_vector, l2_normalize, vector_to_blob
from app.knowledge.retrieval import KnowledgeIndex, keyword_search, search_knowledge
from app.knowledge.text import fold_vi, fts_query

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "knowledge"))


class FakeEmbedder:
    """Maps a query to a fixed vector; raises EmbeddingError when `fail` is set."""

    def __init__(self, vector: np.ndarray | None = None, fail: bool = False):
        self.vector = vector
        self.fail = fail

    def embed_query(self, text: str) -> np.ndarray:
        if self.fail:
            raise EmbeddingError("Voyage transport error: ReadTimeout")
        return self.vector


def _seed_kb(conn) -> None:
    dim = 4
    with transaction(conn):
        conn.execute("INSERT INTO kb_sources VALUES ('src-a','Ảnh bảng giá','user_photo',NULL,'biblio-79-nguy-nhu-kon-tum',"
                     "'verified_branch','2026-11-14T00:00:00.000Z',NULL,NULL,'{}')")
        docs = [
            ("doc-hours", "Giờ mở cửa", "opening_hours", "Quán mở cửa 07:00 – 22:30 hằng ngày.", [1, 0, 0, 0]),
            ("doc-park", "Gửi xe", "faq", "Bãi đỗ xe có tính phí trong làng sinh viên.", [0, 1, 0, 0]),
            ("doc-room", "Phòng hội thảo", "room_rental", "Phòng 4 sức chứa 20 người.", [0, 0, 1, 0]),
        ]
        for i, (doc_id, title, cat, content, vec) in enumerate(docs):
            conn.execute("INSERT INTO kb_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                         (doc_id, title, cat, "fact", "biblio-79-nguy-nhu-kon-tum", "verified_branch", "src-a", None,
                          "2026-11-14T00:00:00.000Z", content, f"h{i}", json.dumps({"citations": ["src-a"]})))
            conn.execute("INSERT INTO kb_chunks VALUES (?,?,?,?,?,?,?)", (f"{doc_id}#0", doc_id, 0, title, f"{title}\n{content}", f"c{i}", 10))
            conn.execute("INSERT INTO kb_chunks_fts(chunk_id, title, content) VALUES (?,?,?)", (f"{doc_id}#0", fold_vi(title), fold_vi(content)))
            conn.execute("INSERT INTO kb_embeddings VALUES (?,?,?,?,?,?)",
                         (f"{doc_id}#0", "voyage-4-lite", dim, f"c{i}", vector_to_blob(l2_normalize(np.array([vec], dtype=np.float32))[0]),
                          "2026-11-14T00:00:00.000Z"))
        conn.executemany("INSERT INTO kb_meta VALUES (?,?)", [("embedding_model", "voyage-4-lite"), ("embedding_dimension", str(dim))])


def test_migrations_are_idempotent(db):
    assert apply_migrations(db) == []
    versions = [r[0] for r in db.execute("SELECT version FROM schema_migrations ORDER BY version")]
    assert versions[:2] == [1, 2]


def test_fold_vi_handles_d_stroke_and_tones():
    assert fold_vi("Cà phê ĐEN đá") == "ca phe den da"
    assert fts_query("Giờ mở cửa?") == '"gio" OR "mo" OR "cua"'


def test_vector_blob_roundtrip():
    vec = l2_normalize(np.array([[3.0, 4.0]], dtype=np.float32))[0]
    assert np.allclose(blob_to_vector(vector_to_blob(vec), 2), [0.6, 0.8])


def test_vector_search_ranks_and_attributes(db):
    _seed_kb(db)
    index = KnowledgeIndex.load(db)
    res = search_knowledge(db, index, FakeEmbedder(np.array([0, 0.1, 1, 0], dtype=np.float32)), "phòng 20 người")
    assert res.mode == "vector"
    assert res.hits[0].document_id == "doc-room"
    assert res.hits[0].source_title == "Ảnh bảng giá"
    assert res.hits[0].citations == ("src-a",)


def test_min_score_returns_empty_for_unrelated_query(db):
    _seed_kb(db)
    index = KnowledgeIndex.load(db)
    res = search_knowledge(db, index, FakeEmbedder(np.array([-1, -1, -1, 0], dtype=np.float32)), "thời tiết Paris")
    assert res.mode == "empty" and res.hits == []


def test_embedding_failure_falls_back_to_keyword_search(db):
    _seed_kb(db)
    index = KnowledgeIndex.load(db)
    res = search_knowledge(db, index, FakeEmbedder(fail=True), "gui xe co mat phi khong")
    assert res.mode == "keyword_fallback"
    assert res.hits[0].document_id == "doc-park"
    assert "ReadTimeout" in (res.error or "")


def test_keyword_search_is_diacritic_insensitive(db):
    _seed_kb(db)
    assert keyword_search(db, "GIỜ MỞ CỬA")[0].document_id == "doc-hours"


def test_chunker_prefixes_title_and_splits_long_documents():
    from ingest import MAX_CHUNK_CHARS, chunk_document

    long_doc = {"id": "d", "title": "T", "content": " ".join(["Câu số một rất dài." for _ in range(120)])}
    chunks = chunk_document(long_doc)
    assert len(chunks) > 1
    assert all(c["content"].startswith("T\n") for c in chunks)
    assert all(len(c["content"]) <= MAX_CHUNK_CHARS + 2 for c in chunks)
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))


@pytest.mark.skipif(not (REPO_ROOT / "data" / "cafe.db").exists(), reason="run scripts/knowledge/ingest.py first")
def test_built_database_has_indexed_knowledge_and_catalog():
    from app.db.connection import connect

    conn = connect(REPO_ROOT / "data" / "cafe.db", read_only=True)
    try:
        assert conn.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0] == 51
        assert conn.execute("SELECT COUNT(*) FROM menu_items WHERE availability='available'").fetchone()[0] == 51  # owner decision: in stock by default
        n_chunks = conn.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0]
        assert n_chunks > 0
        assert conn.execute("SELECT COUNT(*) FROM kb_embeddings WHERE dimension=512 AND length(vector)=2048").fetchone()[0] == n_chunks
    finally:
        conn.close()
