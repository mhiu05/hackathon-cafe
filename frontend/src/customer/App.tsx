import { useEffect, useRef, useState } from 'react';
import { api as defaultApi } from '../api';
import type { ApiClient } from '../api/client';
import type { CafeProfile } from '../api/types';
import { Discover } from './screens/Discover';
import { Menu } from './screens/Menu';
import { Cart } from './screens/Cart';
import { useCart } from './state/useCart';
import { Skeleton } from '../ui/Skeleton';
import { Toast } from '../ui/Toast';
import { OrderTracking } from './screens/OrderTracking';
import { ChatPanel } from './chat/ChatPanel';
import { useEntrance } from '../ui/useMotion';
type Tab = 'discover' | 'menu' | 'chat' | 'cart';
export function App({ api = defaultApi }: { api?: ApiClient }) {
  const [tab, setTab] = useState<Tab>('discover'), [cafe, setCafe] = useState<CafeProfile | null>(null), [error, setError] = useState(''), [retry, setRetry] = useState(0), [notice, setNotice] = useState('');
  const [orderCode, setOrderCode] = useState(() => new URLSearchParams(location.search).get('order'));
  const [mobile, setMobile] = useState(() => window.matchMedia?.('(max-width: 1023px)').matches ?? true);
  const chatRegion = useRef<HTMLElement>(null); const mobileChat = mobile && tab === 'chat';
  const content = useRef<HTMLElement>(null), cartButton = useRef<HTMLButtonElement>(null);
  const cart = useCart();
  useEntrance(content, [tab, orderCode, !!cafe]);
  useEntrance(chatRegion, [mobileChat, !!cafe], { duration: .26, y: 12 });
  useEntrance(cartButton, [cart.count], { y: 0, scale: 1.08 });
  useEffect(() => { let active = true; setError(''); api.getCafe().then(d => { if (active) setCafe(d); }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Không kết nối được máy chủ'); }); return () => { active = false; }; }, [api, retry]);
  useEffect(() => { const update = () => setOrderCode(new URLSearchParams(location.search).get('order')); window.addEventListener('popstate', update); return () => window.removeEventListener('popstate', update); }, []);
  useEffect(() => { const media = window.matchMedia?.('(max-width: 1023px)'); if (!media) return; const update = () => setMobile(media.matches); media.addEventListener('change', update); return () => media.removeEventListener('change', update); }, []);
  useEffect(() => {
    if (!mobileChat || !chatRegion.current) return;
    const region = chatRegion.current; const previous = document.activeElement as HTMLElement | null; const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden'; region.querySelector<HTMLButtonElement>('.mobile-chat-close')?.focus();
    const keydown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); setTab('menu'); return; }
      if (e.key !== 'Tab') return;
      const nodes = [...region.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], textarea:not(:disabled), input:not(:disabled), [tabindex="0"]')].filter(el => el.getClientRects().length > 0);
      const first = nodes[0], last = nodes.at(-1);
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    };
    region.addEventListener('keydown', keydown);
    return () => { region.removeEventListener('keydown', keydown); document.body.style.overflow = overflow; previous?.focus(); };
  }, [mobileChat]);
  function changeTab(next: Tab) { setTab(next); if (orderCode) { history.pushState({}, '', location.pathname); setOrderCode(null); } setNotice(''); }
  function openOrder(code: string) { history.pushState({}, '', `?order=${encodeURIComponent(code)}`); setOrderCode(code); }
  if (error) return <main className="connection-error"><h1 className="screen-heading">Không kết nối được máy chủ</h1><p role="alert">{error}</p><button onClick={() => setRetry(r => r + 1)}>Thử lại</button></main>;
  if (!cafe) return <main><Skeleton label="Đang mở Biblio…" /></main>;
  return <><a href="#main-content" className="skip-link" inert={mobileChat}>Đến nội dung</a><header className="customer-header" inert={mobileChat}><a className="brand" href="/">{cafe.brand_name.toUpperCase()} <span>Café Sách</span></a><small>{cafe.address.split(',')[0]}</small></header>
    {import.meta.env.VITE_API_MODE === 'mock' && <p className="mode-notice" role="status">Chế độ dữ liệu mẫu · chưa kết nối quán</p>}
    <div className="customer-layout"><main ref={content} id="main-content" className="customer-content" inert={mobileChat}>{notice && <Toast message={notice} />}
    {orderCode ? <OrderTracking key={orderCode} code={orderCode} api={api} /> : <><div hidden={tab !== 'discover'}><Discover cafe={cafe} onMenu={() => changeTab('menu')} onChat={() => changeTab('chat')} /></div><div hidden={tab !== 'menu'}><Menu api={api} onAdd={line => { if (cart.lines.length >= 10 && !cart.lines.some(l => l.item_id === line.item_id && l.variant_id === line.variant_id && l.note === line.note)) setNotice('Giỏ tối đa 10 dòng. Hãy điều chỉnh giỏ trước khi thêm.'); else { cart.add(line); setNotice(`Đã thêm ${line.name} vào giỏ`); } }} /></div><div hidden={tab !== 'cart'}><Cart cart={cart} api={api} onMenu={() => changeTab('menu')} onDone={o => openOrder(o.code)} /></div></>}
    </main><aside ref={chatRegion} className={`chat-sidebar ${tab === 'chat' ? 'is-open' : ''}`} role={mobileChat ? 'dialog' : undefined} aria-modal={mobileChat || undefined} aria-label="Trợ lý Biblio"><ChatPanel api={api} onMenu={() => changeTab('menu')} onClose={() => changeTab('menu')} onOpenOrder={code => { openOrder(code); setTab('menu'); }} /></aside></div>
    <nav className="bottom-nav" aria-label="Điều hướng chính" inert={mobileChat}>{([['discover', 'Khám phá'], ['menu', 'Menu'], ['chat', 'Trợ lý'], ['cart', `Giỏ${cart.count ? ` · ${cart.count}` : ''}`]] as const).map(([value, label]) => <button ref={value === 'cart' ? cartButton : undefined} key={value} aria-current={tab === value && !orderCode ? 'page' : undefined} onClick={() => changeTab(value)}>{label}</button>)}</nav></>;
}
