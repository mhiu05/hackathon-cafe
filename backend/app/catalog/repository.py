from __future__ import annotations

import sqlite3

from app.catalog.dto import menu_response_dto, services_response_dto
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


def _tool_items(conn: sqlite3.Connection) -> list[dict]:
    menu = menu_response_dto(conn)
    categories = {c["id"]: c for c in menu["categories"]}
    return [{"item_id": i["id"], "name": i["name"], "category": i["category_id"],
        "kind": categories[i["category_id"]]["kind"], "price_vnd": i["price_vnd"],
        "price_min_vnd": i["price_min_vnd"],
        "variants": [{"variant_id": v["id"], "label": v["label"], "price_vnd": v["price_vnd"]} for v in i["variants"]],
        "availability": i["availability"], "availability_note": i["availability_note"]}
        for i in menu["items"] if i["is_orderable"]]


def search_menu_items(conn: sqlite3.Connection, *, query: str | None, category_id: str | None,
                      max_price_vnd: int | None, kind: str = "any", limit: int = 10) -> dict:
    tokens = fold_vi(query or "").split()
    items = [i for i in _tool_items(conn) if (not category_id or i["category"] == category_id)
        and (kind == "any" or i["kind"] == kind) and (max_price_vnd is None or i["price_min_vnd"] <= max_price_vnd)
        and all(t in fold_vi(i["name"]) for t in tokens)]
    order = {r["id"]: r["sort_order"] for r in conn.execute("SELECT id,sort_order FROM menu_items")}
    items.sort(key=lambda i: (i["price_min_vnd"], order[i["item_id"]]))
    return {"total": len(items), "items": items[:limit]}


def recommend_items(conn: sqlite3.Connection, *, preferences: list[str], max_price_vnd: int | None,
                    include_food: bool, exclude_item_ids: list[str], limit: int) -> list[dict]:
    import json
    rows = {r["id"]: r for r in conn.execute("SELECT id,suggested_tags_json,sort_order FROM menu_items")}
    items = [i for i in _tool_items(conn) if i["availability"] != "sold_out"
        and (include_food or i["kind"] == "drink") and i["item_id"] not in exclude_item_ids
        and (max_price_vnd is None or i["price_min_vnd"] <= max_price_vnd)]
    for item in items:
        tags = set(json.loads(rows[item["item_id"]]["suggested_tags_json"]))
        item["matched_tags"] = sorted(tags & set(preferences))
        item["reasons"] = (["Tên món gợi ý: " + t for t in item["matched_tags"]] or ["phù hợp ngân sách"])
    items.sort(key=lambda i: (-2 * len(i["matched_tags"]), i["price_min_vnd"], rows[i["item_id"]]["sort_order"]))
    return items[:limit]


def coworking_info(conn: sqlite3.Connection, *, topic: str, min_capacity: int | None, need_tables: bool) -> dict:
    data = services_response_dto(conn)
    capacity = "capacity_tables" if need_tables else "capacity_max"
    rooms = [r for r in data["meeting_rooms"] if min_capacity is None or (r[capacity] or 0) >= min_capacity]
    return {"packages": data["coworking_packages"] if topic != "rooms" else [],
        "rooms": sorted(rooms, key=lambda r: r["price_vnd"]) if topic != "coworking" else [],
        "amenities": [f for f in data["facts"] if f["kind"] == "amenity" and (topic == "all" or f["scope"] == ("meeting_room" if topic == "rooms" else "coworking"))],
        "extras": [f for f in data["facts"] if f["kind"] != "amenity"],
        "booking_policy": data["booking_policy"], "price_basis": data["price_basis"]}
