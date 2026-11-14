from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from uuid import uuid4

from app.db.connection import transaction
from app.errors import ApiError
from app.orders.state import REASON_REQUIRED, STATUS_LABELS, allowed_next
from app.timeutil import add_minutes, utc_now


@dataclass(frozen=True)
class LineInput:
    item_id: str
    variant_id: str | None
    quantity: int
    note: str | None = None


def _validate_lines(lines: list[LineInput]) -> None:
    if not lines:
        raise ApiError(422, "CART_EMPTY", "Giỏ hàng đang trống.")
    if len(lines) > 10:
        raise ApiError(422, "CART_TOO_LARGE", "Giỏ hàng tối đa 10 dòng.")
    for line in lines:
        if type(line.quantity) is not int or not 1 <= line.quantity <= 10 or (line.note is not None and len(line.note) > 120):
            raise ApiError(422, "VALIDATION_ERROR", "Số lượng hoặc ghi chú không hợp lệ.")


def _request(lines: list[LineInput], customer_name: str | None, table_label: str | None, note: str | None) -> dict:
    _validate_lines(lines)
    for value, limit in ((customer_name, 40), (table_label, 20), (note, 200)):
        if value is not None and len(value) > limit:
            raise ApiError(422, "VALIDATION_ERROR", "Thông tin đơn hàng quá dài.")
    return {"lines": [asdict(l) for l in lines], "customer_name": customer_name, "table_label": table_label, "note": note}


def _hash(request: dict) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def quote_cart(conn: sqlite3.Connection, lines: list[LineInput]) -> dict:
    _validate_lines(lines)
    quoted, unknown, unverified = [], [], []
    for n, line in enumerate(lines, 1):
        item = conn.execute("SELECT * FROM menu_items WHERE id=?", (line.item_id,)).fetchone()
        if item is None:
            raise ApiError(422, "ITEM_NOT_FOUND", "Không tìm thấy món.", {"item_id": line.item_id})
        if item["availability"] == "sold_out" or not item["is_orderable"]:
            raise ApiError(422, "ITEM_UNAVAILABLE", f"Món '{item['name']}' hiện không đặt được.", {"item_id": line.item_id})
        variants = conn.execute("SELECT * FROM menu_item_variants WHERE item_id=?", (line.item_id,)).fetchall()
        variant = next((v for v in variants if v["id"] == line.variant_id), None)
        if variants and line.variant_id is None:
            raise ApiError(422, "VARIANT_REQUIRED", "Vui lòng chọn biến thể món.", {"item_id": line.item_id})
        if line.variant_id is not None and variant is None:
            raise ApiError(422, "INVALID_VARIANT", "Biến thể không thuộc món này.", {"item_id": line.item_id})
        price = variant["price_vnd"] if variant else item["base_price_vnd"]
        quoted.append({"line_no": n, "item_id": line.item_id, "variant_id": line.variant_id,
            "item_name": item["name"], "variant_label": variant["label"] if variant else None,
            "unit_price_vnd": price, "quantity": line.quantity, "line_total_vnd": price * line.quantity,
            "availability": item["availability"], "note": line.note})
        if item["availability"] == "unknown" and line.item_id not in unknown:
            unknown.append(line.item_id)
        if not item["price_verified"] and line.item_id not in unverified:
            unverified.append(line.item_id)
    warnings = []
    if unknown:
        warnings.append({"code": "AVAILABILITY_UNCONFIRMED", "message": "Quán chưa xác nhận còn món; nhân viên sẽ kiểm tra khi nhận đơn.", "item_ids": unknown})
    if unverified:
        warnings.append({"code": "PRICE_UNVERIFIED", "message": "Giá theo menu chụp ngày 14/11/2026, chờ quán xác nhận.", "item_ids": unverified})
    total = sum(l["line_total_vnd"] for l in quoted)
    return {"lines": quoted, "subtotal_vnd": total, "total_vnd": total, "item_count": sum(l.quantity for l in lines),
        "currency": "VND", "warnings": warnings, "quoted_at": utc_now()}


def get_order(conn: sqlite3.Connection, *, order_id: int | None = None, code: str | None = None) -> dict:
    row = conn.execute("SELECT * FROM orders WHERE id=? OR code=?", (order_id, code)).fetchone()
    if row is None:
        raise ApiError(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng.")
    keys = ("id", "code", "status", "source", "customer_name", "table_label", "note", "subtotal_vnd", "total_vnd",
            "item_count", "status_reason", "created_at", "updated_at")
    result = {k: row[k] for k in keys}
    result["status_label"] = STATUS_LABELS[row["status"]]
    result["lines"] = [dict(r) for r in conn.execute("SELECT line_no,item_id,variant_id,item_name_snapshot AS item_name,"
        "variant_label_snapshot AS variant_label,unit_price_vnd,quantity,line_total_vnd,note FROM order_items WHERE order_id=? ORDER BY line_no", (row["id"],))]
    result["events"] = [dict(r) for r in conn.execute("SELECT from_status,to_status,actor,note,created_at FROM order_events WHERE order_id=? ORDER BY id", (row["id"],))]
    return result


def list_orders(conn: sqlite3.Connection, *, status: str | None = None, conversation_id: str | None = None, limit: int = 20) -> list[dict]:
    rows = conn.execute("SELECT id FROM orders WHERE (? IS NULL OR status=?) AND (? IS NULL OR conversation_id=?) ORDER BY id DESC LIMIT ?",
        (status, status, conversation_id, conversation_id, limit))
    return [get_order(conn, order_id=r["id"]) for r in rows]


def order_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts = dict.fromkeys(STATUS_LABELS, 0)
    counts.update({r["status"]: r["n"] for r in conn.execute("SELECT status,COUNT(*) n FROM orders GROUP BY status")})
    return counts


def _insert_order(conn: sqlite3.Connection, request: dict, quote: dict, *, source: str, idempotency_key: str, conversation_id: str | None) -> dict:
    now = utc_now()
    row = conn.execute("INSERT INTO orders(code,conversation_id,source,customer_name,table_label,note,subtotal_vnd,total_vnd,item_count,idempotency_key,request_hash,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("tmp-" + uuid4().hex, conversation_id, source, request["customer_name"], request["table_label"], request["note"], quote["subtotal_vnd"], quote["total_vnd"], quote["item_count"], idempotency_key, _hash(request), now, now))
    oid = row.lastrowid
    conn.execute("UPDATE orders SET code=printf('BB-%04d',id) WHERE id=?", (oid,))
    for l in quote["lines"]:
        conn.execute("INSERT INTO order_items(order_id,line_no,item_id,variant_id,item_name_snapshot,variant_label_snapshot,unit_price_vnd,quantity,line_total_vnd,note) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (oid, l["line_no"], l["item_id"], l["variant_id"], l["item_name"], l["variant_label"], l["unit_price_vnd"], l["quantity"], l["line_total_vnd"], l["note"]))
    conn.execute("INSERT INTO order_events(order_id,from_status,to_status,actor,created_at) VALUES (?,NULL,'pending','customer',?)", (oid, now))
    return get_order(conn, order_id=oid)


def create_order(conn: sqlite3.Connection, *, lines: list[LineInput], expected_total_vnd: int, customer_name: str | None,
                 table_label: str | None, note: str | None, source: str, idempotency_key: str, conversation_id: str | None) -> tuple[dict, bool]:
    request = _request(lines, customer_name, table_label, note)
    if not 8 <= len(idempotency_key) <= 100:
        raise ApiError(400, "BAD_REQUEST", "Idempotency-Key cần từ 8 đến 100 ký tự.")
    with transaction(conn):
        existing = conn.execute("SELECT id,request_hash FROM orders WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        if existing:
            if existing["request_hash"] != _hash(request):
                raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Khóa yêu cầu đã dùng cho giỏ hàng khác.")
            return get_order(conn, order_id=existing["id"]), True
        quote = quote_cart(conn, lines)
        if quote["total_vnd"] != expected_total_vnd:
            raise ApiError(409, "PRICE_CHANGED", "Giá đã thay đổi, vui lòng kiểm tra lại.", {"quote": quote})
        return _insert_order(conn, request, quote, source=source, idempotency_key=idempotency_key, conversation_id=conversation_id), False


def transition_status(conn: sqlite3.Connection, *, order_id: int, to_status: str, expected_status: str, reason: str | None) -> dict:
    with transaction(conn):
        order = get_order(conn, order_id=order_id)
        if order["status"] != expected_status:
            raise ApiError(409, "STATUS_CONFLICT", "Đơn hàng đã được cập nhật.", {"current_status": order["status"]})
        allowed = allowed_next(order["status"])
        if to_status not in allowed:
            raise ApiError(409, "INVALID_TRANSITION", "Không thể chuyển trạng thái này.", {"allowed": allowed})
        reason = reason.strip() if reason else None
        if (reason is not None and not 3 <= len(reason) <= 200) or (to_status in REASON_REQUIRED and not reason):
            raise ApiError(422, "VALIDATION_ERROR", "Vui lòng nhập lý do từ 3 đến 200 ký tự.")
        now = utc_now()
        changed = conn.execute("UPDATE orders SET status=?,status_reason=?,updated_at=? WHERE id=? AND status=?", (to_status, reason, now, order_id, expected_status))
        if changed.rowcount != 1:
            raise ApiError(409, "STATUS_CONFLICT", "Đơn hàng đã được cập nhật.")
        conn.execute("INSERT INTO order_events(order_id,from_status,to_status,actor,note,created_at) VALUES (?,?,?,'admin',?,?)", (order_id, expected_status, to_status, reason, now))
        return get_order(conn, order_id=order_id)


def create_draft(conn: sqlite3.Connection, *, conversation_id: str, lines: list[LineInput], customer_name: str | None, table_label: str | None, note: str | None) -> dict:
    request = _request(lines, customer_name, table_label, note)
    with transaction(conn):
        quote = quote_cart(conn, lines)
        now, did = utc_now(), uuid4().hex
        conn.execute("INSERT INTO order_drafts(id,conversation_id,request_json,quote_json,total_vnd,created_at,expires_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (did, conversation_id, json.dumps(request, ensure_ascii=False), json.dumps(quote, ensure_ascii=False), quote["total_vnd"], now, add_minutes(now, 30), now))
        return get_draft(conn, did)


def _draft_row(conn: sqlite3.Connection, draft_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT d.*,o.code AS order_code FROM order_drafts d LEFT JOIN orders o ON o.id=d.order_id WHERE d.id=?", (draft_id,)).fetchone()
    if row is None:
        raise ApiError(404, "DRAFT_NOT_FOUND", "Không tìm thấy đơn nháp.")
    return row


def get_draft(conn: sqlite3.Connection, draft_id: str) -> dict:
    row = _draft_row(conn, draft_id)
    if row["status"] == "open" and utc_now() > row["expires_at"]:
        raise ApiError(410, "DRAFT_EXPIRED", "Đơn nháp đã hết hạn.")
    req = json.loads(row["request_json"])
    return {"draft_id": row["id"], "status": row["status"], "quote": json.loads(row["quote_json"]),
        "customer_name": req["customer_name"], "table_label": req["table_label"], "note": req["note"],
        "order_code": row["order_code"], "created_at": row["created_at"], "expires_at": row["expires_at"]}


def confirm_draft(conn: sqlite3.Connection, *, draft_id: str, expected_total_vnd: int) -> tuple[dict, bool]:
    price_error = None
    with transaction(conn):
        row = _draft_row(conn, draft_id)
        if row["status"] == "confirmed":
            return get_order(conn, order_id=row["order_id"]), True
        if row["status"] == "discarded":
            raise ApiError(409, "DRAFT_DISCARDED", "Đơn nháp đã bị bỏ.")
        if utc_now() > row["expires_at"]:
            raise ApiError(410, "DRAFT_EXPIRED", "Đơn nháp đã hết hạn.")
        request = json.loads(row["request_json"])
        quote = quote_cart(conn, [LineInput(**l) for l in request["lines"]])
        if quote["total_vnd"] != expected_total_vnd:
            conn.execute("UPDATE order_drafts SET quote_json=?,total_vnd=?,updated_at=? WHERE id=?", (json.dumps(quote, ensure_ascii=False), quote["total_vnd"], utc_now(), draft_id))
            price_error = ApiError(409, "PRICE_CHANGED", "Giá đã thay đổi, vui lòng kiểm tra lại.", {"quote": quote})
        else:
            order = _insert_order(conn, request, quote, source="agent_draft", idempotency_key="draft:" + draft_id, conversation_id=row["conversation_id"])
            conn.execute("UPDATE order_drafts SET status='confirmed',order_id=?,updated_at=? WHERE id=?", (order["id"], utc_now(), draft_id))
    if price_error:
        raise price_error
    return order, False


def discard_draft(conn: sqlite3.Connection, *, draft_id: str) -> dict:
    with transaction(conn):
        row = _draft_row(conn, draft_id)
        if row["status"] == "confirmed":
            raise ApiError(409, "DRAFT_ALREADY_CONFIRMED", "Đơn nháp đã được xác nhận.")
        conn.execute("UPDATE order_drafts SET status='discarded',updated_at=? WHERE id=?", (utc_now(), draft_id))
    return {"draft_id": draft_id, "status": "discarded"}
