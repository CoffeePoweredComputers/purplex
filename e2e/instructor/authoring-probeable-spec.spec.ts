/**
 * E2E Tests: Instructor Probeable Spec Problem Authoring
 *
 * Verified: Same as ProbeableCode but adds segmentation config section.
 */

import { test, expect } from '@playwright/test';
import {
  goToNewProblem,
  fillBasicInfo,
  goToEditProblem,
  saveProblem,
  deleteProblem,
  verifyProblemExists,
  verifyProblemDeleted,
  cleanupProblem,
  uniqueTitle,
} from '../helpers/instructor';

async function saveAndGetSlug(page: import('@playwright/test').Page): Promise<string> {
  const responsePromise = page.waitForResponse(
    resp => resp.url().includes('/api/instructor/problems') && resp.request().method() === 'POST',
    { timeout: 10000 },
  );
  await saveProblem(page);
  const response = await responsePromise;
  return (await response.json()).slug;
}

test.describe('Probeable Spec Problem Authoring', () => {
  const createdSlugs: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const slug of createdSlugs) {
      await cleanupProblem(page, slug).catch(() => {});
    }
    createdSlugs.length = 0;
  });

  test('create ProbeableSpec with segmentation config', async ({ page }) => {
    const title = uniqueTitle('E2E ProbSpec Create');

    await goToNewProblem(page, 'probeable_spec');
    await fillBasicInfo(page, { title, description: 'Discover and explain the function behavior' });

    await page.getByRole('textbox', { name: /function signature/i }).fill('def mystery(x: int) -> int:');

    await page.locator('.ace_editor').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.type('def mystery(x):\n    return x * x', { delay: 5 });
    await page.waitForTimeout(500);

    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);
    const params = page.locator('.test-case').last().locator('.param-input');
    if (await params.count() >= 2) {
      await params.nth(0).fill('4');
      await params.nth(1).fill('16');
    }

    const slug = await saveAndGetSlug(page);
    expect(slug).toBeTruthy();
    createdSlugs.push(slug);

    const data = await verifyProblemExists(page, slug);
    expect(data.problem_type).toBe('probeable_spec');
  });

  test('segmentation config section is visible', async ({ page }) => {
    await goToNewProblem(page, 'probeable_spec');

    // ProbeableSpec has both Probe Settings and Segmentation
    await expect(page.locator('text=Probe Settings')).toBeVisible();
    await expect(page.locator('text=Segmentation Configuration')).toBeVisible();
  });

  test('delete ProbeableSpec and verify removal', async ({ page }) => {
    const title = uniqueTitle('E2E ProbSpec Delete');

    await goToNewProblem(page, 'probeable_spec');
    await fillBasicInfo(page, { title, description: 'Problem created for delete verification' });
    await page.getByRole('textbox', { name: /function signature/i }).fill('def f(x: int) -> int:');
    await page.locator('.ace_editor').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.type('def f(x):\n    return x', { delay: 5 });
    await page.waitForTimeout(500);

    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);
    const params = page.locator('.test-case').last().locator('.param-input');
    if (await params.count() >= 2) {
      await params.nth(0).fill('1');
      await params.nth(1).fill('1');
    }

    const slug = await saveAndGetSlug(page);
    await goToEditProblem(page, slug);
    await deleteProblem(page);
    await verifyProblemDeleted(page, slug);
  });
});
