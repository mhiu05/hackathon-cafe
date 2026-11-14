import type { OrderQuote, Order } from '../api/types';
import { formatVnd } from '../lib/format';
export function OrderSlip({ order }: { order: OrderQuote | Order }) {
  return <div className="order-slip"><ul className="receipt-lines">{order.lines.map(line => <li key={line.line_no}><div className="price-row"><span>{line.quantity} × {line.item_name}{line.variant_label ? ` (${line.variant_label})` : ''}</span><span className="price">{formatVnd(line.line_total_vnd)}</span></div>{line.note && <small>{line.note}</small>}</li>)}</ul>
    <div className="price-row receipt-total"><strong>Tổng cộng</strong><strong className="price">{formatVnd(order.total_vnd)}</strong></div>
    {'warnings' in order && order.warnings.map(w => <p key={w.code} className="warning"><small>{w.message}</small></p>)}
  </div>;
}
