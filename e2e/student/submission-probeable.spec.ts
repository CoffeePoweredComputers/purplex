/**
 * E2E Tests: Probeable Code & Refute Submission Flow
 *
 * Tests the Probeable Code submission workflow for e2e-probeable-code-1
 * and the Refute problem (e2e-refute-1) deadline enforcement.
 *
 * Probeable Code has two phases:
 *   1. Probe phase: students query the oracle with inputs to discover behavior
 *      (POST /api/problems/<slug>/probe/ answers synchronously)
 *   2. Code phase: students write implementation code and submit
 *
 * The E2E stack runs Celery eagerly (CELERY_EAGER=true), so POST /api/submit/
 * grades the submission synchronously in the local Docker sandbox
 * (DOCKER_POOL_ENABLED=false) and the SSE stream reports completion at once.
 *
 * Probe history lives in Redis per (problem, user) with no reset, so tests
 * that probe or submit run as a fresh student (e2e/helpers/users.ts).
 *
 * Seeded data:
 *   - CS101-2024 course with e2e-code problem set (soft past deadline)
 *   - e2e-probeable-code-1: mystery(lst) -- actually sorted(lst) (e2e-code, p=1)
 *     function_signature: "def mystery(lst: list[int]) -> list[int]"
 *     probe_mode: "explore", one test case: mystery([3, 1, 2]) == [1, 2, 3]
 *   - e2e-probeable-code-typed: double(n) -- n * 2 (e2e-code, p=2)
 *     function_signature: "def double(n: int) -> int"
 *     used to check client-side probe input type validation (#135)
 *   - e2e-refute-1: f(x) = x * 2, claim "always returns positive"
 *     (in e2e-mixed which has hard past deadline -- locked)
 *
 * Prerequisites (same as .github/workflows/e2e.yml):
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true,
 *      CELERY_EAGER=true, DOCKER_POOL_ENABLED=false, and the
 *      purplex/python-sandbox image available to the local Docker daemon
 *   2. Vite dev server on :5173
 *   3. python manage.py create_test_users && python manage.py seed_e2e_data
 */

import { test, expect, Page } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';
import { apiAs } from '../helpers/api';
import { apiAsUser, enrollUser, freshStudent, injectUser, navigateAsFreshStudent } from '../helpers/users';
import { submitCodeAndWait } from '../helpers/submission';
import { codeFeedback, probe } from '../helpers/selectors';

const PROBEABLE_PATH = '/courses/CS101-2024/problem-set/e2e-code?p=1';
const TYPED_PROBEABLE_PATH = '/courses/CS101-2024/problem-set/e2e-code?p=2';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Wait for the probeable code input to render. */
async function waitForProbeableInput(page: Page) {
  await page.locator('.probeable-code-input, .probe-panel, #codeEditor').first().waitFor({
    state: 'visible',
    timeout: 15000,
  });
}

/** Navigate to e2e-code and select e2e-probeable-code-1 as the seeded student. */
async function goToProbeableProblem(page: Page) {
  await navigateAs(page, 'student', PROBEABLE_PATH);
  await waitForProbeableInput(page);
}

/** Type code into the Probeable Code Ace editor. */
async function typeInCodeEditor(page: Page, code: string) {
  const editorTextarea = page.locator('#codeEditor .ace_text-input').first();
  await editorTextarea.focus();
  await page.keyboard.press('Control+a');
  await page.keyboard.press('Backspace');
  await page.keyboard.type(code, { delay: 5 });
}

// ---------------------------------------------------------------------------
// Probeable Code Tests
// ---------------------------------------------------------------------------

test.describe('Probeable Code Submission', () => {
  test('probe panel is visible with section header', async ({ page }) => {
    await goToProbeableProblem(page);

    // The probeable code input component should be rendered
    const probeSection = page.locator('.probeable-code-input');
    await expect(probeSection).toBeVisible({ timeout: 10000 });

    // Should display the section header
    const sectionLabel = probeSection.locator('.section-label').first();
    await expect(sectionLabel).toBeVisible();
  });

  test('probe oracle via API returns sorted result', async ({ page }) => {
    const user = freshStudent('probe-api');
    await injectUser(page, user);
    await enrollUser(page, user);

    const { status, data } = await apiAsUser(
      page,
      user,
      'POST',
      '/api/problems/e2e-probeable-code-1/probe/',
      { input: { lst: [3, 1, 2] }, course_id: 'CS101-2024' },
    );

    expect(status).toBe(200);
    expect(data.success).toBe(true);
    expect(data.error).toBeNull();
    expect(data.result).toEqual([1, 2, 3]);
    expect(data.probe_status.mode).toBe('explore');
  });

  test('code editor is available for writing implementation', async ({ page }) => {
    await goToProbeableProblem(page);

    // Below the probe panel, there should be a code editor
    const codeEditor = page.locator('#codeEditor');
    await expect(codeEditor).toBeVisible({ timeout: 10000 });

    // The submit button for the final code should exist
    const submitBtn = page.locator('#submitButton');
    await expect(submitBtn).toBeVisible();
  });

  test('submitting a correct solution grades it and shows the passing feedback', async ({ page }) => {
    // submitCodeAndWait waits up to 60s for grading in the Docker sandbox.
    test.setTimeout(90_000);
    await navigateAsFreshStudent(page, 'probeable-submit', PROBEABLE_PATH);
    await waitForProbeableInput(page);

    // The mystery function is sorted(); its single test case must pass
    await submitCodeAndWait(page, 'def mystery(lst):\n    return sorted(lst)');

    await expect(page.locator(codeFeedback.passing)).toHaveText('✓ 1 Passing');
    await expect(page.locator(codeFeedback.failing)).toHaveText('✗ 0 Failing');
    await expect(page.locator(codeFeedback.locked)).toHaveCount(0);
    await expect(page.locator(codeFeedback.failingItem)).toHaveCount(0);
    await expect(page.locator(`${codeFeedback.attemptTrigger} .attempt-text`)).toHaveText('1/1');
    const scoreBadge = page.locator(`${codeFeedback.attemptTrigger} .attempt-score-badge`);
    await expect(scoreBadge).toHaveText('✓ 100%');
    await expect(scoreBadge).toHaveAttribute('aria-label', 'Score: 100 percent');
    await expect(scoreBadge).toHaveClass(/score-perfect/);
  });

  test('submit button requires minimum code length', async ({ page }) => {
    await goToProbeableProblem(page);

    // Clear the editor and type something too short
    await typeInCodeEditor(page, 'x = 1');

    const submitBtn = page.locator('#submitButton');
    // Should be disabled due to min_length validation
    await expect(submitBtn).toBeDisabled();
  });

  test('probe history populates after executing probes via UI', async ({ page }) => {
    await navigateAsFreshStudent(page, 'probe-history-ui', PROBEABLE_PATH);
    await expect(page.locator(probe.panel)).toBeVisible();
    // The badge renders once /probe/status/ has loaded
    await expect(page.locator(probe.badge)).toHaveText('· ∞');
    await expect(page.locator(probe.historyButton)).toHaveCount(0);

    // e2e-probeable-code-1 has signature: mystery(lst: list[int]) -> list[int]
    const lstInput = page.locator(probe.paramInput('lst'));
    const probeBtn = page.locator(probe.button);
    const probes: Array<[string, number[]]> = [
      ['[3, 1, 2]', [1, 2, 3]],
      ['[9, 4]', [4, 9]],
    ];

    for (const [value, expected] of probes) {
      await lstInput.fill(value);
      await expect(probeBtn).toBeEnabled();
      const responsePromise = page.waitForResponse(
        (resp) =>
          resp.request().method() === 'POST' &&
          new URL(resp.url()).pathname === '/api/problems/e2e-probeable-code-1/probe/',
      );
      await probeBtn.click();
      const response = await responsePromise;
      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.success).toBe(true);
      expect(body.result).toEqual(expected);
      await expect(page.locator(probe.result)).toHaveText(JSON.stringify(expected));
    }

    const historyBtn = page.locator(probe.historyButton);
    await expect(historyBtn).toHaveText('History (2)');
    await historyBtn.click();

    const rows = page.locator(probe.historyRow);
    await expect(rows).toHaveCount(2);
    await expect(rows.locator('.modal-call')).toHaveText(['mystery([9,4])', 'mystery([3,1,2])']);
    await expect(rows.locator('.modal-result')).toHaveText(['[4,9]', '[1,2,3]']);
  });
});

// ---------------------------------------------------------------------------
// Probe Input Type Validation (#135)
// ---------------------------------------------------------------------------

test.describe('Probe Input Type Validation', () => {
  test('non-integer input for an int parameter shows an error and disables Probe', async ({ page }) => {
    // Fresh student: a probe history containing the typed value would put the
    // button in its 'Already probed' state
    await navigateAsFreshStudent(page, 'probe-typed', TYPED_PROBEABLE_PATH);
    await waitForProbeableInput(page);

    // e2e-probeable-code-typed has signature: double(n: int) -> int
    const nInput = page.locator(probe.paramInput('n'));
    await expect(nInput).toBeVisible();
    await expect(nInput).toBeEnabled();

    const fieldErrors = page.locator(probe.fieldErrors);
    const probeBtn = page.locator(probe.button);

    await nInput.fill('abc');
    await expect(fieldErrors).toBeVisible();
    await expect(page.locator(probe.fieldError('n'))).toHaveText('n: Must be a whole number (e.g. 5)');
    await expect(nInput).toHaveClass(/has-error/);
    await expect(probeBtn).toBeDisabled();

    await nInput.fill('5');
    await expect(fieldErrors).toBeHidden();
    await expect(nInput).not.toHaveClass(/has-error/);
    await expect(probeBtn).toBeEnabled();
  });
});

// ---------------------------------------------------------------------------
// Refute Tests (e2e-mixed has hard past deadline -- locked)
// ---------------------------------------------------------------------------

test.describe('Refute Problem (Deadline Enforcement)', () => {
  test('hard deadline problem set shows locked banner', async ({ page }) => {
    await navigateAs(
      page,
      'student',
      '/courses/CS101-2024/problem-set/e2e-mixed?p=6',
    );

    // The hard past deadline shows the locked banner.
    const banner = page.locator('.deadline-banner.deadline-locked');
    await expect(banner).toBeVisible();
    await expect(banner.locator('.deadline-icon')).toHaveText('🔒');
    await expect(banner.locator('.deadline-text strong')).toHaveText('Submissions Closed');
    await expect(banner.locator('.deadline-text')).toHaveText(
      /^Submissions Closed — This problem set closed on \S.*$/,
    );
  });

  test('API rejects submission on hard-deadline-locked problem set', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    const { status, data } = await apiAs(page, 'student', 'POST', '/api/submit/', {
      problem_slug: 'e2e-refute-1',
      problem_set_slug: 'e2e-mixed',
      course_id: 'CS101-2024',
      raw_input: JSON.stringify({ x: -5 }),
    });

    // SubmissionValidationService._check_deadline rejects it before grading.
    expect(status).toBe(400);
    expect(data.error).toMatch(/^Submission deadline has passed\. This problem set closed on .+\.$/);
    expect(data.code).toBe('validation_error');
  });
});
