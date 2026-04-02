/**
 * E2E Tests: Instructor Debug & Fix Problem Authoring
 *
 * Verified via Playwright exploration scripts before writing tests.
 * DebugFix has 2 Ace editors (reference solution + buggy code),
 * test cases, and bug hints.
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

/** Type into an Ace editor by index (0 = reference solution, 1 = buggy code). */
async function typeInAce(page: import('@playwright/test').Page, index: number, text: string) {
  const aceEditors = page.locator('.ace_editor');
  await aceEditors.nth(index).click();
  await page.waitForTimeout(300);
  await page.keyboard.press('Control+a');
  await page.keyboard.press('Backspace');
  await page.keyboard.type(text, { delay: 5 });
  await page.waitForTimeout(500);
}

/** Save and capture slug from POST response. */
async function saveAndGetSlug(page: import('@playwright/test').Page): Promise<string> {
  const saveBtn = page.getByRole('button', { name: /save/i });
  const disabled = await saveBtn.isDisabled();
  if (disabled) {
    console.log('[saveAndGetSlug] Save button is DISABLED');
    return '';
  }
  const responsePromise = page.waitForResponse(
    resp => resp.url().includes('/api/instructor/problems') && resp.request().method() === 'POST',
    { timeout: 10000 },
  );
  await saveProblem(page);
  const response = await responsePromise;
  const body = await response.json();
  console.log(`[saveAndGetSlug] ${response.status()} slug=${body.slug}`);
  return body.slug;
}

test.describe('Debug & Fix Problem Authoring', () => {
  const createdSlugs: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const slug of createdSlugs) {
      await cleanupProblem(page, slug).catch(() => {});
    }
    createdSlugs.length = 0;
  });

  test('create DebugFix with buggy code and correct solution', async ({ page }) => {
    const title = uniqueTitle('E2E DebugFix Create');

    await goToNewProblem(page, 'debug_fix');
    await fillBasicInfo(page, { title, description: 'Find and fix the loop bug' });

    // Function signature
    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def sum_to_n(n: int) -> int:',
    );

    // Reference solution (Ace editor index 0)
    await typeInAce(page, 0, 'def sum_to_n(n):\n    return sum(range(1, n + 1))');

    // Buggy code (Ace editor index 1)
    await typeInAce(page, 1, 'def sum_to_n(n):\n    return sum(range(1, n))');

    // Add a test case
    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);
    const params = page.locator('.test-case').last().locator('.param-input');
    if (await params.count() >= 2) {
      await params.nth(0).fill('5');
      await params.nth(1).fill('15');
    }

    const slug = await saveAndGetSlug(page);
    expect(slug).toBeTruthy();
    createdSlugs.push(slug);

    const data = await verifyProblemExists(page, slug);
    expect(data.title).toBe(title);
    expect(data.problem_type).toBe('debug_fix');
    expect(data.buggy_code).toContain('range(1, n)');
    expect(data.reference_solution).toContain('range(1, n + 1)');
  });

  test('Test All shows pass/fail badges', async ({ page }) => {
    const title = uniqueTitle('E2E DebugFix TestAll');

    await goToNewProblem(page, 'debug_fix');
    await fillBasicInfo(page, { title, description: 'Test execution verification' });

    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def double(x: int) -> int:',
    );
    await typeInAce(page, 0, 'def double(x):\n    return x * 2');
    await typeInAce(page, 1, 'def double(x):\n    return x + 2');

    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);
    const params = page.locator('.test-case').last().locator('.param-input');
    if (await params.count() >= 2) {
      await params.nth(0).fill('3');
      await params.nth(1).fill('6');
    }

    const slug = await saveAndGetSlug(page);
    createdSlugs.push(slug);

    await goToEditProblem(page, slug);

    const testAllBtn = page.getByRole('button', { name: 'Test All Cases' });
    await expect(testAllBtn).toBeEnabled({ timeout: 5000 });
    await testAllBtn.click();

    // Wait for results
    await page.locator('.status-badge').first().waitFor({ state: 'visible', timeout: 30000 });

    const passed = await page.locator('.status-badge.status-passed').count();
    expect(passed).toBeGreaterThanOrEqual(1);
  });

  test('edit DebugFix: modify buggy code', async ({ page }) => {
    await navigateAs(page, 'instructor', '/instructor/problems');
    await page.waitForTimeout(500);

    const title = uniqueTitle('E2E DebugFix Edit');
    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/problems/', {
      title,
      problem_type: 'debug_fix',
      function_signature: 'def foo(x: int) -> int:',
      reference_solution: 'def foo(x):\n    return x - 1',
      buggy_code: 'def foo(x):\n    return x',
      description: 'Edit buggy code verification test',
      test_cases: [{ inputs: [5], expected_output: 4 }],
    });
    expect(createResult.status).toBe(201);
    const slug = createResult.data.slug;
    createdSlugs.push(slug);

    await goToEditProblem(page, slug);

    // Modify buggy code (second Ace editor)
    await typeInAce(page, 1, 'def foo(x):\n    return x + 1');

    await saveProblem(page);

    const data = await verifyProblemExists(page, slug);
    expect(data.buggy_code).toContain('return x + 1');
  });

  test('add bug hint via the hints section', async ({ page }) => {
    await goToNewProblem(page, 'debug_fix');

    // Bug Hints section should be visible
    const hintsHeading = page.locator('text=Bug Hints');
    await expect(hintsHeading).toBeVisible();

    // The hint input and Add Hint button should exist
    const hintInput = page.getByPlaceholder(/Check the loop/i);
    await expect(hintInput).toBeVisible();

    const addHintBtn = page.getByRole('button', { name: 'Add Hint' });
    // Button should be disabled when input is empty
    await expect(addHintBtn).toBeDisabled();

    // Type a hint and verify button enables
    await hintInput.fill('Check the range parameters');
    await expect(addHintBtn).toBeEnabled();
  });

  test('delete DebugFix and verify removal', async ({ page }) => {
    const title = uniqueTitle('E2E DebugFix Delete');

    await goToNewProblem(page, 'debug_fix');
    await fillBasicInfo(page, { title, description: 'Problem created for delete verification' });

    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def foo(x: int) -> int:',
    );
    await typeInAce(page, 0, 'def foo(x):\n    return x');
    await typeInAce(page, 1, 'def foo(x):\n    return x + 1');

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
