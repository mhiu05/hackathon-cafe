import { useState } from 'react';
import type { StaffRequest } from '../../api/types';
import { formatTime } from '../../lib/format';
export function StaffRequests({ requests, error, onResolve }: { requests: StaffRequest[]; error?: string; onResolve: (id: number) => Promise<void> }) {
  const [pending, setPending] = useState<number | null>(null), [notice, setNotice] = useState('');
  if (!requests.length && !error && !notice) return null;
  async function resolve(id: number) {
    setPending(id); setNotice('');
    try { await onResolve(id); } catch (e) { setNotice(e instanceof Error ? e.message : 'Chưa cập nhật được yêu cầu.'); } finally { setPending(null); }
  }
  return <section className="staff-requests" aria-label="Khách cần hỗ trợ"><h2>Khách cần hỗ trợ <small>{requests.length}</small></h2>
    {(error || notice) && <p className="danger" role="alert">{notice || error}</p>}
    <ul>{requests.map(r => <li key={r.id} className="staff-request"><div><strong>{r.kind_label}</strong> <small>{r.code} · <time dateTime={r.created_at}>{formatTime(r.created_at)}</time></small>
      <p>{r.table_label ?? 'Chưa rõ bàn'}{r.note ? ` · ${r.note}` : ''}</p></div>
      <button className="button-primary" disabled={pending === r.id} onClick={() => void resolve(r.id)}>Đã xử lý</button></li>)}</ul></section>;
}
