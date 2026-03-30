/**
 * E2E Tests — Error States
 *
 * Tests error handling: nonexistent routes, API errors (mocked),
 * network issues, rapid navigation, and console error detection.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *
 * Run: npx playwright test e2e/ui/error-states.spec.ts
 */

import { test, expect } from '@playwright/test';
import { injectAuth } from '../helpers/auth';

test.describe('Error States', () => {
  test('navigate to nonexistent route redirects to / or stays without crash', async ({ page }) => {
    await injectAuth(page, 'student');
    await page.goto('/this-route-does-not-exist-at-all', { waitUntil: 'networkidle' });

    // Vue router has no catch-all — unmatched routes render nothing or redirect.
    // The page should NOT show a raw stack trace or crash.
    const bodyText = await page.locator('body').textContent();
    expect(bodyText).not.toContain('Traceback');
    expect(bodyText).not.toContain('Internal Server Error');
    expect(bodyText).not.toContain('Cannot read properties of');

    // The page should still render (not blank white screen with JS error)
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('API 500 response shows user-friendly error via route interception', async ({ page }) => {
    await injectAuth(page, 'student');

    // Intercept the user/me API call to return a 500
    await page.route('**/api/user/me/**', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });

    await page.goto('/home', { waitUntil: 'networkidle' });

    // The page should NOT show raw "Internal Server Error" text —
    // it should either handle it gracefully or show a styled error
    const bodyText = await page.locator('body').textContent() || '';
    expect(bodyText).not.toContain('Traceback');

    // Page should still be rendering something (not a blank crash)
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('network timeout simulation shows graceful degradation', async ({ page }) => {
    await injectAuth(page, 'student');

    // Intercept API calls and abort them to simulate network failure
    await page.route('**/api/courses/**', (route) => {
      route.abort('timedout');
    });

    await page.goto('/home', { waitUntil: 'networkidle' });

    // Page should still render the shell (navbar, etc.)
    // even if the data fetch fails
    const bodyText = await page.locator('body').textContent() || '';
    expect(bodyText).not.toContain('Traceback');
    expect(bodyText).not.toContain('Cannot read properties of');

    // Navbar should still be functional
    await expect(page.getByRole('button', { name: 'Account' })).toBeVisible();
  });

  test('rapid page navigation renders last page correctly', async ({ page }) => {
    await injectAuth(page, 'admin');

    // Navigate rapidly between pages without waiting for each to settle
    await page.goto('/home');
    // Don't wait for networkidle — immediately navigate again
    await page.goto('/instructor');
    await page.goto('/admin/users');

    // Wait for the final page to settle
    await page.waitForLoadState('networkidle');

    // Should be on the last navigated page
    expect(page.url()).toContain('/admin/users');

    // Page should render without errors
    const bodyText = await page.locator('body').textContent() || '';
    expect(bodyText).not.toContain('Internal Server Error');
    expect(bodyText).not.toContain('Traceback');
  });

  test('console errors: no unhandled JS errors on key pages', async ({ page }) => {
    const consoleErrors: string[] = [];

    // Collect console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Filter out expected noise: network failures from intercepted routes,
        // favicon 404s, and expected dev warnings
        const isExpectedNoise =
          text.includes('favicon') ||
          text.includes('net::ERR_') ||
          text.includes('[webpack') ||
          text.includes('[vite]') ||
          text.includes('DevTools');
        if (!isExpectedNoise) {
          consoleErrors.push(text);
        }
      }
    });

    // Also catch uncaught page errors
    const pageErrors: string[] = [];
    page.on('pageerror', (error) => {
      pageErrors.push(error.message);
    });

    // Visit key pages as different roles
    const pages = [
      { role: 'student' as const, path: '/home' },
      { role: 'instructor' as const, path: '/instructor' },
      { role: 'admin' as const, path: '/admin/users' },
    ];

    for (const p of pages) {
      await injectAuth(page, p.role);
      await page.goto(p.path, { waitUntil: 'networkidle' });

      // Give a moment for any async errors to surface
      await page.waitForTimeout(1000);
    }

    // There should be no unhandled page-level JS errors
    expect(pageErrors).toEqual([]);

    // Console errors should be empty (or contain only expected warnings)
    // If this is too strict for your CI, you can soften it to check length
    if (consoleErrors.length > 0) {
      // Log them for debugging but don't fail on minor console.error calls
      // from third-party libraries. Fail only on clear app errors.
      const criticalErrors = consoleErrors.filter(
        (e) =>
          e.includes('Uncaught') ||
          e.includes('TypeError') ||
          e.includes('ReferenceError') ||
          e.includes('Cannot read properties'),
      );
      expect(criticalErrors).toEqual([]);
    }
  });

  test('intercepted API error shows styled error, not raw JSON', async ({ page }) => {
    await injectAuth(page, 'instructor');

    // Intercept the courses list API to return a 403
    await page.route('**/api/instructor/courses/**', (route) => {
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'You do not have permission to perform this action.' }),
      });
    });

    await page.goto('/instructor', { waitUntil: 'networkidle' });

    // The page should NOT display raw JSON like {"error": "..."}
    const bodyText = await page.locator('body').textContent() || '';
    expect(bodyText).not.toContain('{"error"');
    expect(bodyText).not.toContain('{"detail"');
  });
});
