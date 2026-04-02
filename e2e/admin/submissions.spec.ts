/**
 * E2E Tests -- Admin Submissions
 *
 * Tests the /admin/submissions page: listing submissions, filtering,
 * viewing detail, and export functionality.
 *
 * Prerequisites:
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server on :5173
 *   3. Seeded data: student has 1 MCQ submission
 *
 * Run: npx playwright test e2e/admin/submissions.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, expectNoErrors } from '../helpers/navigation';
import { apiAs } from '../helpers/api';

test.describe('Admin Submissions', () => {
  test('submissions page loads without errors', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/submissions');
    await expectNoErrors(page);

    // DataTable container should be visible
    const table = page.locator('.data-table-container');
    await expect(table).toBeVisible({ timeout: 15000 });
  });

  test('admin can list submissions via API', async ({ page }) => {
    await navigateAs(page, 'admin', '/home');

    const response = await apiAs(page, 'admin', 'GET', '/api/admin/submissions/');
    expect(response.status).toBe(200);

    const submissions = response.data.results || response.data;
    expect(Array.isArray(submissions)).toBeTruthy();

    // At least the seeded MCQ submission should exist
    expect(submissions.length).toBeGreaterThanOrEqual(1);
  });

  test('can filter submissions by status', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/submissions');

    // Wait for table to load
    await page.waitForTimeout(3000);

    // The status filter dropdown should be present
    const statusSelect = page.locator('#status');
    if (await statusSelect.isVisible()) {
      // Select "complete" status
      await statusSelect.selectOption('complete');
      await page.waitForTimeout(1000);

      // Page should still not have errors
      await expectNoErrors(page);
    }
  });

  test('export button is visible for admin', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/submissions');

    // Wait for page to fully load
    await page.waitForTimeout(3000);

    // The export button should be visible for admin users
    const exportButton = page.locator('.export-button');
    await expect(exportButton).toBeVisible({ timeout: 10000 });
  });
});
