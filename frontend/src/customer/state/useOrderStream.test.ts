import { act, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { useOrderStream } from './useOrderStream';
import { mockClient } from '../../api/mockClient';
import order from '../../../../contracts/fixtures/order.json';
import type { Order } from '../../api/types';
import type { ApiClient } from '../../api/client';
afterEach(() => vi.useRealTimers());
it('loads immediately and polls after an SSE disconnect, stopping on unmount', async () => {
  vi.useFakeTimers(); const getOrder = vi.fn().mockResolvedValue(order);
  const client = { ...mockClient, getOrder, streamOrder: async () => { throw new Error('offline'); } };
  const { result, unmount } = renderHook(() => useOrderStream('BB-0001', client));
  await act(async () => { await Promise.resolve(); });
  expect(result.current.order?.code).toBe('BB-0001'); expect(result.current.live).toBe(false);
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(getOrder).toHaveBeenCalledTimes(2); unmount();
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(getOrder).toHaveBeenCalledTimes(2);
});
it('keeps a newer stream update when the initial GET finishes late', async () => {
  let resolve!: (o: Order) => void;
  const getOrder = () => new Promise<Order>(r => { resolve = r; });
  const client: ApiClient = { ...mockClient, getOrder, streamOrder: async (_code, emit, signal) => {
    emit({ event: 'order_status', data: { order: { ...order, status: 'ready', status_label: 'Sẵn sàng', updated_at: '2026-11-14T10:00:00Z' } as Order } });
    await new Promise<void>(r => signal.addEventListener('abort', () => r(), { once: true }));
  } };
  const { result } = renderHook(() => useOrderStream('BB-0001', client));
  await act(async () => resolve(order as Order));
  expect(result.current.order?.status).toBe('ready');
});
