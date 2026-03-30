import { Page, expect } from '@playwright/test';
import { injectAuth } from './auth';

/** Navigate to a page with auth injected. */
export async function navigateAs(
  page: Page,
  role: 'student' | 'student2' | 'instructor' | 'admin',
  path: string,
): Promise<void> {
  await injectAuth(page, role);
  await page.goto(path, { waitUntil: 'networkidle' });
}

/** Wait for text content to appear. */
export async function waitForContent(page: Page, text: string, timeout = 10000): Promise<void> {
  await page.getByText(text).first().waitFor({ state: 'visible', timeout });
}

/** Assert no server errors visible on page. */
export async function expectNoErrors(page: Page): Promise<void> {
  const body = await page.locator('body').textContent();
  expect(body).not.toContain('Internal Server Error');
  expect(body).not.toContain('Traceback');
  expect(body).not.toContain('500');
}
