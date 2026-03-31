/**
 * E2E Tests -- Instructor Problem CRUD
 *
 * Tests the problem list (DataTable with search), and create/edit/delete
 * workflows via the ProblemEditorShell form. Uses unique slugs with
 * timestamps to avoid polluting shared state.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *   4. E2E data seeded: python manage.py seed_e2e_data
 *
 * Run: npx playwright test e2e/instructor/problem-crud.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, expectNoErrors } from '../helpers/navigation';

const PROBLEMS_URL = '/instructor/problems';

test.describe('Instructor Problem CRUD', () => {
  test('problem list shows seeded problems in DataTable', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEMS_URL);

    // Wait for the DataTable to render (loading disappears, table appears)
    await page.locator('.data-table').waitFor({ state: 'visible', timeout: 15000 });

    // The seeded problems should appear in the table
    await expect(page.getByText('E2E: What is a variable?')).toBeVisible();
    await expect(page.getByText('E2E: Sum of List')).toBeVisible();

    await expectNoErrors(page);
  });

  test('search filter narrows problem list', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEMS_URL);
    await page.locator('.data-table').waitFor({ state: 'visible', timeout: 15000 });

    // Use the search input (inside the #filters slot)
    const searchInput = page.locator('.search-input');
    await searchInput.fill('variable');

    // Wait for debounced search to take effect
    await page.waitForTimeout(500);

    // Only the MCQ problem title contains "variable"
    const rows = page.locator('.data-table tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // Every visible row should contain the search term
    for (let i = 0; i < count; i++) {
      const rowText = await rows.nth(i).textContent();
      expect(rowText?.toLowerCase()).toContain('variable');
    }
  });

  test('search with no matches shows empty state', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEMS_URL);
    await page.locator('.data-table, .empty-state, .error-state').first().waitFor({ state: 'visible', timeout: 15000 });

    const searchInput = page.locator('.search-input');
    await searchInput.fill('zzz_no_match_ever_xyz');

    await page.waitForTimeout(500);

    // DataTable empty state should show — wait for the table to disappear
    // and the empty-state div to become visible
    await expect(page.locator('.data-table')).not.toBeVisible({ timeout: 5000 });
    const emptyState = page.locator('.empty-state');
    await expect(emptyState).toBeVisible({ timeout: 5000 });
  });

  test('clicking "Add New Problem" navigates to new problem editor', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEMS_URL);
    await page.locator('.data-table').waitFor({ state: 'visible', timeout: 15000 });

    // The "Add New Problem" button is in the header-actions slot
    const addButton = page.locator('.add-button');
    await expect(addButton).toBeVisible();
    await addButton.click();

    await page.waitForURL('**/instructor/problems/new', { timeout: 10000 });
    expect(page.url()).toContain('/instructor/problems/new');
  });

  test('new problem editor shows type selector and form', async ({ page }) => {
    await navigateAs(page, 'instructor', '/instructor/problems/new');

    // Wait for the editor shell to load
    await page.locator('.problem-form').waitFor({ state: 'visible', timeout: 15000 });

    // Header should indicate "Create" mode
    const header = page.locator('.header h2');
    await expect(header).toContainText(/create/i);

    // Type selector should be visible and enabled
    const typeSelect = page.locator('#problem_type');
    await expect(typeSelect).toBeVisible();
    await expect(typeSelect).toBeEnabled();
  });

  test('problem type selector changes available form fields', async ({ page }) => {
    await navigateAs(page, 'instructor', '/instructor/problems/new');
    await page.locator('.problem-form').waitFor({ state: 'visible', timeout: 15000 });

    const typeSelect = page.locator('#problem_type');

    // Wait for the type selector to be enabled (activity types loaded)
    await expect(typeSelect).toBeEnabled({ timeout: 10000 });

    // Get the initial form HTML fingerprint
    const initialContent = await page.locator('.problem-form').innerHTML();

    // Select a different type (if options exist)
    const options = await typeSelect.locator('option').allTextContents();
    if (options.length >= 2) {
      // Select a type different from the default (eipl at index 1) — use index 0 (debug_fix)
      await typeSelect.selectOption({ index: 0 });

      // Wait for the dynamic editor component to load (uses Suspense)
      await page.waitForTimeout(1500);

      // The form content should have changed (different type-specific editor)
      const newContent = await page.locator('.problem-form').innerHTML();
      expect(newContent).not.toBe(initialContent);
    }
  });

  test('save button is disabled when title is empty', async ({ page }) => {
    await navigateAs(page, 'instructor', '/instructor/problems/new');
    await page.locator('.problem-form').waitFor({ state: 'visible', timeout: 15000 });

    // The save button (btn-primary) should be disabled initially since title is empty
    const saveBtn = page.locator('.btn-primary').filter({ hasText: /save/i });
    await expect(saveBtn).toBeDisabled();
  });

  test('edit an existing problem loads its data', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEMS_URL);
    await page.locator('.data-table').waitFor({ state: 'visible', timeout: 15000 });

    // Find the edit button for the MCQ problem
    const mcqRow = page.locator('.data-table tbody tr').filter({ hasText: 'E2E: What is a variable?' });
    const editBtn = mcqRow.locator('.edit-button');
    await editBtn.click();

    // Should navigate to the edit page
    await page.waitForURL('**/instructor/problems/e2e-mcq-1/edit', { timeout: 10000 });

    // Wait for the editor to load the problem data
    await page.locator('.problem-form').waitFor({ state: 'visible', timeout: 15000 });

    // Header should indicate "Edit" mode
    const header = page.locator('.header h2');
    await expect(header).toContainText(/edit/i);

    // Type selector should be disabled in edit mode
    const typeSelect = page.locator('#problem_type');
    await expect(typeSelect).toBeDisabled();
  });

  test('delete problem from editor shows confirmation dialog', async ({ page }) => {
    // Navigate to a problem's edit page
    await navigateAs(page, 'instructor', '/instructor/problems/e2e-refute-1/edit');
    await page.locator('.problem-form').waitFor({ state: 'visible', timeout: 15000 });

    // Wait for the Delete button to appear (indicates problem data loaded)
    const deleteBtn = page.locator('.header .btn-danger').filter({ hasText: /delete/i });
    await expect(deleteBtn).toBeVisible({ timeout: 10000 });
    await deleteBtn.click();

    // Confirmation dialog should appear (inline dialog in ProblemEditorShell)
    const dialog = page.locator('.dialog-overlay');
    await expect(dialog).toBeVisible({ timeout: 5000 });

    // Dialog should have Cancel and Delete buttons
    await expect(dialog.locator('.btn-secondary').filter({ hasText: /cancel/i })).toBeVisible();
    await expect(dialog.locator('.btn-danger').filter({ hasText: /delete/i })).toBeVisible();

    // Cancel -- do not actually delete the seeded data
    await dialog.locator('.btn-secondary').click();
    await expect(dialog).not.toBeVisible();
  });

  test('delete problem from problem list shows browser confirm', async ({ page }) => {
    await navigateAs(page, 'instructor', PROBLEMS_URL);
    await page.locator('.data-table').waitFor({ state: 'visible', timeout: 15000 });

    // Set up dialog handler to dismiss (cancel) the native confirm dialog
    page.on('dialog', async (dialog) => {
      expect(dialog.type()).toBe('confirm');
      await dialog.dismiss();
    });

    // Click delete on a problem row
    const row = page.locator('.data-table tbody tr').filter({ hasText: 'E2E: Find Counterexample' });
    const deleteBtn = row.locator('.delete-button');
    await deleteBtn.click();

    // After dismissing, the problem should still be in the list
    await expect(row).toBeVisible();
  });
});
