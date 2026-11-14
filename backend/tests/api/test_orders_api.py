BODY = {"lines": [{"item_id": "menu_030", "variant_id": None, "quantity": 1}], "expected_total_vnd": 45000}

def test_post_orders_requires_idempotency_key(client):
    r = client.post("/api/orders", json=BODY)
    assert r.status_code == 400 and r.json()["error"]["code"] == "BAD_REQUEST"

def test_post_orders_created_then_replayed(client):
    h = {"Idempotency-Key": "11111111-2222-3333-4444-555555555555"}
    r1 = client.post("/api/orders", json=BODY, headers=h); r2 = client.post("/api/orders", json=BODY, headers=h)
    assert (r1.status_code, r2.status_code) == (201, 200) and r2.headers["Idempotent-Replay"] == "true"
    assert client.get("/api/orders/BB-0001").json()["status_label"] == "Chờ quán xác nhận"

def test_unknown_order_404(client):
    r = client.get("/api/orders/BB-9999")
    assert r.status_code == 404 and r.json()["error"]["code"] == "ORDER_NOT_FOUND"

async def test_order_stream_first_event_is_snapshot(client, conn):
    from app.api.orders import order_stream
    from starlette.requests import Request
    client.post("/api/orders", json=BODY, headers={"Idempotency-Key": "k" * 12})
    response = await order_stream("BB-0001", Request({"type": "http", "app": client.app}), conn)
    first = await anext(response.body_iterator)
    await response.body_iterator.aclose()
    assert first.splitlines()[0] == "event: order_status"
