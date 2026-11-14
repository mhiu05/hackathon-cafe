import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { App } from './App';
import { mockClient } from '../api/mockClient';
import { ApiError } from '../api/client';
vi.mock('thinking-orbs', () => ({ ThinkingOrb: () => null }));
it('offers a retry when the backend cannot provide the cafe, then recovers', async () => {
  const getCafe = vi.fn().mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', 'Máy chủ chưa sẵn sàng')).mockImplementationOnce(mockClient.getCafe);
  render(<App api={{ ...mockClient, getCafe }} />);
  expect(await screen.findByRole('heading', { name: 'Không kết nối được máy chủ' })).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Thử lại' }));
  expect(await screen.findByRole('button', { name: 'Xem menu' })).toBeInTheDocument();
});
