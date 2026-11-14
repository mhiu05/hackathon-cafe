import { afterEach, expect, it, vi } from 'vitest';
import { liveClient } from './liveClient';
import { ApiError } from './client';
import order from '../../../contracts/fixtures/order.json';
afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear(); localStorage.clear(); });
it('sends the checkout key and persistent conversation id with the contract payload', async () => {
  const fetcher = vi.fn().mockResolvedValue(Response.json(order)); vi.stubGlobal('fetch', fetcher);
  await liveClient.createOrder({ lines: [], expected_total_vnd: 115000 }, 'checkout-key');
  const [url, init] = fetcher.mock.calls[0]; const headers = new Headers(init.headers);
  expect(url).toBe('/api/orders'); expect(headers.get('Idempotency-Key')).toBe('checkout-key');
  expect(headers.get('X-Conversation-Id')).toMatch(/^[0-9a-f]{32}$/);
  expect(JSON.parse(init.body)).toEqual({ lines: [], expected_total_vnd: 115000 });
});
it('uses bearer authorization and removes expired admin tokens on 401', async () => {
  sessionStorage.setItem('biblio.admin', 'test-token');
  const fetcher = vi.fn().mockResolvedValue(Response.json({ error: { code: 'ADMIN_AUTH_REQUIRED', message: 'Hết phiên' } }, { status: 401 })); vi.stubGlobal('fetch', fetcher);
  await expect(liveClient.admin.listOrders()).rejects.toMatchObject({ status: 401, code: 'ADMIN_AUTH_REQUIRED' });
  expect(new Headers(fetcher.mock.calls[0][1].headers).get('Authorization')).toBe('Bearer test-token');
  expect(sessionStorage.getItem('biblio.admin')).toBeNull();
});
it('preserves fresh quotes in structured PRICE_CHANGED errors', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ error: { code: 'PRICE_CHANGED', message: 'Giá thay đổi', details: { quote: { total_vnd: 120000 } } } }, { status: 409 })));
  await expect(liveClient.confirmDraft('draft', 115000)).rejects.toEqual(new ApiError(409, 'PRICE_CHANGED', 'Giá thay đổi', { quote: { total_vnd: 120000 } }));
});
