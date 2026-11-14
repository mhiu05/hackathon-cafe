import { test, expect } from '@playwright/test';
test('live agent recommendation → draft → REST confirm → admin → real order status', async ({ browser }) => {
  test.skip(process.env.E2E_AGENT_LIVE !== '1' || !process.env.E2E_ADMIN_PIN, 'Explicit opt-in only: at most three real model turns, no retries.');
  test.setTimeout(180000);
  const customer = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const staff = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  try {
    await customer.goto('/'); await customer.getByRole('button', { name: 'Trợ lý', exact: true }).click();
    const send = async (text: string) => { await customer.getByLabel('Nhắn Biblio').fill(text); await customer.getByRole('button', { name: 'Gửi', exact: true }).click(); };
    await send('Quán có chỗ yên tĩnh ngồi học không? Wi-Fi thế nào? Gợi ý 2 đồ uống không quá 50.000đ từ menu, chưa đặt món.');
    await expect(customer.locator('.message.assistant').first()).toBeVisible({ timeout: 60000 });
    await expect(customer.getByLabel('Nhắn Biblio')).toBeEnabled({ timeout: 60000 });
    await expect(customer.getByRole('list', { name: 'Hoạt động công cụ' })).toContainText(/gợi ý|món|quán/i);
    await send('Lấy một Trà chanh gừng mật ong nhé. Chuẩn bị đơn nháp để mình xác nhận.');
    await expect(customer.getByRole('heading', { name: 'Đơn nháp của bạn' })).toBeVisible({ timeout: 60000 });
    await expect(customer.locator('.draft-slip')).toContainText('Trà chanh gừng mật ong');
    await expect(customer.locator('.draft-slip .receipt-total')).toContainText('45.000đ');
    await customer.getByRole('button', { name: 'Xác nhận đặt món', exact: true }).click();
    const orderCard = customer.locator('.confirmed-order'); await expect(orderCard).toBeVisible();
    const code = (await orderCard.getByRole('heading').textContent())!;
    await staff.goto('/admin.html'); await staff.getByLabel('Mã PIN').fill(process.env.E2E_ADMIN_PIN!); await staff.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    const slip = staff.locator('.admin-slip').filter({ has: staff.getByRole('heading', { name: code, exact: true }) });
    await slip.getByRole('button', { name: 'Nhận đơn', exact: true }).click(); await slip.getByRole('button', { name: 'Đang pha', exact: true }).click(); await slip.getByRole('button', { name: 'Sẵn sàng', exact: true }).click();
    await customer.getByRole('link', { name: 'Theo dõi đơn', exact: true }).click();
    await expect(customer.locator('#main-content h2').first()).toContainText('Sẵn sàng', { timeout: 2000 });
    await customer.getByRole('button', { name: 'Trợ lý', exact: true }).click(); await send(`Đơn ${code} của mình xong chưa? Hãy tra trạng thái thực tế.`);
    await expect(customer.locator('.message.assistant:not(.streaming)')).toHaveCount(3, { timeout: 60000 });
    await expect(customer.locator('.message.assistant:not(.streaming)').last()).toContainText(/sẵn sàng/i, { timeout: 60000 });
    await expect(customer.getByLabel('Nhắn Biblio')).toBeEnabled({ timeout: 60000 });
    await customer.screenshot({ path: 'test-results/live-agent-390.png', fullPage: true });
    console.log(`LIVE AGENT ${code}: recommendation, server draft, REST confirmation, staff ready, tool-backed status verified; 3 model turns`);
  } finally { await customer.close(); await staff.close(); }
});
