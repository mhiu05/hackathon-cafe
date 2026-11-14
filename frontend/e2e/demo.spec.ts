import { test, expect } from '@playwright/test';
test('live catalog → checkout → admin accepts → customer sees status', async ({ browser, request }) => {
  test.skip(!process.env.E2E_ADMIN_PIN, 'Set E2E_ADMIN_PIN for the live backend; no fixture substitution.');
  const health = await request.get('/api/health'); expect(health.ok()).toBe(true);
  const catalog = await request.get('/api/menu'); expect((await catalog.json()).items).toHaveLength(51);
  const customer = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const staff = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  try {
    await customer.goto('/'); await customer.getByRole('button', { name: 'Xem menu', exact: true }).click();
    await customer.getByRole('button', { name: /Bạc xỉu/ }).click(); await customer.getByRole('button', { name: 'Thêm vào giỏ' }).click();
    await customer.getByRole('button', { name: 'Giỏ · 1', exact: true }).click(); await customer.getByRole('button', { name: 'Xem tổng', exact: true }).click();
    await customer.getByRole('button', { name: 'Đặt món', exact: true }).click();
    const orderHeading = customer.getByRole('heading', { name: /^Đơn BB-/ }); await expect(orderHeading).toBeVisible();
    const code = (await orderHeading.textContent())!.replace('Đơn ', '');
    await expect(customer.getByRole('heading', { name: 'Chờ quán xác nhận', exact: true })).toBeVisible();
    await staff.goto('/admin.html'); await staff.getByLabel('Mã PIN').fill(process.env.E2E_ADMIN_PIN!);
    await staff.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    const slip = staff.locator('.admin-slip').filter({ has: staff.getByRole('heading', { name: code, exact: true }) });
    await expect(slip).toBeVisible(); const started = Date.now();
    await slip.getByRole('button', { name: 'Nhận đơn', exact: true }).click();
    await expect(customer.getByRole('heading', { name: 'Quán đã nhận đơn', exact: true })).toBeVisible({ timeout: 2000 });
    console.log(`LIVE ${code}: customer confirmation latency ${Date.now() - started}ms`);
    await customer.screenshot({ path: 'test-results/live-order-390.png', fullPage: true });
    await staff.screenshot({ path: 'test-results/live-admin-1280.png', fullPage: true });
  } finally { await customer.close(); await staff.close(); }
});
