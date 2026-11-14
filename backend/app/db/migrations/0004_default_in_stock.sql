-- 0004_default_in_stock: owner decision (2026-11-14) — every menu item is in stock by default.
-- Staff still mark items sold out (or "chưa xác nhận") in Admin → Menu; this only flips the seeded 'unknown' state once.

UPDATE menu_items
SET availability = 'available',
    availability_note = NULL
WHERE availability = 'unknown';
