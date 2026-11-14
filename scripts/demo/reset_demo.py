"""Back up and reset commerce/session data; keep the local catalog and knowledge.

Stop uvicorn before running: uv run python scripts/demo/reset_demo.py
"""
from __future__ import annotations

import argparse
import json
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.db.connection import connect, transaction  # noqa: E402
from app.db.migrate import apply_migrations  # noqa: E402
from app.settings import load_settings  # noqa: E402


def reset_demo(db_path: Path, sessions_db: Path, backups_dir: Path) -> dict[str, int]:
    if not db_path.is_file():
        raise FileNotFoundError("Database does not exist; run offline ingestion first.")
    menu = json.loads((REPO_ROOT / "data/knowledge/normalized/menu.json").read_text(encoding="utf-8"))
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backups_dir / f"cafe-{stamp}-{uuid4().hex[:8]}.db"
    with closing(connect(db_path)) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        with closing(connect(backup)) as dst:
            conn.backup(dst)
        apply_migrations(conn)  # a DB from an older checkout may lack newer tables (e.g. staff_requests)
        with transaction(conn):
            conn.execute("UPDATE order_drafts SET order_id=NULL,status='discarded'")
            for table in ("order_events", "order_items", "order_drafts", "orders", "staff_requests", "agent_tool_calls", "agent_runs",
                          "admin_sessions"):
                conn.execute(f"DELETE FROM {table}")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('orders','order_items','order_events','staff_requests','agent_tool_calls')")
            conn.execute("UPDATE menu_items SET availability='available',is_orderable=1")
            for item in menu["items"]:
                conn.execute("UPDATE menu_items SET availability_note=? WHERE id=?", (item["availability_note"], item["id"]))
        counts = {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in ("orders", "order_drafts", "admin_sessions", "agent_runs", "agent_tool_calls", "customer_accounts", "menu_items", "kb_chunks")}
    for suffix in ("", "-wal", "-shm", "-journal"):
        candidate = sessions_db.with_name(sessions_db.name + suffix)
        candidate.unlink(missing_ok=True)
    return counts


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=settings.database_path)
    parser.add_argument("--sessions-db", type=Path, default=settings.agent_sessions_db_path)
    parser.add_argument("--backups-dir", type=Path, default=REPO_ROOT / "data/backups")
    args = parser.parse_args()
    print(json.dumps(reset_demo(args.db, args.sessions_db, args.backups_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()
