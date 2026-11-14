# IMPLEMENTATION HANDOFF — read this first

Biblio AI Café Companion · prepared 2026-11-14 · for the 5-hour build by **Dev A (backend/agent)** and **Dev B (frontend)**.
Read order: this file → `RULES.md` → your plan (`docs/superpowers/plans/2026-11-14-dev-a-backend-agent.md` or
`…-dev-b-frontend.md`) → the docs your plan cites. The master plan (`2026-11-14-master-plan.md`) holds the shared timeline.

## A. Project state

**Done (verified by running):**
- Knowledge collected for **Biblio Café Sách, 79 Ngụy Như Kon Tum** with branch-identity checks (other branches rejected).
- `data/knowledge/normalized/` (committed-ready): `cafe_profile.json`, `menu.json` (51 items, 9 categories, 4 variants, all
  `availability=unknown`), `services.json` (3 co-working packages, 5 rooms, 22 facts), `documents.jsonl` (57; 54 indexable),
  `source_manifest.json` (21), `events.json` (3 past, 0 upcoming), `social_insights.json`, `unverified_claims.json` (21).
- `data/cafe.db` built by `scripts/knowledge/ingest.py`: migrations **0001 catalog** and **0002 knowledge** applied;
  56 chunks with **Voyage `voyage-4-lite`, 512-d float32** vectors (cache `data/knowledge/embeddings/voyage-4-lite_512.jsonl`);
  FTS5 fallback; `kb_meta` holds menu/services notes.
- Retrieval (`backend/app/knowledge/retrieval.py`): vector hit@5 **29/29**, keyword fallback 27/29, SQL checks 8/8
  (`data/knowledge/ingestion_report.md`, `data/knowledge/eval/kb_eval_results.json`). `uv run pytest -q` → **9 passed**.
- Reusable code: `app.settings`, `app.db.connection` (`connect`, `transaction`), `app.db.migrate`, `app.knowledge.*`,
  `app.catalog.dto` (exact JSON of `/api/cafe`, `/api/menu`, `/api/services`).
- Contracts frozen: `docs/api-contracts.md`, fixtures `contracts/fixtures/*` (generated catalog JSON + static order/draft/admin/SSE examples).
- Model check: `gpt-6-luna` + openai-agents 0.24.0 streamed tool calls work (real API, 2026-11-14).
- `.env` has `OPENAI_API_KEY`, `VOYAGE_API_KEY`, `APIFY_API_TOKEN`, `ADMIN_PIN` (≥6 chars) on the owner's laptop.

**Not done (this is the build):** migration 0003, every FastAPI endpoint, order logic, admin auth, the agent runtime, the
whole `frontend/`, demo reset script. The pre-implementation work is committed and pushed to `main` as the baseline
(`chore: pre-implementation baseline …`); each developer branches from it.

**Remaining blockers / open items:**
- Staff confirmation of prices/availability (UI and agent label data as unverified; demo works without it).
- `ModelRetrySettings` / `ModelSettings.timeout` / nested tool-arg schemas with `gpt-6-luna` are unverified → A5 live smoke.
- No verified upcoming events (Facebook page not readable) → by design the agent says so.

## B. Locked decisions (do not re-decide)

| Area | Decision |
|---|---|
| Stack | FastAPI + stdlib sqlite3 (no ORM) + openai-agents 0.24.0 + NumPy; React 19 + Vite 8 multi-page + TypeScript + plain CSS + GSAP + thinking-orbs; uv + pnpm |
| Models | generation `gpt-6-luna`; embeddings `voyage-4-lite`, 512 dims (`input_type` document/query) |
| Agent | single orchestrator, 7 tools: `get_cafe_info`, `search_cafe_knowledge`, `search_menu`, `recommend_drinks`, `get_coworking_info`, `prepare_order`, `get_order_status` (`docs/agent-design.md`) |
| Ordering | agent prepares **drafts only**; customer confirms via `POST /api/orders/drafts/{id}/confirm`; cart via `POST /api/orders` with `Idempotency-Key`; server prices; unknown availability orderable with warning; `sold_out` blocked |
| Identity | customers: no login, shared pre-created account `shared-customer`, per-browser `X-Conversation-Id`; admin: `ADMIN_PIN` → bearer token 12 h |
| Database | `docs/database-design.md` (0003 SQL verbatim, state machine, transactions, reset) |
| API / frontend contracts | `docs/api-contracts.md` (§9 TypeScript types verbatim, §10 client interface, SSE events, orb mapping) |
| UI | `DESIGN.md` (tokens/components) + `docs/ui-ux-spec.md` (screens/states) |
| Repo structure / ownership | `ARCHITECTURE.md §3` — Dev A `backend/**`, `scripts/demo/**`, `contracts/**`; Dev B `frontend/**` |
| Out of scope | payments, events tool, room booking, customer accounts, multi-agent, deployment |

## C. Execution order

| Time | Dev A (`2026-11-14-dev-a-backend-agent.md`) | Dev B (`2026-11-14-dev-b-frontend.md`) | Checkpoint |
|---|---|---|---|
| 0:00–1:00 | A1 foundation + catalog API | B1 scaffold + API layer | C1 live catalog in UI |
| 1:00–2:00 | A2 orders, drafts, bus, SSE | B2 Discover, Menu, Cart checkout | C2 UI order `BB-0001` |
| 2:00–3:00 | A3 admin (≈35 min) → start A4 | B3 order tracking + admin app | C3 admin confirms → customer live |
| 3:00–4:00 | A4 agent tools + streaming | B4 chat panel (mock replay → live) | C4 full agent loop (**P0 done**) |
| 4:00–5:00 | A5 hardening + reset; A6 P1 | B5 states, menu availability, motion, polish | C5 rehearsal ×2 |

Dependencies: B never blocks on A (mock client replays fixtures, including `contracts/fixtures/agent_stream.sse`).
A4 depends on A2 (`create_draft`, `list_orders`); B4 live mode depends on A4; C3 depends on A2+A3+B3.
Test commands: `uv run pytest -q` (backend), `uv run pytest -m live -q` (A5, paid, ≤6 runs), `pnpm test --run` (frontend),
`pnpm exec playwright test` (P1).

## D. Run instructions

Verified in the prep session:
```powershell
uv sync                                                    # Python 3.12.13 venv from uv.lock
uv run python scripts/knowledge/ingest.py --offline        # (re)build data/cafe.db from committed data, no API calls
uv run python scripts/knowledge/verify.py --offline        # data/DB checks + keyword-fallback eval
uv run python scripts/knowledge/verify.py                  # + Voyage vector eval (~355 query tokens)
uv run python scripts/contracts/export_fixtures.py         # regenerate catalog fixtures from data/cafe.db
uv run pytest -q
```
Knowledge refresh (only if sources change): `collect.py web` (free) → edit `data/knowledge/curated/*.json` → `normalize.py` →
`ingest.py` (embeds only new chunks) → `verify.py` → `export_fixtures.py`. Apify re-runs need `--force` and cost money; don't.

Planned (valid after the tasks land):
```powershell
uv run uvicorn app.main:app --reload --port 8000           # backend, single worker
cd frontend; pnpm install; pnpm dev                        # http://localhost:5173  and  /admin.html
uv run python scripts/demo/reset_demo.py                   # between demo runs (stop uvicorn first)
```
Environment (`.env` at repo root; template `.env.example`): `OPENAI_API_KEY`, `VOYAGE_API_KEY`, `APIFY_API_TOKEN` (ingestion only),
`OPENAI_MODEL=gpt-6-luna`, `VOYAGE_EMBEDDING_MODEL=voyage-4-lite`, `VOYAGE_EMBEDDING_DIMENSION=512`, `DATABASE_PATH=./data/cafe.db`,
`ENABLE_APIFY_LIVE_SEARCH=false`, `ENABLE_AGENT_TRACING=true`, `ADMIN_PIN`, `AGENT_SESSIONS_DB_PATH=./data/agent_sessions.db`,
`FRONTEND_ORIGIN=http://localhost:5173`. Frontend: `frontend/.env` with `VITE_API_MODE=live`.
Demo procedure and contingencies: `docs/demo-runbook.md`.

## E. Next-session prompts

Both prompts use the branch workflow in `RULES.md §6` (baseline = `main`).

Dev A (backend/agent) — paste into Claude Code at the repo root:
```text
Read docs/IMPLEMENTATION_HANDOFF.md and the approved Superpowers implementation plan, then implement the application according to the plan.
You are Dev A. First: git checkout main, git pull origin main, then create and switch to a new branch feat/dev-a-backend-agent (never commit on main).
Execute docs/superpowers/plans/2026-11-14-dev-a-backend-agent.md task by task (A1→A6) with superpowers:executing-plans, TDD as written, following RULES.md.
Commit after each task with real passing test output; push the branch. At each integration checkpoint (C1–C5) and when finished: pull main, merge your
branch into main with --no-ff, run uv run pytest -q, push main, then merge main back into your branch (RULES.md §6; never force-push).
Do not redesign the architecture, change the model (gpt-6-luna) or embeddings (voyage-4-lite/512), add technologies, or change docs/api-contracts.md or the
schema without asking me. Touch only backend/**, scripts/demo/**, contracts/** (plus your rows in TASKS.md/PROGRESS.md). Stop and ask if blocked.
```
Dev B (frontend):
```text
Read docs/IMPLEMENTATION_HANDOFF.md and the approved Superpowers implementation plan, then implement the application according to the plan.
You are Dev B. First: git checkout main, git pull origin main, then create and switch to a new branch feat/dev-b-frontend (never commit on main).
Execute docs/superpowers/plans/2026-11-14-dev-b-frontend.md task by task (B1→B5) with superpowers:executing-plans, TDD as written, following RULES.md and DESIGN.md.
Commit after each task with real passing test output; push the branch. At each integration checkpoint (C1–C5) and when finished: pull main, merge your
branch into main with --no-ff, run pnpm test --run (and uv run pytest -q if backend code is present), push main, then merge main back into your branch
(RULES.md §6; never force-push). Use VITE_API_MODE=mock only until the matching backend endpoint exists on main; switch to live at each checkpoint.
Do not redesign the architecture, add libraries beyond the plan, or change docs/api-contracts.md without asking me. Touch only frontend/** (plus your rows
in TASKS.md/PROGRESS.md). Stop and ask if blocked.
```

## F. Final verification of the prep session (2026-11-14)

| Check | Result | Note / impact on the next session |
|---|---|---|
| Normalized menu complete (51 items, integer VND, variants, no price lost) | PASS | `verify.py` |
| Services & co-working data | PASS | 3 packages, 5 rooms, 22 facts |
| Source manifest valid; every document cites a source | PASS | 21 sources |
| No branch mixing (70 Tam Khương only in the disambiguation doc) | PASS | |
| No duplicate documents/chunks | PASS | content-hash unique |
| Unverified data clearly marked | PASS | statuses + `unverified_claims.json`; nothing `owner_verified` |
| JSON/JSONL parse | PASS | |
| Database opens; integrity + FK check | PASS | |
| Embedding dimensions 512, model voyage-4-lite, all chunks embedded | PASS | 56/56 |
| Retrieval runs (vector + fallback) | PASS | 29/29 vector after fixes (26/29 first run); 27/29 keyword |
| API contracts have complete schemas | PASS | `docs/api-contracts.md §1–§10` + fixtures |
| Plan task interfaces consistent | PASS (self-review) | names cross-checked between plans, contracts and fixtures |
| P0 covered by the plan | PASS | `PRD.md §7` ↔ tasks A1–A5, B1–B5a |
| Realistic 2-dev / 5-hour timeline | PARTIAL | tight; scope-reduction rules in the master plan; agent lands ≈3:50 |
| No secrets in git-visible files | PASS | `verify.py` scan; `.env` ignored |
| `.agents/`, `.claude/` unchanged | PASS | `git diff --stat` empty |
| No product feature code beyond allowed scope | PASS | only pipeline/infrastructure modules (`settings`, `db`, `knowledge`, `catalog.dto`) |
| Unverified SDK settings with `gpt-6-luna` (retry/timeout/nested args) | PARTIAL | verify in A5 live smoke; fallback = drop the field |
| Staff confirmation of prices/availability | BLOCKED (external) | ask staff before the demo; app labels data as unverified meanwhile |
| Upcoming events | BLOCKED (external) | none verified; agent answers honestly |

**Status: `CONDITIONALLY_READY`** — data, retrieval, contracts and plans are ready to code against; the remaining conditions
are external confirmations and a live check of three SDK settings, none of which block starting A1/B1.
