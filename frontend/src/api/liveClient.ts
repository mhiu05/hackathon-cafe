import type { ApiClient } from './client';
import type { AgentStreamEvent, OrderStreamEvent, AdminStreamEvent, Order } from './types';
import { apiResponse, request } from './request';
import { getConversationId } from './conversation';
import { readSse } from './sse';
const json = (value: unknown) => JSON.stringify(value);
const auth = () => ({ adminToken: sessionStorage.getItem('biblio.admin') ?? '' });
const conversation = () => ({ 'X-Conversation-Id': getConversationId() });
const enc = encodeURIComponent;
export const liveClient: ApiClient = {
  getCafe: () => request('/api/cafe'),
  getMenu: params => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params ?? {})) if (value !== undefined) query.set(key, String(value));
    return request(`/api/menu${query.size ? `?${query}` : ''}`);
  },
  getServices: () => request('/api/services'),
  quote: lines => request('/api/orders/quote', { method: 'POST', body: json({ lines }) }),
  createOrder: (req, idempotencyKey) => request('/api/orders', { method: 'POST', body: json(req), idempotencyKey, headers: conversation() }),
  confirmDraft: (id, total) => request(`/api/orders/drafts/${enc(id)}/confirm`, { method: 'POST', body: json({ expected_total_vnd: total }) }),
  discardDraft: async id => { await request(`/api/orders/drafts/${enc(id)}/discard`, { method: 'POST' }); },
  getOrder: code => request(`/api/orders/${enc(code)}`),
  listOrders: async id => (await request<{ orders: Order[] }>(`/api/orders${id ? `?conversation_id=${enc(id)}` : ''}`)).orders,
  streamOrder: async (code, emit, signal) => {
    await readSse(await apiResponse(`/api/orders/${enc(code)}/stream`, { signal }), (event, data) => { if (event === 'order_status') emit({ event, data } as OrderStreamEvent); });
  },
  chat: async (message, emit, signal) => {
    await readSse(await apiResponse('/api/agent/chat/stream', { method: 'POST', body: json({ message }), headers: conversation(), signal }), (event, data) => emit({ event, data } as AgentStreamEvent));
  },
  admin: {
    login: pin => request('/api/admin/login', { method: 'POST', body: json({ pin }) }),
    logout: () => request('/api/admin/logout', { ...auth(), method: 'POST' }),
    listOrders: status => request(`/api/admin/orders${status ? `?status=${enc(status)}` : ''}`, auth()),
    updateStatus: (id, req) => request(`/api/admin/orders/${id}/status`, { ...auth(), method: 'PATCH', body: json(req) }),
    updateMenuItem: (id, req) => request(`/api/admin/menu/${enc(id)}`, { ...auth(), method: 'PATCH', body: json(req) }),
    stream: async (emit, signal) => {
      await readSse(await apiResponse('/api/admin/stream', { ...auth(), signal }), (event, data) => { if (event === 'order_created' || event === 'order_updated') emit({ event, data } as AdminStreamEvent); });
    },
  },
};
