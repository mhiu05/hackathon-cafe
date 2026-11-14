import type { ApiClient } from './client';
import { liveClient } from './liveClient';
export const api: ApiClient = import.meta.env.VITE_API_MODE === 'mock'
  ? (await import('./mockClient')).mockClient
  : liveClient;
