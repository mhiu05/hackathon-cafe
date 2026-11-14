from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from app.catalog.dto import cafe_profile_dto, menu_response_dto, services_response_dto
from app.catalog.repository import filter_menu, get_menu_item
from app.deps import get_db

router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    conn.execute("SELECT 1")
    s = request.app.state.settings
    return {"status": "ok", "db": "ok", "knowledge_chunks": len(request.app.state.index),
            "model": s.openai_model, "model_configured": bool(s.openai_api_key), "admin_configured": len(s.admin_pin) >= 6}


@router.get("/cafe")
def cafe(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return cafe_profile_dto(conn, datetime.now(timezone.utc))


@router.get("/menu")
def menu(category: str | None = None, q: str | None = None, max_price_vnd: int | None = None,
         conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return filter_menu(menu_response_dto(conn), category=category, q=q, max_price_vnd=max_price_vnd)


@router.get("/menu/{item_id}")
def item(item_id: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return get_menu_item(conn, item_id)


@router.get("/services")
def services(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return services_response_dto(conn)
