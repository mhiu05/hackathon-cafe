import json, pytest
from pathlib import Path
from app.errors import ApiError
from app.orders.service import LineInput, quote_cart, create_order, transition_status, get_order
FIX = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"
CART = [LineInput("menu_001", "menu_001:den", 2), LineInput("menu_030", None, 1, "ít đá")]

def code_of(exc): return exc.value.code

def test_quote_matches_fixture(conn):
    q = quote_cart(conn, CART); want = json.loads((FIX / "quote.json").read_text(encoding="utf-8"))
    q.pop("quoted_at"); want.pop("quoted_at")
    assert q == want

@pytest.mark.parametrize("lines,code", [
    ([], "CART_EMPTY"), ([LineInput("menu_030", None, 1)] * 11, "CART_TOO_LARGE"),
    ([LineInput("menu_999", None, 1)], "ITEM_NOT_FOUND"), ([LineInput("menu_001", None, 1)], "VARIANT_REQUIRED"),
    ([LineInput("menu_030", "menu_001:den", 1)], "INVALID_VARIANT")])
def test_quote_rejects_invalid_carts(conn, lines, code):
    with pytest.raises(ApiError) as e: quote_cart(conn, lines)
    assert code_of(e) == code and e.value.status == 422

def test_quote_rejects_sold_out(conn):
    conn.execute("UPDATE menu_items SET availability='sold_out' WHERE id='menu_019'")
    with pytest.raises(ApiError) as e: quote_cart(conn, [LineInput("menu_019", None, 1)])
    assert code_of(e) == "ITEM_UNAVAILABLE"

def _create(conn, key="key-000001", total=115000, lines=CART):
    return create_order(conn, lines=lines, expected_total_vnd=total, customer_name="Minh", table_label="Bàn 12", note=None,
                        source="ui", idempotency_key=key, conversation_id=None)

def test_create_order_snapshot_and_event(conn):
    order, replayed = _create(conn)
    assert (order["code"], order["status"], order["total_vnd"], replayed) == ("BB-0001", "pending", 115000, False)
    assert [l["unit_price_vnd"] for l in order["lines"]] == [35000, 45000]
    assert [(e["from_status"], e["to_status"], e["actor"]) for e in order["events"]] == [(None, "pending", "customer")]

def test_create_order_idempotent_replay(conn):
    a, _ = _create(conn); b, replayed = _create(conn)
    assert a["id"] == b["id"] and replayed is True
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1

def test_create_order_idempotency_conflict(conn):
    _create(conn)
    with pytest.raises(ApiError) as e: _create(conn, lines=[LineInput("menu_030", None, 2)], total=90000)
    assert code_of(e) == "IDEMPOTENCY_CONFLICT" and e.value.status == 409

def test_create_order_price_changed(conn):
    with pytest.raises(ApiError) as e: _create(conn, total=100000)
    assert code_of(e) == "PRICE_CHANGED" and e.value.details["quote"]["total_vnd"] == 115000
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0

def test_transitions(conn):
    order, _ = _create(conn)
    assert transition_status(conn, order_id=order["id"], to_status="confirmed", expected_status="pending", reason=None)["status"] == "confirmed"
    with pytest.raises(ApiError) as e: transition_status(conn, order_id=order["id"], to_status="pending", expected_status="confirmed", reason=None)
    assert code_of(e) == "INVALID_TRANSITION"
    with pytest.raises(ApiError) as e: transition_status(conn, order_id=order["id"], to_status="preparing", expected_status="pending", reason=None)
    assert code_of(e) == "STATUS_CONFLICT" and e.value.details["current_status"] == "confirmed"
    with pytest.raises(ApiError) as e: transition_status(conn, order_id=order["id"], to_status="cancelled", expected_status="confirmed", reason=None)
    assert code_of(e) == "VALIDATION_ERROR"
    assert get_order(conn, code="BB-0001")["events"][-1]["actor"] == "admin"


def test_concurrent_retries_create_one_order(db_path, conn):
    from concurrent.futures import ThreadPoolExecutor
    from app.db.connection import connect
    from contextlib import closing
    def request():
        with closing(connect(db_path)) as c:
            return _create(c)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: request(), range(2)))
    assert {o["code"] for o, _ in results} == {"BB-0001"}
    assert sorted(replay for _, replay in results) == [False, True]


def test_write_failure_rolls_back_order_and_items(conn):
    import sqlite3
    conn.execute("CREATE TRIGGER fail_order_event BEFORE INSERT ON order_events BEGIN SELECT RAISE(ABORT,'test failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        _create(conn)
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0] == 0
    assert not conn.in_transaction


def test_replay_and_snapshot_survive_catalog_changes(conn):
    first, _ = _create(conn)
    conn.execute("UPDATE menu_items SET base_price_vnd=90000,availability='sold_out' WHERE id='menu_030'")
    again, replayed = _create(conn)
    assert again == first and replayed
    assert again["lines"][1]["unit_price_vnd"] == 45000
