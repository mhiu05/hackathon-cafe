import { useEffect, useRef, useState } from 'react';
import { api as defaultApi } from '../../api';
import type { ApiClient } from '../../api/client';
import type { Availability, MenuItem, MenuResponse, UpdateMenuItemRequest } from '../../api/types';
import { formatVnd } from '../../lib/format';
import { Skeleton } from '../../ui/Skeleton';
const choices: [Availability, string][] = [['available', 'Còn'], ['sold_out', 'Hết'], ['unknown', 'Chưa xác nhận']];
export function MenuAvailability({ api = defaultApi }: { api?: ApiClient }) {
  const [menu, setMenu] = useState<MenuResponse | null>(null), [error, setError] = useState(''), [pending, setPending] = useState<string | null>(null), [retry, setRetry] = useState(0), [notice, setNotice] = useState('');
  const lock = useRef(false);
  useEffect(() => { let active = true; setError(''); api.getMenu().then(m => { if (active) setMenu(m); }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Không tải được menu'); }); return () => { active = false; }; }, [api, retry]);
  async function update(item: MenuItem, req: UpdateMenuItemRequest) {
    if (lock.current) return; lock.current = true; setPending(item.id); setError(''); setNotice('');
    try { const saved = await api.admin.updateMenuItem(item.id, req); setMenu(old => old ? { ...old, items: old.items.map(i => i.id === saved.id ? saved : i) } : old); setNotice(`Đã cập nhật ${saved.name}`); }
    catch (e) { setError(e instanceof Error ? e.message : 'Chưa lưu được thay đổi. Vui lòng thử lại.'); }
    finally { lock.current = false; setPending(null); }
  }
  if (!menu) return error ? <><p role="alert" className="danger">{error}</p><button onClick={() => setRetry(r => r + 1)}>Thử lại</button></> : <Skeleton label="Đang tải menu tại quầy…" />;
  return <section className="availability-screen"><h1 className="screen-heading">Tình trạng món</h1><p className="muted">Cập nhật theo tình trạng thực tế tại quán. Khách sẽ thấy thông tin từ máy chủ.</p>{error && <p role="alert" className="danger">{error}</p>}<p role="status">{notice}</p>
    {menu.categories.map(category => <section key={category.id} className="availability-category"><h2>{category.name}</h2>{menu.items.filter(i => i.category_id === category.id).map(item => <div key={item.id} role="group" aria-label={item.name} className="availability-row"><div><strong>{item.name}</strong><p className="price">{formatVnd(item.price_min_vnd)}</p></div><div className="availability-controls"><div className="segmented">{choices.map(([value, label]) => <button key={value} aria-pressed={item.availability === value} disabled={pending !== null} onClick={() => void update(item, { availability: value })}>{label}</button>)}</div><label className="radio-label"><input type="checkbox" checked={item.is_orderable} disabled={pending !== null} onChange={e => void update(item, { is_orderable: e.target.checked })} />Cho phép đặt món</label>{pending === item.id && <small role="status">Đang lưu…</small>}</div></div>)}</section>)}
  </section>;
}
