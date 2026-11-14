import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { ConfirmSheet } from './ConfirmSheet';
import { mockClient } from '../../api/mockClient';
import { ApiError } from '../../api/client';
import quoteFixture from '../../../../contracts/fixtures/quote.json';
import type { OrderQuote } from '../../api/types';
import order from '../../../../contracts/fixtures/order.json';
const lines = [{ key: 'a', item_id: 'menu_002', variant_id: null, name: 'Bạc xỉu', variant_label: null, unit_price_vnd: 45000, quantity: 1, note: null }];
const quote = quoteFixture as OrderQuote;
it('re-asks on price change, uses fresh server total and keeps the checkout retry key', async () => {
  const createOrder = vi.fn().mockRejectedValueOnce(new ApiError(409, 'PRICE_CHANGED', 'Giá đã thay đổi', { quote: { ...quote, total_vnd: 120000 } })).mockResolvedValueOnce(order);
  const done = vi.fn(); render(<ConfirmSheet api={{ ...mockClient, quote: async () => quote, createOrder }} lines={lines} onDone={done} />);
  await userEvent.click(await screen.findByRole('button', { name: 'Đặt món' }));
  expect(await screen.findByText('120.000đ')).toBeInTheDocument();
  expect(createOrder).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Đặt món' })).toBeDisabled();
  await userEvent.click(screen.getByRole('checkbox', { name: 'Tôi đã xem giá mới' }));
  await userEvent.click(screen.getByRole('button', { name: 'Đặt món' }));
  await waitFor(() => expect(done).toHaveBeenCalledWith(order));
  expect(createOrder.mock.calls[0][1]).toBe(createOrder.mock.calls[1][1]);
  expect(createOrder.mock.calls[1][0].expected_total_vnd).toBe(120000);
});
it('allows one in-flight request on a rapid double click', async () => {
  const createOrder = vi.fn(() => new Promise<never>(() => {}));
  render(<ConfirmSheet api={{ ...mockClient, quote: async () => quote, createOrder }} lines={lines} onDone={vi.fn()} />);
  await userEvent.dblClick(await screen.findByRole('button', { name: 'Đặt món' }));
  expect(createOrder).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Đặt món' })).toBeDisabled();
});
it('does not accept a new price from the second click of a fast double click', async () => {
  const createOrder = vi.fn().mockRejectedValueOnce(new ApiError(409, 'PRICE_CHANGED', 'Giá đổi', { quote: { ...quote, total_vnd: 120000 } })).mockResolvedValueOnce(order);
  render(<ConfirmSheet api={{ ...mockClient, quote: async () => quote, createOrder }} lines={lines} onDone={vi.fn()} />);
  await userEvent.dblClick(await screen.findByRole('button', { name: 'Đặt món' }));
  expect(createOrder).toHaveBeenCalledTimes(1);
});
