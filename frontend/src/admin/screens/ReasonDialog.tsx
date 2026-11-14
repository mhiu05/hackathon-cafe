import { useState } from 'react';
import { Sheet } from '../../ui/Sheet';
import { Button } from '../../ui/Button';
export function ReasonDialog({ rejecting, pending, onSubmit, onClose }: { rejecting: boolean; pending: boolean; onSubmit: (reason: string) => void; onClose: () => void }) {
  const [reason, setReason] = useState(''), [invalid, setInvalid] = useState(false);
  return <Sheet title={rejecting ? 'Từ chối đơn' : 'Hủy đơn'} onClose={pending ? undefined : onClose}><form onSubmit={e => { e.preventDefault(); if (reason.trim().length < 3) { setInvalid(true); return; } onSubmit(reason.trim()); }}><label htmlFor="transition-reason">Lý do</label><textarea id="transition-reason" maxLength={200} value={reason} onChange={e => setReason(e.target.value)} aria-invalid={invalid} aria-describedby="reason-help" disabled={pending} /><p id="reason-help" className={invalid ? 'danger' : 'muted'}>Nhập lý do từ 3 đến 200 ký tự để khách hiểu.</p><Button disabled={pending}>{rejecting ? 'Xác nhận từ chối' : 'Xác nhận hủy'}</Button></form></Sheet>;
}
