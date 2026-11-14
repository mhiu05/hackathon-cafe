# PRD — Biblio AI Café Companion

Status: **approved design, pre-implementation** (2026-11-14). Canonical product requirements. Details: `docs/agent-design.md`,
`docs/api-contracts.md`, `docs/database-design.md`, `docs/ui-ux-spec.md`, `docs/knowledge-sources.md`.

## 1. Product overview

A local web app for **one café — Biblio Café Sách, 79 Ngụy Như Kon Tum, Làng sinh viên Hacinco, Thanh Xuân, Hà Nội** —
built in a **5-hour hackathon by 2 developers** and demoed on one laptop. Customers explore the café, browse the real menu, ask
an AI agent that answers from a branch-verified knowledge base and SQL, and order (no online payment). Staff receive, confirm and
progress orders in an admin dashboard.

## 2. Problem

Customers of a large book café (reading rooms, co-working, meeting rooms, 51-item menu) ask the same questions — hours, Wi-Fi,
quiet spaces, rooms for N people, what fits a budget — and queue at the counter to order. Information online is scattered and
mixes Biblio's branches (70 Tam Khương, Hà Đông) with this one. The café needs an assistant that knows **this branch**, never
invents facts, and turns a conversation into a real order the staff can act on.

## 3. Users

| User | Needs | Surface |
|---|---|---|
| Students / remote workers from the Hacinco area | quiet seat, Wi-Fi, sockets, cheap drinks, co-working packages | Chat, Menu |
| Group organisers (workshops, meetings) | room by capacity, price per 4-hour session, facilities | Chat, Discover |
| Parents with children | kids area, children's books | Chat, Discover |
| Walk-in customers | browse menu, order fast, track status | Menu, Cart, Order |
| Counter staff | see new orders instantly, accept/reject, update status, mark sold-out | Admin |
| Hackathon judges | the agent visibly uses real tools on real data end to end | both |

## 4. Goals, non-goals, anti-goals

Goals (in priority order): (1) the agent does real, correct work through tools; (2) the end-to-end flow is stable;
(3) customer UX is fast and clear; (4) distinctive UI; (5) code that is easy to read and run.

Non-goals: online payment, multi-café/multi-branch, deployment/cloud/Docker, customer registration, room booking, event
registration, events tool, voice, multi-agent orchestration, live web scraping at request time.

Anti-goals (failure even if it "works"): the agent states a price, stock, event, discount or policy not in the data; an order is
created without a customer's explicit click; staff features break when OpenAI is down; unverified data is presented as
owner-confirmed; another branch's facts are used for this branch.

## 5. Decisions locked with the project owner (2026-11-14)

1. **Agent prepares drafts only.** `prepare_order` stores an order draft with a server-computed quote; the customer clicks
   **Xác nhận đặt món** on the card to create the real order via REST.
2. **Unknown availability is orderable** with a warning on the confirmation card; staff accepting the order is the stock check.
   Only items staff mark **Hết** (`sold_out`) are blocked.
3. **Accounts**: admin logs in with `ADMIN_PIN` (in `.env`). Customers never log in — every customer browser automatically uses one
   shared, pre-created account; chat history is separate per browser (conversation id). All customer orders are visible to any
   customer browser (accepted for the single-laptop demo).
4. **No events tool** in this build; event questions are answered from the knowledge base (no verified upcoming events).

## 6. Functional requirements

### Customer (mobile-first)
- **FR-C1 Discover**: café name, address, phone, hours with open-now, highlights with source labels, Google rating with date, data notice.
- **FR-C2 Menu**: 9 categories, 51 items, search (diacritic-insensitive), price filter, variants (Nâu/Đen; 1/2 người), availability badges, "giá theo menu 14/11/2026 — chờ quán xác nhận" notice.
- **FR-C3 Cart & checkout**: add/edit/remove lines (≤10 lines, qty 1–10, note ≤120), optional name/table/note, server quote, confirm, idempotent create, price-change handling.
- **FR-C4 Order tracking**: order page with live status and timeline; rejected/cancelled reason; "thanh toán tại quầy".
- **FR-C5 AI assistant**: streaming chat; Thinking Orb reflecting backend state; tool activity chips; source labels; order draft card with **Xác nhận đặt món** / **Bỏ qua**; order card after confirmation; degraded-mode banner.

### Agent (7 tools, single orchestrator, `gpt-6-luna`)
- **FR-A1** answer café facts (`get_cafe_info`) and knowledge questions with attribution (`search_cafe_knowledge`, Voyage RAG + FTS fallback).
- **FR-A2** search menu and recommend from SQL only (`search_menu`, `recommend_drinks`); disclose that tags are inferred from names.
- **FR-A3** co-working and room information by capacity (`get_coworking_info`); never claims availability; no booking.
- **FR-A4** prepare an order draft (`prepare_order`) and tell the customer to confirm on the card; never claim an order exists before it does.
- **FR-A5** report order status (`get_order_status`) for this conversation or a given code.
- **FR-A6** multi-turn memory per conversation; refuse out-of-scope requests and prompt injection; say "chưa có thông tin đã xác minh" when evidence is missing.

### Admin (desktop-first)
- **FR-S1** PIN login → token; all admin APIs require it.
- **FR-S2** live order board (pending/confirmed/preparing/ready + finished list), detail, allowed transitions only, reason for reject/cancel, conflict handling.
- **FR-S3 (P1, first after P0)** menu availability (Còn/Hết/Chưa xác nhận) and orderable toggle.
- **FR-S4 (P1)** insights: orders by status, top items, agent runs/tool calls/tokens.

## 7. Priorities

| | Scope |
|---|---|
| **P0** | prepared KB (done) · Voyage retrieval · menu SQL · 7 agent tools · streaming chat with real orb states · multi-turn memory · order drafts + REST confirm · cart checkout · admin login + live order board + transitions · customer live status · degraded mode · backend pytest + key frontend unit tests |
| **P1** | admin menu availability · insights · sources drawer · suggestion chips · chat history restore · GSAP motion · Impeccable critique/polish · Playwright E2E · draft-confirm note in agent memory |
| **P2** | per-customer isolation · events tool/registration · room booking · mini-game · voice · multi-agent · advanced analytics · complex animations |

**Minimum Demoable Product** = all P0 + the E2E scenario below. Cut P2 first, then P1; never break P0.

## 8. Acceptance criteria (P0)

1. Address/hours/phone answers = 79 Ngụy Như Kon Tum / 07:00–22:30 / 0976 214 224 with a source; questions about 70 Tam Khương → "no verified data for that branch".
2. Every price in an agent message equals a price returned by a tool in that run.
3. Sweetness/caffeine/room availability/upcoming events/Wi-Fi password → "chưa có thông tin đã xác minh" + staff/phone hint.
4. `prepare_order` creates exactly one draft and **zero** orders; the reply never says the order is placed.
5. Confirming a draft creates exactly one order (`source=agent_draft`); clicking again returns the same order; expired → 410; price drift → 409 with new quote.
6. Cart checkout: quote → create with `Idempotency-Key`; retry returns the same order; price drift → 409 → UI shows new total.
7. All `/api/admin/*` except login → 401 without token; wrong PIN 401; 6th failure/min 429.
8. Only state-machine transitions succeed; stale `expected_status` → 409; reject/cancel need a reason.
9. New orders appear on the admin board ≤2 s without reload; customer order page reflects admin changes ≤2 s (polling fallback ≤5 s).
10. The orb shows exactly the last backend `agent_state`; reduced-motion users see static orbs/transitions.
11. With an invalid `OPENAI_API_KEY`, chat shows the unavailable banner while menu/cart/order/admin still work.
12. UI labels unverified data ("Chưa xác nhận còn món", price notice); nothing is shown as owner-verified.

## 9. End-to-end scenario (demo path)

1. "Quán ở đâu, mở đến mấy giờ?" → `get_cafe_info` → facts + source.
2. "Có chỗ yên tĩnh ngồi học không?" → `search_cafe_knowledge` → laptop-friendly/quiet + caveat on event noise, cites Google Maps/reviews.
3. "Mình muốn uống gì đó ít ngọt, không quá 50k. Gợi ý rồi đặt một ly." → `recommend_drinks(max_price_vnd=50000)` → 2–3 items, SQL prices, sweetness caveat.
4. "Lấy trà chanh gừng mật ong" → `prepare_order` → draft card (45.000đ, availability warning) → customer taps **Xác nhận đặt món** → order `BB-000N`.
5. Admin board shows it live → **Nhận đơn** → **Đang pha** → **Sẵn sàng**.
6. Customer order page updates live; "Đơn của mình xong chưa?" → `get_order_status` → "Sẵn sàng — mời bạn nhận tại quầy".

Negative cases to pass before the demo: changed price (409), unavailable item (422 / agent explains), empty knowledge (agent says
unverified), duplicate confirm/checkout (same order), unknown order code (404), API error (UI error state), Voyage timeout (keyword
fallback), OpenAI unavailable (degraded mode), admin unauthorized (401), invalid transition (409).
