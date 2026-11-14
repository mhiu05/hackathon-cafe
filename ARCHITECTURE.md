# ARCHITECTURE — Biblio AI Café Companion

Canonical architecture (approved 2026-11-14). Contracts: `docs/api-contracts.md` · schema: `docs/database-design.md` ·
agent: `docs/agent-design.md` · data provenance: `docs/knowledge-sources.md`.

## 1. System overview

```
 Customer browser (Vite :5173 / index.html)            Staff browser (Vite :5173 / admin.html)
   Discover · Menu · Cart · Order · Chat                    PIN login · Order board · Menu availability
   (no login; X-Conversation-Id per browser)                (Authorization: Bearer <token>)
            │  fetch JSON + fetch-SSE via Vite proxy /api            │
            └───────────────────────────┬────────────────────────────┘
                                        ▼
                    FastAPI (uvicorn, ONE worker, :8000) — backend/app/main.py
   ┌────────────┬──────────────────┬───────────────┬──────────────────────────────┐
   │ api/public │ api/orders       │ api/admin     │ api/agent                    │
   │ catalog.dto│ orders.service   │ admin.auth    │ agent.stream → Agents SDK    │
   └─────┬──────┴────────┬─────────┴───────┬───────┴──────────────┬───────────────┘
         │               │   realtime.bus (asyncio pub/sub) ◄──────┤
         ▼               ▼                                         ▼
   data/cafe.db (SQLite WAL): catalog · kb_* + vectors · orders/drafts   OpenAI Responses API (gpt-6-luna)
   data/agent_sessions.db (SDK SQLiteSession per conversation)           Voyage embeddings (query only; 5 s → FTS5 fallback)
```

Offline guarantee: menu, cart, orders, drafts confirm, admin and tracking never call external services. Only `/api/agent/*`
needs OpenAI; retrieval degrades to FTS5 without Voyage. Apify is used only at ingestion time.

## 2. Technology (versions locked by `uv.lock` / `pnpm-lock.yaml`)

| Layer | Choice |
|---|---|
| Python | 3.12.13 via `uv`; single root `pyproject.toml`; package `backend/app` (hatchling, editable) |
| Backend | FastAPI 0.162.7, uvicorn 0.54.0, stdlib `sqlite3` (direct SQL, no ORM), httpx 0.28.1, NumPy 2.5.4 |
| Agent | `openai-agents` 0.24.0 (openai 3.51.0), model `gpt-6-luna` |
| Retrieval | Voyage `voyage-4-lite`, 512-d float32, in-memory NumPy cosine; SQLite FTS5 fallback |
| Ingestion | `apify-client` 3.5.1 (group `ingest`); scripts in `scripts/knowledge/` |
| Tests | pytest 9.2.0, pytest-asyncio 1.5.0, `agents.testing.ScriptedModel`; Vitest 5.1.x + Testing Library 16.3.x + jsdom; Playwright 1.65.x (P1) |
| Frontend | pnpm; Vite 8.3.x multi-page (`index.html` customer, `admin.html` admin; **no router**); React 19.3.x; TypeScript (scaffold default); plain CSS + variables (`DESIGN.md`); `gsap` 3.15.1 + `@gsap/react` 2.1.2; `thinking-orbs` 0.3.2; `@fontsource/fraunces` + `@fontsource/be-vietnam-pro` 5.3.0 |

Excluded by decision: ORM, Redis, Celery, Postgres, vector DBs, Docker, auth providers, Tailwind, UI kits, state libraries, router.

## 3. Repository layout and ownership

```
hackathon/
├── PRD.md · ARCHITECTURE.md · DESIGN.md · RULES.md · TASKS.md · PROGRESS.md · README.md
├── pyproject.toml · uv.lock · .python-version · .env.example · .gitignore
├── biblio_cafe_kb_bundle/                   read-only originals (user-provided)
├── contracts/fixtures/                      API fixtures (generated + static) — both devs read; Dev A regenerates
├── data/cafe.db · agent_sessions.db         gitignored runtime DBs
├── data/knowledge/{curated,normalized,embeddings,eval}/ · raw/ (gitignored) · knowledge_extended.md · ingestion_report.md
├── scripts/knowledge/{collect,normalize,ingest,verify}.py   (done)
├── scripts/contracts/{export_fixtures,write_static_fixtures}.py (done)
├── scripts/demo/reset_demo.py                                 (A5)
├── backend/app/
│   ├── settings.py · db/{connection,migrate}.py · db/migrations/0001,0002 · knowledge/{text,embeddings,retrieval}.py · catalog/dto.py (done)
│   ├── db/migrations/0003_commerce.sql · main.py · errors.py · deps.py · timeutil.py · catalog/repository.py · api/public.py   (A1)
│   ├── orders/{state,service}.py · realtime/{bus,sse}.py · api/orders.py                                                       (A2)
│   ├── admin/auth.py · api/admin.py                                                                                          (A3)
│   └── agent/{context,instructions,tools,factory,stream}.py · api/agent.py                                                    (A4, A5)
├── backend/tests/{conftest.py, knowledge/ (done), api/, orders/, agent/}
├── frontend/                                Dev B only
└── docs/ (+ superpowers/plans/)
```

**Ownership rule**: Dev A writes only `backend/**`, `scripts/demo/**`, `contracts/**`; Dev B writes only `frontend/**`.
Root docs (`TASKS.md`, `PROGRESS.md`) are updated by each dev only in their own sections. A contract change requires both devs
and updates `docs/api-contracts.md` + `contracts/fixtures/` in the same commit.

## 4. Main components

| Component | Responsibility |
|---|---|
| `settings.py` | typed settings from root `.env` + env vars; `redacted()` for logs |
| `db.connection` / `db.migrate` | PRAGMAs (FK, WAL, busy_timeout 5000), `transaction()` = `BEGIN IMMEDIATE`; forward-only migrations |
| `knowledge.*` | Voyage embedder (httpx), `KnowledgeIndex` (NumPy matrix), `asearch_knowledge` (vector → FTS fallback, per-document dedupe, min cosine 0.30) |
| `catalog.dto` / `catalog.repository` | JSON shapes of `/api/cafe`, `/api/menu`, `/api/services`; menu search & recommendation queries |
| `orders.state` / `orders.service` | state machine, labels; `quote_cart`, `create_order`, `create_draft`, `confirm_draft`, `discard_draft`, `transition_status`, `get_order`, `list_orders` |
| `realtime.bus` / `realtime.sse` | in-process pub/sub (`admin`, `order:<id>` topics); SSE formatting + 15 s ping |
| `admin.auth` | PIN check (`hmac.compare_digest`), token issue/verify (sha256 in DB, 12 h), failed-login rate limit |
| `agent.*` | single orchestrator, 7 tools, instructions, SDK streaming → SSE mapping, run/tool logging |
| frontend `api/` | typed client (live/mock), fetch-SSE reader, conversation id |
| frontend `customer/`, `admin/` | screens, state hooks, Thinking Orb, GSAP motion |

## 5. Data flows

**Knowledge (offline, done)**: `collect.py` (web + bounded Apify) → `raw/` → curated decisions → `normalize.py` →
`normalized/*` → `ingest.py` (migrations, catalog UPSERT, chunks, Voyage vectors from cache, FTS) → `cafe.db` → `verify.py` report.

**Chat**: browser `POST /api/agent/chat/stream` (X-Conversation-Id) → lock + rate limit → `Runner.run_streamed` with
`SQLiteSession("chat-"+id)` → tool calls (SQL / retrieval) → SDK events mapped to SSE (`agent_state`, `tool_*`, `text_delta`,
`order_draft`, `message_completed`, `done`) → browser reducer renders orb/chips/text/draft card.

**Agent-prepared order**: `prepare_order` → `create_draft` (quote, `order_drafts` row, 30-min expiry) → SSE `order_draft` → customer
clicks **Xác nhận đặt món** → `POST /api/orders/drafts/{id}/confirm {expected_total_vnd}` → `confirm_draft` (re-quote, idempotent
`draft:<id>`, order + items + event, draft→confirmed) → bus `order_created` → admin board.

**Cart order**: `POST /api/orders/quote` → confirm dialog → `POST /api/orders` (`Idempotency-Key`, `expected_total_vnd`) → same
`create_order` path → bus.

**Staff**: `POST /api/admin/login {pin}` → token → `GET /api/admin/orders` + `GET /api/admin/stream` → `PATCH …/status
{to_status, expected_status, reason}` → `transition_status` (optimistic) → bus `order_updated` → customer `GET /api/orders/{code}/stream`.

## 6. Runtime

- Backend: `uv run uvicorn app.main:app --port 8000` (add `--reload` in dev). **Exactly one worker** (in-memory bus, locks, rate limits).
- Lifespan: `load_settings()` → `connect()` + `apply_migrations()` → `KnowledgeIndex.load()` → `VoyageEmbedder(timeout_s=5, max_retries=0)`
  (None if no key) → `build_agent()` → `EventBus()`; stored on `app.state`.
- Per request: `deps.get_db()` opens and closes a connection (`connect(settings.database_path)`).
- Frontend: `pnpm dev` (Vite proxy `/api` → `:8000`, SSE passes through); customer `http://localhost:5173/`, admin `http://localhost:5173/admin.html`.
- SSE responses: `text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `: ping` every 15 s; client falls back to 5 s polling.

## 7. Security boundaries

| Boundary | Enforcement |
|---|---|
| Secrets | only root `.env` (gitignored); never sent to the frontend; `verify.py` scans git-visible files |
| Admin vs customer | bearer token from PIN for every `/api/admin/*` except login; UI hiding is cosmetic |
| Customer identity | one shared pre-created account (owner decision); conversation id only scopes chat memory and "my latest orders" |
| LLM vs database | 7 tools; 6 read-only; `prepare_order` writes only a draft; orders exist only after a customer REST click |
| Prices | always computed server-side; client `expected_total_vnd` only detects drift (409) |
| Input limits | chat ≤1000 chars; notes ≤120/200; ≤10 lines × ≤10 qty; Pydantic validation; conversation id regex |
| Prompt injection | instructions treat tool/KB text as data; no identity/price tool params; min retrieval score |
| CORS | single origin `FRONTEND_ORIGIN` (dev uses same-origin proxy anyway) |

## 8. Verified locally (2026-11-14)

`uv sync` · `uv run python scripts/knowledge/ingest.py --offline` · `uv run python scripts/knowledge/verify.py --offline` ·
`uv run pytest -q` (9 passed). Planned commands for the app are in `docs/demo-runbook.md` and `docs/IMPLEMENTATION_HANDOFF.md`.
