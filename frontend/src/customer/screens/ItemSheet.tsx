import { useState } from 'react';
import type { MenuItem } from '../../api/types';
import type { CartLine } from '../../lib/cart';
import { formatVnd } from '../../lib/format';
import { Badge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { Sheet } from '../../ui/Sheet';
export function ItemSheet({ item, onAdd, onClose }: { item: MenuItem; onAdd: (line: Omit<CartLine, 'key'>) => void; onClose: () => void }) {
  const [variantId, setVariantId] = useState<string | null>(null), [quantity, setQuantity] = useState(1), [note, setNote] = useState('');
  const variant = item.variants.find(v => v.id === variantId);
  const blocked = !item.is_orderable || item.availability === 'sold_out' || (item.variants.length > 0 && !variant);
  return <Sheet title={item.name} onClose={onClose}><Badge availability={item.availability} orderable={item.is_orderable} />{item.description && <p>{item.description}</p>}
    {item.variants.length > 0 && <fieldset><legend>Chọn loại</legend>{item.variants.map(v => <label className="radio-label" key={v.id}><input type="radio" name="variant" value={v.id} checked={variantId === v.id} onChange={() => setVariantId(v.id)} />{v.label} · {formatVnd(v.price_vnd)}</label>)}</fieldset>}
    <label htmlFor="item-qty">Số lượng</label><input id="item-qty" type="number" min="1" max="10" value={quantity} onChange={e => setQuantity(Math.max(1, Math.min(10, Number(e.target.value) || 1)))} />
    <label htmlFor="item-note">Ghi chú món</label><textarea id="item-note" maxLength={120} value={note} onChange={e => setNote(e.target.value)} />
    {item.suggested_tags.length > 0 && <p className="muted"><small>Gợi ý theo tên món: {item.suggested_tags.join(', ')}</small></p>}
    {!item.price_verified && <p className="warning"><small>Giá đang chờ quán xác nhận.</small></p>}
    <div className="sheet-footer"><span className="price">{formatVnd((variant?.price_vnd ?? item.price_min_vnd) * quantity)}</span><Button disabled={blocked} onClick={() => { onAdd({ item_id: item.id, variant_id: variantId, name: item.name, variant_label: variant?.label ?? null, unit_price_vnd: variant?.price_vnd ?? item.price_min_vnd, quantity, note: note.trim() || null }); onClose(); }}>Thêm vào giỏ</Button></div>
  </Sheet>;
}
