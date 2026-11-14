import type { CartLineInput } from '../api/types';
export type CartLine = { key: string; item_id: string; variant_id: string | null; name: string; variant_label: string | null; unit_price_vnd: number; quantity: number; note: string | null };
export type CartAction = { type: 'add'; line: Omit<CartLine, 'key'> } | { type: 'setQty'; key: string; quantity: number } | { type: 'remove'; key: string } | { type: 'clear' };
export const MAX_LINES = 10, MAX_QTY = 10;
const qty = (n: number) => Math.max(1, Math.min(MAX_QTY, Number.isFinite(n) ? Math.trunc(n) : 1));
export function cartReducer(state: CartLine[], action: CartAction): CartLine[] {
  switch (action.type) {
    case 'clear': return [];
    case 'remove': return state.filter(l => l.key !== action.key);
    case 'setQty': return state.map(l => l.key === action.key ? { ...l, quantity: qty(action.quantity) } : l);
    case 'add': {
      const note = action.line.note?.trim().slice(0, 120) || null;
      const key = JSON.stringify([action.line.item_id, action.line.variant_id, note]);
      const old = state.find(l => l.key === key);
      if (old) return state.map(l => l.key === key ? { ...l, quantity: qty(l.quantity + action.line.quantity) } : l);
      return state.length < MAX_LINES ? [...state, { ...action.line, key, note, quantity: qty(action.line.quantity) }] : state;
    }
  }
}
export function toLineInputs(lines: CartLine[]): CartLineInput[] { return lines.map(({ item_id, variant_id, quantity, note }) => ({ item_id, variant_id, quantity, note })); }
