/**
 * E2E Tests: Instructor Probeable Code Problem Authoring
 *
 * Verified: ProbeableCode has function signature, reference solution (1 Ace editor),
 * probe settings section, and test cases. Save works with just title + desc + sig + solution + test case.
 */

import { test, expect } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';
import { apiAs } from '../helpers/api';
import {
  goToNewProblem,
  goToEditProblem,
  fillBasicInfo,
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

test.describe('Probeable Code Problem Authoring', () => {
  const createdSlugs: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const slug of createdSlugs) {
      await cleanupProblem(page, slug).catch(() => {});
    }
    createdSlugs.length = 0;
  });

  test('create ProbeableCode with test case', async ({ page }) => {
    const title = uniqueTitle('E2E ProbCode Create');

    await goToNewProblem(page, 'probeable_code');
    await fillBasicInfo(page, { title, description: 'Discover and implement the function' });

    await page.getByRole('textbox', { name: /function signature/i }).fill('def double(x: int) -> int:');

    await page.locator('.ace_editor').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.type('def double(x):\n    return x * 2', { delay: 5 });
    await page.waitForTimeout(500);

    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);
    const params = page.locator('.test-case').last().locator('.param-input');
    if (await params.count() >= 2) {
      await params.nth(0).fill('5');
      await params.nth(1).fill('10');
    }

    const slug = await saveAndGetSlug(page);
    expect(slug).toBeTruthy();
    createdSlugs.push(slug);

    const data = await verifyProblemExists(page, slug);
    expect(data.problem_type).toBe('probeable_code');
  });

  test('probe settings section is visible', async ({ page }) => {
    await goToNewProblem(page, 'probeable_code');

    const probeHeading = page.locator('text=Probe Settings');
    await expect(probeHeading).toBeVisible();
  });

  test('delete ProbeableCode and verify removal', async ({ page }) => {
    const title = uniqueTitle('E2E ProbCode Delete');

    await goToNewProblem(page, 'probeable_code');
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
