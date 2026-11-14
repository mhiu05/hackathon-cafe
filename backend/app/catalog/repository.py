from __future__ import annotations

import sqlite3

from app.catalog.dto import menu_response_dto
from app.errors import ApiError
from app.knowledge.text import fold_vi


def filter_menu(menu: dict, *, category: str | None, q: str | None, max_price_vnd: int | None) -> dict:
    tokens = fold_vi(q or "").split()
    return {**menu, "items": [i for i in menu["items"]
        if (not category or i["category_id"] == category)
        and (max_price_vnd is None or i["price_min_vnd"] <= max_price_vnd)
        and all(t in fold_vi(i["name"]) for t in tokens)]}


def get_menu_item(conn: sqlite3.Connection, item_id: str) -> dict:
    for item in menu_response_dto(conn)["items"]:
        if item["id"] == item_id:
            return item
    raise ApiError(404, "ITEM_NOT_FOUND", "Không tìm thấy món.", {"item_id": item_id})
