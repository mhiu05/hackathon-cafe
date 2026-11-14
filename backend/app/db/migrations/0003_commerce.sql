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
