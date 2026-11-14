import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { Insights } from './Insights';
import type { AdminInsights } from '../../api/types';
it('renders server insight totals and top items without calculating revenue locally', async () => {
  const data: AdminInsights = { orders_by_status: { pending: 1, confirmed: 0, preparing: 0, ready: 0, completed: 2, rejected: 0, cancelled: 0 }, orders_total: 3, revenue_completed_vnd: 90000, top_items: [{ item_id: 'menu_002', name: 'Bạc xỉu', quantity: 2 }], agent: { runs: 1, tool_calls: { search_menu: 2 }, tool_errors: 0, input_tokens: 400, output_tokens: 80 } };
  render(<Insights load={async () => data} />);
  expect(await screen.findByText('90.000đ')).toBeInTheDocument();
  expect(screen.getByText('Bạc xỉu')).toBeInTheDocument(); expect(screen.getByText('search_menu')).toBeInTheDocument();
});
