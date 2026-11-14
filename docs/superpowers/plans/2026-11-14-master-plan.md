# Biblio AI Café Companion — Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In 5 hours, two developers ship the P0 loop *Customer → Agent → Knowledge/Menu tool → Recommendation → Order draft → customer confirmation → SQLite order → Admin confirmation → Customer status* on top of the already-built knowledge base.

**Architecture:** One FastAPI process (single worker) with direct SQLite, an in-process SSE bus and a single OpenAI Agents SDK orchestrator with 7 function tools; a Vite multi-page React app (customer `index.html`, admin `admin.html`) talking to `/api` through the Vite proxy. The agent only prepares drafts; real orders come from REST clicks.

**Tech Stack:** Python 3.12 · uv · FastAPI 0.162 · sqlite3 · openai-agents 0.24.0 (`gpt-6-luna`) · Voyage `voyage-4-lite`/512 · NumPy · pytest · pnpm · Vite 8 · React 19 · TypeScript · GSAP 3.15 + @gsap/react · thinking-orbs 0.3.2 · Vitest.

**Spec:** `PRD.md`, `ARCHITECTURE.md`, `DESIGN.md`, `RULES.md`, `docs/api-contracts.md`, `docs/database-design.md`, `docs/agent-design.md`, `docs/ui-ux-spec.md`, `docs/knowledge-sources.md`.

## Global Constraints

- Python `>=3.12,<3.13` via uv; dependencies only from `uv.lock` (`uv add` + note in PROGRESS.md for any addition).
- Model `gpt-6-luna` (`OPENAI_MODEL`); embeddings `voyage-4-lite`, `output_dimension=512`; never change either.
- Database `data/cafe.db` built by `uv run python scripts/knowledge/ingest.py --offline`; migrations 0001–0002 exist, 0003 is added by A1 exactly as `docs/database-design.md §5`.
- Single uvicorn worker; no Redis/Celery/Postgres/vector DB/Docker/ORM/router/UI kit/Tailwind.
- Money = integer VND; timestamps ISO-8601 UTC `…Z`; UI shows UTC+7.
- Customers: no login, shared account `shared-customer`, per-browser `X-Conversation-Id` (32 hex). Admin: `ADMIN_PIN` → bearer token (12 h).
- Agent: 7 tools (`get_cafe_info`, `search_cafe_knowledge`, `search_menu`, `recommend_drinks`, `get_coworking_info`, `prepare_order`, `get_order_status`); `prepare_order` writes only `order_drafts`.
- Availability `unknown` is orderable with warning `AVAILABILITY_UNCONFIRMED`; only `sold_out`/non-orderable is blocked.
- Contracts frozen: `docs/api-contracts.md` + `contracts/fixtures/*`; changes need both devs in one commit.
- File ownership: Dev A `backend/**`, `scripts/demo/**`, `contracts/**`; Dev B `frontend/**`.
- Tests calling OpenAI/Voyage carry `@pytest.mark.live` and are excluded from the default run.

## Review Focus

1. Double click / network retry on **Xác nhận đặt món** or **Đặt món** → exactly one order (draft key `draft:<id>`, `Idempotency-Key`) — tests in A2 (`test_confirm_draft_is_idempotent`, `test_create_order_idempotent_replay`) and B3/B4 (button disabled while pending).
2. Menu price changed by staff between quote and confirm → 409 `PRICE_CHANGED` with the fresh quote shown, never a silent different total — A2 `test_confirm_price_changed_refreshes_quote`, B3 confirm-sheet handling.
3. Agent asked about things that are not in the data (sweetness, room availability, upcoming events, discounts, other branch) → "chưa có thông tin đã xác minh" — A5 live smoke + `kb_eval_questions.json` q10/q14/q21/q23/q27/q28.
4. OpenAI unreachable during the demo → chat shows `MODEL_UNAVAILABLE`, menu/cart/admin keep working — A5 `test_model_error_emits_model_unavailable`, B4 banner test.
5. Two staff tabs acting on the same order → 409 `STATUS_CONFLICT` + refetch, no lost update — A3 `test_stale_expected_status_conflict`, B3 toast.

---

## Plans and ownership

| Plan | Owner | File |
|---|---|---|
| Backend + Agent | Dev A | `docs/superpowers/plans/2026-11-14-dev-a-backend-agent.md` (tasks A1–A6) |
| Frontend + UX | Dev B | `docs/superpowers/plans/2026-11-14-dev-b-frontend.md` (tasks B1–B6) |

Already done (pre-implementation session, do not redo): knowledge pipeline, `data/cafe.db` builder, migrations 0001–0002,
`app.settings`, `app.db.*`, `app.knowledge.*`, `app.catalog.dto`, fixtures, eval set, 9 passing tests.

## Critical path

```
A1 catalog API ─► A2 orders+drafts ─► A3 admin ─► A4 agent ─► A5 hardening ─► C5 rehearsal
      │                │                 │            │
B1 scaffold ─► B2 menu/cart (C1,C2) ─► B3 order page + admin (C3) ─► B4 chat (C4) ─► B5 states/polish
```
The longest chain is backend A1→A4 (agent available ≈3:45). Dev B never waits: every screen is built against `mockClient`
(fixtures, including `agent_stream.sse` replay) and switched to `liveClient` at each checkpoint.

## Five-hour timeline

| Slot | Dev A | Dev B | Integration checkpoint (both) | Testable deliverable | If late |
|---|---|---|---|---|---|
| **0:00–1:00** | A1 foundation: 0003 migration, app factory, errors, public catalog API + contract tests | B1 scaffold: Vite multi-page, tokens/fonts, `types.ts`, `ApiClient` live+mock, SSE parser, format/fold/cart libs + Vitest | **C1 @1:00** — B sets `VITE_API_MODE=live`; Discover/Menu data from `/api/cafe`,`/api/menu` | `pytest backend/tests/api -q` green; `pnpm test --run` green | A: skip `/api/health` extras; B: stay on mock, keep building |
| **1:00–2:00** | A2 orders: state machine, quote/create/drafts confirm/discard, bus, SSE, order APIs | B2 customer shell: tabs, Discover, Menu (filters, variant sheet), Cart + checkout (quote → confirm → create) | **C2 @2:00** — UI checkout creates `BB-0001` in SQLite; `curl /api/orders/BB-0001` | order row visible via API; replay returns same order | B: drop price-filter chips; A: defer `/stream` to A3 slot (polling only) |
| **2:00–3:00** | A3 admin auth + admin API + admin SSE + menu PATCH (0:35) → start A4 tools | B3 order tracking page (SSE+poll) + admin app: PIN login, board, transitions, reason, conflict toast | **C3 @3:00** — admin confirms the UI order; customer page updates live | full non-agent loop works | B: admin as a single list, polling 3 s; A: menu PATCH moves to A6 |
| **3:00–4:00** | A4 agent: repository queries, 7 tools, instructions, streaming SSE, agent API + ScriptedModel tests | B4 chat panel: reducer, orb mapping, tool chips, draft slip → confirm REST, order card, error banner (mock replay first) | **C4 @3:50** — live: recommend → draft → confirm → admin → status (**P0 complete**) | demo script steps 1–9 pass | drop text streaming (render on `message_completed`); drop sources UI |
| **4:00–5:00** | A5 hardening: error mapping, lock/rate limit, live smoke, `reset_demo.py`; A6 P1 (insights, memory note) | B5: loading/empty/error/degraded states, admin Menu availability (P1), GSAP + reduced motion, `/impeccable critique`→`polish` (if green) | **C5 @4:40** — reset + full rehearsal ×2 using `docs/demo-runbook.md` | rehearsal passes twice | freeze features at 4:40; fixes only |

## Integration checkpoints (definition of done)

- **C1**: `uv run uvicorn app.main:app --port 8000` + `pnpm dev`; customer page shows "Biblio Café Sách — 79 Ngụy Như Kon Tum", 51 menu items.
- **C2**: add Bạc xỉu + Cà phê (Đen) → **Đặt món** → order page `BB-0001` status "Chờ quán xác nhận"; second click on a retried request does not create `BB-0002`.
- **C3**: admin logs in with `ADMIN_PIN`, sees `BB-0001` within 2 s, **Nhận đơn** → customer page shows "Quán đã nhận đơn" within 2 s.
- **C4**: in chat "Mình muốn uống gì đó ít ngọt, không quá 50k. Gợi ý rồi đặt một ly." → recommendations with SQL prices → "Lấy trà chanh gừng mật ong" → draft slip 45.000đ → **Xác nhận đặt món** → order card → admin confirms → "Đơn của mình sao rồi?" → status from `get_order_status`.
- **C5**: `scripts/demo/reset_demo.py`, then the 10-step demo table in `docs/demo-runbook.md` passes twice in a row.

## Scope-reduction rules

1. Never cut a P0 cell of `PRD.md §7`; cut P2, then P1 (in this order: Impeccable polish → GSAP → insights → sources UI → history restore → admin menu availability).
2. If the agent is not live at 4:10: demo the UI cart path for ordering and the agent for knowledge/recommendation only; keep working on A4.
3. If SSE misbehaves through the proxy: switch both order page and admin board to 3 s polling (already implemented as fallback).
4. At 4:40 feature freeze; only bug fixes and rehearsal.

## Branching

Baseline = `main` (pre-implementation commit). Dev A works on `feat/dev-a-backend-agent`, Dev B on `feat/dev-b-frontend`, both
created from the latest `main`. At every checkpoint C1–C5 (and when a plan is finished) each dev merges their branch into `main`
with `git merge --no-ff` after tests pass, pushes `main`, and merges `main` back into their branch — so the teammate can pull the
other half for integration. Full procedure: `RULES.md §6`.

## Commands

```powershell
uv sync; uv run python scripts/knowledge/ingest.py --offline       # once per laptop
uv run pytest -q                                                    # backend (default excludes live)
uv run pytest -m live -q                                            # A5 only, needs OPENAI_API_KEY
uv run uvicorn app.main:app --reload --port 8000                    # backend dev
cd frontend; pnpm install; pnpm dev; pnpm test --run                # frontend
```
