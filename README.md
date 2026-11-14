Link demo người dùng: https://kangaroo-donator-exclaim.ngrok-free.dev/
Link demo admin: https://kangaroo-donator-exclaim.ngrok-free.dev/admin.html

# Biblio AI Café Companion

AI-native web app for **one café — Biblio Café Sách, 79 Ngụy Như Kon Tum, Thanh Xuân, Hà Nội** (local hackathon build).
Customers explore the café, browse the real menu, ask an AI concierge that answers from a branch-verified knowledge base and
SQL and prepares order drafts they confirm with one tap (no online payment); staff confirm and progress orders in an admin dashboard.

> Data notice: menu, prices and services come from photos taken in-store on 14/11/2026 and public sources; nothing is
> owner-confirmed yet. See `docs/knowledge-sources.md`.

**Start here:** [`docs/IMPLEMENTATION_HANDOFF.md`](docs/IMPLEMENTATION_HANDOFF.md).

| Root document | Purpose |
|---|---|
| [`PRD.md`](PRD.md) | product, users, decisions, functional requirements, priorities, acceptance |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | stack, folders/ownership, components, data flows, security |
| [`DESIGN.md`](DESIGN.md) | design system (tokens, typography, components, motion, do/don't) |
| [`RULES.md`](RULES.md) | coding standards and what humans/AI agents must and must not do |
| [`TASKS.md`](TASKS.md) | phased task list with priority and status |
| [`PROGRESS.md`](PROGRESS.md) | log of work, issues, decisions, next steps |

Quick checks (work today, no API calls):

```powershell
uv sync
uv run python scripts/knowledge/ingest.py --offline   # builds data/cafe.db
uv run python scripts/knowledge/verify.py --offline
uv run pytest -q
```

Stack: FastAPI + SQLite + OpenAI Agents SDK (`gpt-6-luna`) + Voyage `voyage-4-lite` (512-d) · React + Vite + TypeScript ·
GSAP · Thinking Orbs. Secrets live only in the git-ignored root `.env` (template: `.env.example`).
