import { useEffect, useState } from 'react';
import { ThinkingOrb } from 'thinking-orbs';
import type { AgentState } from '../api/types';
export const ORB_STATE: Record<AgentState, 'breathing' | 'connecting' | 'searching' | 'working' | 'composing'> = { idle: 'breathing', thinking: 'connecting', searching: 'searching', working: 'working', composing: 'composing', error: 'breathing' };
export const ORB_LABEL: Record<AgentState, string> = { idle: 'Sẵn sàng', thinking: 'Đang suy nghĩ', searching: 'Đang tra cứu', working: 'Đang chuẩn bị đơn nháp', composing: 'Đang trả lời', error: 'Có lỗi' };
export function AgentOrb({ state, size = 64 }: { state: AgentState; size?: 64 | 20 }) {
  const [reduced, setReduced] = useState(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false);
  useEffect(() => { const query = window.matchMedia?.('(prefers-reduced-motion: reduce)'); if (!query) return; const update = () => setReduced(query.matches); query.addEventListener('change', update); return () => query.removeEventListener('change', update); }, []);
  return <span className="agent-orb" role="img" aria-label={ORB_LABEL[state]}><ThinkingOrb state={ORB_STATE[state]} size={size} theme="light" paused={state === 'error' || reduced} aria-hidden="true" /></span>;
}
