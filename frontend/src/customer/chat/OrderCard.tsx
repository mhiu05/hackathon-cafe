import type { Order } from '../../api/types';
import { formatVnd } from '../../lib/format';
import type { ApiClient } from '../../api/client';
import { useOrderStream } from '../state/useOrderStream';
export function OrderCard({ order, api, onOpenOrder }: { order: Order; api?: ApiClient; onOpenOrder?: (code: string) => void }) {
  const stream = useOrderStream(order.code, api); const current = stream.order ?? order;
  return <article className="confirmed-order"><h3>{current.code}</h3><p aria-live="polite">{current.status_label}</p>{stream.error && <small className="warning">Đang kết nối lại để cập nhật trạng thái.</small>}<p className="price">{formatVnd(current.total_vnd)}</p><a href={`?order=${encodeURIComponent(current.code)}`} onClick={e => { if (onOpenOrder) { e.preventDefault(); onOpenOrder(current.code); } }}>Theo dõi đơn</a></article>;
}
