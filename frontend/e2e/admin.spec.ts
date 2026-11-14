import { test, expect } from '@playwright/test';
import admin from '../../contracts/fixtures/admin_orders.json' with { type: 'json' };
test('PIN errors, bearer requests and allowed order transitions (fixture API)', async ({ page }) => {
  let attempts = 0;
  await page.route('**/api/admin/login', route => route.fulfill(++attempts === 1 ? { status: 401, json: { error: { code: 'ADMIN_AUTH_REQUIRED', message: 'Sai PIN' } } } : { json: { token: 'fixture-token', expires_at: '2026-11-15T00:00:00Z' } }));
  await page.route('**/api/admin/orders', route => { expect(route.request().headers()['authorization']).toBe('Bearer fixture-token'); return route.fulfill({ json: admin }); });
  await page.route('**/api/admin/stream', route => route.fulfill({ contentType: 'text/event-stream', body: ': ping\n\n' }));
  await page.route('**/api/admin/orders/2/status', route => {
    expect(route.request().postDataJSON()).toEqual({ to_status: 'confirmed', expected_status: 'pending' });
    return route.fulfill({ json: { ...admin.orders[0], status: 'confirmed', status_label: 'Quán đã nhận đơn', allowed_next: ['preparing', 'ready', 'cancelled'], updated_at: '2026-11-14T11:00:00Z' } });
  });
  await page.setViewportSize({ width: 1280, height: 900 }); await page.goto('/admin.html');
  await page.getByLabel('Mã PIN').fill('fixture-pin'); await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText('Mã PIN không đúng');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  const incoming = page.getByRole('region', { name: 'Mới', exact: true });
  await expect(incoming.getByRole('heading', { name: 'BB-0002', exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/admin-1280.png', fullPage: true });
  await incoming.getByRole('button', { name: 'Nhận đơn', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Đã nhận', exact: true }).getByRole('heading', { name: 'BB-0002', exact: true })).toBeVisible();
  await expect(incoming.getByText('Chưa có đơn')).toBeVisible();
});
