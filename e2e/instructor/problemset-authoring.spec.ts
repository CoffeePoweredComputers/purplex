/**
 * E2E Tests: Instructor Problem Set Authoring
 *
 * Verified via Playwright scripts:
 * - Form: title (placeholder "e.g., Python Basics"), description, problems selection
 * - Problems: click .problem-item.available → moves to .problem-item.selected
 * - Save enables when title + at least 1 problem selected
 * - Delete uses browser confirm dialog
 */

import { test, expect } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';
import { apiAs } from '../helpers/api';
import { uniqueTitle } from '../helpers/instructor';

async function goToNewProblemSet(page: import('@playwright/test').Page) {
  await navigateAs(page, 'instructor', '/instructor/problem-sets/new');
  await page.locator('.problem-set-form').waitFor({ state: 'visible', timeout: 15000 });
  await page.waitForTimeout(1000);
}

test.describe('Problem Set Authoring', () => {
  const createdSlugs: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const slug of createdSlugs) {
      await apiAs(page, 'instructor', 'DELETE', `/api/instructor/problem-sets/${slug}/`).catch(() => {});
    }
    createdSlugs.length = 0;
  });

  test('create problem set with title and problems', async ({ page }) => {
    await goToNewProblemSet(page);

    await page.getByPlaceholder('e.g., Python Basics').fill(uniqueTitle('E2E PS'));
    await page.getByPlaceholder(/description/i).fill('Test problem set');

    // Add 2 problems from available list
    await page.locator('.problem-item.available').first().click();
    await page.waitForTimeout(300);
    await page.locator('.problem-item.available').first().click();
    await page.waitForTimeout(300);

    await expect(page.locator('.problem-item.selected')).toHaveCount(2);

    const responsePromise = page.waitForResponse(
      r => r.url().includes('/api/instructor/problem-sets') && r.request().method() === 'POST',
      { timeout: 10000 },
    );
    await page.getByRole('button', { name: /save/i }).click();
    const response = await responsePromise;
    const body = await response.json();
    expect(response.status()).toBe(201);
    createdSlugs.push(body.slug);
  });

  test('save is blocked without title', async ({ page }) => {
    await goToNewProblemSet(page);

    // Add a problem but don't fill title
    await page.locator('.problem-item.available').first().click();
    await page.waitForTimeout(300);

    await expect(page.getByRole('button', { name: /save/i })).toBeDisabled({ timeout: 3000 });
  });

  test('remove problem from selected list', async ({ page }) => {
    await goToNewProblemSet(page);

    await page.getByPlaceholder('e.g., Python Basics').fill(uniqueTitle('E2E PS Remove'));

    // Add 2 problems
    await page.locator('.problem-item.available').first().click();
    await page.waitForTimeout(300);
    await page.locator('.problem-item.available').first().click();
    await page.waitForTimeout(300);

    await expect(page.locator('.problem-item.selected')).toHaveCount(2);

    // Remove one (click the remove button in the selected item)
    const removeBtn = page.locator('.problem-item.selected').first().locator('.remove-btn, button');
    await removeBtn.last().click();
    await page.waitForTimeout(300);

    await expect(page.locator('.problem-item.selected')).toHaveCount(1);
  });

  test('search filters available problems', async ({ page }) => {
    await goToNewProblemSet(page);

    const initialCount = await page.locator('.problem-item').count();
    expect(initialCount).toBeGreaterThan(0);

    // Search for a term that won't match any problem
    await page.getByPlaceholder(/search/i).fill('zzz_nonexistent_xyz');
    await page.waitForTimeout(500);

    const filteredCount = await page.locator('.problem-item').count();
    expect(filteredCount).toBe(0);

    // Clear search and verify all problems return
    await page.getByPlaceholder(/search/i).fill('');
    await page.waitForTimeout(500);

    const restoredCount = await page.locator('.problem-item').count();
    expect(restoredCount).toBe(initialCount);
  });

  test('edit problem set loads existing data', async ({ page }) => {
    // Create via API first
    await navigateAs(page, 'instructor', '/instructor/problem-sets');
    await page.waitForTimeout(500);

    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/problem-sets/', {
      title: uniqueTitle('E2E PS Edit'),
      description: 'Problem set for edit verification',
    });
    expect(createResult.status).toBe(201);
    const slug = createResult.data.slug;
    createdSlugs.push(slug);

    // Navigate to edit
    await page.goto(`/instructor/problem-sets/${slug}/edit`);
    await page.locator('.problem-set-form').waitFor({ state: 'visible', timeout: 15000 });
    await page.waitForTimeout(1000);

    // Title should be loaded
    const titleValue = await page.getByPlaceholder('e.g., Python Basics').inputValue();
    expect(titleValue).toContain('E2E PS Edit');
  });

  test('delete problem set from list', async ({ page }) => {
    // Create via API
    await navigateAs(page, 'instructor', '/instructor/problem-sets');
    await page.waitForTimeout(500);

    const title = uniqueTitle('E2E PS Delete');
    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/problem-sets/', {
      title,
      description: 'Problem set to be deleted in test',
    });
    expect(createResult.status).toBe(201);
    const slug = createResult.data.slug;

    // Reload list
    await page.goto('/instructor/problem-sets');
    await page.waitForTimeout(2000);

    // Find the row with this problem set and click delete
    const row = page.locator('table tbody tr').filter({ hasText: title }).first();
    await row.locator('.delete-button').click();

    // Confirm in the alertdialog
    const dialog = page.getByRole('alertdialog');
    await dialog.waitFor({ state: 'visible', timeout: 5000 });
    await dialog.getByRole('button', { name: /delete/i }).click();
    await page.waitForTimeout(2000);

    // Verify via API
    const fetchResult = await apiAs(page, 'instructor', 'GET', `/api/instructor/problem-sets/${slug}/`);
    expect(fetchResult.status).toBe(404);
  });
});
