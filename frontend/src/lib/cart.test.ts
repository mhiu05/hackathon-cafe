import { expect, it } from 'vitest';
import { cartReducer, toLineInputs, type CartLine } from './cart';
const line = { item_id: 'menu_002', variant_id: null, name: 'Bạc xỉu', variant_label: null, unit_price_vnd: 45000, quantity: 1, note: null };
it('merges matching item/variant/note and caps quantity at ten', () => {
  let s = cartReducer([], { type: 'add', line });
  s = cartReducer(s, { type: 'add', line: { ...line, quantity: 12 } });
  expect(s).toHaveLength(1); expect(s[0].quantity).toBe(10);
});
it('keeps notes separate and caps cart at ten lines', () => {
  let s: CartLine[] = [];
  for (let i = 0; i < 11; i++) s = cartReducer(s, { type: 'add', line: { ...line, note: `n${i}` } });
  expect(s).toHaveLength(10);
  expect(toLineInputs(s)[0]).toEqual({ item_id: 'menu_002', variant_id: null, quantity: 1, note: 'n0' });
});
it('updates quantity, removes lines and clears without mutating old state', () => {
  const s = cartReducer([], { type: 'add', line });
  expect(cartReducer(s, { type: 'setQty', key: s[0].key, quantity: 4 })[0].quantity).toBe(4);
  expect(s[0].quantity).toBe(1);
  expect(cartReducer(s, { type: 'remove', key: s[0].key })).toEqual([]);
  expect(cartReducer(s, { type: 'clear' })).toEqual([]);
});
