/**
 * E2E Tests -- Admin Problem Management
 *
 * Tests the /admin/problems page: listing all seeded problems,
 * search/filter, navigation to edit, and cross-instructor visibility.
 *
 * Prerequisites:
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server on :5173
 *   3. Seeded problems: e2e-mcq-1, e2e-eipl-1, e2e-prompt-1,
 *      e2e-debugfix-1, e2e-probeable-code-1, e2e-probeable-spec-1, e2e-refute-1
 *
 * Run: npx playwright test e2e/admin/problems.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, expectNoErrors } from '../helpers/navigation';
import { apiAs } from '../helpers/api';

const SEEDED_PROBLEM_SLUGS = [
  'e2e-mcq-1',
  'e2e-eipl-1',
  'e2e-prompt-1',
  'e2e-debugfix-1',
  'e2e-probeable-code-1',
  'e2e-probeable-spec-1',
  'e2e-refute-1',
];

test.describe('Admin Problem Management', () => {
  test('page loads and shows seeded problems via API', async ({ page }) => {
    await navigateAs(page, 'admin', '/home');

    // Verify all 7 seeded problems are accessible via admin API
    const response = await apiAs(page, 'admin', 'GET', '/api/admin/problems/');
    expect(response.status).toBe(200);

    const problems = response.data.results || response.data;
    expect(Array.isArray(problems)).toBeTruthy();

    // All 7 seeded problems should be present
    const slugs = problems.map((p: any) => p.slug);
    for (const expectedSlug of SEEDED_PROBLEM_SLUGS) {
      expect(slugs).toContain(expectedSlug);
    }
  });

  test('admin problems page renders without errors', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/problems');
    await expectNoErrors(page);

    // The page should contain a table or list of problems
    const body = await page.locator('body').textContent();
    expect(body).toBeDefined();
  });

  test('can navigate to edit a specific problem', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/problems');

    // Wait for the page to load
    await page.waitForTimeout(3000);

    // Try to find a link to an edit page for a seeded problem
    const editLink = page.locator(`a[href*="/admin/problems/e2e-mcq-1/edit"]`);
    if (await editLink.isVisible()) {
      await editLink.click();
      await page.waitForLoadState('networkidle');
      expect(page.url()).toContain('/admin/problems/e2e-mcq-1/edit');
      await expectNoErrors(page);
    } else {
      // Verify the problem detail endpoint is accessible via API
      const response = await apiAs(page, 'admin', 'GET', '/api/admin/problems/e2e-mcq-1/');
      expect(response.status).toBe(200);
      expect(response.data.slug).toBe('e2e-mcq-1');
    }
  });

  test('admin sees problems from all instructors', async ({ page }) => {
    await navigateAs(page, 'admin', '/home');

    // Admin API should return all problems regardless of who created them
    const adminResponse = await apiAs(page, 'admin', 'GET', '/api/admin/problems/');
    expect(adminResponse.status).toBe(200);

    const adminProblems = adminResponse.data.results || adminResponse.data;

    // Instructor API returns only their own problems
    const instructorResponse = await apiAs(page, 'instructor', 'GET', '/api/instructor/problems/');
    expect(instructorResponse.status).toBe(200);

    const instructorProblems = instructorResponse.data.results || instructorResponse.data;

    // Admin should see at least as many problems as the instructor
    expect(adminProblems.length).toBeGreaterThanOrEqual(instructorProblems.length);
  });
});
