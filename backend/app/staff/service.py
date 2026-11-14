"""Customer → staff help requests ("Gọi nhân viên").

The agent creates them through the `request_staff` tool; staff see and resolve them on the Quầy board.
A conversation may hold at most MAX_OPEN_PER_CONVERSATION open requests so a chat cannot flood the counter.
"""
from __future__ import annotations

import sqlite3

from app.db.connection import transaction
from app.errors import ApiError
from app.timeutil import utc_now

KIND_LABELS = {
    "wifi": "Wi-Fi / mạng",
    "clean_table": "Dọn bàn",
    "water": "Xin nước lọc",
    "find_book": "Tìm sách",
    "payment": "Thanh toán",
    "temperature": "Điều hòa / nhiệt độ",
    "other": "Khác",
}
STATUS_LABELS = {"open": "Đang chờ", "done": "Đã xử lý"}
MAX_OPEN_PER_CONVERSATION = 3


def _dto(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "code": row["code"], "kind": row["kind"], "kind_label": KIND_LABELS[row["kind"]],
            "table_label": row["table_label"], "note": row["note"], "status": row["status"],
            "status_label": STATUS_LABELS[row["status"]], "created_at": row["created_at"], "resolved_at": row["resolved_at"]}


def create_request(conn: sqlite3.Connection, *, conversation_id: str, kind: str, table_label: str | None, note: str | None) -> dict:
    if kind not in KIND_LABELS:
        raise ApiError(422, "VALIDATION_ERROR", "Loại yêu cầu không hợp lệ.")
    for value, limit in ((table_label, 20), (note, 200)):
        if value is not None and len(value) > limit:
            raise ApiError(422, "VALIDATION_ERROR", "Thông tin yêu cầu quá dài.")
    with transaction(conn):
        open_count = conn.execute("SELECT COUNT(*) FROM staff_requests WHERE conversation_id=? AND status='open'",
                                  (conversation_id,)).fetchone()[0]
        if open_count >= MAX_OPEN_PER_CONVERSATION:
            raise ApiError(429, "STAFF_REQUEST_LIMIT",
                           "Bạn đang có nhiều yêu cầu chờ xử lý; nhân viên sẽ tới sớm, hoặc bạn ghé quầy giúp mình nhé.")
        now = utc_now()
        cur = conn.execute("INSERT INTO staff_requests(code,conversation_id,kind,table_label,note,created_at) VALUES ('',?,?,?,?,?)",
                           (conversation_id, kind, table_label, note, now))
        request_id = cur.lastrowid
        conn.execute("UPDATE staff_requests SET code=? WHERE id=?", (f"YC-{request_id:04d}", request_id))
    return get_request(conn, request_id)


def get_request(conn: sqlite3.Connection, request_id: int) -> dict:
    row = conn.execute("SELECT * FROM staff_requests WHERE id=?", (request_id,)).fetchone()
    if row is None:
        raise ApiError(404, "STAFF_REQUEST_NOT_FOUND", "Không tìm thấy yêu cầu.")
    return _dto(row)


def list_requests(conn: sqlite3.Connection, *, status: str | None = None, conversation_id: str | None = None,
                  limit: int = 50) -> list[dict]:
    where, params = [], []
    if status:
        where.append("status=?"); params.append(status)
    if conversation_id:
        where.append("conversation_id=?"); params.append(conversation_id)
    sql = "SELECT * FROM staff_requests" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC LIMIT ?"
    return [_dto(r) for r in conn.execute(sql, (*params, limit))]


def resolve_request(conn: sqlite3.Connection, request_id: int) -> dict:
    with transaction(conn):
        current = get_request(conn, request_id)
        if current["status"] == "open":
            conn.execute("UPDATE staff_requests SET status='done',resolved_at=? WHERE id=?", (utc_now(), request_id))
    return get_request(conn, request_id)
