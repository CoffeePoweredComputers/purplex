/**
 * E2E Tests: Instructor Prompt Problem Authoring
 *
 * Verified: Prompt has image URL + alt text, function signature,
 * reference solution (1 Ace editor), and test cases. Similar to EiPL
 * but with an image instead of code display.
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

test.describe('Prompt Problem Authoring', () => {
  const createdSlugs: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const slug of createdSlugs) {
      await cleanupProblem(page, slug).catch(() => {});
    }
    createdSlugs.length = 0;
  });

  test('create Prompt with image URL and solution', async ({ page }) => {
    const title = uniqueTitle('E2E Prompt Create');

    await goToNewProblem(page, 'prompt');
    await fillBasicInfo(page, { title, description: 'Explain what this image shows' });

    // Image fields (from exploration: placeholder 'https://example.com/image.png')
    await page.getByPlaceholder('https://example.com/image.png').fill('https://example.com/test-image.png');
    await page.getByPlaceholder('Describe the image').fill('A flowchart showing the algorithm');

    // Function signature + reference solution
    await page.getByRole('textbox', { name: /function signature/i }).fill('def process(data: list) -> int:');
    await page.locator('.ace_editor').first().click();
    await page.waitForTimeout(300);
    await page.keyboard.type('def process(data):\n    return sum(data)', { delay: 5 });
    await page.waitForTimeout(500);

    // Test case
    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);
    const params = page.locator('.test-case').last().locator('.param-input');
    if (await params.count() >= 2) {
      await params.nth(0).fill('[1, 2, 3]');
      await params.nth(1).fill('6');
    }

    const slug = await saveAndGetSlug(page);
    expect(slug).toBeTruthy();
    createdSlugs.push(slug);

    const data = await verifyProblemExists(page, slug);
    expect(data.problem_type).toBe('prompt');
    expect(data.image_url).toContain('test-image.png');
  });

  test('save is blocked without image URL', async ({ page }) => {
    await goToNewProblem(page, 'prompt');
    await fillBasicInfo(page, { title: uniqueTitle('E2E Prompt NoImg'), description: 'Missing image URL test' });

    // Fill everything except image URL
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

    await expect(page.getByRole('button', { name: /save/i })).toBeDisabled({ timeout: 3000 });
  });

  test('edit Prompt: change image URL', async ({ page }) => {
    await navigateAs(page, 'instructor', '/instructor/problems');
    await page.waitForTimeout(500);

    const title = uniqueTitle('E2E Prompt Edit');
    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/problems/', {
      title,
      problem_type: 'prompt',
      image_url: 'https://example.com/original.png',
      image_alt_text: 'Original image',
      function_signature: 'def f(x: int) -> int:',
      reference_solution: 'def f(x):\n    return x',
      description: 'Edit image URL verification test',
      test_cases: [{ inputs: [1], expected_output: 1 }],
    });
    expect(createResult.status).toBe(201);
    const slug = createResult.data.slug;
    createdSlugs.push(slug);

    await goToEditProblem(page, slug);

    await page.getByPlaceholder('https://example.com/image.png').fill('https://example.com/updated.png');
    await saveProblem(page);

    const data = await verifyProblemExists(page, slug);
    expect(data.image_url).toContain('updated.png');
  });

  test('delete Prompt and verify removal', async ({ page }) => {
    const title = uniqueTitle('E2E Prompt Delete');

    await goToNewProblem(page, 'prompt');
    await fillBasicInfo(page, { title, description: 'Problem created for delete verification' });
    await page.getByPlaceholder('https://example.com/image.png').fill('https://example.com/del.png');
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
