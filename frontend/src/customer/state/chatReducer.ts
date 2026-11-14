import type { AgentState, AgentStreamEvent, Order, OrderDraft, SourceRef } from '../../api/types';
export type DraftEntry = { draft: OrderDraft; status: 'open' | 'confirming' | 'confirmed' | 'discarded' | 'expired'; order?: Order; notice?: string };
export type ChatState = {
  messages: { id: string; role: 'user' | 'assistant'; text: string; sources: SourceRef[] }[];
  streamingText: string; agentState: AgentState;
  tools: Record<string, { tool: string; label: string; status: 'running' | 'ok' | 'error'; summary?: string }>;
  drafts: Record<string, DraftEntry>; error: { code: string; message: string } | null; busy: boolean;
};
export const initialChatState: ChatState = { messages: [], streamingText: '', agentState: 'idle', tools: {}, drafts: {}, error: null, busy: false };
export type ChatAction = AgentStreamEvent | { event: 'user_message'; data: { text: string } } | { event: 'draft_update'; data: { id: string; patch: Partial<DraftEntry> } } | { event: 'reset'; data: null };
export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.event) {
    case 'reset': return initialChatState;
    case 'user_message': return { ...state, messages: [...state.messages, { id: `user-${state.messages.length}`, role: 'user', text: action.data.text, sources: [] }], streamingText: '', error: null, busy: true };
    case 'run_started': return { ...state, streamingText: '', error: null, busy: true };
    case 'agent_state': return { ...state, agentState: action.data.state };
    case 'text_delta': return { ...state, streamingText: state.streamingText + action.data.delta };
    case 'message_completed': return { ...state, streamingText: '', messages: [...state.messages, { id: `assistant-${state.messages.length}`, role: 'assistant', ...action.data }] };
    case 'tool_started': return { ...state, tools: { ...state.tools, [action.data.call_id]: { tool: action.data.tool, label: action.data.label, status: 'running' } } };
    case 'tool_finished': { const old = state.tools[action.data.call_id]; return { ...state, tools: { ...state.tools, [action.data.call_id]: { tool: action.data.tool, label: old?.label ?? action.data.tool, status: action.data.ok ? 'ok' : 'error', summary: action.data.summary } } }; }
    case 'order_draft': return { ...state, drafts: { ...state.drafts, [action.data.draft.draft_id]: state.drafts[action.data.draft.draft_id] ?? { draft: action.data.draft, status: action.data.draft.status === 'open' ? 'open' : action.data.draft.status } } };
    case 'draft_update': { const old = state.drafts[action.data.id]; return old ? { ...state, drafts: { ...state.drafts, [action.data.id]: { ...old, ...action.data.patch } } } : state; }
    case 'error': return { ...state, busy: false, agentState: 'error', error: { code: action.data.code, message: action.data.message }, tools: Object.fromEntries(Object.entries(state.tools).map(([id, t]) => [id, t.status === 'running' ? { ...t, status: 'error' } : t])) };
    case 'done': return { ...state, busy: false };
    default: return state;
  }
}
