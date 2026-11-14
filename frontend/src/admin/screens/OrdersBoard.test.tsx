import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { OrdersBoard } from './OrdersBoard';
import { ApiError } from '../../api/client';
import type { AdminOrderListResponse } from '../../api/types';
import fixture from '../../../../contracts/fixtures/admin_orders.json';
const orders = (fixture as AdminOrderListResponse).orders;
it('offers only server allowed transitions and requires a reason for rejection', async () => {
  const onTransition = vi.fn().mockResolvedValue(undefined);
  render(<OrdersBoard orders={orders} onTransition={onTransition} />);
  const pending = screen.getByRole('region', { name: 'Mới' });
  expect(within(pending).getByText('BB-0002')).toBeInTheDocument();
  expect(within(pending).getAllByRole('button').map(b => b.textContent)).toEqual(['Nhận đơn', 'Từ chối', 'Hủy']);
  await userEvent.click(within(pending).getByRole('button', { name: 'Từ chối' }));
  await userEvent.click(screen.getByRole('button', { name: 'Xác nhận từ chối' }));
  expect(onTransition).not.toHaveBeenCalled();
  await userEvent.type(screen.getByLabelText('Lý do'), 'Hết nguyên liệu');
  await userEvent.click(screen.getByRole('button', { name: 'Xác nhận từ chối' }));
  expect(onTransition).toHaveBeenCalledWith(2, { to_status: 'rejected', expected_status: 'pending', reason: 'Hết nguyên liệu' });
});
it('announces stale-tab conflicts and refetches the board', async () => {
  const refetch = vi.fn();
  render(<OrdersBoard orders={orders} onTransition={vi.fn().mockRejectedValue(new ApiError(409, 'STATUS_CONFLICT', 'Conflict'))} onRefresh={refetch} />);
  await userEvent.click(within(screen.getByRole('region', { name: 'Mới' })).getByRole('button', { name: 'Nhận đơn' }));
  expect(await screen.findByText('Đơn đã được cập nhật ở nơi khác')).toBeInTheDocument();
  expect(refetch).toHaveBeenCalledOnce();
});
