import { useEffect, useReducer, useRef } from 'react';
import { api as defaultApi } from '../../api';
import { ApiError, type ApiClient } from '../../api/client';
import { resetConversation } from '../../api/conversation';
import { chatReducer, initialChatState } from './chatReducer';
import { runDraftAction } from './draftActions';
export function useChat(api: ApiClient = defaultApi) {
  const [state, dispatch] = useReducer(chatReducer, initialChatState); const latest = useRef(state); latest.current = state;
  const active = useRef<AbortController | null>(null), generation = useRef(0), draftLocks = useRef(new Set<string>());
  useEffect(() => () => { generation.current++; active.current?.abort(); }, []);
  function send(raw: string) {
    const text = raw.trim(); if (!text || text.length > 1000 || active.current) return;
    const abort = new AbortController(); active.current = abort; const run = generation.current; let done = false;
    dispatch({ event: 'user_message', data: { text } });
    void api.chat(text, event => { if (run !== generation.current || abort.signal.aborted) return; if (event.event === 'done') done = true; dispatch(event); }, abort.signal)
      .then(() => { if (!done && run === generation.current && !abort.signal.aborted) dispatch({ event: 'error', data: { code: 'STREAM_INTERRUPTED', message: 'Kết nối trợ lý bị ngắt. Bạn có thể thử lại hoặc đặt món từ Menu.', retryable: true } }); })
      .catch(e => { if (run === generation.current && !abort.signal.aborted) dispatch({ event: 'error', data: { code: e instanceof ApiError ? e.code : 'MODEL_UNAVAILABLE', message: e instanceof Error ? e.message : 'Trợ lý tạm thời không khả dụng', retryable: true } }); })
      .finally(() => { if (active.current === abort) active.current = null; });
  }
  async function draftAction(id: string, action: 'confirm' | 'discard') {
    const entry = latest.current.drafts[id]; if (!entry || entry.status !== 'open' || draftLocks.current.has(id)) return;
    draftLocks.current.add(id); const run = generation.current;
    try { await runDraftAction(api, entry, action, patch => { if (run === generation.current) dispatch({ event: 'draft_update', data: { id, patch } }); }); }
    finally { draftLocks.current.delete(id); }
  }
  return { state, send, confirmDraft: (id: string) => draftAction(id, 'confirm'), discardDraft: (id: string) => draftAction(id, 'discard'), newConversation: () => { if (draftLocks.current.size) return; generation.current++; active.current?.abort(); active.current = null; resetConversation(); dispatch({ event: 'reset', data: null }); } };
}
