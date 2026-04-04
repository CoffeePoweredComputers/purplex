/**
 * E2E Tests: Admin Problem & Course Authoring
 *
 * Admin shares the same Vue components as instructor but uses /api/admin/ endpoints.
 * These tests verify admin-specific workflows:
 * - Problem CRUD through admin routes
 * - Course creation with instructor assignment dropdown
 * - Admin data visibility (sees ALL problems, not just own)
 *
 * Verified via Playwright exploration scripts:
 * - Admin problem create: 201 via /api/admin/problems/
 * - Admin course form: instructor dropdown with real users
 * - Admin problem list: shows ALL problems (25 vs instructor's 9)
 */

import { test, expect } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';
import { apiAs } from '../helpers/api';
import {
  fillBasicInfo,
  saveProblem,
  deleteProblem,
  uniqueTitle,
} from '../helpers/instructor';

/** Navigate to admin new problem form and select type. */
async function goToAdminNewProblem(page: import('@playwright/test').Page, problemType: string) {
  await navigateAs(page, 'admin', '/admin/problems/new');
  const typeSelect = page.locator('#problem_type');
  await typeSelect.waitFor({ state: 'visible', timeout: 15000 });
  await page.waitForTimeout(1000);

  const typeLabels: Record<string, string> = {
    mcq: 'Multiple Choice Question',
    eipl: 'Explain in Plain Language',
    debug_fix: 'Debug and Fix Code',
  };
  await typeSelect.selectOption({ label: typeLabels[problemType] || problemType });
  await page.waitForTimeout(2000);
}

/** Navigate to admin edit page (reuses existing session). */
async function goToAdminEditProblem(page: import('@playwright/test').Page, slug: string) {
  await page.goto(`/admin/problems/${slug}/edit`);
  await page.locator('.problem-form').waitFor({ state: 'visible', timeout: 15000 });
  await page.waitForTimeout(1500);
}

/** Save and capture slug from POST response. */
async function saveAndGetSlug(page: import('@playwright/test').Page): Promise<string> {
  const responsePromise = page.waitForResponse(
    resp => resp.url().includes('/api/admin/problems') && resp.request().method() === 'POST',
    { timeout: 10000 },
  );
  await saveProblem(page);
  const response = await responsePromise;
  return (await response.json()).slug;
}

test.describe('Admin Problem Authoring', () => {
  const createdSlugs: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const slug of createdSlugs) {
      await apiAs(page, 'admin', 'DELETE', `/api/admin/problems/${slug}/`).catch(() => {});
    }
    createdSlugs.length = 0;
  });

  test('create EiPL problem via admin route', async ({ page }) => {
    const title = uniqueTitle('E2E Admin EiPL');

    await goToAdminNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title, description: 'Admin-created EiPL problem' });

    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def add(a: int, b: int) -> int:',
    );
    await page.locator('.ace_editor').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.type('def add(a, b):\n    return a + b', { delay: 5 });
    await page.waitForTimeout(500);

    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);
    const params = page.locator('.test-case').last().locator('.param-input');
    if (await params.count() >= 3) {
      await params.nth(0).fill('2');
      await params.nth(1).fill('3');
      await params.nth(2).fill('5');
    }

    const slug = await saveAndGetSlug(page);
    expect(slug).toBeTruthy();
    createdSlugs.push(slug);

    // Verify via admin API
    const result = await apiAs(page, 'admin', 'GET', `/api/admin/problems/${slug}/`);
    expect(result.status).toBe(200);
    expect(result.data.title).toBe(title);
    expect(result.data.problem_type).toBe('eipl');
  });

  test('edit problem via admin route', async ({ page }) => {
    const title = uniqueTitle('E2E Admin Edit');

    // Create via admin UI
    await goToAdminNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title, description: 'Admin edit test problem' });
    await page.getByRole('textbox', { name: /function signature/i }).fill('def f(x: int) -> int:');
    await page.locator('.ace_editor').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.type('def f(x):\n    return x', { delay: 5 });
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);
    const params = page.locator('.test-case').last().locator('.param-input');
    if (await params.count() >= 2) { await params.nth(0).fill('1'); await params.nth(1).fill('1'); }

    const slug = await saveAndGetSlug(page);
    createdSlugs.push(slug);

    // Navigate to edit (same session)
    await goToAdminEditProblem(page, slug);

    // Change title
    await page.getByPlaceholder('Enter problem title').fill('Updated Admin Title');
    await saveProblem(page);

    const result = await apiAs(page, 'admin', 'GET', `/api/admin/problems/${slug}/`);
    expect(result.data.title).toBe('Updated Admin Title');
  });

  test('delete problem via admin route', async ({ page }) => {
    const title = uniqueTitle('E2E Admin Delete');

    await goToAdminNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title, description: 'Admin delete test problem' });
    await page.getByRole('textbox', { name: /function signature/i }).fill('def f(x: int) -> int:');
    await page.locator('.ace_editor').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.type('def f(x):\n    return x', { delay: 5 });
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);
    const params = page.locator('.test-case').last().locator('.param-input');
    if (await params.count() >= 2) { await params.nth(0).fill('1'); await params.nth(1).fill('1'); }

    const slug = await saveAndGetSlug(page);

    await goToAdminEditProblem(page, slug);
    await deleteProblem(page);

    const result = await apiAs(page, 'admin', 'GET', `/api/admin/problems/${slug}/`);
    expect(result.status).toBe(404);
  });

  test('admin problem list shows ALL problems (not just own)', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/problems');
    await page.locator('table').waitFor({ state: 'visible', timeout: 15000 });

    // Admin should see more problems than the instructor's ~10
    const rowCount = await page.locator('table tbody tr').count();
    expect(rowCount).toBeGreaterThan(10);
  });
});

test.describe('Admin Course Authoring', () => {
  const createdIds: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const id of createdIds) {
      await apiAs(page, 'admin', 'DELETE', `/api/admin/courses/${id}/`).catch(() => {});
    }
    createdIds.length = 0;
  });

  test('course creation form shows instructor dropdown', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/courses/new');
    await page.waitForTimeout(2000);

    // Admin course form has an instructor selector
    const instructorSelect = page.locator('select').filter({
      has: page.locator('option:text("Select an instructor")'),
    });
    await expect(instructorSelect).toBeVisible({ timeout: 5000 });

    // Should have at least one instructor option
    const options = await instructorSelect.locator('option').allTextContents();
    expect(options.length).toBeGreaterThan(1); // "Select an instructor..." + actual instructors
  });

  test('create course with assigned instructor', async ({ page }) => {
    const courseId = `E2E-ADMIN-COURSE-${Date.now()}`;

    await navigateAs(page, 'admin', '/admin/courses/new');
    await page.waitForTimeout(2000);

    await page.getByPlaceholder('e.g., CS101-FALL2024').fill(courseId);
    await page.getByPlaceholder(/Introduction to/i).fill('Admin Created Course');
    await page.getByPlaceholder(/description/i).fill('Course with assigned instructor');

    // Select an instructor (pick the first real option, not "Select an instructor...")
    const instructorSelect = page.locator('select').filter({
      has: page.locator('option:text("Select an instructor")'),
    });
    const options = await instructorSelect.locator('option').allTextContents();
    if (options.length > 1) {
      // Select the second option (first real instructor)
      await instructorSelect.selectOption({ index: 1 });
    }

    const responsePromise = page.waitForResponse(
      r => r.url().includes('/api/') && r.request().method() === 'POST',
      { timeout: 10000 },
    );
    await page.getByRole('button', { name: /create course/i }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(201);
    createdIds.push(courseId);
  });
});

test.describe('Admin Submissions', () => {
  test('submissions page loads', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/submissions');
    await page.waitForTimeout(3000);

    // The page should render without errors (table or empty state)
    const table = page.locator('table');
    const emptyState = page.locator('text=No submissions');
    const hasContent = await table.isVisible().catch(() => false) ||
                       await emptyState.isVisible().catch(() => false);
    expect(hasContent).toBeTruthy();
  });
});
