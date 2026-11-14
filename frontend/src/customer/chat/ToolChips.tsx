import { AgentOrb } from '../../ui/AgentOrb';
import type { AgentState } from '../../api/types';
import type { ChatState } from '../state/chatReducer';
export function ToolChips({ tools, state }: { tools: ChatState['tools']; state: AgentState }) {
  return <ul className="tool-chips" aria-label="Hoạt động công cụ">{Object.entries(tools).map(([id, tool]) => <li key={id} className={tool.status === 'error' ? 'danger' : ''}>{tool.status === 'running' ? <AgentOrb size={20} state={state} /> : <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d={tool.status === 'ok' ? 'M3 8l3 3 7-7' : 'M4 4l8 8M12 4l-8 8'} /></svg>}<span>{tool.label}{tool.summary ? ` · ${tool.summary}` : tool.status === 'running' ? '…' : tool.status === 'error' ? ' · Có lỗi' : ''}</span></li>)}</ul>;
}
