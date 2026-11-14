import { useCallback, useEffect, useRef, useState } from 'react';
import { api as defaultApi } from '../../api';
import type { ApiClient } from '../../api/client';
import type { Order, OrderStatus } from '../../api/types';
const emptyCounts = (): Record<OrderStatus, number> => ({ pending: 0, confirmed: 0, preparing: 0, ready: 0, completed: 0, rejected: 0, cancelled: 0 });
export function useAdminStream(token: string, api: ApiClient = defaultApi) {
  const [orders, setOrders] = useState<Order[]>([]), [live, setLive] = useState(false), [error, setError] = useState(''), [loading, setLoading] = useState(true), [announcement, setAnnouncement] = useState('');
  const epoch = useRef(0); const loadingRef = useRef(false);
  const merge = useCallback((incoming: Order[]) => setOrders(old => {
    const byId = new Map(old.map(o => [o.id, o]));
    for (const order of incoming) { const existing = byId.get(order.id); if (!existing || Date.parse(order.updated_at) >= Date.parse(existing.updated_at)) byId.set(order.id, order); }
    return [...byId.values()].sort((a, b) => b.id - a.id);
  }), []);
  const refetch = useCallback(async () => {
    if (loadingRef.current) return; loadingRef.current = true; const generation = epoch.current;
    try { const response = await api.admin.listOrders(); if (generation === epoch.current) { merge(response.orders); setError(''); } }
    catch (e) { if (generation === epoch.current) setError(e instanceof Error ? e.message : 'Không tải được đơn'); }
    finally { loadingRef.current = false; if (generation === epoch.current) setLoading(false); }
  }, [api, merge]);
  useEffect(() => {
    const generation = ++epoch.current; const abort = new AbortController(); let streamLive = false;
    setOrders([]); setLoading(true); setLive(false); void refetch();
    const disconnected = () => { if (epoch.current === generation) { streamLive = false; setLive(false); } };
    void api.admin.stream(e => {
      if (epoch.current !== generation) return; streamLive = true; setLive(true); merge([e.data.order]);
      if (e.event === 'order_created') setAnnouncement(`Đơn mới ${e.data.order.code}`);
    }, abort.signal).then(disconnected).catch(disconnected);
    const poll = setInterval(() => { if (!streamLive) void refetch(); }, 3000);
    return () => { epoch.current++; abort.abort(); clearInterval(poll); };
  }, [token, api, refetch, merge]);
  const counts = orders.reduce((c, order) => { c[order.status]++; return c; }, emptyCounts());
  return { orders, counts, live, error, loading, announcement, refetch, accept: (order: Order) => merge([order]) };
}
