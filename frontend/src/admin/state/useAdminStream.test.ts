import { act, renderHook, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { useAdminStream } from './useAdminStream';
import { mockClient } from '../../api/mockClient';
import type { ApiClient } from '../../api/client';
import type { AdminOrderListResponse, AdminStreamEvent, Order } from '../../api/types';
import fixture from '../../../../contracts/fixtures/admin_orders.json';
it('refetches authoritative admin actions when an SSE order omits allowed_next', async () => {
  let emit!: (event: AdminStreamEvent) => void;
  const updated: Order = { ...(fixture as AdminOrderListResponse).orders[0], status: 'confirmed', status_label: 'Quán đã nhận đơn', updated_at: '2026-11-14T12:00:00Z' };
  delete updated.allowed_next;
  const listOrders = vi.fn().mockResolvedValueOnce(fixture).mockResolvedValue({ ...fixture, orders: [{ ...updated, allowed_next: ['preparing', 'ready', 'cancelled'] }] });
  const api: ApiClient = { ...mockClient, admin: { ...mockClient.admin, listOrders, stream: async (callback, signal) => { emit = callback; await new Promise<void>(r => signal.addEventListener('abort', () => r(), { once: true })); } } };
  const { result } = renderHook(() => useAdminStream('token', api));
  await waitFor(() => expect(result.current.loading).toBe(false));
  act(() => emit({ event: 'order_updated', data: { order: updated } }));
  await waitFor(() => expect(result.current.orders.find(o => o.id === updated.id)?.allowed_next).toEqual(['preparing', 'ready', 'cancelled']));
  expect(listOrders).toHaveBeenCalledTimes(2);
});
