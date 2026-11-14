# API Contracts (frozen for the hackathon build)

Base URL: relative `/api` (Vite dev proxy → `http://localhost:8000`). All JSON UTF-8. Money = integer VND. Times = ISO-8601 UTC `…Z`.
Single uvicorn worker (in-process event bus). CORS also allows `FRONTEND_ORIGIN` with headers
`Content-Type, X-Conversation-Id, Idempotency-Key, Authorization`.

Fixtures matching these schemas: generated from `data/cafe.db` by `scripts/contracts/export_fixtures.py` →
`contracts/fixtures/{cafe,menu,services}.json`; hand-written → `contracts/fixtures/{quote,draft,order,order_from_draft,admin_orders}.json`,
`contracts/fixtures/agent_stream.sse`. TypeScript source of truth: §9 (copy verbatim to `frontend/src/api/types.ts`).

Identity model (decided 2026-11-14): customers never log in — the backend treats every customer call as the shared
pre-created account `shared-customer`; each browser keeps its own `conversation_id` (uuid4 hex, 32 chars) for chat memory and
"my latest orders". Admin uses a PIN → bearer token. See `docs/database-design.md §8`.

## 1. Error envelope and codes

```json
{ "error": { "code": "ITEM_UNAVAILABLE", "message": "Món 'Trà xoài Yakult' hiện đã hết.", "details": { "item_id": "menu_019" } } }
```

| HTTP | code | When |
|---|---|---|
| 400 | `BAD_REQUEST` | malformed JSON; missing/invalid `X-Conversation-Id` on agent calls; missing `Idempotency-Key` |
| 401 | `ADMIN_AUTH_REQUIRED` | missing/expired/invalid admin token; wrong PIN |
| 404 | `NOT_FOUND`, `ORDER_NOT_FOUND`, `ITEM_NOT_FOUND`, `DRAFT_NOT_FOUND` | resource absent |
| 409 | `PRICE_CHANGED` | `expected_total_vnd` ≠ server total (`details.quote` = fresh `OrderQuote`) |
| 409 | `IDEMPOTENCY_CONFLICT` | same `Idempotency-Key`, different payload |
| 409 | `DRAFT_DISCARDED`, `DRAFT_ALREADY_CONFIRMED` | confirm a discarded draft / discard a confirmed draft |
| 409 | `STATUS_CONFLICT` | `expected_status` ≠ current status (`details.current_status`) |
| 409 | `INVALID_TRANSITION` | transition not in state machine (`details.allowed`) |
| 409 | `RUN_IN_PROGRESS` | another agent run is active for this conversation |
| 410 | `DRAFT_EXPIRED` | draft older than 30 min |
| 422 | `VALIDATION_ERROR` | schema/limit violations (`details.errors` = list of `{loc, msg}`) |
| 422 | `CART_EMPTY`, `CART_TOO_LARGE` | 0 lines / >10 lines |
| 422 | `ITEM_UNAVAILABLE` | item `sold_out` or `is_orderable=0` |
| 422 | `VARIANT_REQUIRED`, `INVALID_VARIANT` | variant rules (database-design §3) |
| 429 | `RATE_LIMITED` | >5 failed admin logins/min/IP; >20 chat messages/min/conversation |
| 503 | `MODEL_UNAVAILABLE` | OpenAI unreachable/auth/quota (agent only) |
| 503 | `ADMIN_NOT_CONFIGURED` | `ADMIN_PIN` empty |

FastAPI's default 422 body is replaced by the envelope (`VALIDATION_ERROR`) via an exception handler.

## 2. Public catalog (no auth)

| Method & path | Response | Notes |
|---|---|---|
| `GET /api/health` | `{status:"ok", db:"ok", knowledge_chunks:int, model:string, model_configured:bool, admin_configured:bool}` | never calls OpenAI |
| `GET /api/cafe` | `CafeProfile` | `is_open_now` computed in UTC+7 (fixed offset) |
| `GET /api/menu?category=&q=&max_price_vnd=` | `MenuResponse` | filters optional; `q` = diacritic-insensitive, every folded token must be in `name_search` |
| `GET /api/menu/{item_id}` | `MenuItem` | 404 `ITEM_NOT_FOUND` |
| `GET /api/services` | `ServicesResponse` | co-working, rooms, facts, booking policy |

Builders: `app.catalog.dto` (`cafe_profile_dto`, `menu_response_dto`, `menu_item_dto`, `services_response_dto`) — already implemented
and used to generate the fixtures; the endpoints must return exactly these.

## 3. Conversation id

The customer app creates `conversation_id = crypto.randomUUID().replaceAll("-", "")` on first load, stores it in
`localStorage["biblio.conversation"]`, and sends header `X-Conversation-Id` on `/api/agent/*` (required, must match `^[0-9a-f]{32}$`,
else `400 BAD_REQUEST`) and on `POST /api/orders` (optional; stored on the order). "Cuộc trò chuyện mới" = generate a new id.

## 4. Orders (customer, no auth)

### `POST /api/orders/quote` — read-only
Request `{ "lines": CartLineInput[] }` → `200 OrderQuote`. Errors: 422 `CART_EMPTY|CART_TOO_LARGE|ITEM_NOT_FOUND|ITEM_UNAVAILABLE|VARIANT_REQUIRED|INVALID_VARIANT|VALIDATION_ERROR`.
Rules: `line_no` = input order (1-based); identical lines are not merged; `warnings` has `AVAILABILITY_UNCONFIRMED` (item_ids with
`availability="unknown"`) and `PRICE_UNVERIFIED` (item_ids with `price_verified=false`), each omitted when empty;
`subtotal_vnd == total_vnd` (no fees/discounts).

### `POST /api/orders` — create from cart
Headers: `Idempotency-Key: <uuid4>` (required, 8–100 chars), `X-Conversation-Id` (optional). Request `CreateOrderRequest`.
`201 Order` · `200 Order` + header `Idempotent-Replay: true` (same key, same payload) · 409 `PRICE_CHANGED|IDEMPOTENCY_CONFLICT` · 422 as quote.
Side effects: `orders` (`source="ui"`), `order_items`, `order_events`; bus `order_created` after COMMIT.

### `GET /api/orders/drafts/{draft_id}` → `OrderDraft` · 404 `DRAFT_NOT_FOUND` (P1: restore card after reload)
### `POST /api/orders/drafts/{draft_id}/confirm` — the only way an agent-prepared order becomes real
Request `{ "expected_total_vnd": int }` → `201 Order` (`source="agent_draft"`) · `200 Order` + `Idempotent-Replay: true` if already
confirmed · 404 `DRAFT_NOT_FOUND` · 409 `PRICE_CHANGED` (draft quote refreshed; show `details.quote`, confirm again) ·
409 `DRAFT_DISCARDED` · 410 `DRAFT_EXPIRED` · 422 `ITEM_UNAVAILABLE` (item became sold out).
### `POST /api/orders/drafts/{draft_id}/discard` → `200 {draft_id, status:"discarded"}` · 404 · 409 `DRAFT_ALREADY_CONFIRMED`

### `GET /api/orders?conversation_id=` → `{ orders: Order[] }` (newest first, max 20; filter optional)
### `GET /api/orders/{code}` → `Order` · 404 `ORDER_NOT_FOUND`
### `GET /api/orders/{code}/stream` → SSE `order_status {order}` on connect and on every change; `: ping` every 15 s.
Client fallback: poll `GET /api/orders/{code}` every 5 s if the stream errors.

## 5. Agent

### `POST /api/agent/chat/stream` → `text/event-stream`
Headers: `X-Conversation-Id` (required). Request `{ "message": string }` (1–1000 chars after trim).
Pre-stream JSON errors: 400, 409 `RUN_IN_PROGRESS`, 422, 429. After streaming starts, failures are an `error` event followed by `done`.

### `GET /api/agent/history` (P1) → `{ messages: { role: "user"|"assistant", text: string }[] }` (header `X-Conversation-Id`)

### SSE wire format
```
event: <name>
data: <single-line JSON>

```
`AgentStreamEvent` (§9):

| event | data | Emitted when (backend truth) |
|---|---|---|
| `run_started` | `{run_id}` | request accepted, before the first model call |
| `agent_state` | `{state}` | on every state change (§6) |
| `tool_started` | `{call_id, tool, label}` | SDK `tool_called` item; label from `TOOL_LABELS` |
| `tool_finished` | `{call_id, tool, ok, summary}` | SDK `tool_output` item; `ok=false` if the tool JSON has `"ok": false` |
| `order_draft` | `{draft: OrderDraft}` | `prepare_order` output contains a draft (row already committed) |
| `text_delta` | `{delta}` | raw `response.output_text.delta` |
| `message_completed` | `{text, sources: SourceRef[]}` | final assistant message; sources = documents returned by `search_cafe_knowledge`/`get_cafe_info` in this run (deduplicated by `source_id`) |
| `error` | `{code, message, retryable}` | `MODEL_UNAVAILABLE`, `MAX_TURNS`, `SESSION_RESET`, `INTERNAL` |
| `done` | `{reason: "completed"|"error"|"cancelled", usage: {input_tokens, output_tokens, requests}}` | always last |

## 6. Agent state → Thinking Orb (single source of truth)

| `agent_state.state` | Backend trigger | Orb `state` | Label (vi) |
|---|---|---|---|
| `idle` | no active run / right before `done` | `breathing` | "Sẵn sàng" |
| `thinking` | run started; after each `tool_output` until the next item | `connecting` | "Đang suy nghĩ" |
| `searching` | `tool_called` of a read tool (`get_cafe_info`, `search_cafe_knowledge`, `search_menu`, `recommend_drinks`, `get_coworking_info`, `get_order_status`) | `searching` | "Đang tra cứu" |
| `working` | `tool_called` of `prepare_order` | `working` | "Đang chuẩn bị đơn nháp" |
| `composing` | first `text_delta` of a message | `composing` | "Đang trả lời" |
| `error` | `error` emitted | `breathing` + `paused` | "Có lỗi" |

The frontend renders the last received `agent_state`; it never invents states or uses timers.

## 7. Admin (header `Authorization: Bearer <token>`)

| Method & path | Request | Response | Errors |
|---|---|---|---|
| `POST /api/admin/login` | `{pin}` | `200 {token, expires_at}` | 401, 429, 503 `ADMIN_NOT_CONFIGURED` |
| `POST /api/admin/logout` | — | `204` | 401 |
| `GET /api/admin/orders?status=&limit=50` | — | `AdminOrderListResponse` (orders include `allowed_next`) | 401 |
| `GET /api/admin/orders/{id}` | — | `Order` (+`allowed_next`) | 401, 404 |
| `PATCH /api/admin/orders/{id}/status` | `UpdateOrderStatusRequest` | `Order` (+`allowed_next`) | 401, 404, 409 `STATUS_CONFLICT|INVALID_TRANSITION`, 422 (`reason` 3–200 chars required for rejected/cancelled) |
| `PATCH /api/admin/menu/{item_id}` (P1, first) | `UpdateMenuItemRequest` | `MenuItem` | 401, 404, 422 |
| `GET /api/admin/stream` | — | SSE `order_created {order}`, `order_updated {order}`, `: ping` | 401 |
| `GET /api/admin/insights` (P1) | — | `AdminInsights` | 401 |

PIN check `hmac.compare_digest(pin, ADMIN_PIN)`; token `secrets.token_urlsafe(32)`; sha256 stored in `admin_sessions`; 12 h expiry.

## 8. Examples

`POST /api/orders/quote` `{"lines":[{"item_id":"menu_001","variant_id":"menu_001:den","quantity":2},{"item_id":"menu_030","variant_id":null,"quantity":1,"note":"ít đá"}]}`
→ `contracts/fixtures/quote.json` (total 115000, two warnings).

`prepare_order` → SSE `order_draft` → card → `POST /api/orders/drafts/3c9e51…/confirm {"expected_total_vnd":45000}` → `201` `contracts/fixtures/order_from_draft.json`.

`PATCH /api/admin/orders/1/status {"to_status":"confirmed","expected_status":"pending"}` → `200 Order` (`status_label:"Quán đã nhận đơn"`, last event actor `admin`).

Full agent transcript (recommend → draft → confirm via REST → status): `contracts/fixtures/agent_stream.sse`.

## 9. TypeScript types (copy verbatim to `frontend/src/api/types.ts`)

```ts
export type Availability = "available" | "sold_out" | "unknown";
export type VerificationStatus = "owner_verified" | "verified_branch" | "brand_general" | "unverified_branch" | "conflicting";
export type OrderStatus = "pending" | "confirmed" | "preparing" | "ready" | "completed" | "rejected" | "cancelled";
export type AgentState = "idle" | "thinking" | "searching" | "working" | "composing" | "error";

export interface ApiErrorBody { error: { code: string; message: string; details?: Record<string, unknown> } }

export interface SourceRef { source_id: string; title: string; url: string | null; retrieved_at: string; verification_status: VerificationStatus }

export interface CafeProfile {
  branch_id: string; brand_name: string; display_name: string;
  address: string; latitude: number; longitude: number; plus_code: string;
  phone: string; opening_hours: { open: string; close: string; days_label: string }; is_open_now: boolean;
  channels: { google_maps_url: string; facebook_url: string; tiktok_url: string; website_url: string | null };
  wifi: { available: boolean; ssid: string; password_policy: "ask_staff" };
  rating_snapshot: { rating: number; reviews_count: number; as_of: string; source_id: string } | null;
  highlights: { label: string; source_id: string }[];
  data_status: "owner_verified" | "user_provided_unverified"; data_notice: string;
  sources: SourceRef[];
}

export interface MenuVariant { id: string; label: string; price_vnd: number }
export interface MenuItem {
  id: string; category_id: string; name: string;
  price_vnd: number | null; price_min_vnd: number; price_max_vnd: number; variants: MenuVariant[];
  availability: Availability; availability_note: string | null; is_orderable: boolean; price_verified: boolean;
  description: string | null; needs_review: string[]; suggested_tags: string[];
}
export interface MenuCategory { id: string; name: string; kind: "drink" | "food"; sort_order: number; item_count: number }
export interface MenuResponse { as_of: string; price_basis: string; categories: MenuCategory[]; items: MenuItem[] }

export interface CoworkingPackage { id: string; label: string; duration_days: number; price_vnd: number; includes_vat: boolean; price_verified: boolean }
export interface MeetingRoom {
  id: string; name: string; area_m2: number; capacity_max: number; capacity_theater: number | null; capacity_tables: number | null;
  layout_note: string; session_hours: number; price_vnd: number; includes_vat: boolean; price_verified: boolean;
}
export interface ServiceFact {
  id: string; scope: "coworking" | "meeting_room" | "cafe"; kind: "amenity" | "extra_service" | "policy"; label: string;
  price_from_vnd: number | null; price_to_vnd: number | null; unit: string | null; note: string | null;
}
export interface ServicesResponse { as_of: string; price_basis: string; coworking_packages: CoworkingPackage[]; meeting_rooms: MeetingRoom[]; facts: ServiceFact[]; booking_policy: string }

export interface CartLineInput { item_id: string; variant_id: string | null; quantity: number; note?: string | null }
export interface QuoteLine {
  line_no: number; item_id: string; variant_id: string | null; item_name: string; variant_label: string | null;
  unit_price_vnd: number; quantity: number; line_total_vnd: number; availability: Availability; note: string | null;
}
export interface QuoteWarning { code: "AVAILABILITY_UNCONFIRMED" | "PRICE_UNVERIFIED"; message: string; item_ids: string[] }
export interface OrderQuote { lines: QuoteLine[]; subtotal_vnd: number; total_vnd: number; item_count: number; currency: "VND"; warnings: QuoteWarning[]; quoted_at: string }

export interface CreateOrderRequest {
  lines: CartLineInput[]; expected_total_vnd: number;
  customer_name?: string | null; table_label?: string | null; note?: string | null;
}
export interface OrderDraft {
  draft_id: string; status: "open" | "confirmed" | "discarded"; quote: OrderQuote;
  customer_name: string | null; table_label: string | null; note: string | null;
  order_code: string | null; created_at: string; expires_at: string;
}
export interface OrderEvent { from_status: OrderStatus | null; to_status: OrderStatus; actor: "customer" | "admin" | "system"; note: string | null; created_at: string }
export interface OrderLine {
  line_no: number; item_id: string; variant_id: string | null; item_name: string; variant_label: string | null;
  unit_price_vnd: number; quantity: number; line_total_vnd: number; note: string | null;
}
export interface Order {
  id: number; code: string; status: OrderStatus; status_label: string; source: "ui" | "agent_draft";
  customer_name: string | null; table_label: string | null; note: string | null;
  lines: OrderLine[]; subtotal_vnd: number; total_vnd: number; item_count: number;
  status_reason: string | null; created_at: string; updated_at: string; events: OrderEvent[];
  allowed_next?: OrderStatus[];            // present only in admin responses
}

export interface AdminLoginResponse { token: string; expires_at: string }
export interface AdminOrderListResponse { orders: Order[]; counts: Record<OrderStatus, number> }
export interface UpdateOrderStatusRequest { to_status: OrderStatus; expected_status: OrderStatus; reason?: string | null }
export interface UpdateMenuItemRequest { availability?: Availability; availability_note?: string | null; is_orderable?: boolean }
export interface AdminInsights {
  orders_by_status: Record<OrderStatus, number>; orders_total: number; revenue_completed_vnd: number;
  top_items: { item_id: string; name: string; quantity: number }[];
  agent: { runs: number; tool_calls: Record<string, number>; tool_errors: number; input_tokens: number; output_tokens: number };
}

export type AgentStreamEvent =
  | { event: "run_started"; data: { run_id: string } }
  | { event: "agent_state"; data: { state: AgentState } }
  | { event: "tool_started"; data: { call_id: string; tool: string; label: string } }
  | { event: "tool_finished"; data: { call_id: string; tool: string; ok: boolean; summary: string } }
  | { event: "order_draft"; data: { draft: OrderDraft } }
  | { event: "text_delta"; data: { delta: string } }
  | { event: "message_completed"; data: { text: string; sources: SourceRef[] } }
  | { event: "error"; data: { code: string; message: string; retryable: boolean } }
  | { event: "done"; data: { reason: "completed" | "error" | "cancelled"; usage: { input_tokens: number; output_tokens: number; requests: number } } };

export type OrderStreamEvent = { event: "order_status"; data: { order: Order } };
export type AdminStreamEvent = { event: "order_created"; data: { order: Order } } | { event: "order_updated"; data: { order: Order } };
```

## 10. Frontend API client (`frontend/src/api/client.ts`)

```ts
export interface ApiClient {
  getCafe(): Promise<CafeProfile>;
  getMenu(params?: { category?: string; q?: string; max_price_vnd?: number }): Promise<MenuResponse>;
  getServices(): Promise<ServicesResponse>;
  quote(lines: CartLineInput[]): Promise<OrderQuote>;
  createOrder(req: CreateOrderRequest, idempotencyKey: string): Promise<Order>;
  confirmDraft(draftId: string, expectedTotalVnd: number): Promise<Order>;
  discardDraft(draftId: string): Promise<void>;
  getOrder(code: string): Promise<Order>;
  listOrders(conversationId?: string): Promise<Order[]>;
  streamOrder(code: string, onEvent: (e: OrderStreamEvent) => void, signal: AbortSignal): Promise<void>;
  chat(message: string, onEvent: (e: AgentStreamEvent) => void, signal: AbortSignal): Promise<void>;
  admin: {
    login(pin: string): Promise<AdminLoginResponse>;
    logout(): Promise<void>;
    listOrders(status?: OrderStatus): Promise<AdminOrderListResponse>;
    updateStatus(orderId: number, req: UpdateOrderStatusRequest): Promise<Order>;
    updateMenuItem(itemId: string, req: UpdateMenuItemRequest): Promise<MenuItem>;
    stream(onEvent: (e: AdminStreamEvent) => void, signal: AbortSignal): Promise<void>;
  };
}
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: Record<string, unknown>) { super(message); }
}
```
`frontend/src/api/sse.ts`: `readSse(response: Response, onEvent: (name: string, data: unknown) => void): Promise<void>` — splits on
blank lines, joins multi-line `data:`, ignores `:` comment lines, tolerates chunks split anywhere.
`frontend/src/api/conversation.ts`: `getConversationId(): string`, `resetConversation(): string`.
`VITE_API_MODE=mock|live` selects `mockClient` (fixtures) or `liveClient`; **the demo runs `live`** (mock is deleted from the
import graph by the env switch, and must not be the default).

## 11. Contract tests

| Test | Owner | Asserts |
|---|---|---|
| `backend/tests/api/test_public_contract.py` | A | `/api/cafe`, `/api/menu`, `/api/services` equal `contracts/fixtures/*.json` (ignoring `is_open_now`) |
| `backend/tests/orders/test_orders_service.py` | A | quote rules, idempotency, PRICE_CHANGED, sold_out, variants, state machine |
| `backend/tests/orders/test_drafts.py` | A | draft never creates an order; confirm once → 1 order; confirm twice → same order; expired/discarded |
| `backend/tests/api/test_admin_api.py` | A | 401 without token, login, 429, transitions, STATUS_CONFLICT, INVALID_TRANSITION |
| `backend/tests/agent/test_agent_stream.py` | A | ScriptedModel run → SSE sequence per §5/§6; `prepare_order` → `order_draft` and 0 orders |
| `frontend/src/api/sse.test.ts` | B | parser: split chunks, comments, multi-event chunks, `agent_stream.sse` fixture parses to the expected event names |
| `frontend/src/lib/cart.test.ts` | B | add/merge/update/remove, max 10 lines/qty, variant-required |
| `frontend/src/customer/state/useChat.test.ts` | B | reducer: states → orb, tool chips, draft card, error |
