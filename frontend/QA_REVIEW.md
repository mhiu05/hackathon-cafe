# Review độc lập và đợt sửa cuối

Phạm vi review: `2b016a2..84d0310`, frontend B1–B5. Hai assessment chạy độc lập, không chia sẻ finding; A hoàn tất trước khi executor đọc báo cáo B.

- A: whole-branch code review + thiết kế, đọc tài liệu/code/tests và 6 ảnh Chromium. Không có Critical; disposition ban đầu **With fixes**. Nielsen ban đầu **27/40**.
- B: detector + audit kỹ thuật, đo Chromium ở 360/390/768/1024/1280 và chữ 200%. Điểm mẫu ban đầu **16/20**. Detector chạy đúng một lần, `[]`, 0 finding. Không có overlay; Playwright MCP bị môi trường chặn, CLI dùng được.
- Điểm trên là đánh giá trước sửa, không phải điểm chấm lại hay chứng nhận WCAG. Không yêu cầu review lặp; executor kiểm chứng material fixes bằng RED→GREEN và toàn suite theo executing-plans.

## Material fixes đã kiểm chứng

| Finding | Sửa | Bằng chứng |
|---|---|---|
| Đơn pending cũ bị đẩy khỏi 50 đơn mới nhất | Tải riêng từng trạng thái đang xử lý, limit 200 theo hợp đồng; dùng counts server, báo khi danh sách chưa đủ | useAdminStream.test: 1 pending cũ + 50 completed mới, RED→GREEN; OrdersBoard.test: counts/cảnh báo RED→GREEN |
| Desktop mở chat làm trắng nội dung chính | Giữ nguyên Menu/Discover/đơn và focus composer; resize mobile→desktop trả lại nội dung | Playwright desktop assistant regression RED→GREEN |
| 409 trả nhanh giữa hai click có thể tự nhận giá mới | Sau PRICE_CHANGED phải đánh dấu **Tôi đã xem giá mới**, rồi bấm xác nhận; giữ nguyên idempotency key | Cả checkout.test và DraftSlip.test đều tái hiện 2 POST trước sửa, 1 POST sau sửa; retry tổng mới/key giữ nguyên vẫn pass |
| Đóng chat từ masthead làm mất focus | Trả về màn trước và trigger còn hiển thị; fallback focus tab đang chọn | Playwright masthead/Escape RED→GREEN, nav/focus-trap regression vẫn pass |
| Viền ô nhập trống chỉ 1,36:1 | Semantic token control-border dùng muted-ink có sẵn | Border/Page **5,21:1**, giữ cream-line cho đường giấy trang trí; xem lại ảnh variant 390px |
| Link gọi điện/chỉ đường chưa đạt target 44px của brief | Mở rộng hit area, giữ cách trình bày chữ | CSS min-height từ control-height 44px; không đổi dữ liệu hoặc palette |

Kết quả sau sửa: **37 unit tests / 18 files passed**, production build passed, **8 Playwright fixture tests passed / 3 live specs skipped mặc định**. Lint exit 0, còn **10 advisory** React (effect reset, mixed component exports, epoch ref cleanup); reviewer không tìm thấy tác động vật chất chỉ từ các advisory này. Không tuyên bố lint không có cảnh báo.

## Deferred minors

- Thanh danh mục menu chưa sticky khi cuộn dài.
- Tên nguồn đầy đủ trên thẻ Khám phá hơi dài ở mobile; attribution/ngày vẫn đầy đủ.

## Rulings và giới hạn

- Hơn 200 đơn trong cùng trạng thái cần phân trang từ backend: frontend hiển thị counts/cảnh báo thiếu dữ liệu, không tự đổi frozen contract. Đây là giới hạn công suất đã báo rõ, không phải bảo đảm phục vụ danh sách không giới hạn.
- Phục hồi lịch sử chat/đơn nháp sau reload là P1 restore riêng, không phải phần B1–B5 bắt buộc. Conversation id vẫn giữ đúng contract để backend duy trì ngữ cảnh.
- C5 và combined-main được kiểm chứng riêng; snapshot không thay cho main đã tích hợp.
- Đánh giá lại focus và hit target thành material fix vì ảnh hưởng đường bàn phím và yêu cầu 44px của brief; các sửa CSS đơn giản được xác minh bằng render, không thêm test chỉ soi cấu trúc CSS.
- Không sửa DESIGN.md/PRODUCT.md, .gitignore, .agents, .claude hay backend. Không đổi API/schema; adapter insights và readiness ruling có trong IMPLEMENTATION_LOG.md.

Questions skipped: đây là nhiệm vụ thực thi đã được duyệt; các finding material được sửa trong phạm vi hiện tại, không yêu cầu thiết kế lại.
