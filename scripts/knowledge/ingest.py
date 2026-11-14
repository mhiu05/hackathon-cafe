"""Build/refresh the SQLite knowledge base + café reference data at DATABASE_PATH (default data/cafe.db).

    uv run python scripts/knowledge/ingest.py              # migrate, load catalog, chunk, embed (cache-first), index
    uv run python scripts/knowledge/ingest.py --offline    # never call Voyage; fail if any chunk lacks a cached vector
    uv run python scripts/knowledge/ingest.py --db data/test.db

Idempotent. Safe to re-run on a database that already holds app tables (orders, chats):
- catalog tables are UPSERTed (menu availability/is_orderable set by staff are preserved);
- kb_* tables are replaced wholesale (no app table references them);
- embeddings come from data/knowledge/embeddings/<model>_<dim>.jsonl keyed by content_hash; only new chunks hit Voyage.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import EMBEDDINGS_DIR, KNOWLEDGE_DIR, NORMALIZED_DIR, read_json, read_jsonl, utc_now, write_json  # noqa: E402

from app.db.connection import connect, transaction  # noqa: E402
from app.db.migrate import apply_migrations  # noqa: E402
from app.knowledge.embeddings import VoyageEmbedder, l2_normalize, vector_to_blob  # noqa: E402
from app.knowledge.text import content_hash, estimate_tokens, fold_vi  # noqa: E402
from app.settings import load_settings  # noqa: E402

INGESTIBLE = {"owner_verified", "verified_branch", "brand_general", "conflicting"}
MAX_CHUNK_CHARS = 900


# ------------------------------------------------------------------------------------------ chunking

def chunk_document(doc: dict) -> list[dict]:
    """Structure-aware chunking: whole document if short, else sentence-packed segments <= MAX_CHUNK_CHARS.

    Every chunk is prefixed with the document title so it is self-describing for embeddings and citations.
    """
    body = doc["content"]
    segments: list[str] = []
    if len(body) <= MAX_CHUNK_CHARS:
        segments = [body]
    else:
        current = ""
        for sentence in _sentences(body):
            if current and len(current) + 1 + len(sentence) > MAX_CHUNK_CHARS:
                segments.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            segments.append(current)
    chunks = []
    for idx, seg in enumerate(segments):
        text = f"{doc['title']}\n{seg}"
        chunks.append({"id": f"{doc['id']}#{idx}", "document_id": doc["id"], "chunk_index": idx, "heading": doc["title"],
                       "content": text, "content_hash": content_hash(text), "token_estimate": estimate_tokens(text)})
    return chunks


def _sentences(text: str) -> list[str]:
    out, start = [], 0
    for i, ch in enumerate(text):
        if ch in ".;!?" and (i + 1 == len(text) or text[i + 1] == " "):
            out.append(text[start : i + 1].strip())
            start = i + 1
    if text[start:].strip():
        out.append(text[start:].strip())
    return out


# ---------------------------------------------------------------------------------- embedding cache

def cache_path(model: str, dim: int) -> Path:
    return EMBEDDINGS_DIR / f"{model}_{dim}.jsonl"


def load_cache(path: Path, dim: int) -> dict[str, np.ndarray]:
    cache: dict[str, np.ndarray] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                vec = np.frombuffer(base64.b64decode(row["vector_b64"]), dtype="<f4")
                if vec.shape[0] == dim:
                    cache[row["content_hash"]] = vec
    return cache


def append_cache(path: Path, model: str, dim: int, items: list[tuple[str, np.ndarray]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        for h, vec in items:
            fh.write(json.dumps({"content_hash": h, "model": model, "dimension": dim,
                                 "vector_b64": base64.b64encode(np.asarray(vec, dtype="<f4").tobytes()).decode()}) + "\n")


# ------------------------------------------------------------------------------------------- loaders

def load_catalog(conn, profile: dict, menu: dict, services: dict, now: str) -> None:
    conn.execute(
        "INSERT INTO cafe_profile(branch_id, brand_name, display_name, address, latitude, longitude, phone, open_time, close_time,"
        " google_maps_url, facebook_url, data_status, profile_json, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(branch_id) DO UPDATE SET brand_name=excluded.brand_name, display_name=excluded.display_name,"
        " address=excluded.address, latitude=excluded.latitude, longitude=excluded.longitude, phone=excluded.phone,"
        " open_time=excluded.open_time, close_time=excluded.close_time, google_maps_url=excluded.google_maps_url,"
        " facebook_url=excluded.facebook_url, data_status=excluded.data_status, profile_json=excluded.profile_json,"
        " updated_at=excluded.updated_at",
        (profile["branch_id"], profile["brand_name"], profile["display_name"], profile["address"]["value"],
         profile["location"]["latitude"], profile["location"]["longitude"], profile["phone"]["value"],
         profile["opening_hours"]["open"], profile["opening_hours"]["close"], profile["channels"]["google_maps"]["url"],
         profile["channels"]["facebook"]["url"], profile["data_status"], json.dumps(profile, ensure_ascii=False), now),
    )
    for c in menu["categories"]:
        conn.execute(
            "INSERT INTO menu_categories(id, name, kind, sort_order) VALUES (?,?,?,?)"
            " ON CONFLICT(id) DO UPDATE SET name=excluded.name, kind=excluded.kind, sort_order=excluded.sort_order",
            (c["id"], c["name"], c["kind"], c["sort_order"]),
        )
    for i in menu["items"]:
        # availability / availability_note / is_orderable are staff-managed after first load: keep existing values.
        conn.execute(
            "INSERT INTO menu_items(id, category_id, name, name_search, base_price_vnd, availability, availability_note, is_orderable,"
            " price_verified, description, note, needs_review_json, suggested_tags_json, source_id, sort_order, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(id) DO UPDATE SET category_id=excluded.category_id, name=excluded.name, name_search=excluded.name_search,"
            " base_price_vnd=excluded.base_price_vnd, price_verified=excluded.price_verified, description=excluded.description,"
            " note=excluded.note, needs_review_json=excluded.needs_review_json, suggested_tags_json=excluded.suggested_tags_json,"
            " source_id=excluded.source_id, sort_order=excluded.sort_order, updated_at=excluded.updated_at",
            (i["id"], i["category_id"], i["name"], i["name_search"], i["base_price_vnd"], i["availability"], i["availability_note"],
             int(i["is_orderable"]), int(i["price_verified"]), i["description"], i["note"], json.dumps(i["needs_review"], ensure_ascii=False),
             json.dumps(i["suggested_tags"], ensure_ascii=False), i["source_id"], i["sort_order"], now),
        )
        for v in i["variants"]:
            conn.execute(
                "INSERT INTO menu_item_variants(id, item_id, label, price_vnd, sort_order) VALUES (?,?,?,?,?)"
                " ON CONFLICT(id) DO UPDATE SET label=excluded.label, price_vnd=excluded.price_vnd, sort_order=excluded.sort_order",
                (v["id"], i["id"], v["label"], v["price_vnd"], v["sort_order"]),
            )
    conn.execute("DELETE FROM coworking_packages")
    conn.execute("DELETE FROM meeting_rooms")
    conn.execute("DELETE FROM service_facts")
    for p in services["coworking_packages"]:
        conn.execute("INSERT INTO coworking_packages VALUES (?,?,?,?,?,?,?,?)",
                     (p["id"], p["label"], p["duration_days"], p["price_vnd"], int(p["includes_vat"]), int(p["price_verified"]),
                      p["source_id"], p["sort_order"]))
    for r in services["meeting_rooms"]:
        conn.execute("INSERT INTO meeting_rooms VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (r["id"], r["name"], r["area_m2"], r["capacity_max"], r["capacity_theater"], r["capacity_tables"], r["layout_note"],
                      r["session_hours"], r["price_vnd"], int(r["includes_vat"]), int(r["price_verified"]), r["source_id"], r["sort_order"]))
    for f in services["service_facts"]:
        conn.execute("INSERT INTO service_facts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (f["id"], f["scope"], f["kind"], f["label"], f["price_from_vnd"], f["price_to_vnd"], f["unit"], f["note"],
                      f["verification_status"], f["source_id"], f["sort_order"]))


def load_knowledge(conn, sources: list[dict], docs: list[dict], chunks: list[dict], vectors: dict[str, np.ndarray],
                   model: str, dim: int, now: str, extra_meta: dict[str, str] | None = None) -> None:
    for table in ("kb_embeddings", "kb_chunks_fts", "kb_chunks", "kb_documents", "kb_sources", "kb_meta"):
        conn.execute(f"DELETE FROM {table}")
    for s in sources:
        conn.execute("INSERT INTO kb_sources VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (s["id"], s["title"], s["source_type"], s["url"], s["branch_id"], s["verification_status"], s["retrieved_at"],
                      s.get("published_at"), s.get("notes"), json.dumps(s.get("metadata") or {}, ensure_ascii=False)))
    for d in docs:
        conn.execute("INSERT INTO kb_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                     (d["id"], d["title"], d["category"], d["content_kind"], d["branch_id"], d["verification_status"], d["source_id"],
                      d["source_url"], d["retrieved_at"], d["content"], d["content_hash"], json.dumps(d["metadata"], ensure_ascii=False)))
    titles = {d["id"]: d["title"] for d in docs}
    for c in chunks:
        conn.execute("INSERT INTO kb_chunks VALUES (?,?,?,?,?,?,?)",
                     (c["id"], c["document_id"], c["chunk_index"], c["heading"], c["content"], c["content_hash"], c["token_estimate"]))
        conn.execute("INSERT INTO kb_chunks_fts(chunk_id, title, content) VALUES (?,?,?)",
                     (c["id"], fold_vi(titles[c["document_id"]]), fold_vi(c["content"])))
        vec = vectors.get(c["content_hash"])
        if vec is not None:
            conn.execute("INSERT INTO kb_embeddings VALUES (?,?,?,?,?,?)",
                         (c["id"], model, dim, c["content_hash"], vector_to_blob(vec), now))
    corpus = hashlib.sha256("".join(sorted(c["content_hash"] for c in chunks)).encode()).hexdigest()
    meta = {"embedding_model": model, "embedding_dimension": str(dim), "built_at": now, "chunk_count": str(len(chunks)),
            "embedded_count": str(sum(c["content_hash"] in vectors for c in chunks)), "corpus_hash": corpus,
            "branch_id": "biblio-79-nguy-nhu-kon-tum", **(extra_meta or {})}
    conn.executemany("INSERT INTO kb_meta(key, value) VALUES (?,?)", list(meta.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, help="override DATABASE_PATH")
    parser.add_argument("--offline", action="store_true", help="do not call Voyage; require cached vectors")
    args = parser.parse_args()

    settings = load_settings()
    db_path = args.db.resolve() if args.db else settings.database_path
    model, dim = settings.voyage_embedding_model, settings.voyage_embedding_dimension

    profile = read_json(NORMALIZED_DIR / "cafe_profile.json")
    menu = read_json(NORMALIZED_DIR / "menu.json")
    services = read_json(NORMALIZED_DIR / "services.json")
    sources = read_json(NORMALIZED_DIR / "source_manifest.json")["sources"]
    all_docs = read_jsonl(NORMALIZED_DIR / "documents.jsonl")
    docs = [d for d in all_docs if d["verification_status"] in INGESTIBLE]
    chunks = [c for d in docs for c in chunk_document(d)]
    if len({c["content_hash"] for c in chunks}) != len(chunks):
        raise SystemExit("Duplicate chunk content detected; fix normalized documents first")

    cpath = cache_path(model, dim)
    cache = load_cache(cpath, dim)
    missing = [c for c in chunks if c["content_hash"] not in cache]
    voyage_tokens = 0
    if missing:
        if args.offline:
            raise SystemExit(f"--offline: {len(missing)} chunks have no cached embedding in {cpath}")
        embedder = VoyageEmbedder(api_key=settings.voyage_api_key, model=model, dimension=dim, timeout_s=60, max_retries=2)
        matrix = embedder.embed_documents([c["content"] for c in missing])
        new = [(c["content_hash"], l2_normalize(matrix[i : i + 1])[0]) for i, c in enumerate(missing)]
        append_cache(cpath, model, dim, new)
        cache.update(dict(new))
        voyage_tokens = embedder.total_tokens

    now = utc_now()
    conn = connect(db_path)
    try:
        applied = apply_migrations(conn)
        with transaction(conn):
            load_catalog(conn, profile, menu, services, now)
            booking = next(f["label"] for f in services["service_facts"] if f["id"] == "room-policy-availability")
            load_knowledge(conn, sources, docs, chunks, cache, model, dim, now, extra_meta={
                "menu_as_of": menu["as_of"], "menu_price_basis": menu["price_basis"],
                "services_as_of": services["as_of"], "services_price_basis": services["price_basis"],
                "booking_policy": booking, "data_notice": "Thông tin và giá theo ảnh chụp tại quán ngày 14/11/2026 và nguồn công khai; quán chưa xác nhận."})
    finally:
        conn.close()

    stats = {"db_path": db_path.relative_to(Path.cwd()).as_posix() if db_path.is_relative_to(Path.cwd()) else db_path.as_posix(),
             "built_at": now, "migrations_applied_now": applied, "documents_total": len(all_docs), "documents_indexed": len(docs),
             "documents_skipped_not_ingestible": len(all_docs) - len(docs), "chunks": len(chunks),
             "embeddings_from_cache": len(chunks) - len(missing), "embeddings_new": len(missing), "voyage_tokens_used": voyage_tokens,
             "embedding_model": model, "embedding_dimension": dim, "menu_items": len(menu["items"]),
             "menu_variants": sum(len(i["variants"]) for i in menu["items"]), "coworking_packages": len(services["coworking_packages"]),
             "meeting_rooms": len(services["meeting_rooms"]), "service_facts": len(services["service_facts"]), "sources": len(sources)}
    if not args.db:  # only the canonical database updates the committed stats file
        write_json(KNOWLEDGE_DIR / "ingest_stats.json", stats)
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
