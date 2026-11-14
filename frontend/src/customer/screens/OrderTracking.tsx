import type { ApiClient } from '../../api/client';
import { useOrderStream } from '../state/useOrderStream';
import { formatDate, formatTime } from '../../lib/format';
import { OrderSlip } from '../../ui/OrderSlip';
import { Skeleton } from '../../ui/Skeleton';
const steps = [['pending', 'Chờ xác nhận'], ['confirmed', 'Đã nhận'], ['preparing', 'Đang pha'], ['ready', 'Sẵn sàng'], ['completed', 'Hoàn tất']] as const;
export function OrderTracking({ code, api }: { code: string; api?: ApiClient }) {
  const { order, live, error } = useOrderStream(code, api);
  if (!order) return <section className="content-section">{error ? <><h1 className="screen-heading">Chưa tải được đơn</h1><p role="alert">{error.message}</p><button onClick={() => location.reload()}>Thử lại</button></> : <Skeleton label="Đang tìm đơn của bạn…" />}</section>;
  const current = steps.findIndex(([s]) => s === order.status);
  return <section className="content-section"><h1 className="screen-heading">Đơn {order.code}</h1><p className="connection-status"><span className={`dot ${live ? 'success' : ''}`} />{live ? 'Đang cập nhật trực tiếp' : 'Tự cập nhật mỗi 5 giây'}</p>{error && <p className="warning" role="alert">{error.message}</p>}
    <h2 className={order.status === 'rejected' || order.status === 'cancelled' ? 'danger' : ''} aria-live="polite">{order.status_label}</h2>
    {current >= 0 && <ol className="status-steps" aria-label="Tiến trình đơn">{steps.map(([s, label], index) => <li key={s} className={index <= current ? 'reached' : ''} aria-current={s === order.status ? 'step' : undefined}>{label}</li>)}</ol>}
    {order.status_reason && <p className="danger">Lý do: {order.status_reason}</p>}<OrderSlip order={order} />
    {(order.customer_name || order.table_label) && <p>{[order.customer_name, order.table_label].filter(Boolean).join(' · ')}</p>}{order.note && <p>Ghi chú: {order.note}</p>}<p>Thanh toán tại quầy.</p>
    <h2>Lịch sử đơn</h2><ol className="order-timeline">{order.events.map((e, i) => <li key={i}><time dateTime={e.created_at}>{formatTime(e.created_at)} · {formatDate(e.created_at)}</time><span>{steps.find(([s]) => s === e.to_status)?.[1] ?? (e.to_status === 'rejected' ? 'Từ chối' : 'Đã hủy')}{e.note ? ` — ${e.note}` : ''}</span></li>)}</ol>
  </section>;
}
