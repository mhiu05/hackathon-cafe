import { useEffect, useReducer } from 'react';
import { cartReducer, type CartLine, type CartAction } from '../../lib/cart';
const KEY = 'biblio.cart';
function load(): CartLine[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    if (!Array.isArray(value)) return [];
    return value.reduce<CartLine[]>((lines, line: unknown) => {
      if (!line || typeof line !== 'object') return lines;
      const l = line as Record<string, unknown>;
      if (typeof l.item_id !== 'string' || typeof l.name !== 'string' || typeof l.unit_price_vnd !== 'number' || typeof l.quantity !== 'number' || !(l.variant_id === null || typeof l.variant_id === 'string')) return lines;
      return cartReducer(lines, { type: 'add', line: { item_id: l.item_id, variant_id: l.variant_id, name: l.name, variant_label: typeof l.variant_label === 'string' ? l.variant_label : null, unit_price_vnd: l.unit_price_vnd, quantity: l.quantity, note: typeof l.note === 'string' ? l.note : null } });
    }, []);
  } catch { return []; }
}
export function useCart() {
  const [lines, dispatch] = useReducer(cartReducer, undefined, load);
  useEffect(() => localStorage.setItem(KEY, JSON.stringify(lines)), [lines]);
  return { lines, add: (line: Omit<CartLine, 'key'>) => dispatch({ type: 'add', line }), setQty: (key: string, quantity: number) => dispatch({ type: 'setQty', key, quantity }), remove: (key: string) => dispatch({ type: 'remove', key }), clear: () => dispatch({ type: 'clear' } as CartAction), count: lines.reduce((s, l) => s + l.quantity, 0), totalEstimateVnd: lines.reduce((s, l) => s + l.quantity * l.unit_price_vnd, 0) };
}
