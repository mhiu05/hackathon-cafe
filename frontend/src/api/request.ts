import { ApiError } from './client';
import type { ApiErrorBody } from './types';
export async function apiResponse(path: string, init: RequestInit & { idempotencyKey?: string; adminToken?: string } = {}): Promise<Response> {
  const { idempotencyKey, adminToken, ...options } = init;
  const headers = new Headers(options.headers);
  if (options.body) headers.set('Content-Type', 'application/json');
  if (idempotencyKey) headers.set('Idempotency-Key', idempotencyKey);
  if (adminToken) headers.set('Authorization', `Bearer ${adminToken}`);
  // Same-origin calls, so no CORS preflight; lets API/SSE calls through ngrok's free-plan browser warning page.
  headers.set('ngrok-skip-browser-warning', '1');
  let response: Response;
  try { response = await fetch(path, { ...options, headers }); }
  catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new ApiError(0, 'NETWORK_ERROR', 'Không kết nối được máy chủ. Vui lòng thử lại.');
  }
  if (!response.ok) {
    if (response.status === 401 && path.startsWith('/api/admin/')) {
      sessionStorage.removeItem('biblio.admin'); window.dispatchEvent(new Event('biblio:unauthorized'));
    }
    let body: ApiErrorBody;
    try { body = await response.json() as ApiErrorBody; } catch { body = { error: { code: 'HTTP_ERROR', message: 'Máy chủ chưa sẵn sàng. Vui lòng thử lại.' } }; }
    throw new ApiError(response.status, body.error?.code ?? 'HTTP_ERROR', body.error?.message ?? 'Đã xảy ra lỗi.', body.error?.details);
  }
  return response;
}
export async function request<T>(path: string, init?: RequestInit & { idempotencyKey?: string; adminToken?: string }): Promise<T> {
  const response = await apiResponse(path, init);
  return response.status === 204 ? undefined as T : await response.json() as T;
}
