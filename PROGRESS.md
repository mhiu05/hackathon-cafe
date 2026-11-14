# PROGRESS — Biblio AI Café Companion

Append newest entries at the top of each section. Times in local time (UTC+7). Owners: Dev A (backend/agent), Dev B (frontend), prep (pre-implementation session).

## Current status

**Phase:** pre-implementation complete; implementation not started. **Ready state:** see `docs/IMPLEMENTATION_HANDOFF.md` §A.
**Next:** both devs read `docs/IMPLEMENTATION_HANDOFF.md`, then start A1 / B1 (`docs/superpowers/plans/`).

## Log

### 2026-11-14 12:40 ? Dev A execution ledger
- Plan: `docs/superpowers/plans/2026-11-14-dev-a-backend-agent.md`; branch `feat/dev-a-backend-agent`, baseline `2b016a2` verified in origin/main; branch pushed.
- Preparation: uv sync succeeded; offline ingest 56 cache vectors, 0 Voyage tokens; verifier rerun with PYTHONIOENCODING=utf-8 succeeded (console cp1252 failed first); pytest: 9 passed in 0.90s.
- Preparation commands regenerated three tracked knowledge reports; retained locally and excluded from Dev A commits (outside ownership).
- Ruling: use this Dev A ledger instead of SDD helper workspace ? helper creates .gitignore, prohibited by user; approved task sequence unchanged.
- Pre-flight A1?A2: ApiError/deps/time/DTO shared signatures consistent. A2?A3: state/service/EventBus interfaces consistent. A1+A2?A4: repository/drafts/status/retrieval consumed consistently. A4?A5?A6: stream/session/observability interfaces consistent.
- C1?C5 integration pending Dev B readiness; no main merge without confirmation.
- Task A1: complete ? RED ModuleNotFoundError app.main; GREEN `uv run --no-sync pytest -q -p no:cacheprovider`: 16 passed in 0.53s; HTTP uvicorn smoke /api/cafe 200, phone verified. UV_CACHE_DIR uses TEMP because default cache is protected. C1 backend ready; Dev B confirmation pending.

### 2026-11-14 — prep session (Claude Code, Superpowers 7.0.2: brainstorming → writing-plans)
- Installed the project-scoped Superpowers plugin (`superpowers@anthropic-plugin-directory` 7.0.2); skills were read from the installed files because the plugin loads only in new sessions.
- Created root `pyproject.toml` (Python 3.12.13, uv) and `uv.lock`; package `backend/app`.
- Verified capabilities with real calls: `gpt-6-luna` available (models endpoint 200) and works with openai-agents 0.24.0 for streamed tool calls, `reasoning.effort` low/none, `verbosity` low, and `needs_approval` (approval flow later dropped by decision); Voyage `voyage-4-lite` returns 512-d vectors; Apify FREE plan, pay-per-event actors.
- Collected data: 8/14 web pages fetched (others blocked: Facebook login wall, findglocal/maptons 403, restaurantguru 503, topcv/1000libraries network — 1000libraries read via WebFetch); Apify Google Maps run `hTvPCbgInf1lsw9ig` ($0.0212), TikTok run `qbedrS1CtnuG11vmc` ($0.0750); Apify rejected per-run caps below $0.50, so caps were set to $0.50 + $0.50 = $1.00 budget.
- Built `data/cafe.db`: catalog (51 items, 4 variants, 3 co-working packages, 5 rooms, 22 facts) + KB (21 sources, 54 indexed docs, 56 chunks, 56 Voyage vectors; 9,174 Voyage document tokens for ingestion, plus ~0.7k query tokens for checks/evals).
- Retrieval eval: first run vector hit@5 26/29 → fixed (per-document dedupe, focused room-booking FAQ, widened q14, q28 accepts empty) → 29/29, hit@1 21/29, MRR 0.806; keyword fallback 27/29; SQL checks 8/8; negative controls below threshold.
- Windows note: `zoneinfo` has no tz database without the `tzdata` package → UTC+7 is a fixed offset in `app.catalog.dto` (Vietnam has no DST).
- Owner decisions recorded (see `PRD.md §5`): agent prepares drafts only; unknown availability orderable with warning; shared pre-created customer account, admin via `ADMIN_PIN` (set in `.env`, ≥6 chars); no events tool.
- Wrote PRD/ARCHITECTURE/DESIGN/RULES/TASKS/PROGRESS, `docs/*` (agent, database, API contracts, UI/UX screens, knowledge sources, demo runbook, handoff), fixtures in `contracts/fixtures/`, and the master + Dev A + Dev B plans.
- `.agents/`, `.claude/`, `.env`, `biblio_cafe_kb_bundle/` untouched by the prep session (the bundle is committed as provided).
- Owner approved: committed and pushed everything to `main` as the baseline; branch workflow per developer added to `RULES.md §6`
  and to the next-session prompts (`feat/dev-a-backend-agent`, `feat/dev-b-frontend`, merge `--no-ff` into `main` at checkpoints and when done).

## Issues / risks

| Date | Issue | Impact | Mitigation / owner |
|---|---|---|---|
| 2026-11-14 | Menu prices/availability not confirmed by staff | agent/UI must label data unverified | UI notices + agent rules; ask staff before demo (owner) |
| 2026-11-14 | `ModelRetrySettings`, `ModelSettings.timeout`, nested Pydantic tool args not yet verified with `gpt-6-luna` | possible schema/setting errors at A4/A5 | live smoke in A5; drop only the failing field and log here (Dev A) |
| 2026-11-14 | Branch Facebook page not readable → no event calendar | no upcoming events to show | KB says "no verified upcoming events"; owner may add events later (P2) |
| 2026-11-14 | TypeScript 7.0.2 is current on npm; scaffold may pin a different TS | type-check tooling differences | use the scaffold default; record version in this file (Dev B) |
| 2026-11-14 | Shared customer account | any customer browser can open any order | accepted for the single-laptop demo (owner decision); P2 isolation |

## Important changes (decisions after design approval)

- 2026-11-14: `create_order` + SDK approval flow → replaced by `prepare_order` drafts + REST confirm (owner).
- 2026-11-14: anonymous per-browser sessions → shared pre-created customer account + per-browser conversation id (owner).
- 2026-11-14: `get_events` tool and events table → removed from this build (owner); KB keeps the events document.
- 2026-11-14: `docs/product-spec.md` → `PRD.md`, `docs/architecture.md` → `ARCHITECTURE.md`, design system → `DESIGN.md` (owner asked for root rule files).

## Next plan

1. Dev A: A1 → A2 → A3 → A4 → A5 (+A6 P1). Dev B: B1 → B2 → B3 → B4 → B5.
2. Checkpoints C1 (1:00), C2 (2:00), C3 (3:00), C4 (3:50), C5 (4:40) per the master plan.
