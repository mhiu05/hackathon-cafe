import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { StaffRequest } from '../../api/types';
import { Badge } from '../../ui/Badge';
import { Composer } from '../../customer/chat/Composer';
import { StaffRequests } from './StaffRequests';
const request: StaffRequest = { id: 3, code: 'YC-0003', kind: 'wifi', kind_label: 'Wi-Fi / mạng', table_label: 'Bàn 5', note: 'Sóng yếu',
  status: 'open', status_label: 'Đang chờ', created_at: '2026-11-14T09:00:00.000Z', resolved_at: null };
it('lists open staff requests and resolves one', async () => {
  const onResolve = vi.fn(async () => {});
  render(<StaffRequests requests={[request]} onResolve={onResolve} />);
  expect(screen.getByRole('region', { name: 'Khách cần hỗ trợ' })).toHaveTextContent('Wi-Fi / mạng');
  expect(screen.getByText('Bàn 5 · Sóng yếu')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Đã xử lý' }));
  expect(onResolve).toHaveBeenCalledWith(3);
});
it('renders nothing when there is no open request', () => {
  const { container } = render(<StaffRequests requests={[]} onResolve={async () => {}} />);
  expect(container).toBeEmptyDOMElement();
});
it('shows no stock badge for in-stock items, only exceptions', () => {
  const { container, rerender } = render(<Badge availability="available" />);
  expect(container).toBeEmptyDOMElement();
  rerender(<Badge availability="sold_out" />); expect(screen.getByText('Hết')).toBeInTheDocument();
  rerender(<Badge availability="available" orderable={false} />); expect(screen.getByText('Tạm ngưng')).toBeInTheDocument();
});
it('composer sends with an icon button named Gửi and has no visible send text', () => {
  const onSend = vi.fn();
  render(<Composer busy={false} onSend={onSend} />);
  const send = screen.getByRole('button', { name: 'Gửi' });
  expect(send).toBeDisabled(); expect(send).not.toHaveTextContent('Gửi');
  fireEvent.change(screen.getByLabelText('Nhắn Biblio'), { target: { value: 'Wi-Fi yếu quá' } });
  fireEvent.click(send); expect(onSend).toHaveBeenCalledWith('Wi-Fi yếu quá');
});
