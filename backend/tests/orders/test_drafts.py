import pytest
from app.errors import ApiError
from app.orders.service import LineInput, create_draft, confirm_draft, discard_draft
CONV = "0" * 32
LINES = [LineInput("menu_024", None, 1)]

def _draft(conn): return create_draft(conn, conversation_id=CONV, lines=LINES, customer_name=None, table_label=None, note=None)

def test_create_draft_creates_no_order(conn):
    d = _draft(conn)
    assert d["status"] == "open" and d["quote"]["total_vnd"] == 45000 and len(d["draft_id"]) == 32
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0

def test_confirm_draft_is_idempotent(conn):
    d = _draft(conn)
    o1, r1 = confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    o2, r2 = confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    assert (o1["code"], o1["source"], r1, r2, o1["id"] == o2["id"]) == ("BB-0001", "agent_draft", False, True, True)
    assert conn.execute("SELECT status FROM order_drafts").fetchone()[0] == "confirmed"

def test_confirm_price_changed_refreshes_quote(conn):
    d = _draft(conn)
    conn.execute("UPDATE menu_items SET base_price_vnd=50000 WHERE id='menu_024'")
    with pytest.raises(ApiError) as e: confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    assert e.value.code == "PRICE_CHANGED" and e.value.details["quote"]["total_vnd"] == 50000
    order, _ = confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=50000)
    assert order["total_vnd"] == 50000

def test_confirm_draft_item_now_sold_out(conn):
    d = _draft(conn)
    conn.execute("UPDATE menu_items SET availability='sold_out' WHERE id='menu_024'")
    with pytest.raises(ApiError) as e: confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    assert e.value.code == "ITEM_UNAVAILABLE"

def test_expired_discarded_and_missing(conn):
    d = _draft(conn)
    conn.execute("UPDATE order_drafts SET expires_at='2000-01-01T00:00:00.000Z'")
    with pytest.raises(ApiError) as e: confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    assert (e.value.status, e.value.code) == (410, "DRAFT_EXPIRED")
    d2 = _draft(conn); discard_draft(conn, draft_id=d2["draft_id"])
    with pytest.raises(ApiError) as e: confirm_draft(conn, draft_id=d2["draft_id"], expected_total_vnd=45000)
    assert e.value.code == "DRAFT_DISCARDED"
    with pytest.raises(ApiError) as e: confirm_draft(conn, draft_id="f" * 32, expected_total_vnd=45000)
    assert e.value.code == "DRAFT_NOT_FOUND"


def test_price_changed_quote_persisted_without_order(conn):
    import json
    d = _draft(conn)
    conn.execute("UPDATE menu_items SET base_price_vnd=50000 WHERE id='menu_024'")
    with pytest.raises(ApiError):
        confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    row = conn.execute("SELECT total_vnd,quote_json FROM order_drafts").fetchone()
    assert row["total_vnd"] == 50000 and json.loads(row["quote_json"])["total_vnd"] == 50000
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_confirmed_draft_cannot_be_discarded(conn):
    d = _draft(conn)
    confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    with pytest.raises(ApiError) as e:
        discard_draft(conn, draft_id=d["draft_id"])
    assert e.value.code == "DRAFT_ALREADY_CONFIRMED"
