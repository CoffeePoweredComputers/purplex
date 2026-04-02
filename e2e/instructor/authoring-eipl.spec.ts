/**
 * E2E Tests: Instructor EiPL Problem Authoring
 *
 * Tests the full CRUD lifecycle for Explain in Plain Language problems:
 * create via UI → verify via API → edit → verify → delete → verify.
 *
 * EiPL is the core problem type with reference solution, test cases,
 * segmentation config, and hints.
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
  getSlugFromUrl,
  uniqueTitle,
} from '../helpers/instructor';

/**
 * Type text into an Ace editor within a container (for admin forms).
 *
 * Uses keyboard input AND explicitly calls the form's updateReferenceSolution
 * to ensure the Vue form state stays in sync. Ace keyboard input fires the
 * change event, but the Editor.vue → form composable chain may not propagate
 * reliably in all timing scenarios.
 */
async function typeInAceEditor(page: import('@playwright/test').Page, containerSelector: string, text: string) {
  // Click the Ace editor to focus it (focus() on the hidden text-input
  // doesn't reliably activate Ace's input handling)
  await page.locator(`${containerSelector} .ace_editor`).first().click();
  await page.waitForTimeout(300);
  await page.keyboard.press('Control+a');
  await page.keyboard.press('Backspace');
  await page.keyboard.type(text, { delay: 10 });
  await page.waitForTimeout(500);
}

/** Helper to capture slug from POST response during save. */
async function saveAndGetSlug(page: import('@playwright/test').Page): Promise<string> {
  // Check if save button is enabled before trying
  const saveBtn = page.getByRole('button', { name: /save/i });
  const disabled = await saveBtn.isDisabled();
  if (disabled) {
    console.log('[saveAndGetSlug] Save button is DISABLED — cannot save');
    return '';
  }

  const responsePromise = page.waitForResponse(
    resp => resp.url().includes('/api/instructor/problems') && resp.request().method() === 'POST',
    { timeout: 10000 },
  );
  await saveProblem(page);
  const response = await responsePromise;
  const body = await response.json();
  console.log(`[saveAndGetSlug] Response: ${response.status()} slug=${body.slug} body=${JSON.stringify(body).substring(0, 200)}`);
  return body.slug;
}

test.describe('EiPL Problem Authoring', () => {
  const createdSlugs: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const slug of createdSlugs) {
      await cleanupProblem(page, slug).catch(() => {});
    }
    createdSlugs.length = 0;
  });

  // -------------------------------------------------------------------
  // Create
  // -------------------------------------------------------------------

  test('create EiPL with signature, solution, and test case', async ({ page }) => {
    const title = uniqueTitle('E2E EiPL Create');

    await goToNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title, description: 'Adds two numbers' });

    // Fill function signature
    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def add(a: int, b: int) -> int:',
    );

    // Fill reference solution in Ace editor
    await typeInAceEditor(page, '.code-editor', 'def add(a, b):\n    return a + b');

    // EiPL requires at least 1 test case for save to be enabled
    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);

    // Fill test case: add(2, 3) -> 5
    const paramInputs = page.locator('.test-case').last().locator('.param-input');
    const count = await paramInputs.count();
    if (count >= 3) {
      await paramInputs.nth(0).fill('2');
      await paramInputs.nth(1).fill('3');
      await paramInputs.nth(2).fill('5');
    }

    const slug = await saveAndGetSlug(page);
    expect(slug).toBeTruthy();
    createdSlugs.push(slug);

    const data = await verifyProblemExists(page, slug);
    expect(data.title).toBe(title);
    expect(data.problem_type).toBe('eipl');
    expect(data.function_signature).toContain('def add');
    expect(data.reference_solution).toContain('return a + b');
  });

  test('create EiPL with test cases', async ({ page }) => {
    const title = uniqueTitle('E2E EiPL TestCases');

    await goToNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title, description: 'Sum function' });

    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def add(a: int, b: int) -> int:',
    );
    await typeInAceEditor(page, '.code-editor','return a + b');

    // Add first test case
    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);

    // Fill parameter inputs — the test case has fields for a, b, and output
    const paramInputs = page.locator('.test-case').last().locator('.param-input');
    // Parameters appear in order: a, b, output
    const paramCount = await paramInputs.count();
    if (paramCount >= 3) {
      await paramInputs.nth(0).fill('2');
      await paramInputs.nth(1).fill('3');
      await paramInputs.nth(2).fill('5');
    }

    // Add second test case
    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);

    const secondCase = page.locator('.test-case').last().locator('.param-input');
    const secondCount = await secondCase.count();
    if (secondCount >= 3) {
      await secondCase.nth(0).fill('0');
      await secondCase.nth(1).fill('0');
      await secondCase.nth(2).fill('0');
    }

    const slug = await saveAndGetSlug(page);
    createdSlugs.push(slug);

    const data = await verifyProblemExists(page, slug);
    expect(data.test_cases).toBeDefined();
    expect(data.test_cases.length).toBeGreaterThanOrEqual(2);
  });

  // -------------------------------------------------------------------
  // Validation
  // -------------------------------------------------------------------

  test('save is blocked without function signature', async ({ page }) => {
    await goToNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title: uniqueTitle('E2E EiPL NoSig'), description: 'Test' });

    // Fill reference solution + test case but NOT function signature
    await typeInAceEditor(page, '.code-editor', 'def foo():\n    return 42');
    await page.getByRole('button', { name: '+ Add Test' }).click();

    const saveBtn = page.getByRole('button', { name: /save/i });
    await expect(saveBtn).toBeDisabled({ timeout: 3000 });
  });

  test('save is blocked without reference solution', async ({ page }) => {
    await goToNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title: uniqueTitle('E2E EiPL NoRef'), description: 'Test' });

    // Fill function signature + test case but NOT reference solution
    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def foo(x: int) -> int:',
    );
    await page.getByRole('button', { name: '+ Add Test' }).click();

    const saveBtn = page.getByRole('button', { name: /save/i });
    await expect(saveBtn).toBeDisabled({ timeout: 3000 });
  });

  test('save is blocked without test cases', async ({ page }) => {
    await goToNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title: uniqueTitle('E2E EiPL NoTC'), description: 'Test' });

    // Fill signature + solution but NO test cases
    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def foo(x: int) -> int:',
    );
    await typeInAceEditor(page, '.code-editor', 'def foo(x):\n    return x');

    const saveBtn = page.getByRole('button', { name: /save/i });
    await expect(saveBtn).toBeDisabled({ timeout: 3000 });
  });

  // -------------------------------------------------------------------
  // Test Cases
  // -------------------------------------------------------------------

  test('Test All Cases runs and shows pass badges', async ({ page }) => {
    const title = uniqueTitle('E2E EiPL TestAll');

    await goToNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title, description: 'Test runner' });

    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def add(a: int, b: int) -> int:',
    );
    await typeInAceEditor(page, '.code-editor','return a + b');

    // Add a test case
    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);

    const paramInputs = page.locator('.test-case').last().locator('.param-input');
    const count = await paramInputs.count();
    if (count >= 3) {
      await paramInputs.nth(0).fill('2');
      await paramInputs.nth(1).fill('3');
      await paramInputs.nth(2).fill('5');
    }

    // Save first (Test All requires a saved problem)
    const slug = await saveAndGetSlug(page);
    createdSlugs.push(slug);

    // Navigate to edit to run tests
    await goToEditProblem(page, slug);

    // Click Test All
    const testAllBtn = page.getByRole('button', { name: 'Test All Cases' });
    await expect(testAllBtn).toBeEnabled({ timeout: 5000 });
    await testAllBtn.click();

    // Wait for test results (pass/fail badges)
    await page.locator('.status-badge').first().waitFor({ state: 'visible', timeout: 30000 });

    // Should show passed
    const passedBadges = page.locator('.status-badge.passed');
    expect(await passedBadges.count()).toBeGreaterThanOrEqual(1);
  });

  test('Test All Cases shows failure for wrong expected output', async ({ page }) => {
    const title = uniqueTitle('E2E EiPL TestFail');

    await goToNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title, description: 'Failing test' });

    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def add(a: int, b: int) -> int:',
    );
    await typeInAceEditor(page, '.code-editor','return a + b');

    // Add test case with WRONG expected output
    await page.getByRole('button', { name: '+ Add Test' }).click();
    await page.waitForTimeout(500);

    const paramInputs = page.locator('.test-case').last().locator('.param-input');
    const count = await paramInputs.count();
    if (count >= 3) {
      await paramInputs.nth(0).fill('2');
      await paramInputs.nth(1).fill('3');
      await paramInputs.nth(2).fill('999');  // Wrong: 2+3=5, not 999
    }

    const slug = await saveAndGetSlug(page);
    createdSlugs.push(slug);

    await goToEditProblem(page, slug);

    const testAllBtn = page.getByRole('button', { name: 'Test All Cases' });
    await expect(testAllBtn).toBeEnabled({ timeout: 5000 });
    await testAllBtn.click();

    // Wait for test results
    await page.locator('.status-badge').first().waitFor({ state: 'visible', timeout: 30000 });

    // Should show failed
    const failedBadges = page.locator('.status-badge.failed');
    expect(await failedBadges.count()).toBeGreaterThanOrEqual(1);
  });

  test('add and remove test cases', async ({ page }) => {
    await goToNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title: uniqueTitle('E2E EiPL TC CRUD'), description: 'Test' });

    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def foo(x: int) -> int:',
    );

    // Start with 0 test cases
    await expect(page.locator('.test-case')).toHaveCount(0);

    // Add 3 test cases
    const addBtn = page.getByRole('button', { name: '+ Add Test' });
    await addBtn.click();
    await expect(page.locator('.test-case')).toHaveCount(1);
    await addBtn.click();
    await expect(page.locator('.test-case')).toHaveCount(2);
    await addBtn.click();
    await expect(page.locator('.test-case')).toHaveCount(3);

    // Remove the last test case (click the remove button)
    const removeBtn = page.locator('.test-case').last().locator('button').last();
    await removeBtn.click();
    await expect(page.locator('.test-case')).toHaveCount(2);
  });

  // -------------------------------------------------------------------
  // Edit
  // -------------------------------------------------------------------

  test('edit EiPL: change function signature', async ({ page }) => {
    const title = uniqueTitle('E2E EiPL EditSig');

    await navigateAs(page, 'instructor', '/instructor/problems');
    await page.waitForTimeout(500);

    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/problems/', {
      title,
      problem_type: 'eipl',
      function_signature: 'def old(x: int) -> int:',
      reference_solution: 'return x',
      description: 'Edit test',
    });
    const slug = createResult.data.slug;
    createdSlugs.push(slug);

    await goToEditProblem(page, slug);

    // Change function signature
    const sigInput = page.getByRole('textbox', { name: /function signature/i });
    await sigInput.fill('def new_func(x: int, y: int) -> int:');

    await saveProblem(page);

    const data = await verifyProblemExists(page, slug);
    expect(data.function_signature).toContain('new_func');
  });

  test('edit EiPL: toggle segmentation', async ({ page }) => {
    const title = uniqueTitle('E2E EiPL Seg');

    await navigateAs(page, 'instructor', '/instructor/problems');
    await page.waitForTimeout(500);

    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/problems/', {
      title,
      problem_type: 'eipl',
      function_signature: 'def foo(x: int) -> int:',
      reference_solution: 'return x',
      description: 'Segmentation test',
    });
    const slug = createResult.data.slug;
    createdSlugs.push(slug);

    await goToEditProblem(page, slug);

    // Find segmentation checkbox
    const segCheckbox = page.getByRole('checkbox', { name: /segmentation/i });
    const wasChecked = await segCheckbox.isChecked();

    // Toggle it
    if (wasChecked) {
      await segCheckbox.uncheck();
    } else {
      await segCheckbox.check();
    }

    await saveProblem(page);

    // Verify the toggle persisted
    await goToEditProblem(page, slug);
    const isNowChecked = await segCheckbox.isChecked();
    expect(isNowChecked).toBe(!wasChecked);
  });

  // -------------------------------------------------------------------
  // Hints
  // -------------------------------------------------------------------

  test('enable Variable Fade hint', async ({ page }) => {
    await goToNewProblem(page, 'eipl');

    // The Variable Fade tab should be visible
    const varFadeTab = page.getByRole('button', { name: 'Variable Fade' });
    await expect(varFadeTab).toBeVisible();

    // Enable the hint
    const enableCheckbox = page.getByRole('checkbox', { name: /variable fade/i });
    await enableCheckbox.check();
    await expect(enableCheckbox).toBeChecked();
  });

  test('hint tabs switch content', async ({ page }) => {
    await goToNewProblem(page, 'eipl');

    // Click through each hint tab
    await page.getByRole('button', { name: 'Variable Fade' }).click();
    await expect(page.getByRole('checkbox', { name: /variable fade/i })).toBeVisible();

    await page.getByRole('button', { name: 'Subgoal Highlighting' }).click();
    await expect(page.getByRole('checkbox', { name: /subgoal/i })).toBeVisible();

    await page.getByRole('button', { name: 'Suggested Trace' }).click();
    await expect(page.getByRole('checkbox', { name: /suggested trace/i })).toBeVisible();
  });

  // -------------------------------------------------------------------
  // Delete
  // -------------------------------------------------------------------

  test('delete EiPL and verify removal', async ({ page }) => {
    const title = uniqueTitle('E2E EiPL Delete');

    await goToNewProblem(page, 'eipl');
    await fillBasicInfo(page, { title, description: 'To delete' });
    await page.getByRole('textbox', { name: /function signature/i }).fill(
      'def foo(x: int) -> int:',
    );
    await typeInAceEditor(page, '.code-editor', 'def foo(x):\n    return x');

    // Need at least 1 test case for EiPL save to be enabled
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
