import type { Order } from '../../api/types';
import { formatVnd } from '../../lib/format';
export function OrderCard({ order, onOpenOrder }: { order: Order; onOpenOrder?: (code: string) => void }) {
  return <article className="confirmed-order"><h3>{order.code}</h3><p>{order.status_label}</p><p className="price">{formatVnd(order.total_vnd)}</p><a href={`?order=${encodeURIComponent(order.code)}`} onClick={e => { if (onOpenOrder) { e.preventDefault(); onOpenOrder(order.code); } }}>Theo dõi đơn</a></article>;
}
