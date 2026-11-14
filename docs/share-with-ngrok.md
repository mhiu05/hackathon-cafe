# Chia sẻ demo cho giám khảo bằng ngrok

Một tunnel duy nhất trỏ vào frontend đã build (`vite preview`, cổng 4173). Vite proxy `/api` sang backend `127.0.0.1:8000`,
nên giám khảo chỉ cần **một link**; chat (SSE), đơn hàng realtime và trang Quầy đều đi qua cùng origin.

```
Giám khảo ──https──▶ ngrok ──▶ 127.0.0.1:4173 (vite preview) ──/api──▶ 127.0.0.1:8000 (FastAPI + agent)
```

## Cài đặt một lần

1. Cài ngrok: `winget install ngrok.ngrok` (hoặc tải ở https://ngrok.com/download).
2. Lấy authtoken ở https://dashboard.ngrok.com/get-started/your-authtoken rồi tự chạy:
   `ngrok config add-authtoken <TOKEN_CỦA_BẠN>` — không dán token vào chat, không commit.
3. (Nên làm) Lấy **domain tĩnh miễn phí** ở https://dashboard.ngrok.com/domains để link không đổi mỗi lần chạy lại.
4. `.env` phải có `OPENAI_API_KEY` và `ADMIN_PIN` (≥ 6 ký tự) — PIN này gửi riêng cho giám khảo để vào trang Quầy.

## Mỗi lần chia sẻ

Tắt các server đang chạy ở cổng 8000/5173/4173 (Ctrl+C), rồi ở thư mục gốc repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/share/start-share.ps1 -Domain ten-cua-ban.ngrok-free.app -ResetDemo
```

- `-Domain`: domain tĩnh (bỏ qua thì ngrok cấp link ngẫu nhiên).
- `-ResetDemo`: sao lưu rồi xóa đơn/chat demo cũ trước khi chia sẻ.
- `-SkipBuild`: dùng lại `frontend/dist` đã build.

Script kiểm tra điều kiện, build frontend, mở 2 cửa sổ (backend, preview), chờ cả hai phản hồi rồi chạy ngrok.
Gửi giám khảo:

| Trang | Link |
|---|---|
| Khách (menu, chat Biblio) | `https://<domain>/` |
| Quầy (đơn, yêu cầu gọi nhân viên) | `https://<domain>/admin.html` + PIN |

Gói free của ngrok hiện trang cảnh báo ở lần mở đầu — giám khảo bấm **Visit Site**. Nhấn Ctrl+C ở cửa sổ ngrok để dừng;
backend và preview tự tắt theo.

## Code đã chỉnh cho việc này

- `frontend/vite.config.ts`: `preview` có proxy `/api` + `allowedHosts` cho tên miền ngrok (thiếu thì Vite trả "Blocked request");
  proxy bật `xfwd` để giữ IP thật của giám khảo.
- Backend chạy với `--proxy-headers --forwarded-allow-ips 127.0.0.1`: giới hạn sai PIN tính theo IP từng người,
  không khóa chung mọi người (đã kiểm: IP A bị khóa sau 5 lần sai, IP B vẫn đăng nhập được).
- `frontend/src/api/request.ts`: gửi header `ngrok-skip-browser-warning` cho mọi lời gọi API.

## Lưu ý

- Máy bạn phải bật và giữ script chạy suốt buổi chấm; tắt máy/ngủ máy là link chết.
- Ai có link đều dùng được chat → tốn token OpenAI. Mỗi cuộc trò chuyện bị giới hạn 20 tin/phút; chỉ gửi link cho giám khảo.
- Tất cả giám khảo dùng chung một tài khoản khách (theo thiết kế), nhưng mỗi trình duyệt có cuộc trò chuyện riêng.
