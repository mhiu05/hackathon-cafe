import { useLayoutEffect, useRef, useState } from 'react';
const MAX = 1000; const COUNTER_FROM = 800; const MAX_HEIGHT = 140;
export function Composer({ busy, onSend }: { busy: boolean; onSend: (text: string) => void }) {
  const [text, setText] = useState(''); const area = useRef<HTMLTextAreaElement>(null);
  // Grow with the message (one line by default) so the conversation keeps most of the panel.
  useLayoutEffect(() => { const el = area.current; if (!el) return; el.style.height = 'auto'; el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`; }, [text]);
  function send() { if (busy || !text.trim()) return; onSend(text.trim()); setText(''); }
  return <form className="composer" onSubmit={e => { e.preventDefault(); send(); }}><label className="sr-only" htmlFor="chat-message">Nhắn Biblio</label>
    <div className="composer-box"><textarea ref={area} id="chat-message" placeholder="Bạn muốn hỏi Biblio điều gì?" value={text} maxLength={MAX} rows={1} onChange={e => setText(e.target.value)} disabled={busy} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }} />
      <button type="submit" className="composer-send" disabled={busy || !text.trim()} aria-busy={busy} aria-label="Gửi" title="Gửi"><svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M10 16V4M5 9l5-5 5 5" /></svg></button></div>
    {text.length >= COUNTER_FROM && <small className="composer-count">{text.length}/{MAX}</small>}</form>;
}
