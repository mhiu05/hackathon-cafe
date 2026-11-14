import { useEffect, useState } from 'react';
import { api as defaultApi } from '../../api';
import type { ApiClient } from '../../api/client';
export function useAdminAuth(api: ApiClient = defaultApi) {
  const [token, setToken] = useState(() => sessionStorage.getItem('biblio.admin'));
  useEffect(() => { const expired = () => setToken(null); window.addEventListener('biblio:unauthorized', expired); return () => window.removeEventListener('biblio:unauthorized', expired); }, []);
  return { token, login: async (pin: string) => { const response = await api.admin.login(pin); sessionStorage.setItem('biblio.admin', response.token); setToken(response.token); }, logout: async () => { try { await api.admin.logout(); } finally { sessionStorage.removeItem('biblio.admin'); setToken(null); } } };
}
