import { useRef, useState } from 'react';
import { ApiError } from '../../api/client';
import type { Order, OrderStatus, UpdateOrderStatusRequest } from '../../api/types';
import { formatTime, formatVnd } from '../../lib/format';
import { OrderSlip } from '../../ui/OrderSlip';
import { Toast } from '../../ui/Toast';
import { ReasonDialog } from './ReasonDialog';
import { OrderTile } from './OrderTile';
export const STATUS_ACTION_LABEL: Record<OrderStatus, string> = { pending: 'Chờ xác nhận', confirmed: 'Nhận đơn', preparing: 'Đang pha', ready: 'Sẵn sàng', completed: 'Hoàn tất', rejected: 'Từ chối', cancelled: 'Hủy' };
const columns = [['pending', 'Mới'], ['confirmed', 'Đã nhận'], ['preparing', 'Đang pha'], ['ready', 'Sẵn sàng']] as const;
export function OrdersBoard({ orders, onTransition, onRefresh }: { orders: Order[]; onTransition: (id: number, req: UpdateOrderStatusRequest) => Promise<unknown>; onRefresh?: () => unknown }) {
  const [pending, setPending] = useState<number | null>(null), [notice, setNotice] = useState(''), [reason, setReason] = useState<{ order: Order; status: 'rejected' | 'cancelled' } | null>(null); const locks = useRef(new Set<number>());
  async function transition(order: Order, status: OrderStatus, text?: string) {
    if (locks.current.has(order.id)) return; locks.current.add(order.id); setPending(order.id); setNotice('');
    try { await onTransition(order.id, { to_status: status, expected_status: order.status, ...(text ? { reason: text } : {}) }); setReason(null); }
    catch (e) { if (e instanceof ApiError && e.code === 'STATUS_CONFLICT') { setNotice('Đơn đã được cập nhật ở nơi khác'); setReason(null); void onRefresh?.(); } else setNotice(e instanceof Error ? e.message : 'Chưa cập nhật được đơn. Vui lòng thử lại.'); }
    finally { locks.current.delete(order.id); setPending(null); }
  }
  const slip = (order: Order) => <OrderTile key={order.id}><div className="price-row"><h3>{order.code}</h3><time dateTime={order.created_at}>{formatTime(order.created_at)}</time></div><small>{order.source === 'agent_draft' ? 'Trợ lý' : 'Giỏ hàng'} · <span className="price">{formatVnd(order.total_vnd)}</span></small><p>{[order.table_label, order.customer_name].filter(Boolean).join(' · ') || 'Nhận tại quầy'}</p><OrderSlip order={order} />{order.note && <p>Ghi chú: {order.note}</p>}{order.status_reason && <p className="danger">{order.status_reason}</p>}<div className="actions">{(order.allowed_next ?? []).map(status => <button className={status === 'rejected' || status === 'cancelled' ? 'button-danger' : 'button-primary'} key={status} disabled={pending === order.id} onClick={() => { if (status === 'rejected' || status === 'cancelled') setReason({ order, status }); else void transition(order, status); }}>{STATUS_ACTION_LABEL[status]}</button>)}</div></OrderTile>;
  const finished = orders.filter(o => ['completed', 'rejected', 'cancelled'].includes(o.status));
  return <>{notice && <Toast message={notice} />}<div className="orders-board">{columns.map(([status, label]) => <section className="order-column" role="region" aria-label={label} key={status}><h2>{label} <small>{orders.filter(o => o.status === status).length}</small></h2>{orders.filter(o => o.status === status).map(slip)}{!orders.some(o => o.status === status) && <p className="empty-column">Chưa có đơn</p>}</section>)}</div><details className="finished-orders"><summary>Đã xong · {finished.length}</summary><div className="finished-grid">{finished.map(slip)}</div></details>{reason && <ReasonDialog rejecting={reason.status === 'rejected'} pending={pending === reason.order.id} onClose={() => setReason(null)} onSubmit={text => void transition(reason.order, reason.status, text)} />}</>;
}
