import { expect, it } from 'vitest';
import { foldVi } from './fold';
it('folds Vietnamese accents and Đ for search', () => {
  expect(foldVi('Trà thạch ĐÀO')).toBe('tra thach dao');
});
