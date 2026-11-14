from __future__ import annotations

STATUS_LABELS = {
    "pending": "Chờ quán xác nhận", "confirmed": "Quán đã nhận đơn", "preparing": "Đang pha chế",
    "ready": "Sẵn sàng — mời bạn nhận tại quầy", "completed": "Hoàn tất", "rejected": "Quán từ chối", "cancelled": "Đã hủy",
}
ALLOWED = {
    "pending": ("confirmed", "rejected", "cancelled"), "confirmed": ("preparing", "ready", "cancelled"),
    "preparing": ("ready", "cancelled"), "ready": ("completed",), "completed": (), "rejected": (), "cancelled": (),
}
REASON_REQUIRED = {"rejected", "cancelled"}


def allowed_next(status: str) -> list[str]:
    return list(ALLOWED.get(status, ()))
