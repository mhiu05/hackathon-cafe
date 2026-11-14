# Dev B — Frontend & UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the customer app (Discover, Menu, Cart/checkout, Order tracking, AI chat with Thinking Orb and draft confirmation) and the admin app (PIN login, live order board, transitions, menu availability) against the frozen API contract.

**Architecture:** Vite multi-page React app in `frontend/` (`index.html` → `src/customer`, `admin.html` → `src/admin`), no router; one typed `ApiClient` with `liveClient` (fetch + fetch-SSE through the Vite proxy `/api`) and `mockClient` (contract fixtures, incl. SSE replay) selected by `VITE_API_MODE`; state in small reducers/hooks; styling from `DESIGN.md` tokens; GSAP and Thinking Orbs for purposeful motion.

**Tech Stack:** pnpm, Vite 8.3.x, React 19.3.x, TypeScript (scaffold default), plain CSS, `gsap` 3.15.1, `@gsap/react` 2.1.2, `thinking-orbs` 0.3.2, `@fontsource/fraunces`, `@fontsource/be-vietnam-pro` 5.3.0, Vitest 5.1.x, @testing-library/react 16.3.x, jsdom; Playwright 1.65.x (P1).

**Spec:** `PRD.md`, `DESIGN.md`, `RULES.md`, `docs/ui-ux-spec.md`, `docs/api-contracts.md` (§3–§10), `contracts/fixtures/*`, master plan.

## Global Constraints

- Write only `frontend/**` (+ your rows in `TASKS.md`/`PROGRESS.md`).
- `src/api/types.ts` = `docs/api-contracts.md §9` verbatim; no `any` in API code; components never call `fetch` directly.
- Relative `/api` URLs only; `VITE_API_MODE=live` at every checkpoint and for the demo; `mock` must not be the default.
- Customer: no login; `X-Conversation-Id` from `getConversationId()` on agent calls and on `POST /api/orders`; idempotency key per checkout attempt.
- Admin token in `sessionStorage["biblio.admin"]`; any 401 → back to login.
- Colours/fonts/radii/spacing only from `src/styles/tokens.css` (values from `DESIGN.md` frontmatter).
- Orb state only from the latest `agent_state` event (`docs/api-contracts.md §6`); no timer-driven fake states.
- Every screen has loading, empty, error and (chat) degraded states; `lang="vi"`; reduced motion respected.
- `pnpm test --run` green before every commit.

## Review Focus

1. Double tap on **Đặt món** / **Xác nhận đặt món** → one request in flight (button disabled) and the same idempotency key reused on retry — `checkout.test.tsx`, `DraftSlip.test.tsx`.
2. `409 PRICE_CHANGED` → the sheet/slip shows `details.quote` totals and asks again, never submits silently — same tests.
3. SSE chunks split mid-line or mid-JSON → no lost/duplicated events — `sse.test.ts`.
4. Backend/agent down → chat banner `MODEL_UNAVAILABLE`, menu and cart still usable — `chatReducer.test.ts` + manual C4 check.
5. Two admin tabs → `409 STATUS_CONFLICT` toast + refetch — `OrdersBoard.test.tsx`.

---

## File map

```
frontend/index.html · admin.html · vite.config.ts · package.json · .env.example (VITE_API_MODE=live)
frontend/src/styles/{tokens.css, base.css}
frontend/src/api/{types.ts, client.ts, request.ts, sse.ts, conversation.ts, liveClient.ts, mockClient.ts, index.ts}
frontend/src/lib/{format.ts, fold.ts, cart.ts, idempotency.ts}
frontend/src/test/{mockApi.ts, setup.ts}
frontend/src/ui/{Button.tsx, Chip.tsx, Sheet.tsx, Badge.tsx, Toast.tsx, Skeleton.tsx, AgentOrb.tsx, OrderSlip.tsx}
frontend/src/customer/{main.tsx, App.tsx}
frontend/src/customer/screens/{Discover.tsx, Menu.tsx, ItemSheet.tsx, Cart.tsx, ConfirmSheet.tsx, OrderTracking.tsx}
frontend/src/customer/chat/{ChatPanel.tsx, MessageList.tsx, ToolChips.tsx, DraftSlip.tsx, OrderCard.tsx, Composer.tsx}
frontend/src/customer/state/{useCart.ts, useOrderStream.ts, chatReducer.ts, useChat.ts}
frontend/src/admin/{main.tsx, App.tsx}
frontend/src/admin/screens/{Login.tsx, OrdersBoard.tsx, ReasonDialog.tsx, MenuAvailability.tsx, Insights.tsx}
frontend/src/admin/state/{useAdminAuth.ts, useAdminStream.ts}
frontend/e2e/demo.spec.ts (P1)
```

---

### Task B1: Scaffold, design tokens, typed API layer (0:00–1:00)

**Files:** scaffold `frontend/`; create everything under `src/styles`, `src/api`, `src/lib`; tests `src/api/sse.test.ts`, `src/lib/format.test.ts`, `src/lib/fold.test.ts`, `src/lib/cart.test.ts`.

**Interfaces (produced, used by B2–B5):**
- `ApiClient` and `ApiError` exactly as `docs/api-contracts.md §10`; `export const api: ApiClient` from `src/api/index.ts`.
- `request<T>(path: string, init?: RequestInit & { idempotencyKey?: string; adminToken?: string }) -> Promise<T>` — throws `ApiError(status, body.error.code, body.error.message, body.error.details)`.
- `readSse(response: Response, onEvent: (name: string, data: unknown) => void): Promise<void>`; `parseSseText(text: string): {event: string; data: unknown}[]` (same parser over a string; used by mock replay and tests).
- `getConversationId(): string` (32 hex, persisted in `localStorage["biblio.conversation"]`), `resetConversation(): string`.
- `formatVnd(n: number): string` ("45.000đ"), `formatTime(iso: string): string` ("16:05", UTC+7), `foldVi(s: string): string`.
- `type CartLine = { key: string; item_id: string; variant_id: string | null; name: string; variant_label: string | null; unit_price_vnd: number; quantity: number; note: string | null }`;
  `cartReducer(state: CartLine[], action: CartAction): CartLine[]` with actions `add | setQty | remove | clear`; `toLineInputs(lines: CartLine[]): CartLineInput[]`; `MAX_LINES = 10`, `MAX_QTY = 10`.
- `newIdempotencyKey(): string` (`crypto.randomUUID()`).

- [ ] **Step 1: Scaffold** (repo root): `pnpm create vite@latest frontend --template react-ts` (answer "No" to optional experimental prompts) → `cd frontend; pnpm install; pnpm add gsap@3.15.1 @gsap/react@2.1.2 thinking-orbs@0.3.2 @fontsource/fraunces @fontsource/be-vietnam-pro; pnpm add -D vitest jsdom @testing-library/react @testing-library/jest-dom`. Record resolved versions in `PROGRESS.md`.
- [ ] **Step 2: Config** — `vite.config.ts`: `build.rollupOptions.input = { main: "index.html", admin: "admin.html" }`; `server.proxy = { "/api": { target: "http://localhost:8000", changeOrigin: true } }`; `server.fs.allow = [".."]` (fixtures live in `../contracts/fixtures`); `test = { environment: "jsdom", globals: true }`. `index.html`/`admin.html`: `<html lang="vi">`, mount `#root`, scripts `src/customer/main.tsx` / `src/admin/main.tsx`. `package.json` script `"test": "vitest"`. `frontend/.env.example`: `VITE_API_MODE=live`.
- [ ] **Step 3: Write failing tests**

```ts
// src/api/sse.test.ts
import { describe, expect, it } from "vitest";
import { parseSseText, readSse } from "./sse";
import transcript from "../../../contracts/fixtures/agent_stream.sse?raw";

describe("sse", () => {
  it("parses the agent transcript fixture", () => {
    const events = parseSseText(transcript);
    expect(events).toHaveLength(35);
    expect(events[0].event).toBe("run_started");
    expect(events.filter((e) => e.event === "order_draft")).toHaveLength(1);
  });
  it("handles chunks split mid-line and comments", async () => {
    const parts = [': ping\n\nevent: text_de', 'lta\ndata: {"delta":"Xin ', 'chào"}\n\n'];
    const body = new ReadableStream({ start(c) { parts.forEach((p) => c.enqueue(new TextEncoder().encode(p))); c.close(); } });
    const got: [string, unknown][] = [];
    await readSse(new Response(body), (n, d) => got.push([n, d]));
    expect(got).toEqual([["text_delta", { delta: "Xin chào" }]]);
  });
});
```
```ts
// src/lib/format.test.ts + fold.test.ts
expect(formatVnd(45000)).toBe("45.000đ"); expect(formatVnd(1100000)).toBe("1.100.000đ");
expect(formatTime("2026-11-14T09:05:00.000Z")).toBe("16:05");
expect(foldVi("Trà thạch ĐÀO")).toBe("tra thach dao");
```
```ts
// src/lib/cart.test.ts
const bacXiu = { item_id: "menu_002", variant_id: null, name: "Bạc xỉu", variant_label: null, unit_price_vnd: 45000, quantity: 1, note: null };
it("merges same item+variant+note and caps quantity", () => {
  let s = cartReducer([], { type: "add", line: bacXiu });
  s = cartReducer(s, { type: "add", line: { ...bacXiu, quantity: 12 } });
  expect(s).toHaveLength(1); expect(s[0].quantity).toBe(10);
});
it("keeps different notes as separate lines and limits to 10 lines", () => {
  let s: CartLine[] = [];
  for (let i = 0; i < 11; i++) s = cartReducer(s, { type: "add", line: { ...bacXiu, note: `n${i}` } });
  expect(s).toHaveLength(10);
  expect(toLineInputs(s)[0]).toEqual({ item_id: "menu_002", variant_id: null, quantity: 1, note: "n0" });
});
```
- [ ] **Step 4: Run** `pnpm test --run` → FAIL. **Step 5: Implement**: `tokens.css` from `DESIGN.md` frontmatter (CSS variables), `base.css` (font imports `@fontsource/be-vietnam-pro/{400,500,600}.css`, `@fontsource/fraunces/600.css`; body on cream-page; focus ring); `types.ts` verbatim; `request.ts`; `sse.ts`; `liveClient.ts` (every method of §10; `chat` posts with `X-Conversation-Id` and reads SSE; `streamOrder`/`admin.stream` likewise); `mockClient.ts` (imports `contracts/fixtures/*.json`; `chat()` replays the next turn of `agent_stream.sse` with 40 ms between events; `confirmDraft` returns `order_from_draft.json`; admin methods use `admin_orders.json`); `index.ts` picks by `import.meta.env.VITE_API_MODE` (default `live`).
- [ ] **Step 6: Run** `pnpm test --run` → PASS; `pnpm build` → no type errors.
- [ ] **Step 7: Commit** `git add frontend && git commit -m "feat(frontend): scaffold, design tokens, typed API client, SSE parser, cart"`

**Acceptance:** C1 — with backend up and `VITE_API_MODE=live`, `api.getMenu()` returns 51 items in the browser console.

---

### Task B2: Customer shell, Discover, Menu, Cart checkout (1:00–2:00)

**Files:** `src/customer/{main,App}.tsx`, `src/ui/{Button,Chip,Sheet,Badge,Skeleton,Toast,OrderSlip}.tsx`, `screens/{Discover,Menu,ItemSheet,Cart,ConfirmSheet}.tsx`, `state/useCart.ts`, `src/test/mockApi.ts` (`mockApiWith(opts: { soldOut?: string[] }): ApiClient` — `mockClient` with a cloned fixture menu whose listed items have `availability: "sold_out"`), `src/test/setup.ts` (`import "@testing-library/jest-dom/vitest"`; add `test.setupFiles` in `vite.config.ts`; `pnpm add -D @testing-library/user-event`); tests `screens/Menu.test.tsx`, `screens/checkout.test.tsx`.

**Interfaces:**
- Consumes B1 `api`, `cartReducer`, `formatVnd`, `foldVi`, `newIdempotencyKey`.
- Produces: `useCart(): { lines, add, setQty, remove, clear, count, totalEstimateVnd }` (persists `localStorage["biblio.cart"]`); `App` tab state `"discover" | "menu" | "chat" | "cart"`, order view when `?order=CODE` (B3 renders it); `openOrder(code: string)` navigates via `history.pushState`.

- [ ] **Step 1: Failing tests**

```tsx
// screens/Menu.test.tsx (uses mockClient data through the real component)
it("filters diacritic-insensitively and disables sold-out items", async () => {
  render(<Menu api={mockApiWith({ soldOut: ["menu_014"] })} onAdd={vi.fn()} />);
  await userEvent.type(await screen.findByRole("searchbox", { name: "Tìm món" }), "tra dao");
  expect(screen.getByText("Trà thạch đào")).toBeInTheDocument();
  expect(screen.getByText("Trà đào cam sả")).toBeInTheDocument();
  expect(screen.queryByText("Bạc xỉu")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Trà thạch đào/ })).toHaveAttribute("aria-disabled", "true");
});
```
```tsx
// screens/checkout.test.tsx
it("re-asks on PRICE_CHANGED and reuses the idempotency key", async () => {
  const createOrder = vi.fn()
    .mockRejectedValueOnce(new ApiError(409, "PRICE_CHANGED", "Giá đã thay đổi", { quote: { ...quote, total_vnd: 120000 } }))
    .mockResolvedValueOnce(order);
  render(<ConfirmSheet api={{ ...mockClient, createOrder }} lines={lines} onDone={vi.fn()} />);
  await userEvent.click(await screen.findByRole("button", { name: "Đặt món" }));
  expect(await screen.findByText("120.000đ")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Đặt món" }));
  expect(createOrder.mock.calls[0][1]).toBe(createOrder.mock.calls[1][1]);            // same Idempotency-Key
  expect(createOrder.mock.calls[1][0].expected_total_vnd).toBe(120000);
});
```
(`quote`, `order` = `contracts/fixtures/quote.json`, `order.json`; components accept an optional `api` prop defaulting to `api` for testability.)
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** per `docs/ui-ux-spec.md §1` (Discover masthead, highlights, rating, data notice; Menu tabs/search/price chips/rows with dotted leaders, availability badges, ItemSheet with variant radio + qty + note; Cart lines + name/table/note; ConfirmSheet: on open `api.quote(...)` + `newIdempotencyKey()`, button disabled while pending, handles 409/422 per spec, on success `clear()` + `openOrder(code)`).
- [ ] **Step 4: Run** `pnpm test --run` → PASS. **Step 5: C1/C2 manual** with live backend: order `BB-0001` created. **Step 6: Commit** `git commit -m "feat(customer): discover, menu, cart checkout with server quote"`

---

### Task B3: Order tracking and admin app (2:00–3:00)

**Files:** `src/customer/screens/OrderTracking.tsx`, `src/customer/state/useOrderStream.ts`, `src/admin/{main,App}.tsx`, `src/admin/screens/{Login,OrdersBoard,ReasonDialog}.tsx`, `src/admin/state/{useAdminAuth,useAdminStream}.ts`; tests `admin/screens/OrdersBoard.test.tsx`, `customer/state/useOrderStream.test.ts`.

**Interfaces:**
- `useOrderStream(code: string): { order: Order | null; live: boolean; error: ApiError | null }` — `api.streamOrder`, on failure poll `api.getOrder` every 5 s.
- `useAdminAuth(): { token: string | null; login(pin): Promise<void>; logout(): void }`; `useAdminStream(token): { orders: Order[]; counts; live: boolean; refetch(): Promise<void> }` — merges `order_created/order_updated` by `id`; on failure poll every 3 s.
- `STATUS_ACTION_LABEL: Record<OrderStatus, string>` = confirmed "Nhận đơn", preparing "Đang pha", ready "Sẵn sàng", completed "Hoàn tất", rejected "Từ chối", cancelled "Hủy".

- [ ] **Step 1: Failing tests**

```tsx
// admin/screens/OrdersBoard.test.tsx
it("renders columns and only allowed actions; reject needs a reason", async () => {
  render(<OrdersBoard orders={adminOrders.orders} onTransition={onTransition} />);
  const pending = screen.getByRole("region", { name: "Mới" });
  expect(within(pending).getByText("BB-0002")).toBeInTheDocument();
  expect(within(pending).getAllByRole("button").map((b) => b.textContent)).toEqual(["Nhận đơn", "Từ chối", "Hủy"]);
  await userEvent.click(within(pending).getByRole("button", { name: "Từ chối" }));
  await userEvent.click(screen.getByRole("button", { name: "Xác nhận từ chối" }));
  expect(onTransition).not.toHaveBeenCalled();                              // reason < 3 chars
  await userEvent.type(screen.getByLabelText("Lý do"), "Hết nguyên liệu");
  await userEvent.click(screen.getByRole("button", { name: "Xác nhận từ chối" }));
  expect(onTransition).toHaveBeenCalledWith(2, { to_status: "rejected", expected_status: "pending", reason: "Hết nguyên liệu" });
});
it("shows a conflict toast on 409 STATUS_CONFLICT", async () => { /* onTransition rejects ApiError(409,"STATUS_CONFLICT") → toast "Đơn đã được cập nhật ở nơi khác" */ });
```
```ts
// customer/state/useOrderStream.test.ts — streamOrder rejects → falls back to polling getOrder (vi.useFakeTimers, advance 5000 ms, expect getOrder called)
```
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** per `docs/ui-ux-spec.md §1 (Đơn)` and `§2` (columns pending/confirmed/preparing/ready + "Đã xong"; slips with `aria-live` announcement for new orders; connection dot live/polling; PIN login with 401/429 messages).
- [ ] **Step 4: Run** → PASS. **Step 5: C3 manual**: admin confirms `BB-0001`; customer page shows "Quán đã nhận đơn" ≤ 2 s. **Step 6: Commit** `git commit -m "feat(admin): PIN login, live order board, transitions; feat(customer): live order tracking"`

---

### Task B4: AI chat panel with Thinking Orb and draft confirmation (3:00–4:00)

**Files:** `src/customer/state/{chatReducer,useChat}.ts`, `src/ui/AgentOrb.tsx`, `src/customer/chat/{ChatPanel,MessageList,ToolChips,DraftSlip,OrderCard,Composer}.tsx`; tests `state/chatReducer.test.ts`, `chat/DraftSlip.test.tsx`, `ui/AgentOrb.test.tsx`.

**Interfaces:**
- `type ChatState = { messages: { id: string; role: "user" | "assistant"; text: string; sources: SourceRef[] }[]; streamingText: string; agentState: AgentState; tools: Record<string, { tool: string; label: string; status: "running" | "ok" | "error"; summary?: string }>; drafts: Record<string, { draft: OrderDraft; status: "open" | "confirming" | "confirmed" | "discarded" | "expired"; order?: Order; notice?: string }>; error: { code: string; message: string } | null; busy: boolean }`
- `chatReducer(state: ChatState, action: AgentStreamEvent | { event: "user_message"; data: { text: string } } | { event: "draft_update"; data: {...} }): ChatState`; `initialChatState`.
- `ORB_STATE: Record<AgentState, "breathing" | "connecting" | "searching" | "working" | "composing">` and `ORB_LABEL: Record<AgentState, string>` per `docs/api-contracts.md §6`.
- `useChat(): { state; send(text: string): void; confirmDraft(id): Promise<void>; discardDraft(id): Promise<void>; newConversation(): void }`.

- [ ] **Step 1: Failing tests**

```ts
// state/chatReducer.test.ts
import transcript from "../../../../contracts/fixtures/agent_stream.sse?raw";
it("replays the fixture transcript into UI state", () => {
  const s = parseSseText(transcript).reduce((st, e) => chatReducer(st, e as AgentStreamEvent), initialChatState);
  expect(s.agentState).toBe("idle");
  expect(s.messages.filter((m) => m.role === "assistant")).toHaveLength(3);
  const [d] = Object.values(s.drafts);
  expect(d.draft.quote.total_vnd).toBe(45000); expect(d.status).toBe("open");
  expect(Object.values(s.tools).map((t) => t.status)).toEqual(["ok", "ok", "ok"]);
});
it("maps error events to the degraded banner", () => {
  const s = chatReducer(initialChatState, { event: "error", data: { code: "MODEL_UNAVAILABLE", message: "Trợ lý tạm thời không khả dụng — bạn vẫn có thể đặt món từ Menu.", retryable: true } });
  expect(s.agentState).toBe("error"); expect(s.error?.code).toBe("MODEL_UNAVAILABLE");
});
```
```tsx
// chat/DraftSlip.test.tsx — click "Xác nhận đặt món" twice quickly → confirmDraft called once; 409 PRICE_CHANGED → shows new total + "Giá vừa thay đổi"; 410 → "Đơn nháp đã hết hạn"; success → OrderCard with "BB-0002".
// ui/AgentOrb.test.tsx — vi.mock("thinking-orbs", () => ({ ThinkingOrb: (p: any) => <div data-testid="orb" data-state={p.state} aria-label={p["aria-label"]} /> }));
//   render <AgentOrb state="searching" /> → data-state "searching", aria-label "Đang tra cứu"; state "working" → "working".
```
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement**: `useChat.send` dispatches `user_message`, then `api.chat(text, dispatch, abort.signal)`; composer disabled while `busy`; `ChatPanel` = bottom sheet on mobile, 400 px right column at ≥1024 px (menu stays usable); `AgentOrb` wraps `ThinkingOrb` (`size={64}`, `theme="light"`, `paused` when `error`); `ToolChips` show 20 px orb while running; `DraftSlip` uses `OrderSlip` + warnings + **Xác nhận đặt món**/**Bỏ qua** (disabled while confirming) and renders `OrderCard` (link `?order=CODE`) after success; `aria-live="polite"` region announces `message_completed`.
- [ ] **Step 4: Run** `pnpm test --run` → PASS (mock replay works without backend). **Step 5: C4 manual (live)**: demo steps 2–9 of `docs/demo-runbook.md`. **Step 6: Commit** `git commit -m "feat(chat): streaming concierge with real agent states, tool chips, draft confirmation"`

---

### Task B5: States, admin menu availability, motion, Impeccable pass, E2E (4:00–5:00)

- [ ] **Degraded & error states** (P0): `/api/health` failure → full-screen retry; chat banner with **Mở Menu**; empty cart; admin empty columns. Test: `App.test.tsx` renders the fallback when `getCafe` rejects.
- [ ] **Admin Menu availability** (P1, first): `admin/screens/MenuAvailability.tsx` — 51 rows grouped by category, segmented Còn/Hết/Chưa xác nhận → `api.admin.updateMenuItem(id, { availability })`, orderable toggle. Test: changing to "Hết" calls `updateMenuItem("menu_019", { availability: "sold_out" })`.
- [ ] **Motion** (P1): `useGSAP` for tab transitions (180 ms), masthead stagger (once), cart badge bump, chat panel open (260 ms), admin new-slip highlight (1.2 s); all inside `gsap.matchMedia()` with a reduced-motion branch that only `gsap.set`s end states.
- [ ] **Impeccable** (P1, only if C4 passed): `/impeccable critique frontend/src/customer` → fix the top 3 findings; `/impeccable audit frontend/src` → fix a11y/contrast issues; optional `/impeccable polish`. Then `/impeccable document` (scan mode) to refresh `DESIGN.md` only if the owner agrees (it must not silently overwrite).
- [ ] **Tổng quan** (P1, after A6 insights): `admin/screens/Insights.tsx` renders `AdminInsights` (orders by status, top 5 items, agent runs/tool calls/tokens) as plain tables — no chart library.
- [ ] **Playwright smoke** (P1): `pnpm add -D @playwright/test; pnpm exec playwright install chromium`; `e2e/demo.spec.ts`: open `/`, add "Bạc xỉu", checkout → order page shows `BB-`; open `/admin.html`, log in with `process.env.E2E_ADMIN_PIN`, click "Nhận đơn" → customer page shows "Quán đã nhận đơn". Run `pnpm exec playwright test` with backend + `pnpm dev` running.
- [ ] **Rehearsal** C5 with Dev A; update `TASKS.md`/`PROGRESS.md`; commit per item (`feat(admin): menu availability`, `feat(ui): purposeful motion with reduced-motion support`, `test(e2e): demo smoke`).
