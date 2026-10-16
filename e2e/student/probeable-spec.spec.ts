/**
 * E2E: Probeable Spec workflows (C24a-C24d).
 *
 * Problem: e2e-probeable-spec-open, index 5 of the e2e-probeable set.
 *   def square(x: int) -> int, reference `return x * x`, probe_mode explore.
 *   Test cases: square(3) = 9 (sample), square(-2) = 4 (hidden).
 *   segmentation_config {"enabled": False}, so a submission whose tests all
 *   pass is graded 'complete' (ProbeableSpecHandler: segmentation disabled ->
 *   complete) with no abstraction step.
 *
 * Grading in the E2E stack: CELERY_EAGER runs the EiPL pipeline inside
 * POST /api/submit/, and USE_MOCK_OPENAI returns the reference solution as
 * all 5 LLM variations, so every variation passes both tests.
 *
 * Fresh users have no AI processing consent. probeable_spec submissions are
 * not consent-gated yet (#161); submit tests grant consent through the API up
 * front so they stay valid once that gate exists.
 *
 * Every test runs as its own fresh student: probe budgets/history live in
 * Redis per (problem, user) with no reset, and submissions accumulate.
 */

import { test, expect, Page } from '@playwright/test';
import { setAceEditorValue } from '../helpers/ace-editor';
import { probe, feedback, problemSet } from '../helpers/selectors';
import { fillProbeArgs } from '../helpers/probe';
import {
  FreshUser,
  apiAsUser,
  enrollUser,
  freshStudent,
  grantAiConsent,
  injectUser,
} from '../helpers/users';

const PROBLEM_SET = 'e2e-probeable';
const PROBLEM_SLUG = 'e2e-probeable-spec-open';
const SPEC_PATH = `/courses/CS101-2024/problem-set/${PROBLEM_SET}?p=5`;
const GRADE_TIMEOUT = 90_000;

/** 60 characters of plain-language description. */
const EXPLANATION = 'Returns the given whole number multiplied by itself squared.';

const SUBMIT_URL = /\/api\/submit\/$/;
const PROBE_URL = new RegExp(`/api/problems/${PROBLEM_SLUG}/probe/$`);

/**
 * Create a fresh student, enroll, optionally grant AI consent, and open the
 * spec problem. Consent must be granted before navigation so the first submit
 * is not intercepted by the consent flow.
 */
async function openSpecProblem(
  page: Page,
  label: string,
  { aiConsent }: { aiConsent: boolean },
): Promise<FreshUser> {
  const user = freshStudent(label);
  await injectUser(page, user);
  await enrollUser(page, user);
  if (aiConsent) {
    await grantAiConsent(page, user);
  }
  await page.goto(SPEC_PATH, { waitUntil: 'networkidle' });
  await expect(page.locator('.probeable-spec-input')).toBeVisible({ timeout: 15_000 });
  return user;
}

/** Probe square(value) through the call line and wait for the oracle response. */
async function probeX(page: Page, value: string): Promise<void> {
  await fillProbeArgs(page, value);
  const button = page.locator(probe.button);
  await expect(button).toBeEnabled();
  const responsePromise = page.waitForResponse(
    (resp) => PROBE_URL.test(new URL(resp.url()).pathname) && resp.request().method() === 'POST',
  );
  await button.click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
}

/** Put the explanation in #promptEditor, submit, and require a 2xx. */
async function submitExplanation(page: Page, text: string): Promise<void> {
  await setAceEditorValue(page, problemSet.promptEditor, text);
  const submitButton = page.locator(problemSet.submitButton);
  await expect(submitButton).toBeEnabled();

  const responsePromise = page.waitForResponse(
    (resp) => SUBMIT_URL.test(new URL(resp.url()).pathname) && resp.request().method() === 'POST',
    { timeout: GRADE_TIMEOUT },
  );
  await submitButton.click();
  const response = await responsePromise;
  expect(response.ok(), `POST /api/submit/ returned ${response.status()}`).toBe(true);
}

test.describe('C24 Probeable Spec', () => {
  test('C24a probe on a spec problem shows oracle results and history', async ({ page }) => {
    await openSpecProblem(page, 'c24a', { aiConsent: false });

    const panel = page.locator('.probeable-spec-input ' + probe.panel);
    await expect(panel).toBeVisible();
    await expect(page.locator(probe.badge)).toHaveText('· ∞');
    await expect(page.locator(probe.badge)).toHaveClass(/status-explore/);
    await expect(page.locator(probe.result)).toHaveText('?');
    await expect(page.locator(probe.historyButton)).toHaveCount(0);

    await probeX(page, '3');
    await expect(page.locator(probe.result)).toHaveText('9');
    await expect(page.locator(probe.historyButton)).toHaveText('History (1)');

    await probeX(page, '-2');
    await expect(page.locator(probe.result)).toHaveText('4');
    await expect(page.locator(probe.historyButton)).toHaveText('History (2)');
    // The call line still holds the last probed value, so the button reports it
    // as already probed (no badge while duplicate).
    await expect(page.locator(probe.button)).toHaveText(/Already probed/);
    await expect(page.locator(probe.button)).toHaveClass(/is-duplicate/);
    await expect(page.locator(probe.button)).toBeDisabled();
    // A new value re-enables probing; explore mode keeps the badge unlimited.
    await fillProbeArgs(page, 'x=7');
    await expect(page.locator(probe.button)).toBeEnabled();
    await expect(page.locator(probe.badge)).toHaveText('· ∞');
    await expect(page.locator(probe.badge)).toHaveClass(/status-explore/);

    await page.locator(probe.historyButton).click();
    await expect(page.locator(probe.historyModal)).toBeVisible();
    const rows = page.locator(probe.historyRow);
    await expect(rows).toHaveCount(2);
    // Newest first.
    await expect(rows.nth(0).locator('.modal-index')).toHaveText('#2');
    await expect(rows.nth(0).locator('.modal-call')).toHaveText('square(-2)');
    await expect(rows.nth(0).locator('.modal-result')).toHaveText('4');
    await expect(rows.nth(1).locator('.modal-index')).toHaveText('#1');
    await expect(rows.nth(1).locator('.modal-call')).toHaveText('square(3)');
    await expect(rows.nth(1).locator('.modal-result')).toHaveText('9');
    await page.locator(probe.close).click();
    await expect(page.locator(probe.historyModal)).toHaveCount(0);
  });

  test('C24b explanation submit grades 100% with both tests shown', async ({ page }) => {
    // One mock-LLM grading: 5 variations x 2 tests in the Docker sandbox.
    test.setTimeout(GRADE_TIMEOUT + 30_000);
    expect(EXPLANATION.length).toBe(60);
    await openSpecProblem(page, 'c24b', { aiConsent: true });

    await submitExplanation(page, EXPLANATION);

    // All 5 mock variations are the reference solution and segmentation is
    // disabled for this problem, so the grade is complete at 100%.
    await expect(page.locator('.notification-container .notification.success')).toContainText(
      'Problem 6: Variations: 5/5 passing',
      { timeout: GRADE_TIMEOUT },
    );

    const container = page.locator(feedback.container);
    await expect(container.locator(feedback.header)).toBeVisible({ timeout: GRADE_TIMEOUT });
    await expect(container.locator('.attempt-text')).toHaveText('1/1');
    await expect(container.locator(feedback.scoreBadge)).toHaveText('100%');
    await expect(container.locator('.explanation-text')).toHaveText(EXPLANATION);

    const correctnessCard = container.locator(feedback.metricCard).first();
    await expect(correctnessCard.locator('.status-metric')).toHaveText('5/5 pass');
    await expect(correctnessCard.locator('.status-label')).toHaveText('Clear');

    // Test rows live in the correctness modal. probeable_spec is outside the
    // #165 truncation rule, so every variation lists both tests, the hidden
    // one included.
    await correctnessCard.click();
    const modal = page.locator('.modal-content.correctness-modal');
    await expect(modal).toBeVisible();
    await expect(modal.locator('.badge-level')).toHaveText('5/5 Versions Pass');
    await expect(modal.locator('.version-pill')).toHaveCount(5);

    for (let i = 0; i < 5; i++) {
      await modal.locator(`#version-tab-${i}`).click();
      const panel = modal.locator(`#version-panel-${i}`);
      await expect(panel).toBeVisible();
      await expect(panel.locator('.details-tests .section-meta')).toHaveText('2/2');
      const tests = panel.locator('.tests-list .test-item');
      await expect(tests).toHaveCount(2);
      await expect(panel.locator('.tests-list .test-item.passing')).toHaveCount(2);
      await expect(tests.nth(0).locator('.test-call')).toHaveText('square(3)');
      await expect(tests.nth(1).locator('.test-call')).toHaveText('square(-2)');
    }
  });

  test('C24c description length bounds gate the submit button', async ({ page }) => {
    await openSpecProblem(page, 'c24c', { aiConsent: false });
    const submitButton = page.locator(problemSet.submitButton);

    // Empty on load.
    await expect(submitButton).toBeDisabled();

    await setAceEditorValue(page, problemSet.promptEditor, 'short');
    await expect(submitButton).toBeDisabled();

    // Minimum is 10 characters after trimming.
    await setAceEditorValue(page, problemSet.promptEditor, '   123456789   ');
    await expect(submitButton).toBeDisabled();
    await setAceEditorValue(page, problemSet.promptEditor, '1234567890');
    await expect(submitButton).toBeEnabled();

    // Maximum is 1000 characters.
    await setAceEditorValue(page, problemSet.promptEditor, 'a'.repeat(1000));
    await expect(submitButton).toBeEnabled();
    await setAceEditorValue(page, problemSet.promptEditor, 'a'.repeat(1001));
    await expect(submitButton).toBeDisabled();
  });

  test('C24d resubmitting shows 2 attempts', async ({ page }) => {
    // Two mock-LLM gradings, each 5 variations x 2 tests in the Docker sandbox.
    test.setTimeout(2 * GRADE_TIMEOUT + 30_000);
    const user = await openSpecProblem(page, 'c24d', { aiConsent: true });
    const container = page.locator(feedback.container);

    await submitExplanation(page, EXPLANATION);
    await expect(container.locator('.attempt-text')).toHaveText('1/1', { timeout: GRADE_TIMEOUT });

    await submitExplanation(page, 'It multiplies the integer argument by itself and returns it.');
    await expect(container.locator('.attempt-text')).toHaveText('2/2', { timeout: GRADE_TIMEOUT });
    await expect(container.locator(feedback.scoreBadge)).toHaveText('100%');

    await container.locator(feedback.attemptSelector).click();
    const panel = container.locator('.attempt-dropdown-panel[role="menu"]');
    await expect(panel).toBeVisible();
    const items = panel.locator('.attempt-item-minimal');
    await expect(items).toHaveCount(2);
    await expect(items.locator('.attempt-num')).toHaveText(['2', '1']);
    await expect(items.locator('.attempt-score-minimal')).toHaveText(['100%', '100%']);

    const { status, data } = await apiAsUser(
      page,
      user,
      'GET',
      `/api/submissions/history/${PROBLEM_SLUG}/?problem_set_slug=${PROBLEM_SET}&course_id=CS101-2024`,
    );
    expect(status).toBe(200);
    expect(data.submissions).toHaveLength(2);
    for (const submission of data.submissions) {
      expect(submission.score).toBe(100);
      expect(submission.completion_status).toBe('complete');
      expect(submission.variations_count).toBe(5);
      // History counts test executions across all 5 variations: 5 x 2 tests.
      expect(submission.tests_passed).toBe(10);
      expect(submission.total_tests).toBe(10);
    }

    // The dropdown shows each attempt's tests_passed/total_tests from history.
    await expect(items.locator('.attempt-tests')).toHaveText(['10/10', '10/10']);
  });
});
