/**
 * E2E Tests -- Privacy & Consent
 *
 * Tests the privacy settings page load, consent API endpoints
 * (list, grant, withdraw), and public privacy/terms pages.
 *
 * Backend endpoints tested:
 *   GET    /api/users/me/consents/               (list consents)
 *   POST   /api/users/me/consents/               (grant consent)
 *   DELETE /api/users/me/consents/<type>/         (withdraw consent)
 *
 * Frontend routes tested:
 *   /settings/privacy   (auth required)
 *   /privacy            (public)
 *   /terms              (public)
 *
 * Prerequisites:
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server on :5173
 *   3. Seeded: student user with consent records
 *
 * Run: npx playwright test e2e/privacy/consent.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, expectNoErrors } from '../helpers/navigation';
import { apiAs } from '../helpers/api';

test.describe('Privacy & Consent', () => {
  test('privacy settings page loads without errors', async ({ page }) => {
    await navigateAs(page, 'student', '/settings/privacy');
    await expectNoErrors(page);

    // The privacy settings page should render
    const settingsContainer = page.locator('.privacy-settings');
    await expect(settingsContainer).toBeVisible({ timeout: 15000 });
  });

  test('consent list API returns student consents', async ({ page }) => {
    await page.goto('/', { waitUntil: 'commit' });

    const res = await apiAs(page, 'student', 'GET', '/api/users/me/consents/');
    expect(res.status).toBe(200);

    // Response should be an object mapping consent types to statuses
    expect(res.data).toBeDefined();
    expect(typeof res.data).toBe('object');
  });

  test('can grant a new consent type via API', async ({ page }) => {
    await page.goto('/', { waitUntil: 'commit' });

    // Grant behavioral_tracking consent (optional type)
    const res = await apiAs(page, 'student', 'POST', '/api/users/me/consents/', {
      consent_type: 'behavioral_tracking',
    });

    // Should succeed (200 or 201)
    expect([200, 201]).toContain(res.status);
  });

  test('can withdraw a consent type via API', async ({ page }) => {
    await page.goto('/', { waitUntil: 'commit' });

    // First ensure the consent is granted
    await apiAs(page, 'student', 'POST', '/api/users/me/consents/', {
      consent_type: 'behavioral_tracking',
    });

    // Now withdraw it
    const res = await apiAs(page, 'student', 'DELETE', '/api/users/me/consents/behavioral_tracking/');
    expect([200, 204]).toContain(res.status);

    // Verify it is now withdrawn by re-fetching consents
    const listRes = await apiAs(page, 'student', 'GET', '/api/users/me/consents/');
    expect(listRes.status).toBe(200);

    // behavioral_tracking should now show as not granted
    if (listRes.data.behavioral_tracking) {
      expect(listRes.data.behavioral_tracking.granted).toBeFalsy();
    }
  });

  test('privacy policy page loads without auth (public)', async ({ page }) => {
    // Public routes should render without authentication (App.vue checks
    // currentRouteRequiresAuth before showing Login)
    await page.goto('/privacy', { waitUntil: 'networkidle' });
    await expectNoErrors(page);

    // Should show the privacy policy page content
    const policyPage = page.locator('.policy-page');
    await expect(policyPage).toBeVisible({ timeout: 10000 });
  });

  test('terms of service page loads without auth (public)', async ({ page }) => {
    await page.goto('/terms', { waitUntil: 'networkidle' });
    await expectNoErrors(page);

    // Should show the terms page content
    const body = await page.locator('body').textContent();
    expect(body).toBeDefined();
    // Should not redirect to login
    expect(page.url()).toContain('/terms');
  });
});
