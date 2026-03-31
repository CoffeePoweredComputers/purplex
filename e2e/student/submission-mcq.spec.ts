/**
 * E2E Tests: MCQ Submission Flow
 *
 * Tests the Multiple Choice Question submission workflow for e2e-mcq-1
 * in the e2e-basics problem set. MCQ submissions are SYNCHRONOUS --
 * the server returns an instant result with no Celery/SSE involvement.
 *
 * Seeded data:
 *   - CS101-2024 course with e2e-basics problem set (future deadline)
 *   - e2e-mcq-1: 4 options (a/b/c/d), option "a" is correct
 *   - Student already has 1 prior correct submission on e2e-mcq-1
 *
 * Prerequisites:
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server on :5173
 *   3. python manage.py create_test_users && python manage.py seed_e2e_data
 */

import { test, expect, Page } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';
import { apiAs } from '../helpers/api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Navigate to the e2e-basics problem set at e2e-mcq-1. */
async function goToMcqProblem(page: Page) {
  await navigateAs(page, 'student', '/courses/CS101-2024/problem-set/e2e-basics?p=0');
  // Wait for the MCQ options to render
  await page.locator('.mcq-options-container').waitFor({ state: 'visible', timeout: 15000 });
}

/** Click an MCQ option by its displayed text. */
async function selectOption(page: Page, text: string) {
  const option = page.locator('.mcq-option').filter({ hasText: text });
  await option.click();
}

/** Click the submit button and wait for the MCQ feedback banner. */
async function submitAndWaitForFeedback(page: Page) {
  const submitBtn = page.locator('#submitButton');
  await expect(submitBtn).toBeEnabled();
  await submitBtn.click();
  // MCQ is synchronous -- feedback appears immediately
  await page.locator('.mcq-feedback .result-banner').waitFor({ state: 'visible', timeout: 10000 });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('MCQ Submission', () => {
  test('correct answer shows success feedback with score 100', async ({ page }) => {
    await goToMcqProblem(page);

    // Option "a" ("A named storage location in memory") is the correct answer
    await selectOption(page, 'A named storage location in memory');

    // Verify the option gets the selected class
    const selectedOption = page.locator('.mcq-option--selected');
    await expect(selectedOption).toBeVisible();

    await submitAndWaitForFeedback(page);

    // Check for correct feedback banner
    const banner = page.locator('.result-banner--correct');
    await expect(banner).toBeVisible();

    // Check the result icon shows checkmark
    const icon = banner.locator('.result-icon');
    await expect(icon).toContainText('\u2713');

    // Score should show 100
    const score = page.locator('.result-score');
    await expect(score).toContainText('100');
  });

  test('incorrect answer shows error feedback with correct answer revealed', async ({ page }) => {
    await goToMcqProblem(page);

    // Select an incorrect option -- "A type of loop" (option b)
    await selectOption(page, 'A type of loop');

    await submitAndWaitForFeedback(page);

    // Check for incorrect feedback banner
    const banner = page.locator('.result-banner--incorrect');
    await expect(banner).toBeVisible();

    // Check the result icon shows X
    const icon = banner.locator('.result-icon');
    await expect(icon).toContainText('\u2717');

    // Score should show 0
    const score = page.locator('.result-score');
    await expect(score).toContainText('0');

    // The correct answer should be revealed
    const correctSection = page.locator('.answer-section').filter({
      has: page.locator('.answer-label', { hasText: /correct answer/i }),
    });
    await expect(correctSection).toBeVisible();
    await expect(correctSection.locator('.answer-value--correct')).toContainText(
      'A named storage location in memory',
    );
  });

  test('submit button is enabled only when an option is selected', async ({ page }) => {
    await goToMcqProblem(page);

    // The seeded student has a prior submission on this MCQ, so the previously
    // selected option may be pre-loaded. Verify the button state is consistent:
    // enabled when an option is selected, disabled when none is.
    const submitBtn = page.locator('#submitButton');
    const selectedOption = page.locator('.mcq-option--selected');
    const hasSelected = await selectedOption.count() > 0;

    if (hasSelected) {
      // Prior selection restored — button should be enabled
      await expect(submitBtn).toBeEnabled();
    } else {
      // No selection — button should be disabled
      await expect(submitBtn).toBeDisabled();
    }
  });

  test('progress bar updates after correct submission', async ({ page }) => {
    await goToMcqProblem(page);

    // Submit correct answer
    await selectOption(page, 'A named storage location in memory');
    await submitAndWaitForFeedback(page);

    // The progress bar button for the current (first) problem should show completed
    const progressBars = page.locator('.progress-bar');
    const firstBar = progressBars.first();
    // After correct MCQ, the bar should have the completed class
    await expect(firstBar).toHaveClass(/completed/);
  });

  test('re-submission on already-completed problem works', async ({ page }) => {
    await goToMcqProblem(page);

    // The student already has a prior correct submission on e2e-mcq-1.
    // Submit again with a different (wrong) answer -- this should still work.
    await selectOption(page, 'A comment in code');

    await submitAndWaitForFeedback(page);

    // Should get incorrect result
    const banner = page.locator('.result-banner--incorrect');
    await expect(banner).toBeVisible();
  });

  test('submission history API records the new attempt', async ({ page }) => {
    await goToMcqProblem(page);

    // Submit a correct answer
    await selectOption(page, 'A named storage location in memory');
    await submitAndWaitForFeedback(page);

    // Check the submission history via the API helper
    const { status, data } = await apiAs(
      page,
      'student',
      'GET',
      '/api/submissions/history/e2e-mcq-1/?problem_set_slug=e2e-basics&course_id=CS101-2024',
    );

    expect(status).toBe(200);

    // Should have at least 2 submissions (1 seeded + 1 we just made)
    const submissions = Array.isArray(data) ? data : data.results || data.submissions || [];
    expect(submissions.length).toBeGreaterThanOrEqual(2);
  });
});
