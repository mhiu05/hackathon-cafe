# PROGRESS — Biblio AI Café Companion

Append newest entries at the top of each section. Times in local time (UTC+7). Owners: Dev A (backend/agent), Dev B (frontend), prep (pre-implementation session).

## Current status

**Integrated status:** backend main45d28e5 + frontendec2c2de verified together after owner confirmation:91 backend passed/6 live deselected,37 frontend passed/build passed,8 fixture E2E passed/3 opt-in live skipped by default. Two real live reset/core-demo run-sets passed on actual merged checkout, each2 orders/3 completed agent runs. C1–C5 core demo ready. Dev B pushes the verified merge and syncs main back to its feature; Dev A should fetch final main. Earlier handoff/status notes below are retained as history. Full report: frontend/DELIVERY_REPORT.md.

**Phase:** pre-implementation complete; implementation not started. **Ready state:** see `docs/IMPLEMENTATION_HANDOFF.md` §A.
**Next:** both devs read `docs/IMPLEMENTATION_HANDOFF.md`, then start A1 / B1 (`docs/superpowers/plans/`).

**Dev A update (2026-11-14 13:54):** A1-A6 implemented and pushed on `feat/dev-a-backend-agent`; final reviewed fixes/rehearsal below. Shared integration C1-C5 awaits Dev B readiness. The pre-implementation status above is retained as the original handoff record.

## Log

### 2026-11-14 15:04 (UTC+7) — Dev B serialized integration, stage 2
- Fetched Dev A merge45d28e5; its PROGRESS entry records stage1 handoff and Dev B next. Two initial auto-review requests timed out before running; owner explicitly confirmed the integration scope, then individual Git steps succeeded.
- Pulled main --ff-only, merged frontendec2c2de --no-ff --no-commit. Only TASKS.md/PROGRESS.md conflicted; preserved each owner's task statuses and both complete logs, no source conflicts or backend edits.
- Merged checkout gates: `uv run pytest -q`91 passed/6 live deselected; frontend37 passed; production build passed; fixture Playwright8 passed/3 dedicated live specs skipped by default.
- C5 on actual merged source (backend junction resolves to this checkout/backend, DB/session/backup isolated): two reset/core-demo run-sets passed. Each creates2 real orders and3 completed agent runs without error_code; actual knowledge/SQL/draft/status tools logged. Lượt1 also used recommend_drinks; lượt2 used search_menu for grounded recommendations. Both checkout replay and≤2s customer-update assertions pass, admin Menu/insights live pass. No fake responses.
- C1–C5 core checks marked complete. Merge commit is created/pushed only after these green gates; main then syncs back into feat/dev-b-frontend. Dev A can fetch final origin/main for stage3. Original DB/.env/protected files unchanged; all rehearsal servers stopped. Remaining polish/limits in DELIVERY_REPORT.md.

### 2026-11-14 14:25 (UTC+7) — Dev B · final live handoff
- Two clean reset/core-demo run-sets on snapshot9e0a3b1: each2 real orders,3 completed agent runs, no error_code. Actual tools logged: cafe info, RAG knowledge, SQL menu, prepare_order, get_order_status. Earlier A4 live run exercised recommend_drinks too.
- Fixed live-test completion gate: wait final message and done-driven enabled composer before closing; initial prematurely-cancelled runs excluded. Removed an overly-specific recommend_drinks-only assertion after real SQL search_menu grounding was verified. Existing clean run validated offline, second clean run executed after reset.
- Final `run_live_smoke.py`2 passed: same-code HTTP200 Idempotent-Replay; staff confirmation→customer1098ms; menu availability and insights live. Wrapper Windows stdout forced UTF-8 while retaining secret redaction. No additional model calls for this smoke.
- Main remains unmerged; protected files/backend/contracts untouched. Delivery report, exact Dev A notes and review dispositions committed with final test/report changes. Optional minor polish only; waiting for serialized integration handoff.

### 2026-11-14 14:12 (UTC+7) — Dev B · independent review fixes
- Independent code/design A + detector/audit B completed. Detector0 findings; initial A27/40 / B16/20. QA_REVIEW.md preserves scope and dispositions, no claim of rescored certification.
- RED→GREEN fixes: old active orders outside latest50; counts server/coverage notice; desktop chat keeps content; mobile masthead dismissal restores focus; fast PRICE_CHANGED double-click now requires explicit price-review acknowledgement for cart/draft. Input control border5,21:1, phone/direction targets44px via existing tokens.
- Final frontend gate: `pnpm.cmd test --run`37 passed; build passed; Playwright8 fixture passed/3 live gated by default. Lint exit0 with10 React advisory warnings retained/documented. Frozen types compared verbatim against §9, match; protected files/contracts/backend unchanged.
- Remaining minor polish: sticky categories, shorter source labels. Preparing two reset/live rehearsals on9e0a3b1; no main merge.

### 2026-11-14 14:02 - Dev A serialized integration, stage 1
- Owner reports Dev B B1-B5 pushed at `84d0310`; remote SHA verified. This answers the pending readiness coordination request; begin Dev A's first merge only.
- Dev A feature HEAD `ff78ab3` is pushed and reviewed; full suite previously 91 passed / 6 live deselected. Local main and origin/main both remain `2b016a2` before this integration.
- Dev B progress reports frontend unit/build/fixture checks and C1-C4 live smoke against backend snapshots. Those results are not yet combined-main acceptance. C1-C5 rows stay pending until serialized integration and integrated checks.
- Sequence: Dev A merge backend into main, run backend suite and push; then Dev B pulls that main, merges frontend, runs required checks and pushes; finally Dev A fetches/merges final origin/main into feature branch and verifies.
- Expected preparation-generated knowledge report modifications remain preserved locally and outside commits. No frontend/schema/contract/.gitignore changes by Dev A; no extra paid tests.

### 2026-11-14 13:57 (UTC+7) — Dev B · B5 hardening/P1
- Error/retry, empty/loading/degraded states; accessible mobile chat dialog with focus trap/Escape/inert background; live order cards; admin Menu availability and Tổng quan; GSAP via useGSAP/matchMedia with static reduced-motion state; removed scaffold assets and replaced favicon.
- `pnpm.cmd test --run` → 18 files / 33 passed; `pnpm.cmd build` passed. `pnpm.cmd exec playwright test` → 6 fixture tests passed / 2 live tests deliberately skipped by default. Explicit live cart smoke passed (64ms customer update); explicit live AI test passed on snapshot81648a3 (BB-0003, three real turns).
- Found live admin SSE without allowed_next; regression RED→GREEN; frontend refetches authenticated actions instead of guessing permissions. Exact Dev A handoff in frontend/INTEGRATION_NOTES.md. First live AI attempt reached real confirmed BB-0002 but stopped on missing actions; corrected run passed.
- Latest Dev A9e0a3b1 exported to ignored snapshot; `python -m pytest .../backend/tests -q -m 'not live'` → 87 passed, 6 deselected. No backend source modifications or main merge.
- ApiClient §10 omits insights despite §7 endpoint / §9 type. Isolated typed api/insights.ts adapter uses existing auth/error/request layer; frozen interface unchanged. Mock analytics show live-required, not invented values.
- Impeccable context loaded using existing DESIGN.md/PRD/UI spec; no PRODUCT.md or design-system rewrite. Final independent design/code review and detector pending. Lint exits successfully with advisory React warnings; final report will retain their disposition.

### 2026-11-14 13:54 - Dev A final verification and review
- Final review: independent read-only whole-branch review (`2b016a2..9e0a3b1`), 0 Critical, 2 Important, 0 Minor. Reviewer resumed after an account usage-limit interruption; no extra model smoke tests or external calls were run.
- Final: fixed prior-response cleanup releasing a subsequent run's conversation guard - `test_old_response_cleanup_cannot_release_the_next_run` RED (third request incorrectly accepted) -> GREEN; async per-request release-once shared by generator/background, including never-started response cleanup.
- Final: fixed malformed model arguments crashing tool telemetry/recovery - `test_malformed_model_tool_args_are_logged_and_model_recovers` RED (INTERNAL, missing metric) -> GREEN; bounded valid JSON fallback for logging, failed tool event/metric retained, model recovery completes.
- Final full suite `uv run pytest -q`: **91 passed, 6 deselected in 8.88s**. Regression file: 3 passed in 0.94s. No live tests included; A5 six-run budget remains exhausted.
- Backend rehearsal twice: `test_backend_demo_rehearsal_twice` passed (1 passed in 4.56s): reset/backup -> catalog/KB -> recommendation -> draft with no order -> REST confirm twice creates one BB-0001 -> admin confirmed/preparing/ready -> tool reads real status; integrity/FK checks pass each round. ScriptedModel controls model decisions; actual SQL/retrieval/services/API/session/reset code executes. Full UI rehearsal is still pending.
- Final data checks: local DB integrity/FK, 56/56 embeddings with voyage-4-lite/512, FTS consistency pass. Migration 0003 SQL and agent instructions match approved documents verbatim. Secret scan of git-visible files passes; .env/DB remain ignored. Python 3.12.13, openai-agents 0.24.0 verified.
- Earlier rulings retained: Dev A PROGRESS ledger substitutes for helper that creates .gitignore (cost if wrong: less automated task bookkeeping); infinite SSE uses direct iterator + real HTTP tests instead of buffered TestClient.stream (cost if wrong: client integration differences, addressed by HTTP test); explicit budget echoes excluded from item-price assertions (cost if wrong: overly broad exclusion, covered by fabricated-item regression).
- Final: Ruling: cross-browser order access stays shared-account behavior as explicitly approved - cost if wrong: customer isolation absent; P2.
- Final: Ruling: multi-worker synchronization/distributed rate limits/continuous auth revalidation of existing admin SSE stay outside single-worker demo - cost if wrong: unsafe multi-worker use or already-open admin stream remains until disconnected.
- Final: Ruling: canonical request hash excludes expected total and conversation id as specified - cost if wrong: same-key replay ignores those changed fields.
- Final: Ruling: budget filtering uses minimum variant price as specified and returns actual variant prices - cost if wrong: a higher-priced variant can exceed the requested ceiling; customer quote remains authoritative.
- Final: Ruling: confirmation-memory note stays best-effort without durable retries - cost if wrong: optional chat memory can miss the note; order/status SQL remains authoritative.
- Final: Ruling: no additional mechanism for duplicate model-generated drafts or universal prompt/factual guarantees without an evidenced failure - cost if wrong: extra drafts or unsuitable model text; tools still cannot create orders.
- Final: Ruling: reset assumes stopped server and distinct commerce/session paths, following the documented runbook - cost if wrong: live traffic races or data loss from misconfigured reset paths; do not use outside those assumptions.
- Final: Ruling: frontend integration awaits Dev B and further paid tests stay stopped at approved budget - cost if wrong: combined UI behavior remains unverified until C1-C5; no main merge/push performed.
- Deferred minors: none from independent review. Backend P1 A6a/A6b complete; remaining P1 frontend tasks belong to Dev B, P2 backlog unchanged.
- Three tracked knowledge report files were regenerated by the user-required preparation commands; preserved locally, excluded from Dev A commits, not discarded.

### 2026-11-14 13:45 - Dev A A6
- Task A6a/A6b: complete - RED insights/history 404 and absent memory note; GREEN full suite: 87 passed, 6 deselected in 7.38s.
- AdminInsights returns status totals, completed-only revenue, top-five item quantities and agent/tool/token metrics; admin auth enforced.
- Draft confirmation appends one assistant note only after a new commit; idempotent replay does not duplicate it. Optional memory errors cannot invalidate an already committed checkout. History returns text-only user/assistant messages scoped to the requested conversation.
- P1 backend endpoints complete. Final branch review and backend rehearsal next; full frontend integration C1-C5 pending Dev B readiness.

### 2026-11-14 13:39 - Dev A A5
- Task A5: complete - RED missing guard/reset modules; GREEN `uv run --no-sync pytest -q -p no:cacheprovider`: 84 passed, 6 deselected in 8.15s. All paid tests excluded by default.
- Guards return pre-stream 409/429; corrupt tool sessions clear with SESSION_RESET; max-turns handler gives friendly output plus MAX_TURNS; consumer/in-flight cancellation persists cancelled; SDK transient retry and tool timeout verified offline.
- reset_demo backs up SQLite, clears commerce/tokens/sessions, restores unknown availability and original notes, preserves KB/catalog/shared account; next order BB-0001; tested on temporary database only.
- A5 live batch: 3 passed, 2 failed (recommend/events transport RuntimeError); offline local HTTP reproduction confirmed SDK shared async client + pytest per-test loops => Event loop is closed. Live module now shares one event loop like FastAPI.
- A5 run 6 (last): recommend_drinks + search_cafe_knowledge completed with vector retrieval, usage input=4800/output=271/requests=2. Initial assertion falsely classified echoed customer budget 50.000d as item price. Offline read-only replay of stored response passed corrected price/context checks. No further paid runs. A4 used one separate approved smoke run.
- Ruling: strip only explicit budget-threshold echoes before exact price assertions - user ceiling is not an invented item price; regression still rejects a fabricated item priced at that ceiling. SDK timeout=30/retry max_retries=2 and nested strict order args accepted; no setting removed, model unchanged.
- Auto-review rejected persisting full live transcript due to potential sensitive content. Safer read-only SELECT inspection succeeded; no transcript artifact retained.
- Fixed PowerShell ASCII pipe corruption in newly generated Vietnamese test strings and Dev A ledger separators; application strings were written through apply_patch and unaffected.
- C5 integrated rehearsal still pending Dev B; no main merge/push.

### 2026-11-14 13:37 (UTC+7) — Dev B · B4 streaming assistant
- Chat reducer/hook, true SSE-driven orb (64px + 20px tools), messages/sources, composer, draft REST confirmation/discard, price refresh/expiry and order card → tracking. Abort/new conversation prevents stale emissions; a truncated stream reports interruption.
- RED missing chat/orb/draft/hook modules → `pnpm.cmd test --run`: 13 files / 28 passed. `pnpm.cmd exec playwright test`: 5 passed with fixture API, including recommend→draft→REST confirm once→tracking and model unavailable while Menu/cart remain usable. `pnpm.cmd build` passed.
- Fetched origin: backend A4 present at `81648a3` on Dev A branch; main remains baseline. Preparing isolated backend snapshot for live tests, not altering Dev A files or merging main. Asked for serialized integration clearance while continuing frontend work.
- B4 frontend ready; C4 live acceptance pending the snapshot test and eventual combined main verification.

### 2026-11-14 13:33 (UTC+7) — Dev B · B3 staff loop
- Customer SSE tracking with 5s fallback and stale-GET protection; admin PIN UI/session token, authenticated stream with 3s fallback, status columns/allowed actions, reason dialog, 409 conflict refetch and announcements.
- B3 RED: missing board/hook modules; GREEN `pnpm.cmd test --run` → 9 files / 19 passed; `pnpm.cmd build` passed. Hook test clients stabilized to match production dependency identity.
- `pnpm.cmd exec playwright test e2e/admin.spec.ts` → 1 passed (fixture API): incorrect PIN, login token, actual bearer request headers, pending→confirmed board move at 1280px. Playwright now starts its Vite server automatically after a previous dev process ended.
- Commit-boundary correction: delayed B2 Git staging included B3 production files in `5906e6d`; B3 tests are recorded in the following commit. History kept intact, no force push/rewrite. From now on wait for commit commands to finish before editing next-task files.
- C3 live latency still unverified: no backend runtime on current main; no main merge attempted without Dev A confirmation.

### 2026-11-14 13:25 - Dev A A4
- Task A4: complete - RED agent modules/repository functions missing; GREEN full suite: 68 passed in 6.56s.
- Seven approved async tools; verbatim instructions; SQL menu/recommendations, existing Voyage/FTS retrieval only, SQLiteSession per conversation, SDK events mapped to contract SSE and persisted run/tool metrics.
- Deterministic tests cover all seven tools, sold_out/unknown errors, sources, conversation-scoped status, multi-turn memory, and full API loop: search - draft (0 orders) - REST confirm twice (1 order) - admin confirmed - status tool reads real total/status.
- A4 live run 1: gpt-6-luna called get_cafe_info; text reports 07:00-22:30; completed, usage input=4359/output=42, requests=2; temporary DB, tracing disabled. A5 smoke budget remains <=6 runs (planned 5).
- C4 backend ready; integrated UI loop remains pending Dev B implementation/readiness.

### 2026-11-14 13:20 (UTC+7) — Dev B · B2 customer ordering
- Discover with API facts/source dates, Menu token/diacritic search, category/price filters, stock labels, required variants, quantities/notes; persistent cart and server-quote confirmation. Retry key retained, double submission guarded; PRICE_CHANGED asks again with fresh quote.
- `pnpm.cmd test --run` → 7 files / 15 passed; `pnpm.cmd build` passed after explicitly typing the JSON test fixture as OrderQuote.
- Playwright CLI: `pnpm.cmd exec playwright test e2e/responsive.spec.ts` → 2 passed, 390px and 1280px; menu, variant selection, add-to-cart and no horizontal overflow verified. Inspected Discover and variant-sheet screenshots. API responses intercepted from frozen fixtures, not live integration proof.
- Added planned @playwright/test 1.65.0 earlier for B2 responsive verification (CLI Chromium installed). Playwright MCP calls rejected by environment approval policy, CLI works.
- C1/C2 still pending Dev A live endpoints and serialized integration clearance. Feature branch ready for frontend review; main untouched.

### 2026-11-14 13:10 - Dev A A3
- Task A3: complete - RED 10 admin tests fail on missing routes; GREEN `uv run --no-sync pytest -q -p no:cacheprovider`: 55 passed in 3.18s.
- PIN uses constant-time UTF-8 comparison; DB stores sha256 tokens with 12h expiry; all protected routes reject absent token; failed-login limit, expired token, logout revocation, menu sold_out, STATUS_CONFLICT and INVALID_TRANSITION verified.
- Real HTTP uvicorn test: customer receives initial pending snapshot, admin changes to confirmed, customer receives order_status and admin receives order_updated; headers verified. C3 backend ready, UI integration pending Dev B.

### 2026-11-14 13:08 (UTC+7) — Dev B · B1 foundation
- Branch `feat/dev-b-frontend` from baseline `2b016a2`; fetched/pulled latest main, verified ancestry and pushed upstream. No pre-existing uncommitted changes.
- B1: React multi-page entries, design tokens/self-hosted fonts, frozen TS types/client, live/mock clients, incremental SSE parser, conversation id, cart, VND/UTC+7 formatting.
- TDD: initial five suites failed for missing implementation; `pnpm.cmd test --run` → 5 files / 11 tests passed; `pnpm.cmd build` → passed.
- Resolved/pinned: React/DOM 19.3.1; Vite 8.3.8; TypeScript 7.0.2; plugin-react 6.3.0; GSAP 3.15.1; @gsap/react 2.1.2; thinking-orbs 0.3.2; both fonts 5.3.0; Vitest 5.1.0; jsdom 31.0.0; Testing Library React 16.3.3 / jest-dom 7.0.1 / user-event 14.6.10. Scaffold oxlint 1.93.0, React type packages 19.3.0, Node types 24.19.2.
- Node 24.13.0 / pnpm 11.0.8; use `pnpm.cmd` because PowerShell execution policy blocks pnpm.ps1. Caches require sandbox escalation. `uv sync`, offline ingestion (0 paid calls) and `uv run pytest -q` → 9 passed. Restored only the generated ingestion stats file to retain ownership boundaries.
- C1 live remains pending: API endpoints absent at baseline. Live is the default; fixture mode is opt-in, never claimed as integrated proof. Waiting for Dev A confirmation before any main merge.
- Ruling: execution ledger in `frontend/IMPLEMENTATION_LOG.md`; do not run skill scratch scripts that create a .gitignore outside assigned files. Root .gitignore, .agents, .claude, .env and frozen contracts unchanged.

### 2026-11-14 13:00 - Dev A A2
- Task A2: complete - RED app.orders missing; GREEN full suite 44 passed in 1.46s. Extra checks: concurrent same-key requests create exactly one order; event-write failure rolls back order+items; price snapshots/replay survive changed catalog; PRICE_CHANGED quote persists; bus bounded queue and heartbeat verified.
- Ruling: plan TestClient.stream test replaced with direct async response iterator test - ASGI TestClient buffers an infinite SSE response, so it cannot return its first line; snapshot and wire event still asserted, real HTTP smoke scheduled.
- C1 clarification from owner: Dev B only pushed an empty baseline branch, no implementation; integration postponed. Verified main/origin/main still 2b016a2, no merge or main push occurred. Temporarily stashed A2 tests restored in full.
- C2 backend ready; customer UI integration pending Dev B.

### 2026-11-14 12:40 - Dev A execution ledger
- Plan: `docs/superpowers/plans/2026-11-14-dev-a-backend-agent.md`; branch `feat/dev-a-backend-agent`, baseline `2b016a2` verified in origin/main; branch pushed.
- Preparation: uv sync succeeded; offline ingest 56 cache vectors, 0 Voyage tokens; verifier rerun with PYTHONIOENCODING=utf-8 succeeded (console cp1252 failed first); pytest: 9 passed in 0.90s.
- Preparation commands regenerated three tracked knowledge reports; retained locally and excluded from Dev A commits (outside ownership).
- Ruling: use this Dev A ledger instead of SDD helper workspace - helper creates .gitignore, prohibited by user; approved task sequence unchanged.
- Pre-flight A1->A2: ApiError/deps/time/DTO shared signatures consistent. A2->A3: state/service/EventBus interfaces consistent. A1+A2->A4: repository/drafts/status/retrieval consumed consistently. A4->A5->A6: stream/session/observability interfaces consistent.
- C1-C5 integration pending Dev B readiness; no main merge without confirmation.
- Task A1: complete - RED ModuleNotFoundError app.main; GREEN `uv run --no-sync pytest -q -p no:cacheprovider`: 16 passed in 0.53s; HTTP uvicorn smoke /api/cafe 200, phone verified. UV_CACHE_DIR uses TEMP because default cache is protected. C1 backend ready; Dev B confirmation pending.

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
