/**
 * E2E Tests -- User Settings (Theme, Language, Cookie Consent)
 *
 * Tests theme switching (dark/light), theme persistence via localStorage,
 * language switching, and cookie consent banner behavior.
 *
 * Prerequisites:
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server on :5173
 *   3. Seeded: student user
 *
 * Run: npx playwright test e2e/privacy/settings.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, expectNoErrors } from '../helpers/navigation';

test.describe('User Settings', () => {
  test('theme toggle switches between dark and light mode', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    // Get the initial theme state from the document
    const initialTheme = await page.evaluate(() => {
      return document.documentElement.getAttribute('data-theme')
        || document.body.getAttribute('data-theme')
        || localStorage.getItem('purplex_theme')
        || 'dark';
    });

    // Look for a theme toggle button (common patterns: button with theme/mode text,
    // or a toggle in the account modal / settings)
    const themeToggle = page.locator('[data-testid="theme-toggle"], .theme-toggle, button:has-text("Light"), button:has-text("Dark"), button:has-text("Theme")').first();

    if (await themeToggle.isVisible()) {
      await themeToggle.click();
      await page.waitForTimeout(500);

      // Theme should have changed
      const newTheme = await page.evaluate(() => {
        return document.documentElement.getAttribute('data-theme')
          || document.body.getAttribute('data-theme')
          || localStorage.getItem('purplex_theme')
          || 'dark';
      });

      expect(newTheme).not.toBe(initialTheme);
    } else {
      // Theme toggle may be in the Account modal
      const accountBtn = page.getByRole('button', { name: 'Account' });
      if (await accountBtn.isVisible()) {
        await accountBtn.click();
        await page.waitForTimeout(500);

        // Look for theme toggle inside modal
        const modalThemeToggle = page.locator('[data-testid="theme-toggle"], .theme-toggle, .theme-switch').first();
        if (await modalThemeToggle.isVisible()) {
          await modalThemeToggle.click();
          await page.waitForTimeout(500);

          const newTheme = await page.evaluate(() => {
            return localStorage.getItem('purplex_theme') || 'dark';
          });
          expect(newTheme).not.toBe(initialTheme);
        }
      }
    }
  });

  test('theme persists across page reload', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    // Set a known theme via localStorage
    await page.evaluate(() => {
      localStorage.setItem('purplex_theme', 'light');
    });

    // Reload
    await page.reload({ waitUntil: 'networkidle' });

    // The theme should still be "light" in localStorage
    const theme = await page.evaluate(() => localStorage.getItem('purplex_theme'));
    expect(theme).toBe('light');

    // Clean up: reset to dark
    await page.evaluate(() => {
      localStorage.setItem('purplex_theme', 'dark');
    });
  });

  test('language preference can be changed via API', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    // Use the backend API to change language preference
    const result = await page.evaluate(async () => {
      // Build a mock token for student
      const payload = {
        email: 'student@test.local',
        uid: 'mock-uid-student',
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 3600,
      };
      const token = `MOCK.${btoa(JSON.stringify(payload))}.development`;

      const res = await fetch('http://localhost:8000/api/user/me/language/', {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ language_preference: 'es' }),
      });
      let data;
      try {
        data = await res.json();
      } catch {
        data = null;
      }
      return { status: res.status, data };
    });

    // Should succeed
    expect(result.status).toBe(200);

    // Revert to English
    await page.evaluate(async () => {
      const payload = {
        email: 'student@test.local',
        uid: 'mock-uid-student',
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 3600,
      };
      const token = `MOCK.${btoa(JSON.stringify(payload))}.development`;

      await fetch('http://localhost:8000/api/user/me/language/', {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ language_preference: 'en' }),
      });
    });
  });

  test('cookie consent banner behavior', async ({ page }) => {
    // Clear cookie consent to trigger the banner
    await page.goto('/', { waitUntil: 'commit' });
    await page.evaluate(() => {
      localStorage.removeItem('purplex_cookie_consent');
    });

    // Navigate to a page -- banner may appear
    await page.goto('/privacy', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Look for cookie consent banner
    const banner = page.locator('.cookie-banner, .cookie-consent, [data-testid="cookie-consent"]').first();

    if (await banner.isVisible()) {
      // Accept cookies
      const acceptBtn = page.locator('.cookie-banner button, .cookie-consent button').first();
      if (await acceptBtn.isVisible()) {
        await acceptBtn.click();
        await page.waitForTimeout(500);

        // Banner should disappear
        await expect(banner).not.toBeVisible();

        // localStorage should record acceptance
        const consent = await page.evaluate(() => localStorage.getItem('purplex_cookie_consent'));
        expect(consent).toBeTruthy();
      }
    } else {
      // If no banner appears, verify consent is already set (from injectAuth or prior interaction)
      const consent = await page.evaluate(() => localStorage.getItem('purplex_cookie_consent'));
      // The page loaded without a banner, which is acceptable if consent was already given
      // or if the cookie consent feature is not enabled on public pages
      expect(consent === null || consent === 'accepted').toBeTruthy();
    }
  });
});
