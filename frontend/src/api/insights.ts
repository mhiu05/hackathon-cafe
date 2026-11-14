import { ApiError } from './client';
import type { AdminInsights } from './types';
import { request } from './request';
// §7 defines this P1 endpoint; keep the frozen §10 ApiClient interface unchanged.
export async function getAdminInsights(): Promise<AdminInsights> {
  if (import.meta.env.VITE_API_MODE === 'mock') throw new ApiError(503, 'LIVE_REQUIRED', 'Tổng quan cần kết nối trực tiếp với quán.');
  return request('/api/admin/insights', { adminToken: sessionStorage.getItem('biblio.admin') ?? '' });
}
