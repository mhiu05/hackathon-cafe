import { useCallback, useEffect, useState } from 'react';
import type { ApiClient } from '../../api/client';
import type { StaffRequest } from '../../api/types';
// Open "Gọi nhân viên" requests created by the customer agent. Live over SSE, polling every 5 s while the stream is down.
export function useStaffRequests(token: string, api: ApiClient) {
  const [requests, setRequests] = useState<StaffRequest[]>([]), [announcement, setAnnouncement] = useState(''), [error, setError] = useState('');
  const upsert = useCallback((incoming: StaffRequest) => setRequests(old => [incoming, ...old.filter(r => r.id !== incoming.id)].filter(r => r.status === 'open').sort((a, b) => a.id - b.id)), []);
  const refetch = useCallback(async () => {
    try { setRequests((await api.admin.listStaffRequests('open')).requests.sort((a, b) => a.id - b.id)); setError(''); }
    catch (e) { setError(e instanceof Error ? e.message : 'Không tải được yêu cầu của khách'); }
  }, [api]);
  useEffect(() => {
    const abort = new AbortController(); let live = false; void refetch();
    void api.admin.streamStaffRequests(e => {
      live = true; upsert(e.data.request);
      if (e.event === 'staff_request_created') setAnnouncement(`Khách cần hỗ trợ: ${e.data.request.kind_label}${e.data.request.table_label ? ` · ${e.data.request.table_label}` : ''}`);
    }, abort.signal).catch(() => {}).finally(() => { live = false; });
    const poll = setInterval(() => { if (!live) void refetch(); }, 5000);
    return () => { abort.abort(); clearInterval(poll); };
  }, [token, api, refetch, upsert]);
  const resolve = useCallback(async (id: number) => { upsert(await api.admin.resolveStaffRequest(id)); }, [api, upsert]);
  return { requests, announcement, error, resolve };
}
