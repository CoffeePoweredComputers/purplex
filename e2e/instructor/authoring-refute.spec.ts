/**
 * E2E Tests: Instructor Refute Problem Authoring
 *
 * Verified: Refute has claim text, claim predicate, function signature,
 * reference solution (1 Ace editor). No test cases required.
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

test.describe('Refute Problem Authoring', () => {
  const createdSlugs: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const slug of createdSlugs) {
      await cleanupProblem(page, slug).catch(() => {});
    }
    createdSlugs.length = 0;
  });

  test('create Refute with claim and predicate', async ({ page }) => {
    const title = uniqueTitle('E2E Refute Create');

    await goToNewProblem(page, 'refute');
    await fillBasicInfo(page, { title, description: 'Find a counterexample to disprove the claim' });

    // Claim fields (placeholders from exploration)
    await page.getByPlaceholder(/always returns a positive/i).fill('The function always returns a positive number');
    await page.getByPlaceholder(/result > 0/i).fill('result > 0');

    // Function signature
    await page.getByRole('textbox', { name: /function signature/i }).fill('def mystery(x: int) -> int:');

    // Reference solution
    await page.locator('.ace_editor').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.type('def mystery(x):\n    return x * x - 1', { delay: 5 });
    await page.waitForTimeout(500);

    const slug = await saveAndGetSlug(page);
    expect(slug).toBeTruthy();
    createdSlugs.push(slug);

    const data = await verifyProblemExists(page, slug);
    expect(data.problem_type).toBe('refute');
    expect(data.claim_text).toContain('positive number');
  });

  test('save is blocked without claim text', async ({ page }) => {
    await goToNewProblem(page, 'refute');
    await fillBasicInfo(page, { title: uniqueTitle('E2E Refute NoClaim'), description: 'Missing claim text test' });

    // Fill everything except claim
    await page.getByPlaceholder(/result > 0/i).fill('result > 0');
    await page.getByRole('textbox', { name: /function signature/i }).fill('def f(x: int) -> int:');
    await page.locator('.ace_editor').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.type('def f(x):\n    return x', { delay: 5 });
    await page.waitForTimeout(500);

    await expect(page.getByRole('button', { name: /save/i })).toBeDisabled({ timeout: 3000 });
  });

  test('edit Refute: change claim text', async ({ page }) => {
    await navigateAs(page, 'instructor', '/instructor/problems');
    await page.waitForTimeout(500);

    const title = uniqueTitle('E2E Refute Edit');
    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/problems/', {
      title,
      problem_type: 'refute',
      claim_text: 'Original claim',
      claim_predicate: 'result > 0',
      function_signature: 'def f(x: int) -> int:',
      reference_solution: 'def f(x):\n    return x * x - 1',
      description: 'Edit claim text verification test',
    });
    expect(createResult.status).toBe(201);
    const slug = createResult.data.slug;
    createdSlugs.push(slug);

    await goToEditProblem(page, slug);
    await page.getByPlaceholder(/always returns/i).fill('Updated claim text for testing');
    await saveProblem(page);

    const data = await verifyProblemExists(page, slug);
    expect(data.claim_text).toContain('Updated claim');
  });

  test('delete Refute and verify removal', async ({ page }) => {
    const title = uniqueTitle('E2E Refute Delete');

    await goToNewProblem(page, 'refute');
    await fillBasicInfo(page, { title, description: 'Problem created for delete verification' });
    await page.getByPlaceholder(/always returns a positive/i).fill('Test claim for delete');
    await page.getByPlaceholder(/result > 0/i).fill('result > 0');
    await page.getByRole('textbox', { name: /function signature/i }).fill('def f(x: int) -> int:');
    await page.locator('.ace_editor').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.type('def f(x):\n    return x', { delay: 5 });
    await page.waitForTimeout(500);

    const slug = await saveAndGetSlug(page);
    await goToEditProblem(page, slug);
    await deleteProblem(page);
    await verifyProblemDeleted(page, slug);
  });
});
