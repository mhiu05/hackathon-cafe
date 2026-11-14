import { ApiError, type ApiClient } from '../../api/client';
import type { OrderQuote } from '../../api/types';
import type { DraftEntry } from './chatReducer';
export async function runDraftAction(api: ApiClient, entry: DraftEntry, action: 'confirm' | 'discard', update: (patch: Partial<DraftEntry>) => void): Promise<void> {
  update({ status: 'confirming', notice: undefined });
  try {
    if (action === 'confirm') { const order = await api.confirmDraft(entry.draft.draft_id, entry.draft.quote.total_vnd); update({ status: 'confirmed', order }); }
    else { await api.discardDraft(entry.draft.draft_id); update({ status: 'discarded' }); }
  } catch (e) {
    if (e instanceof ApiError && e.code === 'PRICE_CHANGED' && e.details?.quote) update({ status: 'open', draft: { ...entry.draft, quote: e.details.quote as unknown as OrderQuote }, notice: 'Giá vừa thay đổi, vui lòng xác nhận lại' });
    else if (e instanceof ApiError && e.status === 410) update({ status: 'expired', notice: 'Đơn nháp đã hết hạn — nhắn lại để tạo mới' });
    else if (e instanceof ApiError && e.code === 'DRAFT_DISCARDED') update({ status: 'discarded', notice: 'Đơn nháp đã được bỏ qua' });
    else update({ status: 'open', notice: e instanceof Error ? e.message : 'Không xử lý được đơn nháp. Vui lòng thử lại.' });
  }
}
