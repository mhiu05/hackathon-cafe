import type { Availability } from '../api/types';
// In stock is the default (owner decision 2026-11-14): only exceptions get a badge.
export function Badge({ availability, orderable = true }: { availability: Availability; orderable?: boolean }) {
  if (orderable && availability === 'available') return null;
  return <span className={`badge ${!orderable || availability === 'sold_out' ? 'danger' : 'warning'}`}>{!orderable ? 'Tạm ngưng' : availability === 'sold_out' ? 'Hết' : 'Chưa chắc còn món'}</span>;
}
