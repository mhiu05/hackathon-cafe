import { useEffect, useRef } from 'react';
import type { ApiClient } from '../../api/client';
import { AgentOrb, ORB_LABEL } from '../../ui/AgentOrb';
import { useChat } from '../state/useChat';
import { MessageList } from './MessageList';
import { ToolChips } from './ToolChips';
import { DraftSlip } from './DraftSlip';
import { Composer } from './Composer';
export function ChatPanel({ api, onMenu, onClose, onOpenOrder }: { api?: ApiClient; onMenu: () => void; onClose: () => void; onOpenOrder: (code: string) => void }) {
  const chat = useChat(api); const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'nearest' }); }, [chat.state.messages.length, chat.state.streamingText]);
  const confirming = Object.values(chat.state.drafts).some(d => d.status === 'confirming');
  return <><header className="chat-heading"><AgentOrb state={chat.state.agentState} /><div><h2>Hỏi Biblio</h2><small>{ORB_LABEL[chat.state.agentState]}</small></div><button className="mobile-chat-close" onClick={onClose}>Đóng</button></header><button className="new-conversation" disabled={confirming} onClick={chat.newConversation}>Cuộc trò chuyện mới</button>
    <div className="chat-scroll">{!chat.state.messages.length && <section className="chat-welcome"><h3>Biblio ở đây.</h3><p>Bạn muốn tìm một món uống, hỏi về không gian hay theo dõi đơn?</p><div className="suggestion-list">{['Giờ mở cửa?', 'Gợi ý món dưới 50k', 'Phòng cho 20 người'].map(text => <button key={text} disabled={chat.state.busy} onClick={() => chat.send(text)}>{text}</button>)}</div><p className="muted"><small>Thông tin có nguồn tham khảo. Giá và tình trạng món chờ quán xác nhận.</small></p></section>}
    <MessageList state={chat.state} /><ToolChips tools={chat.state.tools} state={chat.state.agentState} />{Object.values(chat.state.drafts).map(entry => <DraftSlip key={entry.draft.draft_id} draft={entry.draft} entry={entry} api={api} onConfirm={() => chat.confirmDraft(entry.draft.draft_id)} onDiscard={() => chat.discardDraft(entry.draft.draft_id)} onOpenOrder={onOpenOrder} />)}
    {chat.state.error && <div className="chat-error" role="alert"><p>{chat.state.error.code === 'MODEL_UNAVAILABLE' ? 'Trợ lý tạm thời không khả dụng — bạn vẫn có thể đặt món từ Menu.' : chat.state.error.message}</p><button onClick={onMenu}>Mở Menu</button></div>}<div ref={end} /></div><Composer busy={chat.state.busy} onSend={chat.send} />
  </>;
}
