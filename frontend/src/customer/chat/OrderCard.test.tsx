import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { OrderCard } from './OrderCard';
import { mockClient } from '../../api/mockClient';
import type { ApiClient } from '../../api/client';
import type { Order } from '../../api/types';
import fixture from '../../../../contracts/fixtures/order_from_draft.json';
it('keeps a confirmed draft card current when staff progress the real order', async () => {
  const order = fixture as Order;
  const current: Order = { ...order, status: 'ready', status_label: 'Sẵn sàng — mời bạn nhận tại quầy', updated_at: '2026-11-14T12:00:00Z' };
  const api: ApiClient = { ...mockClient, getOrder: async () => current, streamOrder: async (_code, emit, signal) => { emit({ event: 'order_status', data: { order: current } }); await new Promise<void>(r => signal.addEventListener('abort', () => r(), { once: true })); } };
  render(<OrderCard order={order} api={api} />);
  expect(await screen.findByText('Sẵn sàng — mời bạn nhận tại quầy')).toBeInTheDocument();
  expect(screen.queryByText('Chờ quán xác nhận')).not.toBeInTheDocument();
});
