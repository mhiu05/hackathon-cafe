# TASKS — Biblio AI Café Companion

Status legend: `[x]` done · `[~]` in progress · `[ ]` todo · `[!]` blocked. Priority: P0 must-have · P1 important · P2 nice-to-have.
Each owner updates only their rows. Detailed steps: `docs/superpowers/plans/` (master, dev-a, dev-b).

## Phase 0 — Pre-implementation (done 2026-11-14)

| ID | Task | Pri | Owner | Status |
|---|---|---|---|---|
| P0-01 | Repo audit, toolkit check (Superpowers 7.0.2 installed for the project) | P0 | prep | [x] |
| P0-02 | Collect knowledge: web sources, Apify Google Maps (1 place, 30 reviews) + TikTok (20 videos), $0.096 | P0 | prep | [x] |
| P0-03 | Branch-identity curation, normalized dataset (menu 51, services, 57 docs, sources 21, unverified 21) | P0 | prep | [x] |
| P0-04 | SQLite catalog + KB schema (0001, 0002), Voyage `voyage-4-lite`/512 embeddings (56 chunks), FTS5 fallback | P0 | prep | [x] |
| P0-05 | Retrieval module + eval (30 Q; vector hit@5 29/29, keyword 27/29, SQL 8/8) + 9 unit tests | P0 | prep | [x] |
| P0-06 | Model/SDK compatibility smoke (`gpt-6-luna` × openai-agents 0.24.0) | P0 | prep | [x] |
| P0-07 | Design docs, contracts, fixtures, root docs (PRD/ARCHITECTURE/DESIGN/RULES/TASKS/PROGRESS), plans, handoff | P0 | prep | [x] |

## Phase 1 — Foundation & catalog (0:00–1:00)

| ID | Task | Pri | Owner | Status |
|---|---|---|---|---|
| A1 | App factory, 0003 migration, errors, deps, public catalog API + contract tests | P0 | Dev A | [ ] |
| B1 | Vite multi-page scaffold, tokens/fonts, typed ApiClient (live+mock), SSE parser, cart/format libs + tests | P0 | Dev B | [x] |
| C1 | Checkpoint: customer UI reads live `/api/cafe` + `/api/menu` | P0 | both | [ ] |

## Phase 2 — Orders (1:00–2:00)

| ID | Task | Pri | Owner | Status |
|---|---|---|---|---|
| A2 | Quote, idempotent orders, drafts confirm/discard, event bus, order SSE, order APIs + tests | P0 | Dev A | [ ] |
| B2 | Customer shell, Discover, Menu (search/filter/variants), Cart + confirm sheet + tests | P0 | Dev B | [x] |
| C2 | Checkpoint: UI checkout creates `BB-0001`; retry returns same order | P0 | both | [ ] |

## Phase 3 — Staff loop (2:00–3:00)

| ID | Task | Pri | Owner | Status |
|---|---|---|---|---|
| A3 | Admin PIN login/tokens/rate limit, admin orders API, transitions, admin SSE, menu PATCH + tests | P0 | Dev A | [ ] |
| B3 | Order tracking (SSE + polling), admin app (login, board, transitions, reason, conflict toast) + tests | P0 | Dev B | [x] |
| C3 | Checkpoint: admin confirms; customer page updates ≤2 s | P0 | both | [ ] |

## Phase 4 — Agent (3:00–4:00)

| ID | Task | Pri | Owner | Status |
|---|---|---|---|---|
| A4 | Repository queries, 7 tools, instructions, SSE streaming endpoint + ScriptedModel tests | P0 | Dev A | [ ] |
| B4 | Chat panel: reducer, AgentOrb mapping, tool chips, draft slip → REST confirm, order card, banner + tests | P0 | Dev B | [x] |
| C4 | Checkpoint: recommend → draft → confirm → admin → status (P0 complete) | P0 | both | [ ] |

## Phase 5 — Hardening, polish, rehearsal (4:00–5:00)

| ID | Task | Pri | Owner | Status |
|---|---|---|---|---|
| A5 | Guards (409/429), error mapping, cancellation, retries, live smoke (`-m live`), `reset_demo.py` | P0 | Dev A | [ ] |
| B5a | Loading/empty/error/degraded states | P0 | Dev B | [~] |
| B5b | Admin Menu availability screen | P1 | Dev B | [ ] |
| A6a | `/api/admin/insights` | P1 | Dev A | [ ] |
| B5c | Admin Tổng quan screen | P1 | Dev B | [ ] |
| A6b | Draft-confirm note into agent memory; `/api/agent/history` | P1 | Dev A | [ ] |
| B5d | GSAP motion + reduced motion | P1 | Dev B | [ ] |
| B5e | Impeccable critique/audit/polish pass | P1 | Dev B | [ ] |
| B5f | Playwright demo smoke | P1 | Dev B | [ ] |
| C5 | Reset + rehearsal ×2 (`docs/demo-runbook.md`) | P0 | both | [ ] |

## Backlog (P2 — do not start before P0 + P1 are green)

- Per-customer accounts / order isolation · events tool + event registration · room booking · chat history UI · mini-game ·
  voice · multi-agent · advanced analytics · complex animations · owner-verified data workflow UI.

## Owner follow-ups (not code)

- [ ] Ask staff: today's availability, current prices, meaning of the X next to "Trà xoài Yakult", "Bơ già dừa non" name,
  ordering/payment rules, upcoming events (see `data/knowledge/normalized/unverified_claims.json`).
- [x] Commit and push the pre-implementation work to `main` as the baseline (2026-11-14); devs branch from it (`RULES.md §6`).
