/**
 * E2E Tests — Navigation
 *
 * Tests navbar rendering per role, AccountModal open/close, and logo navigation.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *
 * Run: npx playwright test e2e/ui/navigation.spec.ts
 */

import { test, expect } from '@playwright/test';
import { injectAuth } from '../helpers/auth';

test.describe('Navigation', () => {
  test('student navbar: Logo + Account button, no Instructor/Admin', async ({ page }) => {
    await injectAuth(page, 'student');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Logo should be visible (the logo image in the navbar)
    const logo = page.locator('nav .logo-icon');
    await expect(logo).toBeVisible();

    // Account button should be visible
    await expect(page.getByRole('button', { name: 'Account' })).toBeVisible();

    // Instructor and Admin links should NOT be visible
    await expect(page.getByRole('link', { name: 'Instructor' })).not.toBeVisible();
    await expect(page.getByRole('link', { name: 'Admin' })).not.toBeVisible();
  });

  test('instructor navbar: Logo + Instructor link + Account', async ({ page }) => {
    await injectAuth(page, 'instructor');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Logo visible
    await expect(page.locator('nav .logo-icon')).toBeVisible();

    // Instructor link should be visible
    await expect(page.getByRole('link', { name: 'Instructor' })).toBeVisible();

    // Account button should be visible
    await expect(page.getByRole('button', { name: 'Account' })).toBeVisible();

    // Admin link should NOT be visible for regular instructor
    await expect(page.getByRole('link', { name: 'Admin' })).not.toBeVisible();
  });

  test('admin navbar: Logo + Instructor + Admin + Account', async ({ page }) => {
    await injectAuth(page, 'admin');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Logo visible
    await expect(page.locator('nav .logo-icon')).toBeVisible();

    // Both Instructor and Admin links visible
    await expect(page.getByRole('link', { name: 'Instructor' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Admin' })).toBeVisible();

    // Account button visible
    await expect(page.getByRole('button', { name: 'Account' })).toBeVisible();
  });

  test('AccountModal opens when clicking account button', async ({ page }) => {
    await injectAuth(page, 'student');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Click Account button
    await page.getByRole('button', { name: 'Account' }).click();

    // Modal should appear with dialog role
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();

    // Modal should show "Account Settings" title
    await expect(modal.getByText('Account Settings')).toBeVisible();

    // Modal should show the user email
    await expect(modal.getByText('student@test.local')).toBeVisible();

    // Modal should show Account Type with role badge
    await expect(modal.getByText('Account Type')).toBeVisible();

    // Modal should have Sign Out button
    await expect(modal.getByRole('button', { name: 'Sign Out' })).toBeVisible();

    // Modal should have Privacy Settings link
    await expect(modal.getByText('Privacy Settings')).toBeVisible();
  });

  test('AccountModal closes on close button click', async ({ page }) => {
    await injectAuth(page, 'student');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Open modal
    await page.getByRole('button', { name: 'Account' }).click();
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();

    // Click the close button (the x button in modal header)
    await page.locator('.close-button').click();

    // Modal should be hidden
    await expect(modal).not.toBeVisible();
  });

  test('logo click navigates to /home', async ({ page }) => {
    await injectAuth(page, 'instructor');

    // Navigate to a non-home page first
    await page.goto('/instructor', { waitUntil: 'networkidle' });

    // Click the logo link (router-link to /home)
    await page.locator('nav .logo-link').click();

    // Should navigate to /home
    await page.waitForURL('**/home', { timeout: 10000 });
    expect(page.url()).toContain('/home');
  });
});
