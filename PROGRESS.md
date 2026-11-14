# PROGRESS — Biblio AI Café Companion

Append newest entries at the top of each section. Times in local time (UTC+7). Owners: Dev A (backend/agent), Dev B (frontend), prep (pre-implementation session).

## Current status

**Phase:** pre-implementation complete; implementation not started. **Ready state:** see `docs/IMPLEMENTATION_HANDOFF.md` §A.
**Next:** both devs read `docs/IMPLEMENTATION_HANDOFF.md`, then start A1 / B1 (`docs/superpowers/plans/`).

## Log

### 2026-11-14 13:08 (UTC+7) — Dev B · B1 foundation
- Branch `feat/dev-b-frontend` from baseline `2b016a2`; fetched/pulled latest main, verified ancestry and pushed upstream. No pre-existing uncommitted changes.
- B1: React multi-page entries, design tokens/self-hosted fonts, frozen TS types/client, live/mock clients, incremental SSE parser, conversation id, cart, VND/UTC+7 formatting.
- TDD: initial five suites failed for missing implementation; `pnpm.cmd test --run` → 5 files / 11 tests passed; `pnpm.cmd build` → passed.
- Resolved/pinned: React/DOM 19.3.1; Vite 8.3.8; TypeScript 7.0.2; plugin-react 6.3.0; GSAP 3.15.1; @gsap/react 2.1.2; thinking-orbs 0.3.2; both fonts 5.3.0; Vitest 5.1.0; jsdom 31.0.0; Testing Library React 16.3.3 / jest-dom 7.0.1 / user-event 14.6.10. Scaffold oxlint 1.93.0, React type packages 19.3.0, Node types 24.19.2.
- Node 24.13.0 / pnpm 11.0.8; use `pnpm.cmd` because PowerShell execution policy blocks pnpm.ps1. Caches require sandbox escalation. `uv sync`, offline ingestion (0 paid calls) and `uv run pytest -q` → 9 passed. Restored only the generated ingestion stats file to retain ownership boundaries.
- C1 live remains pending: API endpoints absent at baseline. Live is the default; fixture mode is opt-in, never claimed as integrated proof. Waiting for Dev A confirmation before any main merge.
- Ruling: execution ledger in `frontend/IMPLEMENTATION_LOG.md`; do not run skill scratch scripts that create a .gitignore outside assigned files. Root .gitignore, .agents, .claude, .env and frozen contracts unchanged.

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
