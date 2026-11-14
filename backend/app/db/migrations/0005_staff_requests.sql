-- 0005_staff_requests: customer → staff help requests created by the agent tool `request_staff`.

CREATE TABLE staff_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,            -- 'YC-' || printf('%04d', id)
    conversation_id TEXT NOT NULL CHECK (length(conversation_id) = 32),
    kind            TEXT NOT NULL CHECK (kind IN
                        ('wifi','clean_table','water','find_book','payment','temperature','other')),
    table_label     TEXT CHECK (table_label IS NULL OR length(table_label) <= 20),
    note            TEXT CHECK (note IS NULL OR length(note) <= 200),
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','done')),
    created_at      TEXT NOT NULL,
    resolved_at     TEXT,
    CHECK ((status = 'done') = (resolved_at IS NOT NULL))
);
CREATE INDEX idx_staff_requests_status_created ON staff_requests(status, created_at DESC);
CREATE INDEX idx_staff_requests_conversation ON staff_requests(conversation_id, created_at DESC);
