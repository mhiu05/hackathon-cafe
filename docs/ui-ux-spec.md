# UI/UX Spec — screens and states

Design system (tokens, typography, components, motion, do/don't): **[`/DESIGN.md`](../DESIGN.md)**. Product rules: `/PRD.md`.
Method: Impeccable (`.claude/skills/impeccable`) is a design process, not a component library. Build functional screens first;
only after the P0 loop passes run `/impeccable critique` → fix → `/impeccable audit` → `/impeccable polish` on
`frontend/src/customer` and `frontend/src/admin` (Dev B, hour 4–5).

## 1. Customer (mobile-first; ≥1024 px adds the 400 px chat column)

```
┌ Khám phá ─────────────────────┐   ┌ Menu ─────────────────────────┐   ┌ Trợ lý ────────────────────────┐
│ BIBLIO                         │   │ [Cà phê][Trà lạnh][Matcha]…→  │   │ (orb) Đang chuẩn bị đơn nháp   │
│ Café Sách                      │   │ Tìm món…   [≤35k][≤45k][≤55k] │   │ ────────────────────────────── │
│ ─────── (caramel rule)         │   │ CÀ PHÊ                         │   │ Bạn: ít ngọt, dưới 50k…        │
│ 79 Ngụy Như Kon Tum · Hacinco  │   │ Bạc xỉu ............ 45.000đ  │   │ ◌ Đang tìm món hợp ý  ✓ 3 gợi ý│
│ ● Đang mở · 07:00–22:30        │   │   Chưa xác nhận còn món        │   │ Biblio: Mình chưa có thông tin │
│ 0976 214 224                   │   │ Cà phê nâu / đen ... 35.000đ  │   │ độ ngọt đã xác minh…            │
│ [ Hỏi Biblio ]  [ Xem menu ]   │   │   Nâu · Đen                    │   │ ┌ ĐƠN NHÁP ─ ─ ─ ─ ─ ─ ─ ─ ┐  │
│ ┌ thẻ mục lục ┐┌ thẻ mục lục ┐ │   │ …                              │   │ │1× Trà chanh gừng  45.000đ │  │
│ │Hợp làm việc ││Phù hợp trẻ em│ │   │ Giá theo menu 14/11/2026 —     │   │ │Tổng              45.000đ  │  │
│ │laptop       ││              │ │   │ đang chờ quán xác nhận         │   │ │⚠ Quán chưa xác nhận còn món│  │
│ │Google Maps  ││Google Maps   │ │   │                    [Giỏ • 2]  │   │ │[Bỏ qua] [Xác nhận đặt món]│  │
│ └─────────────┘└──────────────┘ │   └────────────────────────────────┘   │ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │
│ ★ 4,4 · 178 đánh giá (14/11)   │                                        │ [ Nhập câu hỏi…        ] (➤)  │
└ [Khám phá][Menu][Trợ lý][Giỏ] ┘                                        └────────────────────────────────┘
```

- **Khám phá**: masthead (Teal Deep); open-now dot from `is_open_now`; address, phone (tap to call); highlights as index cards with
  source stamps; rating with date; co-working/rooms teaser from `/api/services` (P1); `data_notice` line at the bottom.
- **Menu**: sticky category tabs; search (client-side `fold` of name, diacritic-insensitive); price chips; rows with dotted leaders;
  tap → bottom sheet: variants (radio, required if any), quantity 1–10, note ≤120, **Thêm vào giỏ**; inferred tags only here, labelled
  "Gợi ý theo tên món". Badges: `unknown` → Muted "Chưa xác nhận còn món"; `sold_out` → strike + "Hết", add disabled;
  `is_orderable=false` → "Tạm ngưng", add disabled.
- **Trợ lý**: header orb 64 px + label; message list; tool chips (one per `tool_started`, resolved on `tool_finished`); **draft slip**
  for each `order_draft` (lines, total, warnings, expiry note "Đơn nháp giữ 30 phút"); **Xác nhận đặt món** → `confirmDraft(draft_id,
  quote.total_vnd)` → slip turns into an **order card** (code, status, "Theo dõi đơn"); `409 PRICE_CHANGED` → slip re-renders with
  `details.quote` and the notice "Giá vừa thay đổi, vui lòng xác nhận lại"; `410` → slip greyed "Đơn nháp đã hết hạn — nhắn lại để tạo mới";
  **Bỏ qua** → `discardDraft` and grey the slip. Composer: Enter sends, Shift+Enter newline, 1000-char limit, disabled while a run
  streams (`RUN_IN_PROGRESS` prevention). Error banner on `MODEL_UNAVAILABLE` with **Mở Menu**. "Cuộc trò chuyện mới" resets the
  conversation id (P1). Suggestion chips (P1): "Giờ mở cửa?", "Gợi ý món dưới 50k", "Phòng cho 20 người".
- **Giỏ hàng**: lines with stepper/remove; optional Tên (≤40), Bàn/khu vực (≤20), Ghi chú (≤200); **Xem tổng** → quote → confirm sheet
  (server lines, total, warnings) → **Đặt món** (`createOrder` with an idempotency key created when the sheet opens) → order page.
  `409 PRICE_CHANGED` → sheet shows the new quote and asks again. Empty state: "Giỏ đang trống — xem Menu hoặc hỏi Biblio".
- **Đơn** (`?order=BB-0001`, also reachable from order cards): status stepper Chờ xác nhận → Đã nhận → Đang pha → Sẵn sàng → Hoàn tất;
  timeline from `events`; rejected/cancelled shows `status_reason`; "Thanh toán tại quầy"; live via `streamOrder`, polling fallback 5 s.

## 2. Admin (desktop-first)

```
┌ Biblio · Quầy ──────────────── [Đơn hàng] [Menu] [Tổng quan] ─────── ● Trực tuyến  [Đăng xuất] ┐
│ MỚI (1)            │ ĐÃ NHẬN (1)        │ ĐANG PHA (0)       │ SẴN SÀNG (0)      │ Đã xong ▸ (0)    │
│ ┌ BB-0002 · 16:05 ┐│ ┌ BB-0001 · 16:00 ┐│                    │                   │                  │
│ │ Trợ lý · 45.000đ ││ │ Bàn 12 · Minh    ││                    │                   │                  │
│ │ 1× Trà chanh gừng││ │ 2× Cà phê (Đen)  ││                    │                   │                  │
│ │ [Nhận] [Từ chối] ││ │ [Đang pha][Sẵn sàng]                   │                   │                  │
│ └──────────────────┘│ └──────────────────┘│                    │                   │                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```
- **Đăng nhập**: one PIN field; 401 → "Mã PIN không đúng"; 429 → "Thử lại sau 1 phút"; token in `sessionStorage["biblio.admin"]`;
  any 401 later → back to login.
- **Đơn hàng**: columns pending/confirmed/preparing/ready; terminal statuses in a collapsible "Đã xong" list. Slip: code, local time,
  source (Giỏ hàng / Trợ lý), name/table, lines, total, note. Buttons = `allowed_next` (labels: confirmed "Nhận đơn", preparing
  "Đang pha", ready "Sẵn sàng", completed "Hoàn tất", rejected "Từ chối", cancelled "Hủy"). Reject/cancel opens a reason field
  (3–200 chars). New order → slip highlight + `role="status"` "Đơn mới BB-0002". `409` → toast "Đơn đã được cập nhật ở nơi khác" + refetch.
  Connection dot reflects the admin SSE (green live / amber polling).
- **Menu** (P1, first after P0): 51 items grouped by category; segmented control Còn / Hết / Chưa xác nhận; orderable toggle.
- **Tổng quan** (P1): orders by status, top items, agent runs, tool calls by tool, tokens.

## 3. States (every screen)

| State | Treatment |
|---|---|
| Loading | static skeleton rows (menu, board); buttons inline spinner + disabled |
| Empty | cart (above); admin column "Chưa có đơn"; chat first-run: greeting + 3 suggestion chips |
| Error | inline banner with **Thử lại** for API errors; toast for 409; full-screen fallback only if `/api/health` fails |
| Degraded (no model) | chat banner "Trợ lý tạm thời không khả dụng — bạn vẫn có thể đặt món từ Menu" |
| Offline backend | full-screen "Không kết nối được máy chủ" with retry |

## 4. Accessibility checklist

`lang="vi"` on both HTML entries; semantic buttons/links; focus ring per DESIGN.md; touch targets ≥44 px; text contrast ≥4.5:1;
`aria-live="polite"` announces each `message_completed` (not every delta) and new admin orders; draft slip heading receives focus
when it appears; Escape closes sheets; labelled form fields with `aria-describedby` errors; orb `aria-label` = state label;
reduced motion honoured by GSAP `matchMedia` and by `thinking-orbs` itself.

## 5. Frontend structure (Dev B)

```
frontend/index.html · admin.html · vite.config.ts (multi-page input; dev proxy '/api' → http://localhost:8000)
frontend/src/api/{types.ts, client.ts, liveClient.ts, mockClient.ts, sse.ts, conversation.ts, fixtures.ts}
frontend/src/lib/{format.ts, fold.ts, cart.ts, idempotency.ts}
frontend/src/styles/{tokens.css, base.css}
frontend/src/ui/{Button.tsx, Chip.tsx, Sheet.tsx, Badge.tsx, Toast.tsx, Skeleton.tsx, AgentOrb.tsx, OrderSlip.tsx}
frontend/src/customer/{main.tsx, App.tsx, screens/{Discover,Menu,Cart,OrderTracking}.tsx,
                       chat/{ChatPanel,MessageList,ToolChips,DraftSlip,OrderCard,Composer}.tsx,
                       state/{useChat.ts, chatReducer.ts, useCart.ts, useOrderStream.ts}}
frontend/src/admin/{main.tsx, App.tsx, screens/{Login,OrdersBoard,MenuAvailability,Insights}.tsx, state/{useAdminAuth.ts,useAdminStream.ts}}
```
