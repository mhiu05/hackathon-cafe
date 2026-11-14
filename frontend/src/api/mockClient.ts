import type { ApiClient } from './client';
import { ApiError } from './client';
import type { CafeProfile, MenuResponse, ServicesResponse, OrderQuote, Order, AdminOrderListResponse, AgentStreamEvent } from './types';
import cafe from '../../../contracts/fixtures/cafe.json';
import menu from '../../../contracts/fixtures/menu.json';
import services from '../../../contracts/fixtures/services.json';
import quote from '../../../contracts/fixtures/quote.json';
import order from '../../../contracts/fixtures/order.json';
import draftOrder from '../../../contracts/fixtures/order_from_draft.json';
import adminOrders from '../../../contracts/fixtures/admin_orders.json';
import transcript from '../../../contracts/fixtures/agent_stream.sse?raw';
import { parseSseText } from './sse';
import { foldVi } from '../lib/fold';
const copy = <T,>(value: T): T => structuredClone(value);
const turns: AgentStreamEvent[][] = [];
for (const e of parseSseText(transcript)) { if (e.event === 'run_started') turns.push([]); turns.at(-1)?.push(e as AgentStreamEvent); }
let turn = 0;
function untilAbort(signal: AbortSignal): Promise<void> {
  return new Promise(resolve => { if (signal.aborted) resolve(); else signal.addEventListener('abort', () => resolve(), { once: true }); });
}
export const mockClient: ApiClient = {
  getCafe: async () => copy(cafe as CafeProfile),
  getMenu: async params => {
    const data = copy(menu as MenuResponse); const tokens = foldVi(params?.q ?? '').split(/\s+/).filter(Boolean);
    data.items = data.items.filter(i => (!params?.category || i.category_id === params.category) && tokens.every(t => foldVi(i.name).includes(t)) && (params?.max_price_vnd === undefined || i.price_min_vnd <= params.max_price_vnd)); return data;
  },
  getServices: async () => copy(services as ServicesResponse),
  quote: async () => copy(quote as OrderQuote),
  createOrder: async () => copy(order as Order),
  confirmDraft: async () => copy(draftOrder as Order),
  discardDraft: async () => {},
  getOrder: async code => { const found = [order, draftOrder].find(o => o.code === code); if (!found) throw new ApiError(404, 'ORDER_NOT_FOUND', 'Không tìm thấy đơn.'); return copy(found as Order); },
  listOrders: async () => copy([order, draftOrder] as Order[]),
  streamOrder: async (code, emit, signal) => { const found = await mockClient.getOrder(code); if (!signal.aborted) emit({ event: 'order_status', data: { order: found } }); await untilAbort(signal); },
  chat: async (_message, emit, signal) => {
    const events = turns[turn++ % turns.length];
    for (const e of events) { if (signal.aborted) return; emit(copy(e)); await new Promise(resolve => setTimeout(resolve, 40)); }
  },
  admin: {
    login: async () => ({ token: 'fixture-only', expires_at: '2026-11-15T00:00:00Z' }), logout: async () => {},
    listOrders: async () => copy(adminOrders as AdminOrderListResponse),
    updateStatus: async (id, req) => { const found = adminOrders.orders.find(o => o.id === id); if (!found) throw new ApiError(404, 'NOT_FOUND', 'Không tìm thấy đơn.'); return { ...copy(found as Order), status: req.to_status }; },
    updateMenuItem: async (id, req) => { const found = (menu as MenuResponse).items.find(i => i.id === id); if (!found) throw new ApiError(404, 'ITEM_NOT_FOUND', 'Không tìm thấy món.'); return { ...copy(found), ...req }; },
    stream: async (_emit, signal) => untilAbort(signal),
    listStaffRequests: async () => ({ requests: [] }),
    resolveStaffRequest: async () => { throw new ApiError(404, 'STAFF_REQUEST_NOT_FOUND', 'Không tìm thấy yêu cầu.'); },
    streamStaffRequests: async (_emit, signal) => untilAbort(signal),
  },
};
