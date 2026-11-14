import type { Availability } from '../api/types';
export function Badge({ availability, orderable = true }: { availability: Availability; orderable?: boolean }) {
  return <span className={`badge ${!orderable || availability === 'sold_out' ? 'danger' : availability === 'unknown' ? 'warning' : 'success'}`}>{!orderable ? 'Tạm ngưng' : availability === 'unknown' ? 'Chưa xác nhận còn món' : availability === 'sold_out' ? 'Hết' : 'Còn món'}</span>;
}
