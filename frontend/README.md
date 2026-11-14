# Biblio - frontend

React 19 + Vite 8 multi-page, TypeScript, plain CSS, GSAP and Thinking Orbs.

Node 24 / pnpm 11. On Windows use pnpm.cmd if PowerShell blocks pnpm.ps1.

## Run

From frontend/:

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd dev
```

Customer: http://localhost:5173/ | Staff: http://localhost:5173/admin.html. The Vite proxy sends /api to localhost:8000. Start Dev A's single-worker backend from the repo root.

The serialized integration now includes Dev A's runtime. Start it from the repo root with `uv run uvicorn app.main:app --port 8000` (one worker), then run Vite from frontend/. Isolated test helpers remain available for regression/rehearsal without changing the original database.

Live is the default. For fixture-only development set VITE_API_MODE=mock in the process environment or a local frontend/.env. Mock mode is visibly labelled and excluded from production's live import graph. Never put keys or ADMIN_PIN in VITE_* variables.

## Verify

```powershell
pnpm.cmd test --run
pnpm.cmd build
pnpm.cmd lint
pnpm.cmd exec playwright test
```

The default Playwright suite intercepts fixture API responses for deterministic tests; live tests skip unless credentials/explicit opt-in are supplied. Playwright starts Vite automatically. E2E_BASE_URL can point to an already running frontend. Screenshots go to ignored test-results/.

Live checks from the repo root, using configured PIN in memory without printing it:

```powershell
.venv\Scripts\python.exe frontend/scripts/run_live_smoke.py
.venv\Scripts\python.exe frontend/scripts/run_live_smoke.py --agent
```

The first command uses real local order/admin APIs without model calls. The second explicitly opts into at most three real agent turns (no automatic retries) and may use OpenAI/Voyage.

For parallel backend validation, export a committed Dev A backend/ snapshot into frontend/node_modules/.cache/ and run scripts/serve_backend_snapshot.py --snapshot PATH. It reads the existing root configuration, backs up the source catalogue to its own database, disables test tracing and leaves backend source, root .env and the source database unchanged. Never use this helper to infer combined-main acceptance.

## Contracts and integration

All requests go through src/api; types.ts is copied verbatim from docs/api-contracts.md section 9. Prices and allowed admin transitions are server-authoritative. Order confirmation requires a customer click; retries retain their key; price drift asks again. Chat context is scoped by the persisted 32-hex conversation id.

See [INTEGRATION_NOTES.md](INTEGRATION_NOTES.md) for live results and the admin SSE field mismatch. [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) records task gates and execution rulings. Main integration passed after Dev A's handoff and the owner's confirmation.

The completed task/test/checkpoint report is [DELIVERY_REPORT.md](DELIVERY_REPORT.md). For isolated reset rehearsals, run scripts/run_snapshot_rehearsals.py --snapshot PATH --runs 2 --agent from the repo root. It uses Dev A's reset script with backups and bounds each rehearsal to three real agent turns; --verify-only validates existing run logs without model calls.
