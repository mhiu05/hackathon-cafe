from app.catalog.repository import search_menu_items, recommend_items, coworking_info

def test_search_menu_matcha(conn):
    res = search_menu_items(conn, query="matcha", category_id=None, max_price_vnd=None)
    assert res["total"] == 5 and {i["item_id"] for i in res["items"]} >= {"menu_030", "menu_034"}

def test_search_menu_budget_drinks(conn):
    res = search_menu_items(conn, query=None, category_id=None, max_price_vnd=40000, kind="drink", limit=20)
    assert res["items"] and all(i["price_min_vnd"] <= 40000 and i["kind"] == "drink" for i in res["items"])

def test_recommend_respects_budget_and_sold_out(conn):
    conn.execute("UPDATE menu_items SET availability='sold_out' WHERE id='menu_024'")
    items = recommend_items(conn, preferences=["vi-chua", "tra"], max_price_vnd=50000, include_food=False, exclude_item_ids=[], limit=3)
    assert len(items) == 3 and all(i["item_id"] != "menu_024" for i in items)
    assert [i["item_id"] for i in items] == ["menu_018", "menu_007", "menu_023"]   # score 5, then score-3 ties by price, sort_order
    assert all(i["price_min_vnd"] <= 50000 for i in items) and all({"vi-chua", "tra"} & set(i["matched_tags"]) for i in items)

def test_coworking_rooms_by_capacity(conn):
    assert coworking_info(conn, topic="rooms", min_capacity=20, need_tables=False)["rooms"][0]["name"] == "Phòng 4"
    assert coworking_info(conn, topic="rooms", min_capacity=60, need_tables=True)["rooms"][0]["name"] == "Phòng 3"
