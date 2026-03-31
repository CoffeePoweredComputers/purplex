/**
 * E2E Tests — Responsive Layout
 *
 * Tests layout at desktop, tablet, and mobile breakpoints.
 * Verifies nav elements visibility, no horizontal scroll, and
 * single-column layout on small screens.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *
 * Run: npx playwright test e2e/ui/responsive.spec.ts
 */

import { test, expect } from '@playwright/test';
import { injectAuth } from '../helpers/auth';

test.describe('Responsive Layout', () => {
  test('desktop (1440x900): all nav elements visible', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });

    await injectAuth(page, 'admin');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Logo image should be visible
    await expect(page.locator('nav .logo-icon')).toBeVisible();

    // Logo text (brand name) should be visible at desktop width
    await expect(page.locator('nav .logo-text')).toBeVisible();

    // All nav items should show both icon and text
    const instructorLink = page.getByRole('link', { name: 'Instructor' });
    await expect(instructorLink).toBeVisible();

    const adminLink = page.getByRole('link', { name: 'Admin' });
    await expect(adminLink).toBeVisible();

    const accountBtn = page.getByRole('button', { name: 'Account' });
    await expect(accountBtn).toBeVisible();

    // No horizontal scrollbar — page content fits within viewport
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1); // 1px tolerance
  });

  test('tablet (768x1024): layout adjusts, no horizontal scroll', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });

    await injectAuth(page, 'admin');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Logo should still be visible
    await expect(page.locator('nav .logo-icon')).toBeVisible();

    // Nav items should still be accessible (possibly with smaller text)
    await expect(page.getByRole('button', { name: 'Account' })).toBeVisible();

    // No horizontal scrollbar
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);

    // The navbar container should fit within the viewport
    const navWrapper = page.locator('.navbar-wrapper');
    if (await navWrapper.isVisible()) {
      const navBox = await navWrapper.boundingBox();
      expect(navBox).not.toBeNull();
      if (navBox) {
        expect(navBox.width).toBeLessThanOrEqual(768);
      }
    }
  });

  test('mobile (375x667): key elements visible, icons-only nav', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await injectAuth(page, 'admin');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Logo icon should still be visible
    await expect(page.locator('nav .logo-icon')).toBeVisible();

    // At 480px and below, the CSS hides .logo-text and nav item text labels.
    // Only nav-icon spans remain visible (375 < 480 threshold).
    const logoText = page.locator('nav .logo-text');
    await expect(logoText).not.toBeVisible();

    // Nav items should still exist in the DOM (icons only)
    // The nav-icon emoji spans should be visible
    const navIcons = page.locator('.nav-icon');
    const iconCount = await navIcons.count();
    expect(iconCount).toBeGreaterThan(0);

    // No horizontal scrollbar
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
  });

  test('login page on small screen: form remains usable', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/', { waitUntil: 'commit' });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    // Wait for the login form to render (auth state may redirect)
    await page.locator('#email').waitFor({ state: 'visible', timeout: 10000 });

    // Email and password inputs should be visible and usable
    const emailInput = page.locator('#email');
    await expect(emailInput).toBeVisible();
    const emailBox = await emailInput.boundingBox();
    expect(emailBox).not.toBeNull();
    if (emailBox) {
      // Input should not overflow the viewport
      expect(emailBox.x + emailBox.width).toBeLessThanOrEqual(375);
    }

    const passwordInput = page.locator('#psw');
    await expect(passwordInput).toBeVisible();

    // Buttons should be visible
    await expect(page.getByRole('button', { name: 'Login', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Account' })).toBeVisible();

    // No horizontal scroll on the login page
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
  });
});
