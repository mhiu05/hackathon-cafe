import { useEffect, useRef, useState } from 'react';
import { api as defaultApi } from '../../api';
import type { ApiClient } from '../../api/client';
import type { OrderDraft, OrderQuote } from '../../api/types';
import { OrderSlip } from '../../ui/OrderSlip';
import { Button } from '../../ui/Button';
import type { DraftEntry } from '../state/chatReducer';
import { runDraftAction } from '../state/draftActions';
import { OrderCard } from './OrderCard';
export function DraftSlip({ draft, api = defaultApi, entry: controlled, onConfirm, onDiscard, onOpenOrder }: { draft: OrderDraft; api?: ApiClient; entry?: DraftEntry; onConfirm?: () => Promise<void>; onDiscard?: () => Promise<void>; onOpenOrder?: (code: string) => void }) {
  const [local, setLocal] = useState<DraftEntry>({ draft, status: 'open' }); const entry = controlled ?? local;
  const [reviewedQuote, setReviewedQuote] = useState<OrderQuote | null>(null);
  const changedPrice = entry.notice?.startsWith('Giá vừa thay đổi') ?? false;
  const needsPriceReview = changedPrice && reviewedQuote !== entry.draft.quote;
  const lock = useRef(false), heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus({ preventScroll: true }); }, []);
  async function action(kind: 'confirm' | 'discard') {
    if (lock.current || entry.status !== 'open' || (kind === 'confirm' && needsPriceReview)) return; lock.current = true;
    try { const handler = kind === 'confirm' ? onConfirm : onDiscard; if (handler) await handler(); else await runDraftAction(api, entry, kind, patch => setLocal(old => ({ ...old, ...patch }))); }
    finally { lock.current = false; }
  }
  if (entry.status === 'confirmed' && entry.order) return <OrderCard order={entry.order} api={api} onOpenOrder={onOpenOrder} />;
  return <article className={`draft-slip ${entry.status === 'expired' || entry.status === 'discarded' ? 'inactive' : ''}`}><h3 ref={heading} tabIndex={-1}>Đơn nháp của bạn</h3><p className="muted"><small>Chưa đặt món · Đơn nháp giữ 30 phút</small></p><OrderSlip order={entry.draft.quote} />{entry.notice && <p className="warning" role="alert">{entry.notice}</p>}{changedPrice && <label className="radio-label"><input type="checkbox" checked={!needsPriceReview} onChange={e => setReviewedQuote(e.target.checked ? entry.draft.quote : null)} />Tôi đã xem giá mới</label>}{entry.status === 'discarded' && <p>Đã bỏ qua đơn nháp</p>}<div className="actions"><button disabled={entry.status !== 'open'} onClick={() => void action('discard')}>Bỏ qua</button><Button disabled={entry.status !== 'open' || needsPriceReview} aria-busy={entry.status === 'confirming'} onClick={() => void action('confirm')}>Xác nhận đặt món</Button></div></article>;
}
