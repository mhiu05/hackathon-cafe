import { test, expect } from '@playwright/test';
test('live catalog → checkout → admin accepts → customer sees status', async ({ browser, request }) => {
  test.skip(!process.env.E2E_ADMIN_PIN, 'Set E2E_ADMIN_PIN for the live backend; no fixture substitution.');
  const health = await request.get('/api/health'); expect(health.ok()).toBe(true);
  const catalog = await request.get('/api/menu'); expect((await catalog.json()).items).toHaveLength(51);
  const customer = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const staff = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  try {
    await customer.goto('/'); await customer.getByRole('button', { name: 'Xem menu', exact: true }).click();
    await expect(customer.getByText('51 món', { exact: true })).toBeVisible();
    await customer.getByRole('button', { name: /Bạc xỉu/ }).click(); await customer.getByRole('button', { name: 'Thêm vào giỏ' }).click();
    await customer.getByRole('button', { name: 'Giỏ · 1', exact: true }).click(); await customer.getByRole('button', { name: 'Xem tổng', exact: true }).click();
    const posted = customer.waitForRequest(r => r.method() === 'POST' && new URL(r.url()).pathname === '/api/orders');
    await customer.getByRole('button', { name: 'Đặt món', exact: true }).click();
    const checkoutRequest = await posted;
    const orderHeading = customer.getByRole('heading', { name: /^Đơn BB-/ }); await expect(orderHeading).toBeVisible();
    const code = (await orderHeading.textContent())!.replace('Đơn ', '');
    const replay = await request.post('/api/orders', { headers: { 'Idempotency-Key': checkoutRequest.headers()['idempotency-key'], 'X-Conversation-Id': checkoutRequest.headers()['x-conversation-id'] }, data: checkoutRequest.postDataJSON() });
    expect(replay.status()).toBe(200); expect(replay.headers()['idempotent-replay']).toBe('true'); expect((await replay.json()).code).toBe(code);
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
test('live admin saves menu availability and reads server insights', async ({ page }) => {
  test.skip(!process.env.E2E_ADMIN_PIN, 'Requires a real configured backend; no fixtures.');
  await page.goto('/admin.html'); await page.getByLabel('Mã PIN').fill(process.env.E2E_ADMIN_PIN!);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await page.getByRole('navigation', { name: 'Điều hướng quầy' }).getByRole('button', { name: 'Menu', exact: true }).click();
  const item = page.getByRole('group', { name: 'Trà xoài Yakult', exact: true });
  await item.getByRole('button', { name: 'Hết', exact: true }).click();
  await expect(item.getByRole('button', { name: 'Hết', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await item.getByRole('button', { name: 'Chưa xác nhận', exact: true }).click();
  await expect(item.getByRole('button', { name: 'Chưa xác nhận', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Tổng quan', exact: true }).click();
  await expect(page.getByRole('table', { name: 'Đơn theo trạng thái' })).toBeVisible();
  await expect(page.getByRole('table', { name: 'Hoạt động trợ lý' })).toBeVisible();
});
