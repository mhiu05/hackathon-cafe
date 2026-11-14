-- 0001_catalog: café reference data for branch biblio-79-nguy-nhu-kon-tum.
-- Loaded (replace-all) by scripts/knowledge/ingest.py from data/knowledge/normalized/*.json.
-- Operational truth for prices/availability lives HERE (SQL), never in embeddings.
-- Timestamps: ISO-8601 UTC strings 'YYYY-MM-DDTHH:MM:SS.sssZ'. Money: INTEGER VND.

CREATE TABLE cafe_profile (
    branch_id           TEXT PRIMARY KEY,
    brand_name          TEXT NOT NULL,
    display_name        TEXT NOT NULL,
    address             TEXT NOT NULL,
    latitude            REAL,
    longitude           REAL,
    phone               TEXT,
    open_time           TEXT,              -- 'HH:MM' local Asia/Ho_Chi_Minh
    close_time          TEXT,              -- 'HH:MM'
    google_maps_url     TEXT,
    facebook_url        TEXT,
    data_status         TEXT NOT NULL CHECK (data_status IN ('owner_verified', 'user_provided_unverified')),
    profile_json        TEXT NOT NULL,     -- full normalized cafe_profile.json (facts + provenance)
    updated_at          TEXT NOT NULL
);

CREATE TABLE menu_categories (
    id                  TEXT PRIMARY KEY,  -- slug, e.g. 'ca-phe'
    name                TEXT NOT NULL UNIQUE,
    kind                TEXT NOT NULL CHECK (kind IN ('drink', 'food')),
    sort_order          INTEGER NOT NULL
);

CREATE TABLE menu_items (
    id                  TEXT PRIMARY KEY,  -- stable source id, e.g. 'menu_014'
    category_id         TEXT NOT NULL REFERENCES menu_categories(id),
    name                TEXT NOT NULL,     -- exactly as printed on the menu photo
    name_search         TEXT NOT NULL,     -- lowercase, diacritics removed, đ->d (for LIKE search)
    base_price_vnd      INTEGER CHECK (base_price_vnd IS NULL OR base_price_vnd > 0),  -- NULL => variant required
    availability        TEXT NOT NULL DEFAULT 'unknown' CHECK (availability IN ('available', 'sold_out', 'unknown')),
    availability_note   TEXT,
    is_orderable        INTEGER NOT NULL DEFAULT 1 CHECK (is_orderable IN (0, 1)),
    price_verified      INTEGER NOT NULL DEFAULT 0 CHECK (price_verified IN (0, 1)),
    description         TEXT,              -- verified description only; NULL when no verified source
    note                TEXT,              -- data-entry note from the photo transcription
    needs_review_json   TEXT NOT NULL DEFAULT '[]',
    suggested_tags_json TEXT NOT NULL DEFAULT '[]',  -- INFERRED tags for recommendation; not facts
    source_id           TEXT NOT NULL,     -- kb source id, e.g. 'src-photo-drink-menu'
    sort_order          INTEGER NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX idx_menu_items_category ON menu_items(category_id, sort_order);
CREATE INDEX idx_menu_items_price ON menu_items(base_price_vnd);

CREATE TABLE menu_item_variants (
    id                  TEXT PRIMARY KEY,  -- '<item_id>:<slug>', e.g. 'menu_023:2-nguoi'
    item_id             TEXT NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
    label               TEXT NOT NULL,
    price_vnd           INTEGER NOT NULL CHECK (price_vnd > 0),
    sort_order          INTEGER NOT NULL,
    UNIQUE (item_id, label)
);

CREATE TABLE coworking_packages (
    id                  TEXT PRIMARY KEY,  -- 'cowork-1-day' | 'cowork-1-week' | 'cowork-1-month'
    label               TEXT NOT NULL,
    duration_days       INTEGER NOT NULL CHECK (duration_days > 0),
    price_vnd           INTEGER NOT NULL CHECK (price_vnd > 0),
    includes_vat        INTEGER NOT NULL CHECK (includes_vat IN (0, 1)),
    price_verified      INTEGER NOT NULL DEFAULT 0 CHECK (price_verified IN (0, 1)),
    source_id           TEXT NOT NULL,
    sort_order          INTEGER NOT NULL
);

CREATE TABLE meeting_rooms (
    id                  TEXT PRIMARY KEY,  -- 'room-1'..'room-4', 'cafe-space'
    name                TEXT NOT NULL UNIQUE,
    area_m2             INTEGER NOT NULL CHECK (area_m2 > 0),
    capacity_max        INTEGER NOT NULL CHECK (capacity_max > 0),       -- largest printed capacity
    capacity_theater    INTEGER,           -- chairs only
    capacity_tables     INTEGER,           -- tables + chairs
    layout_note         TEXT,
    session_hours       INTEGER NOT NULL CHECK (session_hours > 0),
    price_vnd           INTEGER NOT NULL CHECK (price_vnd > 0),          -- per session
    includes_vat        INTEGER NOT NULL CHECK (includes_vat IN (0, 1)),
    price_verified      INTEGER NOT NULL DEFAULT 0 CHECK (price_verified IN (0, 1)),
    source_id           TEXT NOT NULL,
    sort_order          INTEGER NOT NULL
);

CREATE TABLE service_facts (
    id                  TEXT PRIMARY KEY,
    scope               TEXT NOT NULL CHECK (scope IN ('coworking', 'meeting_room', 'cafe')),
    kind                TEXT NOT NULL CHECK (kind IN ('amenity', 'extra_service', 'policy')),
    label               TEXT NOT NULL,
    price_from_vnd      INTEGER CHECK (price_from_vnd IS NULL OR price_from_vnd > 0),
    price_to_vnd        INTEGER CHECK (price_to_vnd IS NULL OR price_to_vnd > 0),
    unit                TEXT,
    note                TEXT,
    verification_status TEXT NOT NULL,
    source_id           TEXT NOT NULL,
    sort_order          INTEGER NOT NULL
);
CREATE INDEX idx_service_facts_scope ON service_facts(scope, kind, sort_order);
