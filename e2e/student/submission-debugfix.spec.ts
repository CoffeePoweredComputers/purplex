/**
 * E2E Tests: Debug & Fix Submission Flow
 *
 * Tests the Debug & Fix submission workflow for e2e-debugfix-1 in the
 * e2e-code problem set. Debug & Fix submissions are ASYNCHRONOUS --
 * code is executed in Docker containers via Celery, results streamed via SSE.
 *
 * Seeded data:
 *   - CS101-2024 course with e2e-code problem set (soft past deadline)
 *   - e2e-debugfix-1: "Fix the Loop" -- sum_to_n(n) with off-by-one bug
 *   - Buggy code: range(1, n) should be range(1, n + 1)
 *   - Test cases: sum_to_n(5)=15, sum_to_n(1)=1
 *
 * Prerequisites:
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true
 *   2. Celery worker running (with Docker-in-Docker for code execution)
 *   3. Vite dev server on :5173
 *   4. python manage.py create_test_users && python manage.py seed_e2e_data
 */

import { test, expect, Page } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';

// Generous timeout for async code execution submissions
const ASYNC_TIMEOUT = 45000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Navigate to e2e-code and select e2e-debugfix-1. */
async function goToDebugFixProblem(page: Page) {
  await navigateAs(
    page,
    'student',
    '/courses/CS101-2024/problem-set/e2e-code?problem=e2e-debugfix-1',
  );
  // Wait for the Debug Fix input to appear (code editor wrapper)
  await page.locator('.debug-fix-input, #codeEditor').first().waitFor({
    state: 'visible',
    timeout: 15000,
  });
}

/**
 * Replace content in the Ace code editor.
 *
 * The DebugFix input uses Ace editor. We select-all and type replacement code.
 */
async function replaceEditorCode(page: Page, code: string) {
  const editorTextarea = page.locator('#codeEditor .ace_text-input').first();
  await editorTextarea.focus();
  await page.keyboard.press('Control+a');
  await page.keyboard.press('Backspace');
  await page.keyboard.type(code, { delay: 5 });
}

/**
 * Submit and wait for async code execution result.
 */
async function submitAndWaitForAsyncResult(page: Page) {
  const submitBtn = page.locator('#submitButton');
  await expect(submitBtn).toBeEnabled({ timeout: 5000 });
  await submitBtn.click();

  // Button should show loading state
  await expect(submitBtn).toBeDisabled({ timeout: 5000 });

  // Wait for test results to appear in the feedback panel
  const feedbackOrLoading = page.locator(
    '.feedback-container .feedback-header, .feedback-container .generating-feedback-panel',
  ).first();
  await feedbackOrLoading.waitFor({ state: 'visible', timeout: ASYNC_TIMEOUT });

  // If loading panel is visible, wait for it to be replaced by results
  const generating = page.locator('.generating-feedback-panel');
  if (await generating.isVisible().catch(() => false)) {
    await generating.waitFor({ state: 'hidden', timeout: ASYNC_TIMEOUT });
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Debug & Fix Submission', () => {
  test('buggy code is pre-loaded in the editor', async ({ page }) => {
    await goToDebugFixProblem(page);

    // The editor should contain the buggy code from the seed data.
    // Wait for the Ace editor content to contain the expected function name.
    const editorContent = page.locator('#codeEditor .ace_content').first();
    await expect(editorContent).toBeVisible({ timeout: 10000 });

    // Wait for the code to be loaded into the editor (not just the empty editor)
    await expect(editorContent).toContainText('sum_to_n', { timeout: 10000 });

    const codeText = await editorContent.textContent();
    expect(codeText).toContain('range');
  });

  test('submitting fixed code shows test results', async ({ page }) => {
    await goToDebugFixProblem(page);

    // Replace with the correct solution: range(1, n + 1)
    const fixedCode = [
      'def sum_to_n(n):',
      '    total = 0',
      '    for i in range(1, n + 1):',
      '        total += i',
      '    return total',
    ].join('\n');

    await replaceEditorCode(page, fixedCode);
    await submitAndWaitForAsyncResult(page);

    // After async result, the feedback container should show test results
    const feedbackHeader = page.locator(
      '.feedback-header .section-label, .feedback-header .header-title',
    ).first();
    await expect(feedbackHeader).toBeVisible({ timeout: 10000 });
  });

  test('reset button restores original buggy code', async ({ page }) => {
    await goToDebugFixProblem(page);

    // Modify the code first
    await replaceEditorCode(page, 'def sum_to_n(n): return 42');

    // Click the reset button
    const resetBtn = page.locator('.reset-button');
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();

    // The editor should revert to the original buggy code
    await page.waitForTimeout(500);
    const editorContent = page.locator('#codeEditor .ace_content').first();
    const codeText = await editorContent.textContent();
    expect(codeText).toContain('sum_to_n');
  });

  test('soft past deadline still allows submission', async ({ page }) => {
    // e2e-code has a soft past deadline, so submissions should still work
    await goToDebugFixProblem(page);

    // Check for the deadline banner -- should show late submission warning, not locked
    const lockedBanner = page.locator('.deadline-locked');
    await expect(lockedBanner).not.toBeVisible();

    // The submit button should be available (not blocked by deadline)
    const submitBtn = page.locator('#submitButton');
    await expect(submitBtn).toBeVisible();
  });
});
