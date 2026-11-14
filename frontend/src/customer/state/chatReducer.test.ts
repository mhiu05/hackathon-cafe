import { expect, it } from 'vitest';
import { chatReducer, initialChatState } from './chatReducer';
import { parseSseText } from '../../api/sse';
import type { AgentStreamEvent } from '../../api/types';
import transcript from '../../../../contracts/fixtures/agent_stream.sse?raw';
it('replays real wire events into messages, tool results and a server-priced draft', () => {
  const state = parseSseText(transcript).reduce((s, e) => chatReducer(s, e as AgentStreamEvent), initialChatState);
  expect(state.agentState).toBe('idle');
  expect(state.messages.filter(m => m.role === 'assistant')).toHaveLength(3);
  expect(Object.values(state.drafts)[0].draft.quote.total_vnd).toBe(45000);
  expect(Object.values(state.drafts)[0].status).toBe('open');
  expect(Object.values(state.tools).map(t => t.status)).toEqual(['ok', 'ok', 'ok']);
});
it('exposes degraded mode without losing completed conversation', () => {
  const state = chatReducer(initialChatState, { event: 'error', data: { code: 'MODEL_UNAVAILABLE', message: 'Trợ lý tạm thời không khả dụng', retryable: true } });
  expect(state.error?.code).toBe('MODEL_UNAVAILABLE'); expect(state.agentState).toBe('error'); expect(state.busy).toBe(false);
});
it('does not infer tool states or discard an error when done arrives', () => {
  let s = chatReducer(initialChatState, { event: 'agent_state', data: { state: 'searching' } });
  s = chatReducer(s, { event: 'tool_started', data: { call_id: 'x', tool: 'prepare_order', label: 'Chuẩn bị' } });
  expect(s.agentState).toBe('searching');
  s = chatReducer(s, { event: 'error', data: { code: 'MODEL_UNAVAILABLE', message: 'Thử lại', retryable: true } });
  s = chatReducer(s, { event: 'done', data: { reason: 'error', usage: { input_tokens: 0, output_tokens: 0, requests: 1 } } });
  expect(s.error?.code).toBe('MODEL_UNAVAILABLE'); expect(s.busy).toBe(false);
});
