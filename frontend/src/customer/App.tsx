import { useEffect, useState } from 'react';
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
type Tab = 'discover' | 'menu' | 'chat' | 'cart';
export function App({ api = defaultApi }: { api?: ApiClient }) {
  const [tab, setTab] = useState<Tab>('discover'), [cafe, setCafe] = useState<CafeProfile | null>(null), [error, setError] = useState(''), [retry, setRetry] = useState(0), [notice, setNotice] = useState('');
  const [orderCode, setOrderCode] = useState(() => new URLSearchParams(location.search).get('order'));
  const cart = useCart();
  useEffect(() => { let active = true; setError(''); api.getCafe().then(d => { if (active) setCafe(d); }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Không kết nối được máy chủ'); }); return () => { active = false; }; }, [api, retry]);
  useEffect(() => { const update = () => setOrderCode(new URLSearchParams(location.search).get('order')); window.addEventListener('popstate', update); return () => window.removeEventListener('popstate', update); }, []);
  function changeTab(next: Tab) { setTab(next); if (orderCode) { history.pushState({}, '', location.pathname); setOrderCode(null); } setNotice(''); }
  function openOrder(code: string) { history.pushState({}, '', `?order=${encodeURIComponent(code)}`); setOrderCode(code); }
  if (error) return <main className="connection-error"><h1 className="screen-heading">Không kết nối được máy chủ</h1><p role="alert">{error}</p><button onClick={() => setRetry(r => r + 1)}>Thử lại</button></main>;
  if (!cafe) return <main><Skeleton label="Đang mở Biblio…" /></main>;
  return <><a href="#main-content" className="skip-link">Đến nội dung</a><header className="customer-header"><a className="brand" href="/">BIBLIO <span>Café Sách</span></a><small>79 Ngụy Như Kon Tum</small></header>
    {import.meta.env.VITE_API_MODE === 'mock' && <p className="mode-notice" role="status">Chế độ dữ liệu mẫu · chưa kết nối quán</p>}
    <div className="customer-layout"><main id="main-content" className="customer-content">{notice && <Toast message={notice} />}
    {orderCode ? <OrderTracking key={orderCode} code={orderCode} api={api} /> : <><div hidden={tab !== 'discover'}><Discover cafe={cafe} onMenu={() => changeTab('menu')} onChat={() => changeTab('chat')} /></div><div hidden={tab !== 'menu'}><Menu api={api} onAdd={line => { if (cart.lines.length >= 10 && !cart.lines.some(l => l.item_id === line.item_id && l.variant_id === line.variant_id && l.note === line.note)) setNotice('Giỏ tối đa 10 dòng. Hãy điều chỉnh giỏ trước khi thêm.'); else { cart.add(line); setNotice(`Đã thêm ${line.name} vào giỏ`); } }} /></div><div hidden={tab !== 'cart'}><Cart cart={cart} api={api} onMenu={() => changeTab('menu')} onDone={o => openOrder(o.code)} /></div></>}
    </main><aside className={`chat-sidebar ${tab === 'chat' ? 'is-open' : ''}`} aria-label="Trợ lý Biblio"><ChatPanel api={api} onMenu={() => changeTab('menu')} onClose={() => changeTab('menu')} onOpenOrder={code => { openOrder(code); setTab('menu'); }} /></aside></div>
    <nav className="bottom-nav" aria-label="Điều hướng chính">{([['discover', 'Khám phá'], ['menu', 'Menu'], ['chat', 'Trợ lý'], ['cart', `Giỏ${cart.count ? ` · ${cart.count}` : ''}`]] as const).map(([value, label]) => <button key={value} aria-current={tab === value && !orderCode ? 'page' : undefined} onClick={() => changeTab(value)}>{label}</button>)}</nav></>;
}
