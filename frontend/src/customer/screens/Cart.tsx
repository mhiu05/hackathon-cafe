import { useState } from 'react';
import type { ApiClient } from '../../api/client';
import type { Order } from '../../api/types';
import type { useCart } from '../state/useCart';
import { formatVnd } from '../../lib/format';
import { Button } from '../../ui/Button';
import { ConfirmSheet } from './ConfirmSheet';
export function Cart({ cart, api, onMenu, onDone }: { cart: ReturnType<typeof useCart>; api?: ApiClient; onMenu: () => void; onDone: (order: Order) => void }) {
  const [name, setName] = useState(''), [table, setTable] = useState(''), [note, setNote] = useState(''), [confirm, setConfirm] = useState(false);
  return <section className="content-section"><h1 className="screen-heading">Giỏ của bạn</h1>{!cart.lines.length ? <div className="empty-state"><h2>Giỏ đang trống</h2><p>Xem Menu hoặc hỏi Biblio để chọn món.</p><Button onClick={onMenu}>Mở Menu</Button></div> : <><ul className="cart-lines">{cart.lines.map(l => <li key={l.key}><div className="price-row"><strong>{l.name}{l.variant_label ? ` (${l.variant_label})` : ''}</strong><span className="price">{formatVnd(l.unit_price_vnd * l.quantity)}</span></div>{l.note && <small>{l.note}</small>}<div className="actions"><label className="quantity-label">Số lượng {l.name}<input type="number" min="1" max="10" value={l.quantity} onChange={e => cart.setQty(l.key, Number(e.target.value))} /></label><button onClick={() => cart.remove(l.key)} aria-label={`Xóa ${l.name}`}>Xóa</button></div></li>)}</ul>
    <p className="price-row"><span>Tạm tính</span><strong className="price">{formatVnd(cart.totalEstimateVnd)}</strong></p><p className="muted"><small>Giá cuối cùng được quán tính ở bước xác nhận.</small></p>
    <label htmlFor="customer-name">Tên (không bắt buộc)</label><input id="customer-name" maxLength={40} value={name} onChange={e => setName(e.target.value)} autoComplete="given-name" />
    <label htmlFor="table-label">Bàn/khu vực (không bắt buộc)</label><input id="table-label" maxLength={20} value={table} onChange={e => setTable(e.target.value)} />
    <label htmlFor="order-note">Ghi chú đơn (không bắt buộc)</label><textarea id="order-note" maxLength={200} value={note} onChange={e => setNote(e.target.value)} /><Button onClick={() => setConfirm(true)}>Xem tổng</Button>
    {confirm && <ConfirmSheet api={api} lines={cart.lines} customer={{ customer_name: name.trim() || null, table_label: table.trim() || null, note: note.trim() || null }} onDone={o => { cart.clear(); setConfirm(false); onDone(o); }} onClose={() => setConfirm(false)} />}</>}</section>;
}
