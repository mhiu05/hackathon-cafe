# Dev A — Backend & Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the FastAPI backend (catalog, orders, drafts, admin, realtime) and the single-orchestrator agent with 7 tools and SSE streaming, satisfying `docs/api-contracts.md` exactly.

**Architecture:** `backend/app` package on top of the existing `settings`, `db`, `knowledge`, `catalog.dto` modules; direct SQL with `transaction()`; service functions are pure DB logic, API routers publish to the in-process `EventBus` after commit; agent built once at startup and streamed per request with `SQLiteSession` per conversation.

**Tech Stack:** Python 3.12, FastAPI 0.162.7, uvicorn 0.54.0, sqlite3, openai-agents 0.24.0 (`gpt-6-luna`), httpx, NumPy, pytest 9 + pytest-asyncio 1.5 (`asyncio_mode=auto`), `agents.testing.ScriptedModel`.

**Spec:** `PRD.md`, `ARCHITECTURE.md`, `RULES.md`, `docs/api-contracts.md`, `docs/database-design.md`, `docs/agent-design.md`, master plan `docs/superpowers/plans/2026-11-14-master-plan.md`.

## Global Constraints

- Write only `backend/**`, `scripts/demo/**`, `contracts/**` (+ your rows in `TASKS.md`/`PROGRESS.md`).
- All SQL parameterised; multi-statement writes in `with transaction(conn):`; timestamps from `app.timeutil.utc_now()`; money `int` VND.
- Error envelope + codes exactly as `docs/api-contracts.md §1`; Vietnamese `message`.
- Customer endpoints: no auth, account `shared-customer`; `X-Conversation-Id` must match `^[0-9a-f]{32}$` where required.
- Admin endpoints (except login): `Authorization: Bearer <token>`; PIN compare with `hmac.compare_digest`; token sha256 stored; 12 h.
- Agent: model from `settings.openai_model` (`gpt-6-luna`); tools return `as_tool_json(...)`; identity from context only; `prepare_order` never writes `orders`.
- Tests never call OpenAI/Voyage unless `@pytest.mark.live`; run `uv run pytest -q` before every commit.
- Precondition on each laptop: `uv sync` and `uv run python scripts/knowledge/ingest.py --offline` (creates `data/cafe.db`).

## Review Focus

1. Confirming the same draft twice / retrying a cart POST → one order — `test_confirm_draft_is_idempotent`, `test_create_order_idempotent_replay` (A2).
2. Price drift between quote and confirm → `409 PRICE_CHANGED` + fresh quote, no order — `test_confirm_price_changed_refreshes_quote` (A2).
3. Staff marks an item sold out while a draft is open → confirm returns `422 ITEM_UNAVAILABLE` — `test_confirm_draft_item_now_sold_out` (A2).
4. Stale admin tab → `409 STATUS_CONFLICT`, not an overwrite — `test_stale_expected_status_conflict` (A3).
5. OpenAI failure mid-chat → SSE `error MODEL_UNAVAILABLE` + `done(error)`, server keeps serving orders — `test_model_error_emits_model_unavailable` (A4).

---

## File map

| File | Task | Responsibility |
|---|---|---|
| `backend/app/db/migrations/0003_commerce.sql` | A1 | DDL from `docs/database-design.md §5` verbatim |
| `backend/app/timeutil.py` | A1 | `utc_now() -> str`, `parse_ts(value: str) -> datetime`, `add_minutes(ts: str, minutes: int) -> str` |
| `backend/app/errors.py` | A1 | `ApiError`, `install_error_handlers(app)` |
| `backend/app/deps.py` | A1 | `CUSTOMER_ACCOUNT_ID`, `get_settings`, `get_db`, `optional_conversation_id`, `require_conversation_id`, `require_admin` (A3) |
| `backend/app/main.py` | A1 | `create_app(settings: Settings \| None = None) -> FastAPI`, lifespan, CORS, routers; `app = create_app()` |
| `backend/app/catalog/repository.py` | A1, A4 | `filter_menu`, `get_menu_item`, `search_menu_items`, `recommend_items`, `coworking_info` |
| `backend/app/api/public.py` | A1 | `/api/health`, `/api/cafe`, `/api/menu`, `/api/menu/{item_id}`, `/api/services` |
| `backend/app/orders/state.py` | A2 | `STATUS_LABELS`, `ALLOWED`, `REASON_REQUIRED`, `allowed_next(status)` |
| `backend/app/orders/service.py` | A2 | `LineInput`, `quote_cart`, `create_order`, `get_order`, `list_orders`, `order_counts`, `transition_status`, `create_draft`, `get_draft`, `confirm_draft`, `discard_draft` |
| `backend/app/realtime/bus.py` · `sse.py` | A2 | `EventBus`; `format_sse`, `sse_response`, `with_heartbeat` |
| `backend/app/api/orders.py` | A2 | customer order + draft endpoints, order SSE |
| `backend/app/admin/auth.py` · `api/admin.py` | A3 | PIN login, tokens, rate limit; admin endpoints + admin SSE + menu PATCH |
| `backend/app/agent/{context,instructions,tools,factory,stream}.py` · `api/agent.py` | A4–A5 | agent per `docs/agent-design.md` |
| `scripts/demo/reset_demo.py` | A5 | demo reset per `docs/database-design.md §9` |
| `backend/tests/conftest.py` (modify) | A1 | shared fixtures `pristine_db`, `db_path`, `settings`, `client`, `conn` (visible to api/, orders/, agent/) |

---

### Task A1: App foundation, commerce migration, public catalog API (0:00–0:50)

**Files:**
- Create: `backend/app/db/migrations/0003_commerce.sql`, `backend/app/timeutil.py`, `backend/app/errors.py`, `backend/app/deps.py`, `backend/app/main.py`, `backend/app/catalog/repository.py`, `backend/app/api/__init__.py`, `backend/app/api/public.py`
- Modify: `backend/tests/conftest.py` (add shared fixtures; keep the existing `db` fixture)
- Test: `backend/tests/api/__init__.py` (empty), `backend/tests/api/test_public_contract.py`

**Interfaces:**
- Consumes: `app.settings.Settings/load_settings`, `app.db.connection.connect/transaction`, `app.db.migrate.apply_migrations`, `app.catalog.dto.{cafe_profile_dto, menu_response_dto, menu_item_dto, services_response_dto}`, `app.knowledge.retrieval.KnowledgeIndex`, `app.knowledge.embeddings.VoyageEmbedder`, `app.knowledge.text.fold_vi`.
- Produces:
  - `create_app(settings: Settings | None = None) -> FastAPI`; `app.state.settings`, `app.state.index: KnowledgeIndex`, `app.state.embedder: VoyageEmbedder | None`, `app.state.bus` (A2), `app.state.agent` (A4).
  - `class ApiError(Exception): (status: int, code: str, message: str, details: dict | None = None)`.
  - `deps.get_db(request) -> Iterator[sqlite3.Connection]`; `deps.CUSTOMER_ACCOUNT_ID = "shared-customer"`;
    `deps.optional_conversation_id(x_conversation_id: str | None = Header(None)) -> str | None`;
    `deps.require_conversation_id(...) -> str` (400 `BAD_REQUEST` if missing/invalid).
  - `repository.filter_menu(menu: dict, *, category: str | None, q: str | None, max_price_vnd: int | None) -> dict`;
    `repository.get_menu_item(conn, item_id: str) -> dict` (404 `ITEM_NOT_FOUND`).

- [ ] **Step 1: Add shared fixtures** — append to `backend/tests/conftest.py` (root conftest, so `tests/orders` and `tests/agent` can use them)

```python
import shutil, sqlite3
from contextlib import closing
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.db.connection import connect
from app.db.migrate import apply_migrations
from app.main import create_app
from app.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
ADMIN_PIN = "246810"

@pytest.fixture(scope="session")
def pristine_db(tmp_path_factory) -> Path:
    src = REPO_ROOT / "data" / "cafe.db"
    if not src.exists():
        pytest.skip("run: uv run python scripts/knowledge/ingest.py --offline")
    dst = tmp_path_factory.mktemp("pristine") / "cafe.db"
    with closing(connect(src, read_only=True)) as s, closing(sqlite3.connect(dst)) as d:
        s.backup(d)
    return dst

@pytest.fixture()
def db_path(pristine_db, tmp_path) -> Path:
    dst = tmp_path / "cafe.db"
    shutil.copy(pristine_db, dst)
    return dst

@pytest.fixture()
def settings(db_path, tmp_path) -> Settings:
    return Settings(openai_api_key="test-key", voyage_api_key="", database_path=db_path,
                    agent_sessions_db_path=tmp_path / "sessions.db", admin_pin=ADMIN_PIN, enable_agent_tracing=False)

@pytest.fixture()
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c

@pytest.fixture()
def conn(db_path):
    c = connect(db_path); apply_migrations(c)
    yield c
    c.close()
```

- [ ] **Step 2: Write the failing tests** — `backend/tests/api/test_public_contract.py`

```python
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
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest backend/tests/api/test_public_contract.py -v` → FAIL (`ModuleNotFoundError: app.main`).
- [ ] **Step 4: Implement**
  - `0003_commerce.sql`: copy the SQL block of `docs/database-design.md §5` verbatim.
  - `timeutil.utc_now()` same format as `scripts/knowledge/_paths.utc_now` (`%Y-%m-%dT%H:%M:%S.mmmZ`).
  - `errors.install_error_handlers`: `ApiError` → `JSONResponse(status, {"error": {...}})`; `RequestValidationError` → 422 `VALIDATION_ERROR`, `details.errors=[{"loc": e["loc"], "msg": e["msg"]}]`; `HTTPException` 404 → `NOT_FOUND`; other `Exception` → 500 `INTERNAL` (log stack).
  - `main.create_app`: lifespan opens `connect(settings.database_path)`, `apply_migrations`, `KnowledgeIndex.load(conn)`, embedder = `VoyageEmbedder(api_key, model, dimension, timeout_s=5, max_retries=0)` if key else `None`; CORS for `settings.frontend_origin`; include `public` router. `health`: `knowledge_chunks=len(app.state.index)`, `model_configured=bool(settings.openai_api_key)`, `admin_configured=len(settings.admin_pin) >= 6`.
  - `public.py`: `GET /api/menu` uses `filter_menu(menu_response_dto(conn), …)` (filter items only; categories unchanged; price uses `price_min_vnd`; `q` = every `fold_vi` token in the item's folded name).
- [ ] **Step 5: Run** — `uv run pytest -q` → all PASS (9 existing + 7 new).
- [ ] **Step 6: Smoke** — `uv run uvicorn app.main:app --port 8000` then `curl http://localhost:8000/api/cafe` → JSON with `"phone": "0976 214 224"`.
- [ ] **Step 7: Commit** — `git add backend && git commit -m "feat(api): app foundation, commerce migration, public catalog endpoints"`

**Acceptance:** responses equal fixtures; envelope on errors; C1 unblocked.

---

### Task A2: Orders, drafts, realtime bus and customer order API (0:50–2:00)

**Files:**
- Create: `backend/app/orders/__init__.py`, `backend/app/orders/state.py`, `backend/app/orders/service.py`, `backend/app/realtime/__init__.py`, `backend/app/realtime/bus.py`, `backend/app/realtime/sse.py`, `backend/app/api/orders.py`
- Modify: `backend/app/main.py` (create `EventBus` in lifespan; include orders router)
- Test: `backend/tests/orders/__init__.py`, `backend/tests/orders/test_orders_service.py`, `backend/tests/orders/test_drafts.py`, `backend/tests/api/test_orders_api.py`

**Interfaces:**
- Consumes: A1 `ApiError`, `get_db`, `optional_conversation_id`, `utc_now`.
- Produces (used by A3, A4):
  - `state.STATUS_LABELS: dict[str, str]` (labels in `docs/database-design.md §6`), `state.ALLOWED: dict[str, tuple[str, ...]]`, `state.REASON_REQUIRED = {"rejected", "cancelled"}`, `state.allowed_next(status: str) -> list[str]`.
  - `@dataclass(frozen=True) class LineInput: item_id: str; variant_id: str | None; quantity: int; note: str | None = None`
  - `quote_cart(conn, lines: list[LineInput]) -> dict` (OrderQuote)
  - `create_order(conn, *, lines, expected_total_vnd: int, customer_name: str | None, table_label: str | None, note: str | None, source: str, idempotency_key: str, conversation_id: str | None) -> tuple[dict, bool]`
  - `get_order(conn, *, order_id: int | None = None, code: str | None = None) -> dict` · `list_orders(conn, *, status=None, conversation_id=None, limit=20) -> list[dict]` · `order_counts(conn) -> dict[str, int]`
  - `transition_status(conn, *, order_id: int, to_status: str, expected_status: str, reason: str | None) -> dict`
  - `create_draft(conn, *, conversation_id: str, lines, customer_name, table_label, note) -> dict` (OrderDraft) · `get_draft(conn, draft_id) -> dict` · `confirm_draft(conn, *, draft_id: str, expected_total_vnd: int) -> tuple[dict, bool]` · `discard_draft(conn, *, draft_id: str) -> dict`
  - `EventBus.publish(topic: str, event: str, data: dict) -> None`; `EventBus.subscribe(topic: str) -> AsyncIterator[tuple[str, dict]]` (async context-managed generator, queue maxsize 100, drop oldest when full)
  - `sse.format_sse(event: str, data: dict) -> str`; `sse.sse_response(gen: AsyncIterator[str]) -> StreamingResponse` (headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`); `sse.with_heartbeat(gen, interval_s: float = 15) -> AsyncIterator[str]` (yields `": ping\n\n"` on idle).
  - Order DTO = `Order` in `docs/api-contracts.md §9` (without `allowed_next`); events ordered by id.

- [ ] **Step 1: Write failing service tests** — `backend/tests/orders/test_orders_service.py` (uses the root `conn` fixture)

```python
import json, pytest
from pathlib import Path
from app.errors import ApiError
from app.orders.service import LineInput, quote_cart, create_order, transition_status, get_order
FIX = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"
CART = [LineInput("menu_001", "menu_001:den", 2), LineInput("menu_030", None, 1, "ít đá")]

def code_of(exc): return exc.value.code

def test_quote_matches_fixture(conn):
    q = quote_cart(conn, CART); want = json.loads((FIX / "quote.json").read_text(encoding="utf-8"))
    q.pop("quoted_at"); want.pop("quoted_at")
    assert q == want

@pytest.mark.parametrize("lines,code", [
    ([], "CART_EMPTY"), ([LineInput("menu_030", None, 1)] * 11, "CART_TOO_LARGE"),
    ([LineInput("menu_999", None, 1)], "ITEM_NOT_FOUND"), ([LineInput("menu_001", None, 1)], "VARIANT_REQUIRED"),
    ([LineInput("menu_030", "menu_001:den", 1)], "INVALID_VARIANT")])
def test_quote_rejects_invalid_carts(conn, lines, code):
    with pytest.raises(ApiError) as e: quote_cart(conn, lines)
    assert code_of(e) == code and e.value.status == 422

def test_quote_rejects_sold_out(conn):
    conn.execute("UPDATE menu_items SET availability='sold_out' WHERE id='menu_019'")
    with pytest.raises(ApiError) as e: quote_cart(conn, [LineInput("menu_019", None, 1)])
    assert code_of(e) == "ITEM_UNAVAILABLE"

def _create(conn, key="key-000001", total=115000, lines=CART):
    return create_order(conn, lines=lines, expected_total_vnd=total, customer_name="Minh", table_label="Bàn 12", note=None,
                        source="ui", idempotency_key=key, conversation_id=None)

def test_create_order_snapshot_and_event(conn):
    order, replayed = _create(conn)
    assert (order["code"], order["status"], order["total_vnd"], replayed) == ("BB-0001", "pending", 115000, False)
    assert [l["unit_price_vnd"] for l in order["lines"]] == [35000, 45000]
    assert [(e["from_status"], e["to_status"], e["actor"]) for e in order["events"]] == [(None, "pending", "customer")]

def test_create_order_idempotent_replay(conn):
    a, _ = _create(conn); b, replayed = _create(conn)
    assert a["id"] == b["id"] and replayed is True
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1

def test_create_order_idempotency_conflict(conn):
    _create(conn)
    with pytest.raises(ApiError) as e: _create(conn, lines=[LineInput("menu_030", None, 2)], total=90000)
    assert code_of(e) == "IDEMPOTENCY_CONFLICT" and e.value.status == 409

def test_create_order_price_changed(conn):
    with pytest.raises(ApiError) as e: _create(conn, total=100000)
    assert code_of(e) == "PRICE_CHANGED" and e.value.details["quote"]["total_vnd"] == 115000
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0

def test_transitions(conn):
    order, _ = _create(conn)
    assert transition_status(conn, order_id=order["id"], to_status="confirmed", expected_status="pending", reason=None)["status"] == "confirmed"
    with pytest.raises(ApiError) as e: transition_status(conn, order_id=order["id"], to_status="pending", expected_status="confirmed", reason=None)
    assert code_of(e) == "INVALID_TRANSITION"
    with pytest.raises(ApiError) as e: transition_status(conn, order_id=order["id"], to_status="preparing", expected_status="pending", reason=None)
    assert code_of(e) == "STATUS_CONFLICT" and e.value.details["current_status"] == "confirmed"
    with pytest.raises(ApiError) as e: transition_status(conn, order_id=order["id"], to_status="cancelled", expected_status="confirmed", reason=None)
    assert code_of(e) == "VALIDATION_ERROR"
    assert get_order(conn, code="BB-0001")["events"][-1]["actor"] == "admin"
```

- [ ] **Step 2: Write failing draft tests** — `backend/tests/orders/test_drafts.py`

```python
import pytest
from app.errors import ApiError
from app.orders.service import LineInput, create_draft, confirm_draft, discard_draft
CONV = "0" * 32
LINES = [LineInput("menu_024", None, 1)]

def _draft(conn): return create_draft(conn, conversation_id=CONV, lines=LINES, customer_name=None, table_label=None, note=None)

def test_create_draft_creates_no_order(conn):
    d = _draft(conn)
    assert d["status"] == "open" and d["quote"]["total_vnd"] == 45000 and len(d["draft_id"]) == 32
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0

def test_confirm_draft_is_idempotent(conn):
    d = _draft(conn)
    o1, r1 = confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    o2, r2 = confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    assert (o1["code"], o1["source"], r1, r2, o1["id"] == o2["id"]) == ("BB-0001", "agent_draft", False, True, True)
    assert conn.execute("SELECT status FROM order_drafts").fetchone()[0] == "confirmed"

def test_confirm_price_changed_refreshes_quote(conn):
    d = _draft(conn)
    conn.execute("UPDATE menu_items SET base_price_vnd=50000 WHERE id='menu_024'")
    with pytest.raises(ApiError) as e: confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    assert e.value.code == "PRICE_CHANGED" and e.value.details["quote"]["total_vnd"] == 50000
    order, _ = confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=50000)
    assert order["total_vnd"] == 50000

def test_confirm_draft_item_now_sold_out(conn):
    d = _draft(conn)
    conn.execute("UPDATE menu_items SET availability='sold_out' WHERE id='menu_024'")
    with pytest.raises(ApiError) as e: confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    assert e.value.code == "ITEM_UNAVAILABLE"

def test_expired_discarded_and_missing(conn):
    d = _draft(conn)
    conn.execute("UPDATE order_drafts SET expires_at='2000-01-01T00:00:00.000Z'")
    with pytest.raises(ApiError) as e: confirm_draft(conn, draft_id=d["draft_id"], expected_total_vnd=45000)
    assert (e.value.status, e.value.code) == (410, "DRAFT_EXPIRED")
    d2 = _draft(conn); discard_draft(conn, draft_id=d2["draft_id"])
    with pytest.raises(ApiError) as e: confirm_draft(conn, draft_id=d2["draft_id"], expected_total_vnd=45000)
    assert e.value.code == "DRAFT_DISCARDED"
    with pytest.raises(ApiError) as e: confirm_draft(conn, draft_id="f" * 32, expected_total_vnd=45000)
    assert e.value.code == "DRAFT_NOT_FOUND"
```

- [ ] **Step 3: Write failing API tests** — `backend/tests/api/test_orders_api.py`

```python
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

def test_order_stream_first_event_is_snapshot(client):
    client.post("/api/orders", json=BODY, headers={"Idempotency-Key": "k" * 12})
    with client.stream("GET", "/api/orders/BB-0001/stream") as s:
        first = next(s.iter_lines())
    assert first == "event: order_status"
```

- [ ] **Step 4: Run** — `uv run pytest backend/tests/orders backend/tests/api/test_orders_api.py -v` → FAIL (module missing).
- [ ] **Step 5: Implement** `state.py`, `service.py` (follow the step lists in `docs/database-design.md §7` exactly; `request_hash = sha256(json.dumps({...}, sort_keys=True, ensure_ascii=False))`; drafts: `draft_id = uuid4().hex`, `expires_at = add_minutes(now, 30)`, `OrderDraft.order_code` from the joined order; quote is computed with the same connection inside `transaction()`), `bus.py`, `sse.py`, `api/orders.py` (Pydantic request models with limits from §4; `Idempotency-Key` header 8–100 chars else 400; after a non-replayed create/confirm: `bus.publish("admin","order_created",{"order":o})` and `bus.publish(f"order:{o['id']}","order_status",{"order":o})`; `GET /api/orders/{code}/stream` yields the snapshot first then subscription events through `with_heartbeat`).
- [ ] **Step 6: Run** — `uv run pytest -q` → PASS.
- [ ] **Step 7: Commit** — `git commit -m "feat(orders): quote, idempotent orders, drafts confirm/discard, SSE bus"`

**Acceptance:** C2 — UI checkout creates `BB-0001`; repeated POST with same key returns it with `Idempotent-Replay: true`.

---

### Task A3: Admin authentication and admin API (2:00–2:35)

**Files:**
- Create: `backend/app/admin/__init__.py`, `backend/app/admin/auth.py`, `backend/app/api/admin.py`
- Modify: `backend/app/deps.py` (`require_admin`), `backend/app/main.py` (router; `LoginRateLimiter` on `app.state`)
- Test: `backend/tests/api/test_admin_api.py`

**Interfaces:**
- Consumes: A2 service/state/bus/sse.
- Produces: `auth.login(conn, settings, pin: str, client_ip: str, limiter: LoginRateLimiter) -> dict` (`{token, expires_at}`; 401/429/503); `auth.verify(conn, token: str) -> None` (401 `ADMIN_AUTH_REQUIRED`); `auth.logout(conn, token)`; `class LoginRateLimiter(max_failures=5, window_s=60)`: `check(ip)`, `record_failure(ip)`; `deps.require_admin(request, authorization: str | None = Header(None)) -> str`.
- Admin order DTO = A2 order + `allowed_next` = `state.allowed_next(status)`.

- [ ] **Step 1: Write failing tests** — `backend/tests/api/test_admin_api.py`

```python
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
```
Add one test with `Settings(admin_pin="")` → login `503 ADMIN_NOT_CONFIGURED` (build a second app via `create_app(dataclasses.replace(settings, admin_pin=""))`).

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (`hmac.compare_digest(pin.encode(), settings.admin_pin.encode())`; token `secrets.token_urlsafe(32)`; store `sha256` hex; expiry 12 h checked in `verify`; client IP from `request.client.host`; `/api/admin/stream` subscribes to topic `admin`; status PATCH publishes `order_updated` to `admin` and `order_status` to `order:<id>`; menu PATCH validates `availability` enum and returns `menu_item_dto`).
- [ ] **Step 4: Run** `uv run pytest -q` → PASS. **Step 5: Commit** `git commit -m "feat(admin): PIN login, bearer tokens, order transitions, admin SSE, menu availability"`

**Acceptance:** C3 — admin confirms an order and the customer stream receives `order_status` with `confirmed`.

---

### Task A4: Agent — tools, instructions, streaming endpoint (2:35–3:50)

**Files:**
- Modify: `backend/app/catalog/repository.py` (add `search_menu_items`, `recommend_items`, `coworking_info`)
- Create: `backend/app/agent/__init__.py`, `context.py`, `instructions.py`, `tools.py`, `factory.py`, `stream.py`, `backend/app/api/agent.py`
- Modify: `backend/app/main.py` (build agent once: `app.state.agent = build_agent(settings)`; include agent router)
- Test: `backend/tests/agent/__init__.py`, `backend/tests/agent/helpers.py`, `backend/tests/agent/test_repository_queries.py`, `backend/tests/agent/test_agent_stream.py`

**Interfaces:**
- Consumes: A1 repository/dto, A2 `create_draft`, `list_orders`, `get_order`, `STATUS_LABELS`; `app.knowledge.retrieval.asearch_knowledge`.
- Produces:
  - `search_menu_items(conn, *, query: str | None, category_id: str | None, max_price_vnd: int | None, kind: str = "any", limit: int = 10) -> dict` (`{"total": int, "items": [...]}` with item shape of `docs/agent-design.md §4`)
  - `recommend_items(conn, *, preferences: list[str], max_price_vnd: int | None, include_food: bool, exclude_item_ids: list[str], limit: int) -> list[dict]`
  - `coworking_info(conn, *, topic: str, min_capacity: int | None, need_tables: bool) -> dict`
  - `@dataclass class AgentContext: conversation_id: str; run_id: str; db_path: Path; index: KnowledgeIndex; embedder: VoyageEmbedder | None; sources: dict[str, dict] = field(default_factory=dict)`
  - `INSTRUCTIONS: str` (verbatim `docs/agent-design.md §5`); `ALL_TOOLS: list[FunctionTool]` (7); `as_tool_json(payload: dict) -> str`
  - `build_agent(settings: Settings, *, model: Model | str | None = None) -> Agent[AgentContext]`; `build_run_config(settings, conversation_id: str, run_id: str) -> RunConfig`
  - `@dataclass class AgentDeps: settings: Settings; agent: Agent; index: KnowledgeIndex; embedder: VoyageEmbedder | None`
  - `run_chat_stream(deps: AgentDeps, conversation_id: str, message: str, *, session: Session | None = None) -> AsyncIterator[str]` (SSE strings; default session `SQLiteSession("chat-"+conversation_id, settings.agent_sessions_db_path)`)
  - `POST /api/agent/chat/stream` (requires `X-Conversation-Id`)

- [ ] **Step 1: Write failing query tests** — `backend/tests/agent/test_repository_queries.py`

```python
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
```

- [ ] **Step 2: Write failing stream tests** — `backend/tests/agent/helpers.py` + `test_agent_stream.py`

```python
# helpers.py
import json
def parse_sse(chunks: list[str]) -> list[tuple[str, dict]]:
    out = []
    for block in "".join(chunks).split("\n\n"):
        lines = [l for l in block.splitlines() if l and not l.startswith(":")]
        if lines:
            out.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return out
async def collect(gen) -> list[tuple[str, dict]]:
    return parse_sse([c async for c in gen])
```

```python
# test_agent_stream.py
import openai, pytest
from agents import SQLiteSession
from agents.testing import ScriptedModel, ModelStep, assistant_message, function_call
from app.agent.factory import build_agent
from app.agent.stream import AgentDeps, run_chat_stream
from app.knowledge.retrieval import KnowledgeIndex
from .helpers import collect
CONV = "a" * 32

def deps_for(settings, conn, steps):
    return AgentDeps(settings=settings, agent=build_agent(settings, model=ScriptedModel(steps)),
                     index=KnowledgeIndex.load(conn), embedder=None)

async def run(deps, message, tmp_path):
    return await collect(run_chat_stream(deps, CONV, message, session=SQLiteSession("t", tmp_path / "s.db")))

async def test_menu_question_streams_tool_then_text(settings, conn, tmp_path):
    deps = deps_for(settings, conn, [[function_call("search_menu", {"query": "matcha"}, call_id="c1")],
                                     [assistant_message("Có 5 món matcha.")]])
    ev = await run(deps, "Menu matcha có gì?", tmp_path)
    states = [d["state"] for n, d in ev if n == "agent_state"]
    assert [n for n, _ in ev][0] == "run_started" and ev[-1][0] == "done" and ev[-1][1]["reason"] == "completed"
    assert states == ["thinking", "searching", "thinking", "composing", "idle"]
    assert next(d for n, d in ev if n == "tool_finished") == {"call_id": "c1", "tool": "search_menu", "ok": True, "summary": "5 món"}

async def test_prepare_order_emits_draft_and_creates_no_order(settings, conn, tmp_path):
    args = {"lines": [{"item_id": "menu_024", "variant_id": None, "quantity": 1, "note": None}],
            "customer_name": None, "table_label": None, "note": None}
    deps = deps_for(settings, conn, [[function_call("prepare_order", args, call_id="c2")],
                                     [assistant_message("Bạn bấm Xác nhận đặt món nhé.")]])
    ev = await run(deps, "Lấy 1 trà chanh gừng mật ong", tmp_path)
    draft = next(d["draft"] for n, d in ev if n == "order_draft")
    assert draft["quote"]["total_vnd"] == 45000 and draft["status"] == "open"
    assert "working" in [d["state"] for n, d in ev if n == "agent_state"]
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0

async def test_prepare_order_unknown_item_returns_tool_error(settings, conn, tmp_path):
    args = {"lines": [{"item_id": "menu_999", "variant_id": None, "quantity": 1, "note": None}],
            "customer_name": None, "table_label": None, "note": None}
    deps = deps_for(settings, conn, [[function_call("prepare_order", args, call_id="c3")], [assistant_message("Món không có.")]])
    ev = await run(deps, "Lấy món 999", tmp_path)
    assert next(d for n, d in ev if n == "tool_finished")["ok"] is False and not [1 for n, _ in ev if n == "order_draft"]

async def test_model_error_emits_model_unavailable(settings, conn, tmp_path):
    err = openai.APIConnectionError(request=__import__("httpx").Request("POST", "https://api.openai.com/v1/responses"))
    deps = deps_for(settings, conn, [ModelStep.raise_error(err)])
    ev = await run(deps, "Xin chào", tmp_path)
    assert ("error", {"code": "MODEL_UNAVAILABLE", "message": "Trợ lý tạm thời không khả dụng — bạn vẫn có thể đặt món từ Menu.", "retryable": True}) in ev
    assert ev[-1][0] == "done" and ev[-1][1]["reason"] == "error"
```

- [ ] **Step 3: Run** — `uv run pytest backend/tests/agent -v` → FAIL.
- [ ] **Step 4: Implement repository queries** (SQL in `docs/agent-design.md §4`; folded-token matching as in A1; `recommend_items` scoring exactly as specified; items include `matched_tags` and `reasons`).
- [ ] **Step 5: Implement agent modules** per `docs/agent-design.md §3–§6`: tools are `async` with `@function_tool(timeout=…, failure_error_function=tool_failure)`; the first parameter is `ctx: RunContextWrapper[AgentContext]`; `prepare_order` calls `create_draft` inside `transaction()` via `connect(ctx.context.db_path)`; `build_agent(settings, model=None)` uses `model or settings.openai_model`, `ModelSettings(reasoning=Reasoning(effort="low"), verbosity="low")` only when `model` is a string; `stream.py` maps SDK events, writes `agent_runs`/`agent_tool_calls`, and maps `openai.APIConnectionError|AuthenticationError|RateLimitError|APIStatusError(>=500)` → `MODEL_UNAVAILABLE` (message exactly as in the test).
- [ ] **Step 6: Run** `uv run pytest -q` → PASS. **Step 7: Live check (1 call, ~$0.001)** — start uvicorn and
  `curl -N -X POST localhost:8000/api/agent/chat/stream -H "Content-Type: application/json" -H "X-Conversation-Id: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" -d "{\"message\":\"Quán mở cửa mấy giờ?\"}"` → events include `tool_started get_cafe_info` and text containing `22:30`.
- [ ] **Step 8: Commit** — `git commit -m "feat(agent): 7 tools, instructions, SSE streaming with real agent states"`

**Acceptance:** C4 — agent recommends with SQL prices, emits `order_draft`, creates 0 orders; draft confirm via REST works from the UI.

---

### Task A5: Reliability, live smoke tests, demo reset (3:50–4:30)

**Files:**
- Modify: `backend/app/agent/stream.py`, `backend/app/agent/factory.py`, `backend/app/api/agent.py`
- Create: `scripts/demo/reset_demo.py`, `backend/tests/agent/test_guards.py`, `backend/tests/agent/test_live_smoke.py`, `backend/tests/test_reset_demo.py`

**Interfaces:**
- Produces: `class ConversationGuard: acquire(conversation_id) -> bool` / `release(conversation_id)` (409 `RUN_IN_PROGRESS`), `allow_message(conversation_id) -> bool` (20/min → 429); `reset_demo(db_path: Path, sessions_db: Path, backups_dir: Path) -> dict[str, int]`; `assert_prices_grounded(text: str, allowed_prices: set[int]) -> None` (test helper: every `\d{1,3}(\.\d{3})+đ` amount in `text` ∈ allowed).

- [ ] **Step 1: Failing tests** — `test_guards.py`: two concurrent requests with the same conversation id → one `409 RUN_IN_PROGRESS` (call `ConversationGuard` directly: `acquire` twice → `True, False`); 21st message in 60 s → `False`; missing header → 400 via `client.post("/api/agent/chat/stream", json={"message":"hi"})`.
  `test_reset_demo.py`: create an order + draft in a temp DB copy, run `reset_demo(...)` → `orders`, `order_drafts`, `admin_sessions` count 0, `menu_items` all `unknown`, a backup file exists, `customer_accounts` still 1 row.
- [ ] **Step 2: Implement** guard + rate limit in `api/agent.py`; cancellation (`except asyncio.CancelledError: result.cancel(); status='cancelled'`); `MAX_TURNS` via `error_handlers`; `SESSION_RESET` on `openai.BadRequestError` mentioning tool/function output (`await session.clear_session()`); model settings with `timeout=30` and `retry=ModelRetrySettings(...)` per `docs/agent-design.md §8` — if the live smoke rejects a field, remove only that field and log it in `PROGRESS.md`. `reset_demo.py` per `docs/database-design.md §9` with `if __name__ == "__main__":` printing counts.
- [ ] **Step 3: Live smoke** — `test_live_smoke.py` (all `@pytest.mark.live`, skip if no key) for the 5 prompts in `docs/agent-design.md §9`, using `run_chat_stream` against a temp DB copy and the real model. Run `uv run pytest -m live -q` (≤6 model runs). Record results in `PROGRESS.md`.
- [ ] **Step 4: Run** `uv run pytest -q` → PASS. **Step 5: Commit** `git commit -m "feat(agent): guards, error mapping, live smoke; chore: demo reset script"`

**Acceptance:** degraded mode works with `OPENAI_API_KEY=invalid uv run uvicorn …` (chat → `MODEL_UNAVAILABLE`, orders still work); reset script restores a clean demo in < 5 s.

---

### Task A6: P1 and integration support (4:30–5:00)

- [ ] `GET /api/admin/insights` (`AdminInsights` shape): orders by status, `orders_total`, `revenue_completed_vnd` (sum `total_vnd` where `completed`), top 5 items by quantity, agent runs/tool calls/errors/tokens from `agent_runs`/`agent_tool_calls`. Test: `test_insights_counts_orders_and_tool_calls`.
- [ ] Draft-confirm memory note: in `POST /api/orders/drafts/{id}/confirm`, after commit, `await SQLiteSession("chat-"+conversation_id, …).add_items([{"role": "assistant", "content": f"Đơn {code} đã được tạo từ đơn nháp ({total}) và đang chờ quán xác nhận."}])`. Test via `get_items()`.
- [ ] `GET /api/agent/history` (text items only). Test with a seeded session.
- [ ] Fix integration bugs reported by Dev B; rehearse with `docs/demo-runbook.md`; update `TASKS.md`/`PROGRESS.md`. Commit per fix.
