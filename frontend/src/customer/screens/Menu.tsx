import { useEffect, useState } from 'react';
import { api as defaultApi } from '../../api';
import type { ApiClient } from '../../api/client';
import type { MenuResponse, MenuItem } from '../../api/types';
import type { CartLine } from '../../lib/cart';
import { foldVi } from '../../lib/fold';
import { formatDate, formatVnd } from '../../lib/format';
import { Badge } from '../../ui/Badge';
import { Chip } from '../../ui/Chip';
import { Skeleton } from '../../ui/Skeleton';
import { ItemSheet } from './ItemSheet';
export function Menu({ api = defaultApi, onAdd }: { api?: ApiClient; onAdd: (line: Omit<CartLine, 'key'>) => void }) {
  const [data, setData] = useState<MenuResponse | null>(null), [error, setError] = useState(''), [retry, setRetry] = useState(0);
  const [query, setQuery] = useState(''), [category, setCategory] = useState(''), [maxPrice, setMaxPrice] = useState(0), [item, setItem] = useState<MenuItem | null>(null);
  useEffect(() => { let active = true; setError(''); api.getMenu().then(d => { if (active) setData(d); }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Không tải được menu'); }); return () => { active = false; }; }, [api, retry]);
  if (error) return <section className="content-section"><p role="alert">{error}</p><button onClick={() => setRetry(r => r + 1)}>Thử lại</button></section>;
  if (!data) return <Skeleton label="Đang mở thực đơn…" />;
  const tokens = foldVi(query).trim().split(/\s+/).filter(Boolean);
  const items = data.items.filter(i => (!category || i.category_id === category) && tokens.every(t => foldVi(i.name).includes(t)) && (!maxPrice || i.price_min_vnd <= maxPrice));
  return <section className="content-section menu-screen"><div className="section-heading"><h1 className="screen-heading">Thực đơn</h1><small>{data.items.length} món</small></div><p className="muted">Chọn một món cho buổi ghé Biblio.</p>
    <div className="category-tabs" aria-label="Danh mục món"><Chip aria-pressed={!category} onClick={() => setCategory('')}>Tất cả</Chip>{data.categories.map(c => <Chip key={c.id} aria-pressed={category === c.id} onClick={() => setCategory(c.id)}>{c.name}</Chip>)}</div>
    <label className="sr-only" htmlFor="menu-search">Tìm món</label><input id="menu-search" type="search" placeholder="Tìm món bạn thích…" value={query} onChange={e => setQuery(e.target.value)} />
    <div className="price-filters" aria-label="Lọc giá">{[0, 35000, 45000, 55000].map(p => <Chip key={p} aria-pressed={maxPrice === p} onClick={() => setMaxPrice(p)}>{p ? `≤ ${formatVnd(p)}` : 'Mọi mức giá'}</Chip>)}</div>
    {!items.length && <p role="status">Chưa tìm thấy món phù hợp. Thử tên hoặc mức giá khác.</p>}
    {data.categories.map(c => { const group = items.filter(i => i.category_id === c.id); return group.length > 0 && <section className="menu-category" key={c.id}><h2>{c.name}</h2>{group.map(i => <button key={i.id} className="menu-row" aria-disabled={!i.is_orderable || i.availability === 'sold_out'} onClick={() => { if (i.is_orderable && i.availability !== 'sold_out') setItem(i); }}><span className="price-row"><span className={i.availability === 'sold_out' ? 'sold-out' : ''}>{i.name}</span><span className="leader" /><span className="price">{i.price_min_vnd !== i.price_max_vnd ? `${formatVnd(i.price_min_vnd)}–${formatVnd(i.price_max_vnd)}` : formatVnd(i.price_min_vnd)}</span></span><span className="row-meta"><Badge availability={i.availability} orderable={i.is_orderable} />{i.variants.length > 0 && <small>{i.variants.map(v => v.label).join(' · ')}</small>}</span></button>)}</section>; })}
    <p className="data-notice">Giá theo menu {formatDate(data.as_of)} — chờ quán xác nhận. {data.price_basis}</p>{item && <ItemSheet key={item.id} item={item} onAdd={onAdd} onClose={() => setItem(null)} />}
  </section>;
}
