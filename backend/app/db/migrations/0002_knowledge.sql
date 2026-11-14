-- 0002_knowledge: provenance-tracked knowledge base with Voyage vectors and an FTS5 fallback.
-- Written only by scripts/knowledge/ingest.py; read by app.knowledge.retrieval.

CREATE TABLE kb_sources (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    source_type         TEXT NOT NULL CHECK (source_type IN (
                            'user_photo', 'google_maps', 'google_maps_review', 'tiktok',
                            'web_article', 'directory_listing', 'facebook', 'owner', 'kb_curation')),
    url                 TEXT,
    branch_id           TEXT,
    verification_status TEXT NOT NULL CHECK (verification_status IN (
                            'owner_verified', 'verified_branch', 'brand_general',
                            'unverified_branch', 'conflicting', 'rejected')),
    retrieved_at        TEXT NOT NULL,
    published_at        TEXT,
    notes               TEXT,
    metadata_json       TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE kb_documents (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    category            TEXT NOT NULL CHECK (category IN (
                            'overview', 'location', 'opening_hours', 'facilities', 'coworking',
                            'room_rental', 'food_beverage', 'events', 'customer_insights', 'faq', 'branches')),
    content_kind        TEXT NOT NULL CHECK (content_kind IN ('fact', 'review', 'inference', 'event', 'product', 'service')),
    branch_id           TEXT NOT NULL,
    verification_status TEXT NOT NULL CHECK (verification_status IN (
                            'owner_verified', 'verified_branch', 'brand_general',
                            'unverified_branch', 'conflicting')),   -- 'rejected' is never ingested
    source_id           TEXT NOT NULL REFERENCES kb_sources(id),
    source_url          TEXT,
    retrieved_at        TEXT NOT NULL,
    content             TEXT NOT NULL,
    content_hash        TEXT NOT NULL UNIQUE,
    metadata_json       TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_kb_documents_category ON kb_documents(category);

CREATE TABLE kb_chunks (
    id                  TEXT PRIMARY KEY,  -- '<document_id>#<chunk_index>'
    document_id         TEXT NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    chunk_index         INTEGER NOT NULL CHECK (chunk_index >= 0),
    heading             TEXT,
    content             TEXT NOT NULL,     -- exact text that was embedded (title/heading prefixed)
    content_hash        TEXT NOT NULL UNIQUE,
    token_estimate      INTEGER NOT NULL,
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE kb_embeddings (
    chunk_id            TEXT PRIMARY KEY REFERENCES kb_chunks(id) ON DELETE CASCADE,
    model               TEXT NOT NULL,
    dimension           INTEGER NOT NULL CHECK (dimension > 0),
    content_hash        TEXT NOT NULL,     -- must equal kb_chunks.content_hash
    vector              BLOB NOT NULL,     -- float32 little-endian, L2-normalised
    created_at          TEXT NOT NULL,
    CHECK (length(vector) = dimension * 4)
);

-- Diacritic-insensitive keyword fallback (used when Voyage is unavailable or times out).
CREATE VIRTUAL TABLE kb_chunks_fts USING fts5(
    chunk_id UNINDEXED,
    title,
    content,
    tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TABLE kb_meta (
    key                 TEXT PRIMARY KEY,
    value               TEXT NOT NULL
);
