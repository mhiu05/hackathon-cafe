import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { useChat } from './useChat';
import { mockClient } from '../../api/mockClient';
import type { ApiClient } from '../../api/client';
import type { AgentStreamEvent } from '../../api/types';
it('prevents overlapping runs, reports a stream ending without done, and keeps user text', async () => {
  let finish!: () => void; const chat = vi.fn(() => new Promise<void>(resolve => { finish = resolve; }));
  const api = { ...mockClient, chat }; const { result } = renderHook(() => useChat(api));
  act(() => { result.current.send('Xin chào'); result.current.send('Lặp'); });
  expect(chat).toHaveBeenCalledTimes(1); expect(result.current.state.busy).toBe(true);
  await act(async () => finish());
  expect(result.current.state.error?.code).toBe('STREAM_INTERRUPTED');
  expect(result.current.state.messages[0].text).toBe('Xin chào');
});
it('resets context and ignores late events from an aborted conversation', async () => {
  let emit!: (e: AgentStreamEvent) => void; let signal!: AbortSignal;
  const api: ApiClient = { ...mockClient, chat: async (_message, callback, abort) => { emit = callback; signal = abort; await new Promise<void>(resolve => abort.addEventListener('abort', () => resolve(), { once: true })); } };
  const { result } = renderHook(() => useChat(api));
  act(() => result.current.send('Câu cũ'));
  act(() => result.current.newConversation());
  expect(signal.aborted).toBe(true);
  act(() => emit({ event: 'message_completed', data: { text: 'Phản hồi cũ', sources: [] } }));
  expect(result.current.state.messages).toEqual([]);
});
