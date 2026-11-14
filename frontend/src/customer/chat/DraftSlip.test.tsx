import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { DraftSlip } from './DraftSlip';
import { mockClient } from '../../api/mockClient';
import { ApiError } from '../../api/client';
import type { OrderDraft } from '../../api/types';
import fixture from '../../../../contracts/fixtures/draft.json';
import order from '../../../../contracts/fixtures/order_from_draft.json';
const draft = fixture as OrderDraft;
it('blocks double confirmation while pending', async () => {
  const confirmDraft = vi.fn(() => new Promise<never>(() => {}));
  render(<DraftSlip draft={draft} api={{ ...mockClient, confirmDraft }} />);
  await userEvent.dblClick(screen.getByRole('button', { name: 'Xác nhận đặt món' }));
  expect(confirmDraft).toHaveBeenCalledTimes(1);
});
it('shows a fresh price and requires a new click before confirming', async () => {
  const confirmDraft = vi.fn().mockRejectedValueOnce(new ApiError(409, 'PRICE_CHANGED', 'Giá đổi', { quote: { ...draft.quote, total_vnd: 50000 } })).mockResolvedValueOnce(order);
  render(<DraftSlip draft={draft} api={{ ...mockClient, confirmDraft }} />);
  await userEvent.click(screen.getByRole('button', { name: 'Xác nhận đặt món' }));
  expect(await screen.findByText('50.000đ')).toBeInTheDocument();
  expect(screen.getByText(/Giá vừa thay đổi/)).toBeInTheDocument(); expect(confirmDraft).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'Xác nhận đặt món' })).toBeDisabled();
  await userEvent.click(screen.getByRole('checkbox', { name: 'Tôi đã xem giá mới' }));
  await userEvent.click(screen.getByRole('button', { name: 'Xác nhận đặt món' }));
  expect(await screen.findByText('BB-0002')).toBeInTheDocument();
  expect(confirmDraft.mock.calls[1]).toEqual([draft.draft_id, 50000]);
});
it('disables expired drafts after the backend returns 410', async () => {
  render(<DraftSlip draft={draft} api={{ ...mockClient, confirmDraft: async () => { throw new ApiError(410, 'DRAFT_EXPIRED', 'Hết hạn'); } }} />);
  await userEvent.click(screen.getByRole('button', { name: 'Xác nhận đặt món' }));
  expect(await screen.findByText(/Đơn nháp đã hết hạn/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Xác nhận đặt món' })).toBeDisabled();
});
it('requires fresh price review even when PRICE_CHANGED returns between double-clicks', async () => {
  const confirmDraft = vi.fn().mockRejectedValueOnce(new ApiError(409, 'PRICE_CHANGED', 'Giá đổi', { quote: { ...draft.quote, total_vnd: 50000 } })).mockResolvedValueOnce(order);
  render(<DraftSlip draft={draft} api={{ ...mockClient, confirmDraft }} />);
  await userEvent.dblClick(screen.getByRole('button', { name: 'Xác nhận đặt món' }));
  expect(confirmDraft).toHaveBeenCalledTimes(1);
});
