import type { ApiClient } from '../api/client';
import { mockClient } from '../api/mockClient';
export function mockApiWith({ soldOut = [] }: { soldOut?: string[] }): ApiClient {
  return { ...mockClient, getMenu: async params => { const data = await mockClient.getMenu(params); return { ...data, items: data.items.map(i => soldOut.includes(i.id) ? { ...i, availability: 'sold_out' } : i) }; } };
}
