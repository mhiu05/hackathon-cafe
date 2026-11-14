"""Verify normalized data, the SQLite knowledge base and retrieval quality; write the ingestion report.

    uv run python scripts/knowledge/verify.py              # full: data + DB checks + retrieval eval (calls Voyage for ~32 queries)
    uv run python scripts/knowledge/verify.py --offline    # no Voyage calls: keyword-fallback retrieval only

Outputs: data/knowledge/eval/kb_eval_results.json and data/knowledge/ingestion_report.md. Exit code 1 if any check FAILs.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import (  # noqa: E402
    BRAND_ID, BRANCH_ID, CURATED_DIR, EVAL_DIR, KNOWLEDGE_DIR, NORMALIZED_DIR, REPO_ROOT, read_json, read_jsonl, write_json,
)

from app.db.connection import connect  # noqa: E402
from app.knowledge.embeddings import VoyageEmbedder  # noqa: E402
from app.knowledge.retrieval import KnowledgeIndex, search_knowledge  # noqa: E402
from app.settings import load_settings  # noqa: E402

STATUSES = {"owner_verified", "verified_branch", "brand_general", "unverified_branch", "conflicting", "rejected"}
KINDS = {"fact", "review", "inference", "event", "product", "service"}
INGESTIBLE = {"owner_verified", "verified_branch", "brand_general", "conflicting"}
REQUIRED_DOC_FIELDS = ("id", "title", "content", "category", "branch_id", "source_type", "source_url", "verification_status",
                       "content_kind", "retrieved_at", "metadata")
SECRET_PATTERNS = [re.compile(p) for p in (r"sk-[A-Za-z0-9_\-]{20,}", r"apify_api_[A-Za-z0-9]{20,}", r"pa-[A-Za-z0-9_\-]{30,}")]


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def check(self, name: str, ok: bool, detail: str = "", *, partial: bool = False) -> bool:
        self.rows.append((name, "PASS" if ok else ("PARTIAL" if partial else "FAIL"), detail))
        return ok

    @property
    def failed(self) -> bool:
        return any(s == "FAIL" for _, s, _ in self.rows)


def check_files(rep: Report) -> dict:
    out: dict = {}
    for name in ("cafe_profile.json", "menu.json", "services.json", "source_manifest.json", "events.json", "social_insights.json",
                 "unverified_claims.json"):
        try:
            out[name] = read_json(NORMALIZED_DIR / name)
            rep.check(f"parse {name}", True)
        except Exception as exc:  # noqa: BLE001
            rep.check(f"parse {name}", False, str(exc))
    for name in ("external_knowledge.json", "synthesis_documents.json"):
        try:
            read_json(CURATED_DIR / name)
            rep.check(f"parse curated/{name}", True)
        except Exception as exc:  # noqa: BLE001
            rep.check(f"parse curated/{name}", False, str(exc))
    docs = read_jsonl(NORMALIZED_DIR / "documents.jsonl")
    out["documents"] = docs
    rep.check("parse documents.jsonl", True, f"{len(docs)} records")
    return out


def check_data(rep: Report, data: dict) -> None:
    docs, menu, services = data["documents"], data["menu.json"], data["services.json"]
    sources = {s["id"]: s for s in data["source_manifest.json"]["sources"]}
    missing_fields = [d["id"] for d in docs if any(f not in d for f in REQUIRED_DOC_FIELDS)]
    rep.check("documents have required fields", not missing_fields, ", ".join(missing_fields[:5]))
    bad_enum = [d["id"] for d in docs if d["verification_status"] not in STATUSES or d["content_kind"] not in KINDS]
    rep.check("documents use allowed status/kind enums", not bad_enum, ", ".join(bad_enum[:5]))
    rep.check("no web data marked owner_verified",
              not any(d["verification_status"] == "owner_verified" for d in docs)
              and not any(s["verification_status"] == "owner_verified" for s in sources.values()))
    wrong_branch = [d["id"] for d in docs if d["verification_status"] in INGESTIBLE and d["branch_id"] not in (BRANCH_ID, BRAND_ID)]
    rep.check("ingestible documents belong to branch 79 NNKT or brand-general", not wrong_branch, ", ".join(wrong_branch))
    tam_khuong = [d["id"] for d in docs if d["verification_status"] in INGESTIBLE and "70 Tam Khương" in d["content"]
                  and d["category"] != "branches"]
    rep.check("70 Tam Khương facts not mixed into operational documents", not tam_khuong, ", ".join(tam_khuong))
    unknown_src = [d["id"] for d in docs if d["source_id"] not in sources]
    rep.check("every document cites a source in source_manifest", not unknown_src, ", ".join(unknown_src))
    hashes = [d["content_hash"] for d in docs]
    rep.check("no duplicate documents (content_hash unique)", len(hashes) == len(set(hashes)))
    items = menu["items"]
    rep.check("menu has 51 items in 9 categories", len(items) == 51 and len(menu["categories"]) == 9, f"{len(items)} items")
    bad_price = [i["id"] for i in items if not ((isinstance(i["base_price_vnd"], int) and i["base_price_vnd"] > 0) ^ bool(i["variants"]))]
    rep.check("each item has exactly one of base_price_vnd or variants (integer VND)", not bad_price, ", ".join(bad_price))
    bundle = read_json(REPO_ROOT / "biblio_cafe_kb_bundle" / "biblio_menu.json")
    lost = []
    for raw in bundle["items"]:
        norm = next(i for i in items if i["id"] == raw["id"])
        raw_prices = sorted([v["price_vnd"] for v in raw.get("variants") or []] or [raw["price_vnd"]])
        norm_prices = sorted({v["price_vnd"] for v in norm["variants"]} or {norm["base_price_vnd"]})
        if sorted(set(raw_prices)) != norm_prices:
            lost.append(raw["id"])
    rep.check("no price information lost vs. bundle", not lost, ", ".join(lost))
    rep.check("every item in stock by default (owner decision)", all(i["availability"] == "available" for i in items))
    rep.check("services: 3 coworking packages, 5 rooms",
              len(services["coworking_packages"]) == 3 and len(services["meeting_rooms"]) == 5)
    unverified = data["unverified_claims.json"]
    rep.check("unverified claims recorded", len(unverified) >= 10, f"{len(unverified)} claims")
    ev = data["events.json"]
    rep.check("no upcoming event presented as verified", ev["upcoming_verified"] == 0
              and all(e["event_status"] != "upcoming" for e in ev["events"]))


def check_secrets(rep: Report) -> None:
    try:
        tracked = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=REPO_ROOT, capture_output=True, text=True,
                                 check=True).stdout.splitlines()
    except Exception as exc:  # noqa: BLE001
        rep.check("secret scan of git-visible files", False, f"git unavailable: {exc}")
        return
    hits = []
    for rel in tracked:
        if rel.startswith((".agents/", ".claude/")) or rel.endswith((".png", ".jpg", ".db", ".exe")):
            continue
        p = REPO_ROOT / rel
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(rx.search(text) for rx in SECRET_PATTERNS):
            hits.append(rel)
    ignored = subprocess.run(["git", "check-ignore", ".env", "data/cafe.db", "data/knowledge/raw/x"], cwd=REPO_ROOT,
                             capture_output=True, text=True).stdout.split()
    rep.check("no secrets in git-visible files", not hits, ", ".join(hits))
    rep.check(".env, data/cafe.db and raw/ are gitignored", len(ignored) == 3, " ".join(ignored))


def check_db(rep: Report, db_path: Path, model: str, dim: int) -> dict:
    stats: dict = {}
    if not rep.check("database file exists", db_path.exists(), str(db_path)):
        return stats
    conn = connect(db_path, read_only=True)
    try:
        rep.check("PRAGMA integrity_check", conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
        rep.check("PRAGMA foreign_key_check", not conn.execute("PRAGMA foreign_key_check").fetchall())
        versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
        rep.check("migrations 0001, 0002 applied", versions[:2] == [1, 2], str(versions))
        for t in ("menu_items", "menu_item_variants", "menu_categories", "coworking_packages", "meeting_rooms", "service_facts",
                  "kb_sources", "kb_documents", "kb_chunks", "kb_embeddings", "kb_chunks_fts"):
            stats[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        rep.check("every chunk has an embedding", stats["kb_chunks"] == stats["kb_embeddings"] > 0,
                  f"{stats['kb_embeddings']}/{stats['kb_chunks']}")
        rep.check("FTS rows match chunks", stats["kb_chunks_fts"] == stats["kb_chunks"])
        bad_dim = conn.execute("SELECT COUNT(*) FROM kb_embeddings WHERE dimension != ? OR length(vector) != ? OR model != ?",
                               (dim, dim * 4, model)).fetchone()[0]
        rep.check(f"embedding model/dimension = {model}/{dim}", bad_dim == 0, f"{bad_dim} mismatched")
        stale = conn.execute("SELECT COUNT(*) FROM kb_embeddings e JOIN kb_chunks c ON c.id=e.chunk_id "
                             "WHERE c.content_hash != e.content_hash").fetchone()[0]
        rep.check("embeddings match current chunk content", stale == 0)
        rejected = conn.execute("SELECT COUNT(*) FROM kb_documents WHERE verification_status NOT IN "
                                "('owner_verified','verified_branch','brand_general','conflicting')").fetchone()[0]
        rep.check("no rejected/pending documents indexed", rejected == 0)
        stats["meta"] = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM kb_meta")}
    finally:
        conn.close()
    return stats


SQL_CHECKS = {
    "coworking_month_price": ("SELECT price_vnd FROM coworking_packages WHERE id='cowork-1-month'", lambda rows: rows == [(990000,)]),
    "room_for_20": ("SELECT name, price_vnd FROM meeting_rooms WHERE capacity_max >= 20 ORDER BY capacity_max, price_vnd LIMIT 1",
                    lambda rows: rows == [("Phòng 4", 770000)]),
    "room_tables_60": ("SELECT name FROM meeting_rooms WHERE capacity_tables >= 60 ORDER BY price_vnd LIMIT 1",
                       lambda rows: rows == [("Phòng 3",)]),
    "drinks_under_50k": ("SELECT COUNT(*) FROM menu_items i JOIN menu_categories c ON c.id=i.category_id "
                         "LEFT JOIN menu_item_variants v ON v.item_id=i.id "
                         "WHERE c.kind='drink' AND COALESCE(i.base_price_vnd, v.price_vnd) < 50000",
                         lambda rows: rows[0][0] > 0),
    "matcha_items": ("SELECT name FROM menu_items WHERE category_id='matcha' ORDER BY sort_order",
                     lambda rows: [r[0] for r in rows] == ["Matcha latte", "Matcha cookie", "Matcha kem chesse",
                                                           "Matcha xoài nhiệt đới", "Matcha dừa non"]),
    "food_items": ("SELECT COUNT(*) FROM menu_items i JOIN menu_categories c ON c.id=i.category_id WHERE c.kind='food'",
                   lambda rows: rows[0][0] == 12),
    "yakult_available": ("SELECT availability, availability_note IS NULL FROM menu_items WHERE id='menu_019'",
                         lambda rows: rows == [("available", 1)]),
}


def run_eval(rep: Report, db_path: Path, settings, offline: bool) -> dict:
    questions = read_json(EVAL_DIR / "kb_eval_questions.json")
    conn = connect(db_path, read_only=True)
    index = KnowledgeIndex.load(conn)
    embedder = None if offline else VoyageEmbedder(api_key=settings.voyage_api_key, model=settings.voyage_embedding_model,
                                                   dimension=settings.voyage_embedding_dimension, timeout_s=15)
    results = []
    for q in questions["questions"]:
        row: dict = {"id": q["id"], "question": q["question"], "answer_path": q["answer_path"]}
        if q.get("sql_check"):
            sql, pred = SQL_CHECKS[q["sql_check"]]
            rows = [tuple(r) for r in conn.execute(sql).fetchall()]
            row["sql_check"] = {"name": q["sql_check"], "pass": bool(pred(rows)), "rows": rows[:5]}
        if q["expected_doc_ids"]:
            vec = search_knowledge(conn, index, embedder, q["question"], top_k=5) if embedder else None
            kw = search_knowledge(conn, index, None, q["question"], top_k=5)
            for label, res in (("vector", vec), ("keyword", kw)):
                if res is None:
                    continue
                docs = [h.document_id for h in res.hits]
                empty_ok = bool(q.get("accept_empty")) and not docs and label == "vector"
                row[label] = {"mode": res.mode, "top5": docs, "scores": [h.score for h in res.hits], "error": res.error,
                              "hit": empty_ok or any(d in q["expected_doc_ids"] for d in docs), "accepted_empty": empty_ok,
                              "rank": next((i + 1 for i, d in enumerate(docs) if d in q["expected_doc_ids"]), None)}
        results.append(row)
    negatives = []
    for n in questions.get("negative_controls", []):
        if embedder:
            res = search_knowledge(conn, index, embedder, n["question"], top_k=5, min_score=0.0)
            negatives.append({"id": n["id"], "question": n["question"], "top_score": res.hits[0].score if res.hits else None,
                              "top_doc": res.hits[0].document_id if res.hits else None})
    conn.close()

    retrieval_rows = [r for r in results if "vector" in r or "keyword" in r]
    summary = {"questions": len(results), "retrieval_questions": len(retrieval_rows),
               "sql_checks": sum(1 for r in results if "sql_check" in r),
               "sql_pass": sum(1 for r in results if r.get("sql_check", {}).get("pass")),
               "keyword_hit_at_5": sum(1 for r in retrieval_rows if r.get("keyword", {}).get("hit")),
               "voyage_query_tokens": embedder.total_tokens if embedder else 0}
    if embedder:
        hits = [r for r in retrieval_rows if r["vector"]["hit"]]
        summary["vector_hit_at_5"] = len(hits)
        summary["vector_hit_at_1"] = sum(1 for r in retrieval_rows if r["vector"]["rank"] == 1)
        summary["vector_accepted_empty"] = sum(1 for r in retrieval_rows if r["vector"].get("accepted_empty"))
        summary["vector_mrr"] = round(sum(1 / r["vector"]["rank"] for r in hits if r["vector"]["rank"]) / len(retrieval_rows), 3)
        summary["negative_controls"] = negatives
        rep.check("retrieval hit@5 (vector) >= 90%", len(hits) >= 0.9 * len(retrieval_rows),
                  f"{len(hits)}/{len(retrieval_rows)}", partial=len(hits) >= 0.75 * len(retrieval_rows))
    rep.check("keyword fallback hit@5 >= 60%", summary["keyword_hit_at_5"] >= 0.6 * len(retrieval_rows),
              f"{summary['keyword_hit_at_5']}/{len(retrieval_rows)}", partial=True)
    rep.check("SQL fact checks", summary["sql_pass"] == summary["sql_checks"], f"{summary['sql_pass']}/{summary['sql_checks']}")
    out = {"summary": summary, "results": results}
    write_json(EVAL_DIR / "kb_eval_results.json", out)
    return out


def write_report(rep: Report, data: dict, db_stats: dict, evaluation: dict | None) -> None:
    ingest = read_json(KNOWLEDGE_DIR / "ingest_stats.json") if (KNOWLEDGE_DIR / "ingest_stats.json").exists() else {}
    social = data["social_insights.json"]
    sources = data["source_manifest.json"]["sources"]
    apify = [s for s in sources if (s.get("metadata") or {}).get("run_id")]
    runs = {s["metadata"]["run_id"]: s["metadata"] for s in apify}
    lines = ["# Ingestion report — Biblio 79 Ngụy Như Kon Tum", "",
             "> Sinh bởi `scripts/knowledge/verify.py`. Mọi số liệu dưới đây được đo khi chạy script, không ước lượng.", "",
             "## Kết quả kiểm tra", "", "| Check | Kết quả | Chi tiết |", "|---|---|---|"]
    lines += [f"| {n} | {s} | {d} |" for n, s, d in rep.rows]
    lines += ["", "## Ingestion", "", "```json", json.dumps(ingest, ensure_ascii=False, indent=1), "```", "",
              "## Bảng trong SQLite", "", "```json", json.dumps({k: v for k, v in db_stats.items() if k != "meta"}, indent=1), "```", "",
              "## Apify runs (chi phí thực tế do Apify báo cáo)", ""]
    total = 0.0
    for rid, m in runs.items():
        total += float(m.get("usage_total_usd") or 0)
        lines.append(f"- `{m.get('actor_id')}` run `{rid}` — usage_total_usd = {m.get('usage_total_usd')}")
    lines += [f"- **Tổng: {total:.4f} USD** (ngân sách 1 USD; trần cứng mỗi run 0.50 USD qua `max_total_charge_usd`).", "",
              "## Nguồn", "", "| Source | Loại | Trạng thái | URL |", "|---|---|---|---|"]
    lines += [f"| `{s['id']}` | {s['source_type']} | {s['verification_status']} | {s['url'] or '(local)'} |" for s in sources]
    tk, gr = social["tiktok"], social["google_maps_reviews"]
    lines += ["", "## Mạng xã hội", "",
              f"- TikTok: {tk['collected']} video — nhận {tk['accepted']}, chờ xác minh {tk['pending']}, loại {tk['rejected']}.",
              f"- Google Maps reviews: {gr['collected']} review ({gr['date_range'][0]} → {gr['date_range'][1]}), loại lạc đề {gr['excluded_off_topic']}; "
              "không thu thập dữ liệu cá nhân.", ""]
    if evaluation:
        s = evaluation["summary"]
        lines += ["## Đánh giá retrieval", "", "```json", json.dumps(s, ensure_ascii=False, indent=1), "```", "",
                  "| Q | Path | Vector top-1 | Hit@5 | Rank | Keyword hit |", "|---|---|---|---|---|---|"]
        for r in evaluation["results"]:
            v, k = r.get("vector") or {}, r.get("keyword") or {}
            top = v.get("top5", [None])[0] if v.get("top5") else "-"
            lines.append(f"| {r['id']} | {r['answer_path']} | {top} | {v.get('hit', '-')} | {v.get('rank', '-')} | {k.get('hit', '-')} |")
        sql = [r for r in evaluation["results"] if "sql_check" in r]
        lines += ["", "SQL checks: " + ", ".join(f"{r['id']}={'PASS' if r['sql_check']['pass'] else 'FAIL'}" for r in sql), ""]
    lines += ["## Còn thiếu / chưa xác minh", ""]
    lines += [f"- {c['claim']} (`{c['source_id']}`)" for c in data["unverified_claims.json"]]
    (KNOWLEDGE_DIR / "ingestion_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--db", type=Path)
    args = parser.parse_args()
    settings = load_settings()
    db_path = args.db.resolve() if args.db else settings.database_path
    rep = Report()
    data = check_files(rep)
    check_data(rep, data)
    check_secrets(rep)
    db_stats = check_db(rep, db_path, settings.voyage_embedding_model, settings.voyage_embedding_dimension)
    evaluation = run_eval(rep, db_path, settings, args.offline) if db_path.exists() else None
    write_report(rep, data, db_stats, evaluation)
    width = max(len(n) for n, _, _ in rep.rows)
    for n, s, d in rep.rows:
        print(f"{s:8} {n.ljust(width)}  {d}")
    if evaluation:
        print(json.dumps(evaluation["summary"], ensure_ascii=False))
    sys.exit(1 if rep.failed else 0)


if __name__ == "__main__":
    main()
