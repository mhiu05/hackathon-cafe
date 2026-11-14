import json
from pathlib import Path
FIX = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"
def fixture(name): return json.loads((FIX / name).read_text(encoding="utf-8"))

def test_health_reports_knowledge(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["db"] == "ok" and body["knowledge_chunks"] == 56
    assert body["model"] == "gpt-6-luna" and body["admin_configured"] is True

def test_cafe_matches_fixture(client):
    got, want = client.get("/api/cafe").json(), fixture("cafe.json")
    got.pop("is_open_now"); want.pop("is_open_now")
    assert got == want

def test_menu_and_services_match_fixtures(client):
    assert client.get("/api/menu").json() == fixture("menu.json")
    assert client.get("/api/services").json() == fixture("services.json")

def test_menu_filters(client):
    ids = [i["id"] for i in client.get("/api/menu", params={"category": "matcha", "max_price_vnd": 45000}).json()["items"]]
    assert ids == ["menu_030"]
    names = [i["name"] for i in client.get("/api/menu", params={"q": "tra dao"}).json()["items"]]
    assert "Trà thạch đào" in names and "Trà đào cam sả" in names

def test_menu_item_and_404(client):
    assert client.get("/api/menu/menu_023").json()["variants"][1] == {"id": "menu_023:2-nguoi", "label": "2 người", "price_vnd": 60000}
    r = client.get("/api/menu/menu_999")
    assert r.status_code == 404 and r.json()["error"]["code"] == "ITEM_NOT_FOUND"

def test_validation_error_uses_envelope(client):
    r = client.get("/api/menu", params={"max_price_vnd": "abc"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"

def test_migration_0003_seeds_shared_customer(conn):
    assert [r[0] for r in conn.execute("SELECT id FROM customer_accounts")] == ["shared-customer"]
