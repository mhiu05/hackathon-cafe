# Database Design — SQLite (single café)

Files: `data/cafe.db` (catalog + knowledge + commerce; gitignored, rebuilt by `scripts/knowledge/ingest.py`),
`data/agent_sessions.db` (OpenAI Agents SDK `SQLiteSession` store; separate file to avoid write-lock contention).

## 1. Conventions (locked)

| Topic | Rule |
|---|---|
| Connection | Always `app.db.connection.connect(path)`: `foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`, `isolation_level=None` (autocommit) |
| Transactions | Multi-statement writes use `with transaction(conn):` → `BEGIN IMMEDIATE … COMMIT/ROLLBACK` |
| Timestamps | TEXT ISO-8601 UTC with ms and `Z`: `2026-11-14T04:27:41.526Z` (`app.timeutil.utc_now()`); UI converts to UTC+7 |
| Money | INTEGER VND (35000), never strings like "35k"; totals computed server-side |
| IDs | catalog: stable text ids (`menu_014`, `menu_023:2-nguoi`); orders: INTEGER PK + public `code` `BB-0001`; drafts: uuid4 hex |
| Booleans | INTEGER 0/1 with CHECK |
| JSON columns | suffix `_json`, TEXT, always valid JSON (`'[]'`/`'{}'` defaults) |
| Migrations | forward-only `backend/app/db/migrations/NNNN_name.sql`, applied by `apply_migrations()` at backend startup and by `ingest.py`; recorded in `schema_migrations` |
| Reset | delete DB file + `ingest.py --offline` (full rebuild from committed data), or `scripts/demo/reset_demo.py` (keeps catalog/KB, clears commerce) |

## 2. Migration state

| Version | File | Status | Owner |
|---|---|---|---|
| 0001 | `0001_catalog.sql` | **created & applied** | pipeline |
| 0002 | `0002_knowledge.sql` | **created & applied** | pipeline |
| 0003 | `0003_commerce.sql` | **specified in §5, NOT created** | Dev A, task A1 |

## 3. Catalog (0001 — exists)

`cafe_profile(branch_id PK, …, profile_json)` — one row; `profile_json` is `normalized/cafe_profile.json`.
`menu_categories(id PK slug, name UNIQUE, kind drink|food, sort_order)` — 9 rows.
`menu_items(id PK, category_id FK, name, name_search, base_price_vnd NULL|>0, availability available|sold_out|unknown,
availability_note, is_orderable 0|1, price_verified 0|1, description, note, needs_review_json, suggested_tags_json, source_id, sort_order, updated_at)` — 51 rows.
`menu_item_variants(id PK '<item>:<slug>', item_id FK CASCADE, label, price_vnd>0, sort_order, UNIQUE(item_id,label))` — 4 rows.
`coworking_packages` (3), `meeting_rooms` (5), `service_facts` (22).

**Availability (decided by the owner of the project, 2026-11-14).** Staff-managed in Admin → Menu. Seed = `unknown` for every
item. Ordering: `sold_out` or `is_orderable=0` → `422 ITEM_UNAVAILABLE`; `unknown` → allowed, quote carries
`AVAILABILITY_UNCONFIRMED` (staff accepting the order *is* the stock check); `available` → allowed.
`ingest.py` UPSERTs items but never overwrites `availability`, `availability_note`, `is_orderable` of existing rows.

**Variants.** An item has either `base_price_vnd` (no variants) or `base_price_vnd IS NULL` + ≥1 variant. Order lines must
reference `variant_id` iff the item has variants. Unit price = variant price or base price.

## 4. Knowledge (0002 — exists)

`kb_sources` (21) → `kb_documents` (54 indexed; `rejected`/`unverified_branch` never stored) → `kb_chunks` (56) →
`kb_embeddings(chunk_id PK, model, dimension, content_hash, vector BLOB float32 LE L2-normalised, CHECK length=dim*4)`;
`kb_chunks_fts` (FTS5 over diacritic-folded title/content); `kb_meta` (embedding_model, embedding_dimension, built_at,
corpus_hash, menu_as_of, menu_price_basis, services_as_of, services_price_basis, booking_policy, data_notice).
Embedding cache: `data/knowledge/embeddings/voyage-4-lite_512.jsonl` keyed by chunk `content_hash` (committed → offline rebuild).

## 5. Commerce (0003 — to be created by Dev A exactly as below)

Decisions (2026-11-14): one **shared, pre-created customer account** (`shared-customer`) used automatically by every customer
browser — no customer login, all customer orders belong to it; chat memory is per browser via `conversation_id`.
The agent never creates orders: it creates **order drafts**; the customer confirms a draft through REST. No events table.

```sql
-- 0003_commerce: shared customer account, admin sessions, orders, order drafts, agent observability.

CREATE TABLE customer_accounts (
    id              TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
INSERT INTO customer_accounts(id, display_name, created_at)
VALUES ('shared-customer', 'Khách Biblio', '2026-11-14T00:00:00.000Z');

CREATE TABLE admin_sessions (
    token_hash      TEXT PRIMARY KEY,                -- sha256(admin bearer token) hex; raw token never stored
    created_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL                    -- created_at + 12h
);

CREATE TABLE orders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code                TEXT NOT NULL UNIQUE,        -- 'BB-' || printf('%04d', id)
    customer_account_id TEXT NOT NULL DEFAULT 'shared-customer' REFERENCES customer_accounts(id),
    conversation_id     TEXT CHECK (conversation_id IS NULL OR length(conversation_id) = 32),
    status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN
                            ('pending','confirmed','preparing','ready','completed','rejected','cancelled')),
    source              TEXT NOT NULL CHECK (source IN ('ui','agent_draft')),
    customer_name       TEXT CHECK (customer_name IS NULL OR length(customer_name) <= 40),
    table_label         TEXT CHECK (table_label IS NULL OR length(table_label) <= 20),
    note                TEXT CHECK (note IS NULL OR length(note) <= 200),
    subtotal_vnd        INTEGER NOT NULL CHECK (subtotal_vnd > 0),
    total_vnd           INTEGER NOT NULL CHECK (total_vnd > 0),
    item_count          INTEGER NOT NULL CHECK (item_count > 0),
    idempotency_key     TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 8 AND 100),
    request_hash        TEXT NOT NULL,               -- sha256 of canonical JSON of {lines, customer_name, table_label, note}
    status_reason       TEXT,                        -- required for rejected/cancelled
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX idx_orders_status_created ON orders(status, created_at DESC);
CREATE INDEX idx_orders_conversation ON orders(conversation_id, created_at DESC);

CREATE TABLE order_items (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id                INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    line_no                 INTEGER NOT NULL CHECK (line_no >= 1),
    item_id                 TEXT NOT NULL REFERENCES menu_items(id),
    variant_id              TEXT REFERENCES menu_item_variants(id),
    item_name_snapshot      TEXT NOT NULL,           -- name/price snapshot at order time
    variant_label_snapshot  TEXT,
    unit_price_vnd          INTEGER NOT NULL CHECK (unit_price_vnd > 0),
    quantity                INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 10),
    line_total_vnd          INTEGER NOT NULL,
    note                    TEXT CHECK (note IS NULL OR length(note) <= 120),
    UNIQUE (order_id, line_no),
    CHECK (line_total_vnd = unit_price_vnd * quantity)
);

CREATE TABLE order_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    from_status     TEXT,
    to_status       TEXT NOT NULL,
    actor           TEXT NOT NULL CHECK (actor IN ('customer','admin','system')),
    note            TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX idx_order_events_order ON order_events(order_id, id);

CREATE TABLE order_drafts (
    id                  TEXT PRIMARY KEY,            -- uuid4 hex (32 chars) = draft_id
    customer_account_id TEXT NOT NULL DEFAULT 'shared-customer' REFERENCES customer_accounts(id),
    conversation_id     TEXT NOT NULL CHECK (length(conversation_id) = 32),
    status              TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','confirmed','discarded')),
    request_json        TEXT NOT NULL,               -- {"lines":[...],"customer_name":…,"table_label":…,"note":…}
    quote_json          TEXT NOT NULL,               -- OrderQuote shown on the card (refreshed on PRICE_CHANGED)
    total_vnd           INTEGER NOT NULL CHECK (total_vnd > 0),
    order_id            INTEGER REFERENCES orders(id),
    created_at          TEXT NOT NULL,
    expires_at          TEXT NOT NULL,               -- created_at + 30 min; evaluated on read
    updated_at          TEXT NOT NULL,
    CHECK ((status = 'confirmed') = (order_id IS NOT NULL))
);
CREATE INDEX idx_order_drafts_conversation ON order_drafts(conversation_id, created_at DESC);

CREATE TABLE agent_runs (
    id                  TEXT PRIMARY KEY,            -- uuid4 hex, also SSE run_id
    conversation_id     TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('running','completed','error','cancelled')),
    model               TEXT NOT NULL,
    input_tokens        INTEGER NOT NULL DEFAULT 0,
    output_tokens       INTEGER NOT NULL DEFAULT 0,
    requests            INTEGER NOT NULL DEFAULT 0,
    error_code          TEXT,
    user_message_chars  INTEGER NOT NULL,
    started_at          TEXT NOT NULL,
    finished_at         TEXT
);
CREATE INDEX idx_agent_runs_conversation ON agent_runs(conversation_id, started_at DESC);

CREATE TABLE agent_tool_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    call_id         TEXT NOT NULL,
    tool            TEXT NOT NULL,
    ok              INTEGER NOT NULL CHECK (ok IN (0,1)),
    error_code      TEXT,
    latency_ms      INTEGER NOT NULL,
    args_json       TEXT NOT NULL DEFAULT '{}',      -- tool arguments, free-text fields truncated to 200 chars
    created_at      TEXT NOT NULL
);
CREATE INDEX idx_agent_tool_calls_tool ON agent_tool_calls(tool, created_at);
```

## 6. Order state machine (locked)

```
            ┌──────────► rejected (admin, reason required)
pending ────┼──────────► confirmed ──► preparing ──► ready ──► completed
            │               │  └──────────────────►┘ (confirmed → ready allowed)
            └──► cancelled ◄┴───────── preparing        (admin, reason required)
```

| From | Allowed `to_status` | Actor |
|---|---|---|
| pending | confirmed, rejected, cancelled | admin |
| confirmed | preparing, ready, cancelled | admin |
| preparing | ready, cancelled | admin |
| ready | completed | admin |
| completed / rejected / cancelled | — (terminal) | — |

Customer-initiated cancel is P2. Every transition: `UPDATE orders SET status=?, status_reason=?, updated_at=? WHERE id=? AND status=?`
(optimistic: `expected_status` from the client) → 0 rows ⇒ `409 STATUS_CONFLICT`; not in table ⇒ `409 INVALID_TRANSITION`;
then `INSERT order_events(actor='admin')`; same transaction; publish `order_updated` after COMMIT.

Status labels (vi): pending "Chờ quán xác nhận", confirmed "Quán đã nhận đơn", preparing "Đang pha chế",
ready "Sẵn sàng — mời bạn nhận tại quầy", completed "Hoàn tất", rejected "Quán từ chối", cancelled "Đã hủy".

## 7. Order creation (locked)

```
quote_cart(conn, lines) -> OrderQuote                     # read-only; ApiError 422 CART_EMPTY / CART_TOO_LARGE / ITEM_NOT_FOUND /
                                                          #   ITEM_UNAVAILABLE / VARIANT_REQUIRED / INVALID_VARIANT
create_order(conn, *, lines, expected_total_vnd, customer_name, table_label, note, source, idempotency_key, conversation_id)
  1. validate shape (1..10 lines, qty 1..10, note lengths)                        -> 422 VALIDATION_ERROR
  2. request_hash = sha256(canonical_json({lines, customer_name, table_label, note}))
  3. BEGIN IMMEDIATE
  4. existing = SELECT … WHERE idempotency_key=?
       same request_hash -> COMMIT, return (order, replayed=True)                   [HTTP 200 + Idempotent-Replay: true]
       different hash    -> ROLLBACK, 409 IDEMPOTENCY_CONFLICT
  5. quote = quote_cart(conn, lines)  (inside the transaction)
  6. expected_total_vnd != quote.total_vnd                                        -> ROLLBACK, 409 PRICE_CHANGED {quote}
  7. INSERT orders(code='tmp-'||hex(randomblob(6)), …); UPDATE orders SET code=printf('BB-%04d', id) WHERE id=?
  8. INSERT order_items (snapshots); INSERT order_events(NULL -> 'pending', actor='customer')
  9. COMMIT -> bus.publish("admin", order_created) -> return (order, replayed=False)  [HTTP 201]

create_draft(conn, *, conversation_id, lines, customer_name, table_label, note) -> OrderDraft      # agent tool prepare_order
  quote_cart (errors -> tool error JSON); INSERT order_drafts(status='open', expires_at=now+30min). Never inserts into orders.

confirm_draft(conn, *, draft_id, expected_total_vnd) -> (Order, replayed)                           # POST /api/orders/drafts/{id}/confirm
  BEGIN IMMEDIATE; draft = SELECT … WHERE id=?             -> 404 DRAFT_NOT_FOUND
  status='confirmed'  -> return (its order, replayed=True)                           [200]
  status='discarded'  -> 409 DRAFT_DISCARDED
  now > expires_at    -> 410 DRAFT_EXPIRED
  quote = quote_cart(draft.lines); quote.total_vnd != expected_total_vnd
                      -> UPDATE draft SET quote_json, total_vnd; COMMIT; 409 PRICE_CHANGED {quote}
  steps 7–8 with source='agent_draft', idempotency_key='draft:'+draft_id, conversation_id=draft.conversation_id,
  request_hash of the draft request; UPDATE draft SET status='confirmed', order_id=?; COMMIT; publish             [201]

discard_draft(conn, *, draft_id) -> {draft_id, status:"discarded"}  # open -> discarded; confirmed -> 409 DRAFT_ALREADY_CONFIRMED
```

UI path: `Idempotency-Key` header = uuid4 generated once per checkout attempt and reused on retry.
Agent path: an order exists only after the customer's click on the draft card (REST). No tool writes to `orders`.

## 8. Identity and isolation (locked)

- **Customers**: no login. Every customer request acts as `customer_accounts.id='shared-customer'` (`deps.CUSTOMER_ACCOUNT_ID`).
  Accepted consequence (single-laptop demo): any customer browser can open any order by code and `GET /api/orders` lists all
  customer orders. Per-customer isolation is P2 (schema already carries `customer_account_id`).
- **Conversations**: the browser generates `conversation_id` = uuid4 hex (32 lowercase hex chars) once, stores it in
  `localStorage["biblio.conversation"]`, and sends `X-Conversation-Id` on agent calls (required) and order calls (optional).
  SDK memory: `SQLiteSession("chat-"+conversation_id, AGENT_SESSIONS_DB_PATH)`. `get_order_status()` without a code returns the
  latest 3 orders with the caller's `conversation_id`. Tools read `conversation_id` from the run context, never from arguments.
- **Admin**: PIN from `.env` (`ADMIN_PIN`) → bearer token (sha256 stored, 12 h). Frontend route hiding is cosmetic only.

## 9. Demo reset (task A5, `scripts/demo/reset_demo.py`)

1. `PRAGMA wal_checkpoint(TRUNCATE)`; copy `data/cafe.db` → `data/backups/cafe-<UTC yyyymmddThhmmssZ>.db`.
2. One transaction: `UPDATE order_drafts SET order_id=NULL, status='discarded'; DELETE FROM order_events; DELETE FROM order_items;
   DELETE FROM order_drafts; DELETE FROM orders; DELETE FROM agent_tool_calls; DELETE FROM agent_runs; DELETE FROM admin_sessions;
   DELETE FROM sqlite_sequence WHERE name IN ('orders','order_items','order_events','agent_tool_calls');`
   `UPDATE menu_items SET availability='unknown', is_orderable=1, availability_note=<value from normalized/menu.json>;`
3. Delete `data/agent_sessions.db*`.
4. Print counts. Catalog, knowledge and `customer_accounts` stay (no Voyage call).
