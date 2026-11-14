import { expect, it } from 'vitest';
import { formatVnd, formatTime } from './format';
it('formats integer VND and UTC timestamps in Vietnam time', () => {
  expect(formatVnd(45000)).toBe('45.000đ');
  expect(formatVnd(1100000)).toBe('1.100.000đ');
  expect(formatTime('2026-11-14T09:05:00.000Z')).toBe('16:05');
});
