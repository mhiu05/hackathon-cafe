from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator

from fastapi import Header, Request

from app.db.connection import connect
from app.errors import ApiError
from app.settings import Settings

CUSTOMER_ACCOUNT_ID = "shared-customer"


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(get_settings(request).database_path)
    try:
        yield conn
    finally:
        conn.close()


def optional_conversation_id(x_conversation_id: str | None = Header(None)) -> str | None:
    if x_conversation_id is not None and not re.fullmatch(r"[0-9a-f]{32}", x_conversation_id):
        raise ApiError(400, "BAD_REQUEST", "X-Conversation-Id không hợp lệ.")
    return x_conversation_id


def require_conversation_id(x_conversation_id: str | None = Header(None)) -> str:
    value = optional_conversation_id(x_conversation_id)
    if value is None:
        raise ApiError(400, "BAD_REQUEST", "Thiếu X-Conversation-Id.")
    return value


def require_admin(request: Request, authorization: str | None = Header(None)) -> str:
    from app.admin.auth import verify
    if not authorization or not authorization.startswith("Bearer ") or not authorization[7:]:
        raise ApiError(401, "ADMIN_AUTH_REQUIRED", "Vui lòng đăng nhập quản trị.")
    token = authorization[7:]
    conn = connect(get_settings(request).database_path)
    try:
        verify(conn, token)
    finally:
        conn.close()
    return token
