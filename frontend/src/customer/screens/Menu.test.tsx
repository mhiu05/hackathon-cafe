import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { Menu } from './Menu';
import { mockApiWith } from '../../test/mockApi';
it('filters by Vietnamese search tokens and prevents ordering sold-out items', async () => {
  render(<Menu api={mockApiWith({ soldOut: ['menu_014'] })} onAdd={vi.fn()} />);
  await userEvent.type(await screen.findByRole('searchbox', { name: 'Tìm món' }), 'tra dao');
  expect(screen.getByText('Trà thạch đào')).toBeInTheDocument();
  expect(screen.getByText('Trà đào cam sả')).toBeInTheDocument();
  expect(screen.queryByText('Bạc xỉu')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Trà thạch đào/ })).toHaveAttribute('aria-disabled', 'true');
});
it('requires a variant before adding and keeps customer notes', async () => {
  const add = vi.fn(); render(<Menu api={mockApiWith({})} onAdd={add} />);
  await userEvent.click(await screen.findByRole('button', { name: /Cà phê nâu/ }));
  expect(screen.getByRole('button', { name: 'Thêm vào giỏ' })).toBeDisabled();
  await userEvent.click(screen.getByRole('radio', { name: /Đen/ }));
  await userEvent.type(screen.getByLabelText('Ghi chú món'), 'ít đá');
  await userEvent.click(screen.getByRole('button', { name: 'Thêm vào giỏ' }));
  expect(add).toHaveBeenCalledWith(expect.objectContaining({ item_id: 'menu_001', variant_id: 'menu_001:den', note: 'ít đá', quantity: 1 }));
});
