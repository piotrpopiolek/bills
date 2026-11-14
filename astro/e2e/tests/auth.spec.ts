import { expect, test } from '@playwright/test';

import { cleanupMagicLink, issueMagicLink } from '../fixtures/magic-link';
import { AuthPage } from '../page-objects/AuthPage';
import { BillsPage } from '../page-objects/BillsPage';

test('magic link opens a read-only bills list', async ({ page }) => {
  const token = await issueMagicLink();
  const writes: string[] = [];
  page.on('request', (request) => {
    const method = request.method();
    if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') {
      return;
    }
    const url = request.url();
    if (/\/api\/bills|\/ocr|api\.telegram\.org|generativelanguage/i.test(url)) {
      writes.push(`${method} ${url}`);
    }
  });

  try {
    const auth = new AuthPage(page);
    await auth.gotoVerify(token);
    await expect(auth.heading()).toBeVisible();
    await page.waitForURL('**/dashboard');

    const bills = new BillsPage(page);
    await bills.goto();
    await expect(bills.heading()).toBeVisible();
    await expect(bills.amount('12.50 zł')).toBeVisible();
    await expect(bills.createControl()).toHaveCount(0);
    expect(await page.content()).not.toContain(token);
    expect(writes).toEqual([]);
  } finally {
    await cleanupMagicLink();
  }
});
