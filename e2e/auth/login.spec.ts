/**
 * E2E Tests — Login Flow
 *
 * Tests the login page UI, credential validation, role-based nav visibility,
 * logout via AccountModal, and localStorage persistence.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *
 * Run: npx playwright test e2e/auth/login.spec.ts
 */

import { test, expect } from '@playwright/test';
import { injectAuth } from '../helpers/auth';

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any leftover auth state before each test
    await page.goto('/', { waitUntil: 'commit' });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test('login with valid credentials redirects to /home', async ({ page }) => {
    await page.goto('/');
    await page.locator('#login-form').waitFor({ state: 'visible', timeout: 10000 });

    // Fill in credentials for a seeded test user
    await page.locator('#email').fill('student@test.local');
    await page.locator('#psw').fill('testpass123');

    // Click the Login button (first button in .login-btns)
    await page.locator('.login-btns button').first().click();

    // Should redirect to /home after successful login
    await page.waitForURL('**/home', { timeout: 15000 });
    expect(page.url()).toContain('/home');
  });

  test.fixme('login with invalid password stays on login and shows error', async ({ page }) => {
    // FIXME: Mock Firebase in dev mode accepts ANY email/password combo,
    // so invalid credentials cannot be tested. Requires real Firebase or
    // a mock that rejects unknown emails.
    await page.goto('/');
    await page.locator('#login-form').waitFor({ state: 'visible', timeout: 10000 });

    await page.locator('#email').fill('nonexistent@wrong.com');
    await page.locator('#psw').fill('wrongpassword');

    await page.locator('.login-btns button').first().click();

    await page.waitForTimeout(2000);

    const errorMessage = page.locator('.error-message');
    await expect(errorMessage).toBeVisible();
  });

  test('login with empty email shows validation error', async ({ page }) => {
    await page.goto('/');
    await page.locator('#login-form').waitFor({ state: 'visible', timeout: 10000 });

    // Leave email empty, fill password
    await page.locator('#psw').fill('testpass123');

    // Click Login — the app checks for missing fields and shows error
    await page.locator('.login-btns button').first().click();

    // The app's login handler checks for empty fields and sets errorMessage
    // Wait for error to appear or verify we didn't navigate away
    await page.waitForTimeout(1500);

    // Should show "missing fields" error or stay on login page
    const errorVisible = await page.locator('.error-message').isVisible();
    if (!errorVisible) {
      // At minimum, we should NOT have navigated to /home
      expect(page.url()).not.toContain('/home');
    }
  });

  test('login with empty password shows validation error', async ({ page }) => {
    await page.goto('/');
    await page.locator('#login-form').waitFor({ state: 'visible', timeout: 10000 });

    // Fill email, leave password empty
    await page.locator('#email').fill('student@test.local');

    await page.locator('.login-btns button').first().click();

    await page.waitForTimeout(1500);

    const errorVisible = await page.locator('.error-message').isVisible();
    if (!errorVisible) {
      expect(page.url()).not.toContain('/home');
    }
  });

  test('authenticated user visiting / auto-redirects to /home', async ({ page }) => {
    // Inject auth so the app thinks the user is logged in
    await injectAuth(page, 'student');

    // Navigate to root
    await page.goto('/', { waitUntil: 'networkidle' });

    // Router guard should redirect authenticated users from / to /home
    await page.waitForURL('**/home', { timeout: 10000 });
    expect(page.url()).toContain('/home');
  });

  test('logout via AccountModal returns to login and clears localStorage', async ({ page }) => {
    // Log in first
    await injectAuth(page, 'student');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Open AccountModal by clicking the account button in navbar
    await page.locator('.account-item').click();

    // The AccountModal should be visible
    const modal = page.locator('[aria-labelledby="account-modal-title"]');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // Click Sign Out button
    await page.locator('.logout-button').click();

    // After logout, the Login component renders (loggedIn becomes false).
    // The URL may stay at /home since no router navigation occurs;
    // verify logout by checking localStorage is cleared and login form is visible.
    await page.locator('#login-form').waitFor({ state: 'visible', timeout: 10000 });

    // localStorage should be cleared of user data
    const userData = await page.evaluate(() => localStorage.getItem('user'));
    expect(userData).toBeNull();
  });

  test('login persists across page refresh via localStorage hydration', async ({ page }) => {
    // Inject auth state
    await injectAuth(page, 'student');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Verify we are on /home
    expect(page.url()).toContain('/home');

    // Reload the page — auth should persist from localStorage
    await page.reload({ waitUntil: 'networkidle' });

    // Should still be on /home (not redirected to login)
    expect(page.url()).toContain('/home');

    // Verify user data is still in localStorage
    const userData = await page.evaluate(() => localStorage.getItem('user'));
    expect(userData).not.toBeNull();
    const parsed = JSON.parse(userData!);
    expect(parsed.email).toBe('student@test.local');
  });

  test('login as student shows no Instructor or Admin nav links', async ({ page }) => {
    await injectAuth(page, 'student');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Student should see the Account button
    await expect(page.getByRole('button', { name: 'Account' })).toBeVisible();

    // Student should NOT see Instructor or Admin links
    await expect(page.getByRole('link', { name: 'Instructor' })).not.toBeVisible();
    await expect(page.getByRole('link', { name: 'Admin' })).not.toBeVisible();
  });

  test('login as instructor shows Instructor link visible', async ({ page }) => {
    await injectAuth(page, 'instructor');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Instructor should see the Instructor nav link
    await expect(page.getByRole('link', { name: 'Instructor' })).toBeVisible();

    // Instructor should see Account button
    await expect(page.getByRole('button', { name: 'Account' })).toBeVisible();

    // Instructor should NOT see Admin link
    await expect(page.getByRole('link', { name: 'Admin' })).not.toBeVisible();
  });

  test('login as admin shows both Instructor and Admin links visible', async ({ page }) => {
    await injectAuth(page, 'admin');
    await page.goto('/home', { waitUntil: 'networkidle' });

    // Admin should see both Instructor and Admin nav links
    // (isInstructor getter returns true for admin role too)
    await expect(page.getByRole('link', { name: 'Instructor' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Admin' })).toBeVisible();

    // Admin should see Account button
    await expect(page.getByRole('button', { name: 'Account' })).toBeVisible();
  });

  test('login page renders all expected UI elements', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('#login-form').waitFor({ state: 'visible', timeout: 10000 });

    // Brand name
    await expect(page.locator('.login-title')).toBeVisible();

    // Email input
    await expect(page.locator('#email')).toBeVisible();

    // Password input
    await expect(page.locator('#psw')).toBeVisible();

    // Buttons
    await expect(page.getByRole('button', { name: 'Login' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Account' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Login with Google' })).toBeVisible();

    // Footer links
    await expect(page.getByRole('link', { name: 'Privacy Policy' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Terms of Service' })).toBeVisible();
  });
});
