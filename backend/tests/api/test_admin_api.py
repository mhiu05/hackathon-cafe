ADMIN_PIN = "246810"   # same value as backend/tests/conftest.py
BODY = {"lines": [{"item_id": "menu_030", "variant_id": None, "quantity": 1}], "expected_total_vnd": 45000}

def login(client):
    return {"Authorization": "Bearer " + client.post("/api/admin/login", json={"pin": ADMIN_PIN}).json()["token"]}

def test_admin_requires_token(client):
    r = client.get("/api/admin/orders")
    assert r.status_code == 401 and r.json()["error"]["code"] == "ADMIN_AUTH_REQUIRED"

def test_wrong_pin_then_rate_limited(client):
    codes = [client.post("/api/admin/login", json={"pin": "000000"}).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429

def test_list_and_transition(client):
    client.post("/api/orders", json=BODY, headers={"Idempotency-Key": "k" * 12}); h = login(client)
    listing = client.get("/api/admin/orders", headers=h).json()
    assert listing["counts"]["pending"] == 1 and listing["orders"][0]["allowed_next"] == ["confirmed", "rejected", "cancelled"]
    oid = listing["orders"][0]["id"]
    r = client.patch(f"/api/admin/orders/{oid}/status", headers=h, json={"to_status": "confirmed", "expected_status": "pending"})
    assert r.status_code == 200 and r.json()["status_label"] == "Quán đã nhận đơn"

def test_stale_expected_status_conflict(client):
    client.post("/api/orders", json=BODY, headers={"Idempotency-Key": "k" * 12}); h = login(client)
    body = {"to_status": "confirmed", "expected_status": "pending"}
    client.patch("/api/admin/orders/1/status", headers=h, json=body)
    r = client.patch("/api/admin/orders/1/status", headers=h, json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "STATUS_CONFLICT"

def test_reject_requires_reason(client):
    client.post("/api/orders", json=BODY, headers={"Idempotency-Key": "k" * 12}); h = login(client)
    r = client.patch("/api/admin/orders/1/status", headers=h, json={"to_status": "rejected", "expected_status": "pending"})
    assert r.status_code == 422

def test_menu_patch_blocks_ordering(client):
    h = login(client)
    assert client.patch("/api/admin/menu/menu_030", headers=h, json={"availability": "sold_out"}).json()["availability"] == "sold_out"
    r = client.post("/api/orders/quote", json={"lines": BODY["lines"]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "ITEM_UNAVAILABLE"

def test_logout_revokes(client):
    h = login(client); client.post("/api/admin/logout", headers=h)
    assert client.get("/api/admin/orders", headers=h).status_code == 401


def test_admin_not_configured(settings):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app(replace(settings, admin_pin=""))) as other:
        r = other.post("/api/admin/login", json={"pin": ADMIN_PIN})
    assert r.status_code == 503 and r.json()["error"]["code"] == "ADMIN_NOT_CONFIGURED"


def test_invalid_transition_and_expired_token(client, conn):
    h = login(client)
    client.post("/api/orders", json=BODY, headers={"Idempotency-Key": "k" * 12})
    r = client.patch("/api/admin/orders/1/status", headers=h, json={"to_status": "completed", "expected_status": "pending"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_TRANSITION"
    assert r.json()["error"]["details"]["allowed"] == ["confirmed", "rejected", "cancelled"]
    conn.execute("UPDATE admin_sessions SET expires_at='2000-01-01T00:00:00.000Z'")
    assert client.get("/api/admin/orders", headers=h).status_code == 401


def test_all_admin_routes_require_token(client):
    requests = [("GET", "/api/admin/orders/1", None), ("PATCH", "/api/admin/orders/1/status", {"to_status": "confirmed", "expected_status": "pending"}),
                ("PATCH", "/api/admin/menu/menu_030", {"availability": "sold_out"}), ("GET", "/api/admin/stream", None), ("POST", "/api/admin/logout", None)]
    for method, url, body in requests:
        assert client.request(method, url, json=body).status_code == 401
