import { useEffect, useRef, useState } from 'react';
import { api as defaultApi } from '../../api';
import { ApiError, type ApiClient } from '../../api/client';
import type { CreateOrderRequest, Order, OrderQuote } from '../../api/types';
import { toLineInputs, type CartLine } from '../../lib/cart';
import { newIdempotencyKey } from '../../lib/idempotency';
import { Sheet } from '../../ui/Sheet';
import { OrderSlip } from '../../ui/OrderSlip';
import { Button } from '../../ui/Button';
export function ConfirmSheet({ api = defaultApi, lines, customer = {}, onDone, onClose }: { api?: ApiClient; lines: CartLine[]; customer?: Pick<CreateOrderRequest, 'customer_name' | 'table_label' | 'note'>; onDone: (order: Order) => void; onClose?: () => void }) {
  const [quote, setQuote] = useState<OrderQuote | null>(null), [error, setError] = useState(''), [pending, setPending] = useState(false), [retry, setRetry] = useState(0);
  const [key] = useState(newIdempotencyKey); const lock = useRef(false);
  const [priceChanged, setPriceChanged] = useState(false), [reviewedPrice, setReviewedPrice] = useState(true);
  useEffect(() => { let active = true; setError(''); api.quote(toLineInputs(lines)).then(q => { if (active) setQuote(q); }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Không lấy được báo giá'); }); return () => { active = false; }; }, [api, lines, retry]);
  async function submit() {
    if (!quote || !reviewedPrice || lock.current) return; lock.current = true; setPending(true); setError('');
    try { const order = await api.createOrder({ lines: toLineInputs(lines), ...customer, expected_total_vnd: quote.total_vnd }, key); onDone(order); }
    catch (e) {
      if (e instanceof ApiError && e.code === 'PRICE_CHANGED' && e.details?.quote) { setQuote(e.details.quote as unknown as OrderQuote); setPriceChanged(true); setReviewedPrice(false); setError('Giá vừa thay đổi, vui lòng xác nhận lại'); }
      else setError(e instanceof Error ? e.message : 'Không đặt được món. Vui lòng thử lại.');
    } finally { lock.current = false; setPending(false); }
  }
  return <Sheet title="Xác nhận đơn của bạn" onClose={pending ? undefined : onClose}>{quote ? <OrderSlip order={quote} /> : <p role="status">Đang lấy báo giá từ quán…</p>}{error && <p role="alert" className="danger">{error}</p>}{priceChanged && <label className="radio-label"><input type="checkbox" checked={reviewedPrice} onChange={e => setReviewedPrice(e.target.checked)} />Tôi đã xem giá mới</label>}{!quote && error && <button onClick={() => setRetry(r => r + 1)}>Thử lại</button>}<p className="muted"><small>Thanh toán tại quầy. Nhân viên sẽ kiểm tra và xác nhận đơn.</small></p>{quote && <Button disabled={pending || !reviewedPrice} onClick={() => void submit()} aria-busy={pending}>Đặt món</Button>}</Sheet>;
}
