# Demo Runbook — Biblio AI Café Companion

Commands marked **[verified]** were run in the pre-implementation session (2026-11-14). Commands marked **[planned]**
become valid once the implementation plan's tasks are done.

## 1. Before the hackathon day (once per laptop)

1. Install: `uv` (≥0.11), Node 24 + `pnpm` (≥11), Git. Python 3.12 is fetched by uv.
2. `git clone https://github.com/mhiu05/hackathon-cafe.git` and `cd` into it.
3. Create `.env` from `.env.example`; fill `OPENAI_API_KEY`, `VOYAGE_API_KEY`, `ADMIN_PIN` (≥6 chars; already set on the owner's laptop). `APIFY_API_TOKEN` is only needed to re-collect data.
4. **[verified]** `uv sync`
5. **[verified]** `uv run python scripts/knowledge/ingest.py --offline` — builds `data/cafe.db` from committed normalized data + embedding cache (no API calls).
6. **[verified]** `uv run python scripts/knowledge/verify.py --offline` — all checks PASS except vector eval (skipped offline).
7. **[verified]** `uv run pytest -q`.
8. **[planned]** `cd frontend && pnpm install`.

## 2. Ask the café (before the demo, 10 minutes with staff)

- Which items are available today → set them in Admin → Menu (P1) or leave "Chưa xác nhận" (honest default).
- Are the 14/11/2026 menu prices current? What does the X next to "Trà xoài Yakult" mean?
- Payment at counter? Table numbers or name pickup? (the UI supports both, both optional)
- Any upcoming event we may show? (none verified)
- Permission to mention them as "Biblio Café Sách 79 Ngụy Như Kon Tum" in the demo.

## 3. Start (demo laptop) **[planned]**

```powershell
# Terminal 1 — backend (single worker!)
uv run uvicorn app.main:app --port 8000
# Terminal 2 — frontend
cd frontend; pnpm dev            # http://localhost:5173 (customer), http://localhost:5173/admin.html (staff)
```
Health check: open `http://localhost:8000/api/health` → `{"status":"ok", "knowledge_chunks": 56, "model_configured": true, "admin_configured": true}`.

Window layout: left half = customer view in a phone-sized window (DevTools device mode 390×844); right half = admin tab.

## 4. Demo script (≈4 minutes)

| # | Who/where | Action | What the audience should see |
|---|---|---|---|
| 1 | Customer · Khám phá | open app | real name, address, "Đang mở 07:00–22:30", highlights with source stamps, rating 4,4 (14/11) |
| 2 | Customer · Trợ lý | "Quán có chỗ yên tĩnh ngồi học không? Wi-Fi thế nào?" | orb *searching*, chip "Tra cứu tri thức", answer citing Google Maps/reviews, Wi-Fi password → "hỏi nhân viên" |
| 3 | Customer · Trợ lý | "Mình muốn uống gì đó ít ngọt, không quá 50k. Gợi ý giúp mình rồi đặt một ly." | `recommend_drinks` chip; 2–3 items with SQL prices; honest "chưa có thông tin độ ngọt xác minh" |
| 4 | Customer · Trợ lý | "Lấy Trà chanh gừng mật ong nhé" | orb *working*, chip "Chuẩn bị đơn nháp"; **draft slip** with server total 45.000đ + availability warning; agent says "bấm Xác nhận đặt món", never "đã đặt" |
| 5 | Customer | tap **Xác nhận đặt món** | REST confirm → slip becomes order card **BB-0001** (tap twice: still one order) |
| 6 | Admin | (already logged in) | slip BB-0001 appears in "Mới" within ~1 s, highlighted |
| 7 | Admin | **Nhận đơn** → **Đang pha** → **Sẵn sàng** | buttons only show allowed transitions |
| 8 | Customer · Đơn | open order card | status stepper moves live to "Sẵn sàng — mời bạn nhận tại quầy" |
| 9 | Customer · Trợ lý | "Đơn của mình xong chưa?" | `get_order_status` chip; answer "Sẵn sàng" |
| 10 | Bonus | "Phòng nào cho 20 người, thứ Bảy còn trống không?" | Phòng 4, 770.000đ/4h; honest "không có dữ liệu phòng trống, gọi 0976 214 224" |

Talking points: tools are real SQL/RAG calls; prices never come from the model; the agent can only prepare a draft — the order
exists only after the customer's click; the knowledge base is branch-verified with 21 open questions for the owner; Apify spend
was $0.096. Customers share one pre-created account (owner decision for the demo); chat memory is per browser.

## 5. Contingencies

| Problem | Action |
|---|---|
| OpenAI down / slow | Show degraded mode: chat banner, then do steps 6–8 via Menu → Giỏ → Đặt món (same order pipeline). |
| Voyage down | Nothing to do: retrieval falls back to keyword search (answers still cite sources). |
| Admin SSE stalls | Page polls every 5 s; or press refresh. |
| Wrong state clicked | Admin can cancel with a reason; create a new order. |
| DB messed up | `uv run python scripts/demo/reset_demo.py` **[planned]** (keeps menu/knowledge, clears orders/sessions, backup first) |
| Total disaster | `del data\cafe.db*` then `uv run python scripts/knowledge/ingest.py --offline` **[verified]** |

## 6. Reset between runs **[planned]**

```powershell
# stop uvicorn first (Ctrl+C), then:
uv run python scripts/demo/reset_demo.py
uv run uvicorn app.main:app --port 8000
```
In the browser: clear `localStorage` for localhost:5173 (new conversation id → fresh chat memory) and log in to admin again.
