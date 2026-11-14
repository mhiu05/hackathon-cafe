import { useEffect, useState } from 'react';
import { api as defaultApi } from '../../api';
import { ApiError, type ApiClient } from '../../api/client';
import type { Order } from '../../api/types';
export function useOrderStream(code: string, api: ApiClient = defaultApi): { order: Order | null; live: boolean; error: ApiError | null } {
  const [order, setOrder] = useState<Order | null>(null), [live, setLive] = useState(false), [error, setError] = useState<ApiError | null>(null);
  useEffect(() => {
    const controller = new AbortController(); let active = true; let polling: ReturnType<typeof setInterval> | undefined; let loading = false;
    setOrder(null); setLive(false); setError(null);
    const accept = (next: Order) => { if (!active) return; setOrder(old => old && Date.parse(old.updated_at) > Date.parse(next.updated_at) ? old : next); setError(null); };
    const refresh = async () => { if (loading || !active) return; loading = true; try { accept(await api.getOrder(code)); } catch (e) { if (active) setError(e instanceof ApiError ? e : new ApiError(0, 'NETWORK_ERROR', 'Không tải được đơn. Đang thử kết nối lại.')); } finally { loading = false; } };
    const fallback = () => { if (!active) return; setLive(false); if (!polling) polling = setInterval(() => void refresh(), 5000); };
    void refresh();
    void api.streamOrder(code, e => { if (active) { accept(e.data.order); setLive(true); if (polling) { clearInterval(polling); polling = undefined; } } }, controller.signal).then(fallback).catch(fallback);
    return () => { active = false; controller.abort(); if (polling) clearInterval(polling); };
  }, [code, api]);
  return { order, live, error };
}
