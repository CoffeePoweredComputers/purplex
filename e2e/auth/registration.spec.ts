/**
 * E2E Tests — Registration Flow
 *
 * Tests the multi-step registration: credentials -> age gate -> consent -> home.
 * Covers COPPA age blocking, consent requirements, and navigation between steps.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *
 * Run: npx playwright test e2e/auth/registration.spec.ts
 */

import { test, expect } from '@playwright/test';

/**
 * Build an ISO date string N years before today.
 * Adjusts for birthday-already-passed this year so the age calculation is exact.
 */
function dateYearsAgo(years: number): string {
  const now = new Date();
  const d = new Date(now.getFullYear() - years, now.getMonth(), now.getDate());
  return d.toISOString().split('T')[0];
}

test.describe('Registration Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'commit' });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.goto('/', { waitUntil: 'networkidle' });
  });

  test('full registration flow: credentials -> age gate -> consent -> home', async ({ page }) => {
    const uniqueEmail = `e2e-reg-${Date.now()}@test.local`;

    // Step 1: Enter credentials and click "New Account"
    await page.locator('#email').fill(uniqueEmail);
    await page.locator('#psw').fill('testpass123');
    await page.getByRole('button', { name: 'New Account' }).click();

    // Step 2: Age Gate should appear
    await expect(page.getByText('Age Verification')).toBeVisible();

    // Enter a date making the user 20 years old
    const adultDate = dateYearsAgo(20);
    await page.locator('input[type="date"]').fill(adultDate);
    await page.getByRole('button', { name: 'Continue' }).click();

    // Step 3: Consent Form should appear
    await expect(page.getByText('Data Processing Consent')).toBeVisible();

    // Check the two required checkboxes (Privacy Policy and Terms of Service)
    const checkboxes = page.locator('.consent-item input[type="checkbox"]');
    // First checkbox: Privacy Policy (required)
    await checkboxes.nth(0).check();
    // Second checkbox: Terms of Service (required)
    await checkboxes.nth(1).check();

    // Click Continue to complete registration
    await page.getByRole('button', { name: 'Continue' }).click();

    // Should redirect to /home after registration completes
    await page.waitForURL('**/home', { timeout: 15000 });
    expect(page.url()).toContain('/home');
  });

  test('password under 6 characters shows validation error', async ({ page }) => {
    await page.locator('#email').fill('shortpw@test.local');
    await page.locator('#psw').fill('abc');

    await page.getByRole('button', { name: 'New Account' }).click();

    // Should show password too short error
    const errorMessage = page.locator('.error-message');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('at least 6 characters');

    // Should still be on credentials step (no age gate visible)
    await expect(page.getByText('Age Verification')).not.toBeVisible();
  });

  test('age gate: under 13 shows COPPA block screen', async ({ page }) => {
    await page.locator('#email').fill('child@test.local');
    await page.locator('#psw').fill('testpass123');
    await page.getByRole('button', { name: 'New Account' }).click();

    // Age Gate appears
    await expect(page.getByText('Age Verification')).toBeVisible();

    // Enter a date making the user 10 years old (under 13)
    const childDate = dateYearsAgo(10);
    await page.locator('input[type="date"]').fill(childDate);

    // Should show the child message before submitting
    await expect(page.getByText('Users under 13 require parental or guardian consent')).toBeVisible();

    await page.getByRole('button', { name: 'Continue' }).click();

    // COPPA block screen should appear
    await expect(page.getByText('Parental Consent Required')).toBeVisible();
    await expect(page.getByText('verifiable parental or guardian consent')).toBeVisible();

    // Should have a "Back to Login" button
    await expect(page.getByRole('button', { name: 'Back to Login' })).toBeVisible();
  });

  test('age gate: exactly 13 is allowed through to consent', async ({ page }) => {
    await page.locator('#email').fill('teen13@test.local');
    await page.locator('#psw').fill('testpass123');
    await page.getByRole('button', { name: 'New Account' }).click();

    await expect(page.getByText('Age Verification')).toBeVisible();

    // Enter a date making the user exactly 13
    const thirteenDate = dateYearsAgo(13);
    await page.locator('input[type="date"]').fill(thirteenDate);

    // Should show minor message (13 < 18) but not the child message
    await expect(page.getByText('Users under 18 have additional privacy protections')).toBeVisible();

    await page.getByRole('button', { name: 'Continue' }).click();

    // Should proceed to consent form, NOT the COPPA block
    await expect(page.getByText('Data Processing Consent')).toBeVisible();
    await expect(page.getByText('Parental Consent Required')).not.toBeVisible();
  });

  test('consent form: must check required boxes before proceeding', async ({ page }) => {
    // Navigate to consent step
    await page.locator('#email').fill('consent-test@test.local');
    await page.locator('#psw').fill('testpass123');
    await page.getByRole('button', { name: 'New Account' }).click();

    await expect(page.getByText('Age Verification')).toBeVisible();
    await page.locator('input[type="date"]').fill(dateYearsAgo(20));
    await page.getByRole('button', { name: 'Continue' }).click();

    await expect(page.getByText('Data Processing Consent')).toBeVisible();

    // The Continue button should be disabled when no required checkboxes are checked
    const continueBtn = page.getByRole('button', { name: 'Continue' });
    await expect(continueBtn).toBeDisabled();

    // Check only Privacy Policy (first required)
    const checkboxes = page.locator('.consent-item input[type="checkbox"]');
    await checkboxes.nth(0).check();

    // Still disabled — Terms of Service not checked
    await expect(continueBtn).toBeDisabled();

    // Check Terms of Service (second required)
    await checkboxes.nth(1).check();

    // Now the button should be enabled
    await expect(continueBtn).toBeEnabled();
  });

  test('back button at age gate returns to credentials', async ({ page }) => {
    await page.locator('#email').fill('backtest@test.local');
    await page.locator('#psw').fill('testpass123');
    await page.getByRole('button', { name: 'New Account' }).click();

    // Age Gate visible
    await expect(page.getByText('Age Verification')).toBeVisible();

    // Click Back button
    await page.getByRole('button', { name: 'Back' }).click();

    // Should return to credentials step
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#psw')).toBeVisible();
    await expect(page.getByText('Age Verification')).not.toBeVisible();

    // Email should still be filled in (state preserved)
    const emailValue = await page.locator('#email').inputValue();
    expect(emailValue).toBe('backtest@test.local');
  });

  test('back button at consent returns to age gate', async ({ page }) => {
    await page.locator('#email').fill('backtest2@test.local');
    await page.locator('#psw').fill('testpass123');
    await page.getByRole('button', { name: 'New Account' }).click();

    await expect(page.getByText('Age Verification')).toBeVisible();
    await page.locator('input[type="date"]').fill(dateYearsAgo(20));
    await page.getByRole('button', { name: 'Continue' }).click();

    // Consent form visible
    await expect(page.getByText('Data Processing Consent')).toBeVisible();

    // Click Back button
    await page.getByRole('button', { name: 'Back' }).click();

    // Should return to age gate
    await expect(page.getByText('Age Verification')).toBeVisible();
    await expect(page.getByText('Data Processing Consent')).not.toBeVisible();
  });

  test('registration with empty credentials shows error', async ({ page }) => {
    // Click "New Account" with no email or password
    await page.getByRole('button', { name: 'New Account' }).click();

    // Should show a missing fields error
    const errorMessage = page.locator('.error-message');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('email and password');

    // Should stay on credentials step
    await expect(page.getByText('Age Verification')).not.toBeVisible();
  });
});
