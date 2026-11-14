from contextlib import closing
from pathlib import Path
import importlib.util

from app.db.connection import connect
from app.orders.service import LineInput, create_draft, confirm_draft
from app.staff.service import create_request

_spec = importlib.util.spec_from_file_location("reset_demo", Path(__file__).resolve().parents[2] / "scripts/demo/reset_demo.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
reset_demo = _module.reset_demo


def test_reset_demo_backs_up_and_preserves_catalog_and_knowledge(conn, db_path, tmp_path):
    lines = [LineInput("menu_024", None, 1)]
    d = create_draft(conn, conversation_id="a" * 32, lines=lines, customer_name=None, table_label=None, note=None)
    confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    create_draft(conn, conversation_id="a" * 32, lines=lines, customer_name=None, table_label=None, note=None)
    conn.execute("INSERT INTO admin_sessions VALUES ('hash','2026-01-01','2027-01-01')")
    create_request(conn, conversation_id="a" * 32, kind="wifi", table_label=None, note=None)
    conn.execute("UPDATE menu_items SET availability='sold_out',is_orderable=0")
    sessions = tmp_path / "sessions.db"
    sessions.write_bytes(b"demo session")
    before = conn.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0]
    counts = reset_demo(db_path, sessions, tmp_path / "backups")
    assert counts["orders"] == counts["order_drafts"] == counts["admin_sessions"] == 0
    assert conn.execute("SELECT COUNT(*) FROM customer_accounts").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0] == before == 56
    assert conn.execute("SELECT COUNT(*) FROM menu_items WHERE availability='available' AND is_orderable=1").fetchone()[0] == 51
    assert conn.execute("SELECT COUNT(*) FROM staff_requests").fetchone()[0] == 0
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    backup = next((tmp_path / "backups").glob("cafe-*.db"))
    with closing(connect(backup, read_only=True)) as c:
        assert c.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
    assert not sessions.exists()
    d = create_draft(conn, conversation_id="a" * 32, lines=lines, customer_name=None, table_label=None, note=None)
    order,_ = confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    assert order["code"] == "BB-0001"
