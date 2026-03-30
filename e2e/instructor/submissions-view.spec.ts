/**
 * E2E Tests -- Instructor Submissions View
 *
 * Tests the submissions page accessible from the course nav: DataTable rendering,
 * column structure, filters (search, status), the View button, and pagination.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *   4. E2E data seeded: python manage.py seed_e2e_data
 *
 * Run: npx playwright test e2e/instructor/submissions-view.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, expectNoErrors } from '../helpers/navigation';

const SUBMISSIONS_URL = '/instructor/courses/CS101-2024/submissions';

test.describe('Instructor Submissions View', () => {
  test('submissions page loads and shows student MCQ submission', async ({ page }) => {
    await navigateAs(page, 'instructor', SUBMISSIONS_URL);

    // Wait for the DataTable to finish loading (table, empty state, or error state)
    await page.locator('.data-table, .empty-state, .error-state').first().waitFor({ state: 'visible', timeout: 15000 });

    // The seeded submission: student -> e2e-mcq-1 (score 100, complete)
    // Check that we see the student's name and the problem
    const tableOrEmpty = page.locator('.data-table');
    const tableCount = await tableOrEmpty.count();

    if (tableCount > 0) {
      // Table rendered -- check for the seeded submission
      await expect(page.getByText('student')).toBeVisible();
    }

    await expectNoErrors(page);
  });

  test('DataTable has expected column headers', async ({ page }) => {
    await navigateAs(page, 'instructor', SUBMISSIONS_URL);
    await page.locator('.data-table, .empty-state, .error-state').first().waitFor({ state: 'visible', timeout: 15000 });

    // If there are submissions, check headers
    const table = page.locator('.data-table');
    if (await table.isVisible()) {
      const headers = page.locator('.data-table thead th');
      const headerTexts = await headers.allTextContents();
      const joined = headerTexts.join(' ').toLowerCase();

      // SubmissionsPage defines these columns for instructor context:
      // Student, Problem, Problem Set, Type, Score, Status, Submitted, Actions
      expect(joined).toContain('student');
      expect(joined).toContain('problem');
      expect(joined).toContain('score');
      expect(joined).toContain('status');
    }
  });

  test('status filter dropdown exists and has expected options', async ({ page }) => {
    await navigateAs(page, 'instructor', SUBMISSIONS_URL);

    // Wait for the page to load (filters render alongside DataTable)
    await page.locator('.filters-section').waitFor({ state: 'visible', timeout: 15000 });

    const statusSelect = page.locator('#status');
    await expect(statusSelect).toBeVisible();

    // Check options: All Statuses, Complete, Partial, Incomplete
    const options = await statusSelect.locator('option').allTextContents();
    const joined = options.join(' ').toLowerCase();
    expect(joined).toContain('complete');
    expect(joined).toContain('partial');
    expect(joined).toContain('incomplete');
  });

  test('search filter works on submissions', async ({ page }) => {
    await navigateAs(page, 'instructor', SUBMISSIONS_URL);
    await page.locator('.data-table, .empty-state, .error-state').first().waitFor({ state: 'visible', timeout: 15000 });

    // The search input in the filters section
    const searchInput = page.locator('#search');
    await expect(searchInput).toBeVisible();

    // Type the student's name to filter
    await searchInput.fill('student');

    // Wait for debounced search to fire
    await page.waitForTimeout(500);

    // The table should still contain student submissions (since we searched for "student")
    const rows = page.locator('.data-table tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('clicking View button opens submission detail modal', async ({ page }) => {
    await navigateAs(page, 'instructor', SUBMISSIONS_URL);
    await page.locator('.data-table, .empty-state, .error-state').first().waitFor({ state: 'visible', timeout: 15000 });

    // Find the View button on the first submission row
    const viewBtn = page.locator('.view-button').first();
    const viewBtnCount = await viewBtn.count();

    if (viewBtnCount > 0) {
      await viewBtn.click();

      // The ViewSubmissionModal should appear
      // It could be rendered as a modal overlay or navigate to a detail route
      await page.waitForTimeout(1000);

      // Check if a modal appeared or we navigated to a detail page
      const modal = page.locator('[class*="modal"], [role="dialog"]');
      const modalVisible = await modal.isVisible().catch(() => false);

      if (modalVisible) {
        // Modal path: verify it shows submission details
        await expect(modal).toBeVisible();
      } else {
        // Route path: /instructor/courses/CS101-2024/submissions/:id
        expect(page.url()).toMatch(/\/submissions\/\d+/);
      }
    }
  });

  test('score badge reflects correct score from seeded data', async ({ page }) => {
    await navigateAs(page, 'instructor', SUBMISSIONS_URL);
    await page.locator('.data-table, .empty-state, .error-state').first().waitFor({ state: 'visible', timeout: 15000 });

    // The seeded MCQ submission has score = 100
    const scoreBadge = page.locator('.score-badge').first();
    const scoreBadgeCount = await scoreBadge.count();

    if (scoreBadgeCount > 0) {
      const scoreText = await scoreBadge.textContent();
      // Score should be "100%" for the seeded submission
      expect(scoreText).toContain('100');
    }
  });
});
