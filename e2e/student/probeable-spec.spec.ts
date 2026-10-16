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
 * Grading in the E2E stack: CELERY_EAGER runs the spec pipeline inside
 * POST /api/submit/. The explanation generates ONE code version, and
 * USE_MOCK_OPENAI returns the reference solution for it, so it passes both
 * tests.
 *
 * Feedback is the same ordered test ladder as probeable_code (see
 * probeable-feedback.spec.ts): the top panel quotes the explanation instead of
 * the code, and there is no debug button.
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
import { codeFeedback, probe, problemSet } from '../helpers/selectors';
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

/** Attempts badge: 'n/total' and the score, preceded by its status icon. */
async function expectAttemptBadge(page: Page, attemptText: string, score: string): Promise<void> {
  const trigger = page.locator(codeFeedback.attemptTrigger);
  await expect(trigger.locator('.attempt-text')).toHaveText(attemptText, { timeout: GRADE_TIMEOUT });
  await expect(trigger.locator('.attempt-score-badge')).toHaveText(new RegExp(`^\\S\\s*${score}%\\s*$`));
}

/** Both tests pass: two green pips, two passed rows, nothing failing or locked. */
async function expectAllPassLadder(page: Page): Promise<void> {
  await expect(page.locator(codeFeedback.pip)).toHaveCount(2);
  await expect(page.locator(codeFeedback.pipPass)).toHaveCount(2);
  await expect(page.locator(codeFeedback.pipFail)).toHaveCount(0);
  await expect(page.locator(codeFeedback.pipLock)).toHaveCount(0);
  await expect(page.locator(codeFeedback.lockedRow)).toHaveCount(0);
  await expect(page.locator(codeFeedback.failingItem)).toHaveCount(0);

  const rows = page.locator(codeFeedback.passingItem);
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0).locator('.test-call')).toHaveText('square(3)');
  await expect(rows.nth(0).locator('.result')).toHaveText('9');
  await expect(rows.nth(1).locator('.test-call')).toHaveText('square(-2)');
  await expect(rows.nth(1).locator('.result')).toHaveText('4');
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

  test('C24b explanation submit grades 100% on the test ladder', async ({ page }) => {
    // One mock-LLM grading: 1 generated version x 2 tests in the Docker sandbox.
    test.setTimeout(GRADE_TIMEOUT + 30_000);
    expect(EXPLANATION.length).toBe(60);
    await openSpecProblem(page, 'c24b', { aiConsent: true });

    await submitExplanation(page, EXPLANATION);

    // The generated version is the reference solution and segmentation is
    // disabled for this problem, so the grade is complete at 100%.
    await expect(
      page.locator('.notification-container .notification.success .notification-message'),
    ).toHaveText('Problem 6: 2/2 tests passed', { timeout: GRADE_TIMEOUT });

    await expect(page.locator(codeFeedback.ladder)).toBeVisible({ timeout: GRADE_TIMEOUT });
    await expectAttemptBadge(page, '1/1', '100');

    // Top panel quotes the explanation, then shows the code generated from it.
    const container = page.locator('.feedback-container');
    await expect(container.locator('.explanation-text')).toHaveText(EXPLANATION);
    // The generated code is shown below the explanation, labelled as generated
    await expect(container.locator('.code-section')).toHaveCount(1);
    await expect(container.locator('.code-section .code-header')).toHaveText('Generated Code');

    // Every test passes, so nothing is locked: both rows, the hidden one
    // included, appear as passed one-liners.
    await expectAllPassLadder(page);

    // The student did not write the code: no debugger.
    await expect(container.locator(codeFeedback.debugButton)).toHaveCount(0);
    // Segmentation is disabled: no abstraction card.
    await expect(container.locator('.metric-card')).toHaveCount(0);
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
    // Two mock-LLM gradings, each 1 generated version x 2 tests in the Docker sandbox.
    test.setTimeout(2 * GRADE_TIMEOUT + 30_000);
    const user = await openSpecProblem(page, 'c24d', { aiConsent: true });

    await submitExplanation(page, EXPLANATION);
    await expectAttemptBadge(page, '1/1', '100');

    await submitExplanation(page, 'It multiplies the integer argument by itself and returns it.');
    await expectAttemptBadge(page, '2/2', '100');
    await expectAllPassLadder(page);

    await page.locator(codeFeedback.attemptTrigger).click();
    const panel = page.locator(codeFeedback.attemptPanel);
    await expect(panel).toBeVisible();
    const items = panel.locator(codeFeedback.attemptItem);
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
      // One generated version, graded on both tests; nothing locked.
      expect(submission.variations_count).toBe(1);
      expect(submission.tests_passed).toBe(2);
      expect(submission.total_tests).toBe(2);
      expect(submission.locked_count).toBe(0);
    }

    // The dropdown shows each attempt's tests_passed/total_tests from history.
    await expect(items.locator('.attempt-tests')).toHaveText(['2/2', '2/2']);
  });
});
