import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { MenuAvailability } from './MenuAvailability';
import { mockClient } from '../../api/mockClient';
it('updates availability through the authenticated client and renders the server result', async () => {
  const updateMenuItem = vi.fn(mockClient.admin.updateMenuItem);
  render(<MenuAvailability api={{ ...mockClient, admin: { ...mockClient.admin, updateMenuItem } }} />);
  const row = await screen.findByRole('group', { name: 'Trà xoài Yakult' });
  await userEvent.click(within(row).getByRole('button', { name: 'Hết' }));
  await waitFor(() => expect(updateMenuItem).toHaveBeenCalledWith('menu_019', { availability: 'sold_out' }));
  expect(within(row).getByRole('button', { name: 'Hết' })).toHaveAttribute('aria-pressed', 'true');
});
