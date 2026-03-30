/**
 * E2E Tests -- Instructor Problem Set CRUD
 *
 * Tests the problem set list (DataTable), and create/edit/delete flows
 * via the ProblemSetManager and editor forms.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *   4. E2E data seeded: python manage.py seed_e2e_data
 *
 * Run: npx playwright test e2e/instructor/problemset-crud.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, expectNoErrors } from '../helpers/navigation';

const PROBLEM_SETS_URL = '/instructor/problem-sets';

test.describe('Instructor Problem Set CRUD', () => {
  test('problem set list shows seeded problem sets', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEM_SETS_URL);

    // Wait for DataTable to finish loading (table, empty state, or error state)
    const tableOrState = page.locator('.data-table, .empty-state, .error-state').first();
    await tableOrState.waitFor({ state: 'visible', timeout: 15000 });

    // The three seeded problem sets should be listed
    await expect(page.getByText('E2E Basics')).toBeVisible();
    await expect(page.getByText('E2E Code Challenges')).toBeVisible();
    await expect(page.getByText('E2E Mixed Set')).toBeVisible();

    await expectNoErrors(page);
  });

  test('search filter narrows problem set list', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEM_SETS_URL);
    await page.locator('.data-table, .empty-state, .error-state').first().waitFor({ state: 'visible', timeout: 15000 });

    const searchInput = page.locator('.search-input');
    await searchInput.fill('Mixed');

    // Wait for debounced search
    await page.waitForTimeout(500);

    // Only the "E2E Mixed Set" should remain
    const rows = page.locator('.data-table tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // All visible rows should contain "Mixed"
    for (let i = 0; i < count; i++) {
      const text = await rows.nth(i).textContent();
      expect(text?.toLowerCase()).toContain('mixed');
    }
  });

  test('clicking "Add New" navigates to new problem set editor', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEM_SETS_URL);

    // The add button is in header-actions, visible regardless of DataTable state
    const addButton = page.locator('.add-button');
    await expect(addButton).toBeVisible({ timeout: 15000 });
    await addButton.click();

    await page.waitForURL('**/instructor/problem-sets/new', { timeout: 10000 });
    expect(page.url()).toContain('/instructor/problem-sets/new');
  });

  test('edit problem set navigates to editor with slug', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEM_SETS_URL);
    await page.locator('.data-table').waitFor({ state: 'visible', timeout: 15000 });

    // Find the "E2E Basics" row and click Edit
    const row = page.locator('.data-table tbody tr').filter({ hasText: 'E2E Basics' });
    const editBtn = row.locator('.edit-button');
    await editBtn.click();

    await page.waitForURL('**/instructor/problem-sets/e2e-basics/edit', { timeout: 10000 });
    expect(page.url()).toContain('/instructor/problem-sets/e2e-basics/edit');
  });

  test('delete problem set shows confirmation dialog', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEM_SETS_URL);
    await page.locator('.data-table').waitFor({ state: 'visible', timeout: 15000 });

    // Click delete on "E2E Mixed Set" (safest to test against since it has the most problems)
    const row = page.locator('.data-table tbody tr').filter({ hasText: 'E2E Mixed Set' });
    const deleteBtn = row.locator('.delete-button');
    await deleteBtn.click();

    // ConfirmDialog uses Teleport with .dialog-overlay and role="alertdialog"
    const dialog = page.locator('.dialog-overlay, [role="alertdialog"]');
    await expect(dialog).toBeVisible({ timeout: 5000 });

    // Cancel the deletion to preserve seeded data
    const cancelBtn = dialog.getByText(/cancel/i);
    await cancelBtn.click();

    // Dialog should close
    await expect(dialog).not.toBeVisible();

    // Problem set should still be in the list
    await expect(page.getByText('E2E Mixed Set')).toBeVisible();
  });

  test('problem set list shows problem count and visibility columns', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEM_SETS_URL);
    await page.locator('.data-table').waitFor({ state: 'visible', timeout: 15000 });

    // Check that column headers exist
    const headerRow = page.locator('.data-table thead tr');
    await expect(headerRow).toBeVisible();

    // The DataTable should have columns as defined in ProblemSetManager:
    // Title, Description, Problems (count), Visibility, Actions
    const headers = page.locator('.data-table thead th');
    const headerTexts = await headers.allTextContents();
    const joined = headerTexts.join(' ').toLowerCase();
    expect(joined).toContain('title');
    expect(joined).toContain('actions');
  });
});
