import { useState } from 'react';
import { Button } from '../../ui/Button';
export function Composer({ busy, onSend }: { busy: boolean; onSend: (text: string) => void }) {
  const [text, setText] = useState('');
  function send() { if (busy || !text.trim()) return; onSend(text.trim()); setText(''); }
  return <form className="composer" onSubmit={e => { e.preventDefault(); send(); }}><label className="sr-only" htmlFor="chat-message">Nhắn Biblio</label><textarea id="chat-message" placeholder="Bạn muốn hỏi Biblio điều gì?" value={text} maxLength={1000} rows={2} onChange={e => setText(e.target.value)} disabled={busy} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }} /><div className="composer-footer"><small>{text.length}/1000</small><Button disabled={busy || !text.trim()} aria-busy={busy}>Gửi</Button></div></form>;
}
