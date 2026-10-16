/**
 * E2E: probeable_code submission feedback (workflows B14-B23).
 *
 * Problem: e2e-probeable-locked (problem set e2e-probeable, p=2), seeded by
 * seed_e2e_data. clamp(n) = max(0, min(n, 10)), explore probe mode, four
 * ordered tests: clamp(5) -> 5, clamp(0) -> 0, clamp(-3) -> 0, clamp(20) -> 10.
 *
 * Truncation rule (#165): the rows shown are the passing tests up to the
 * first failure plus that first failing test; every later test is locked.
 * The ladder shows one pip per test (pass / fail / locked) and never the
 * outcome of a locked test.
 *
 * With CELERY_EAGER=true, POST /api/submit/ grades synchronously in the Docker
 * sandbox. Every test uses a fresh student, so attempts never leak between
 * tests or runs.
 */

import { test, expect, Page } from '@playwright/test';
import { FreshUser, apiAsUser, navigateAsFreshStudent } from '../helpers/users';
import { submitCodeAndWait, submitSyntaxErrorAndReadMessage } from '../helpers/submission';
import { setAceEditorValue } from '../helpers/ace-editor';
import { codeFeedback } from '../helpers/selectors';

const CLAMP_URL = '/courses/CS101-2024/problem-set/e2e-probeable?p=2';
const GRADING_TIMEOUT = 60_000;

const SOLUTIONS = {
  correct: 'def clamp(n):\n    return max(0, min(n, 10))',
  failsFirst: 'def clamp(n):\n    return 0 if n == 5 else max(0, min(n, 10))',
  identity: 'def clamp(n):\n    return n',
  failsLast: 'def clamp(n):\n    return max(0, n)',
  divideByZero: 'def clamp(n):\n    return n // 0',
  syntaxError: 'def clamp(n):\n    return (n',
} as const;

// Each test owns a fresh user, so they can run concurrently across workers.
test.describe.configure({ mode: 'parallel' });

// Grading runs in the Docker sandbox and some tests submit twice.
test.beforeEach(() => {
  test.setTimeout(150_000);
});

async function openClamp(page: Page, label: string): Promise<FreshUser> {
  const user = await navigateAsFreshStudent(page, label, CLAMP_URL);
  await expect(page.locator('.probeable-code-input')).toBeVisible();
  await expect(page.locator('#codeEditor .ace_editor')).toBeVisible();
  return user;
}

async function submitAndGrade(page: Page, code: string): Promise<void> {
  await submitCodeAndWait(page, code, GRADING_TIMEOUT);
}

/** Pips in order (pass, fail, locked) and the locked row under the ledger. */
async function expectLadder(
  page: Page,
  pass: number,
  fail: number,
  locked: number,
  lockedText: string | null,
): Promise<void> {
  await expect(page.locator(codeFeedback.pip)).toHaveCount(pass + fail + locked);
  await expect(page.locator(codeFeedback.pipPass)).toHaveCount(pass);
  await expect(page.locator(codeFeedback.pipFail)).toHaveCount(fail);
  await expect(page.locator(codeFeedback.pipLock)).toHaveCount(locked);
  if (lockedText === null) {
    await expect(page.locator(codeFeedback.lockedRow)).toHaveCount(0);
  } else {
    await expect(page.locator(codeFeedback.lockedRow)).toHaveText(lockedText);
  }
}

async function expectSingleFailingRow(
  page: Page,
  call: string,
  expected: string,
  actual: string,
): Promise<void> {
  const failing = page.locator(codeFeedback.failingItem);
  await expect(failing).toHaveCount(1);
  await expect(failing.locator('.test-call')).toHaveText(call);
  await expect(failing.locator('.expected')).toHaveText(expected);
  await expect(failing.locator('.actual')).toHaveText(actual);
  await expect(failing.locator('.actual')).not.toHaveClass(/is-error/);
}

/** Passed rows start closed; open each one and check call and result, in order. */
async function expectPassingRows(page: Page, rows: Array<[string, string]>): Promise<void> {
  const items = page.locator(codeFeedback.passingItem);
  await expect(items).toHaveCount(rows.length);
  for (let i = 0; i < rows.length; i++) {
    const row = items.nth(i);
    await expect(row).toHaveClass(/closed/);
    await expect(row.locator('.result')).toBeHidden();
    await row.click();
    await expect(row).toHaveClass(/open/);
    await expect(row.locator('.test-call')).toHaveText(rows[i][0]);
    await expect(row.locator('.result')).toHaveText(rows[i][1]);
  }
}

async function expectAttemptBadge(page: Page, attemptText: string, score: string): Promise<void> {
  const trigger = page.locator(codeFeedback.attemptTrigger);
  await expect(trigger.locator('.attempt-text')).toHaveText(attemptText);
  await expect(trigger.locator('.attempt-score-badge')).toHaveText(new RegExp(`^\\S\\s*${score}%\\s*$`));
}

// ---------------------------------------------------------------------------
// B14: input rejected before grading
// ---------------------------------------------------------------------------

test.describe('B14 rejected submissions', () => {
  test('B14a too-short code keeps the submit button disabled', async ({ page }) => {
    await openClamp(page, 'b14a');

    await setAceEditorValue(page, '#codeEditor', 'x');
    await expect(page.locator('#submitButton')).toBeDisabled();
  });

  test('B14b syntax error is reported with its line and creates no attempt', async ({ page }) => {
    const user = await openClamp(page, 'b14b');

    const message = await submitSyntaxErrorAndReadMessage(page, SOLUTIONS.syntaxError);
    expect(message).toMatch(/^Syntax error: .+ \(line 2\)$/);

    // Server state: the user has no stored attempt on this problem. No
    // problem-set or course filter, so an attempt stored anywhere would show.
    const history = await apiAsUser(
      page,
      user,
      'GET',
      '/api/submissions/history/e2e-probeable-locked/',
    );
    expect(history.status).toBe(200);
    expect(history.data.total_attempts).toBe(0);
    expect(history.data.submissions).toEqual([]);

    // The feedback panel stays in its empty state: no results, no attempts.
    const container = page.locator('.feedback-container');
    await expect(container.locator('.empty-state')).toHaveText(
      /Submit your solution to see test results/,
    );
    await expect(page.locator('.feedback-header')).toHaveCount(0);
    await expect(page.locator(codeFeedback.ladder)).toHaveCount(0);
    await expect(page.locator(codeFeedback.attemptTrigger)).toHaveCount(0);
  });
});

// ---------------------------------------------------------------------------
// B15: grading in progress
// ---------------------------------------------------------------------------

test.describe('B15 grading in progress', () => {
  test('B15 grading in progress disables submit and shows the running-tests panel', async ({ page }) => {
    await openClamp(page, 'b15');
    await setAceEditorValue(page, '#codeEditor', SOLUTIONS.correct);

    // Hold the submit request until the in-flight state has been checked, so
    // the assertions do not race the sandbox.
    let release: () => void = () => {};
    const released = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route('**/api/submit/', async (route) => {
      await released;
      await route.continue();
    });

    const submitButton = page.locator('#submitButton');
    const panel = page.locator('.feedback-container .generating-feedback-panel');
    await expect(submitButton).toBeEnabled();
    await expect(panel).toHaveCount(0);

    const responsePromise = page.waitForResponse(
      (resp) =>
        /\/api\/submit\/$/.test(new URL(resp.url()).pathname) && resp.request().method() === 'POST',
      { timeout: GRADING_TIMEOUT },
    );
    await submitButton.click();

    await expect(submitButton).toBeDisabled();
    await expect(submitButton.locator('.bouncing-dots')).toBeVisible();
    await expect(panel).toBeVisible();
    await expect(panel.locator('.generating-message')).toHaveText('Running tests...');
    await expect(page.locator(codeFeedback.ladder)).toHaveCount(0);

    release();
    expect((await responsePromise).status()).toBe(202);

    await expect(page.locator(codeFeedback.ladder)).toBeVisible({ timeout: GRADING_TIMEOUT });
    await expect(panel).toHaveCount(0);
    await expect(submitButton.locator('.bouncing-dots')).toHaveCount(0);
    await expect(submitButton).toBeEnabled();
    await expectLadder(page, 4, 0, 0, null);
  });
});

// ---------------------------------------------------------------------------
// B16-B19: graded result for a single submission
// ---------------------------------------------------------------------------

test.describe('B16-B19 graded feedback and test locking', () => {
  test('B16 all tests pass: full counts, success toast, 100% badge', async ({ page }) => {
    await openClamp(page, 'b16');

    await submitAndGrade(page, SOLUTIONS.correct);

    // The toast auto-dismisses after 5 s, so check it first.
    await expect(
      page.locator('.notification-container .notification.success .notification-message'),
    ).toHaveText('Problem 3: 4/4 tests passed');
    await expectLadder(page, 4, 0, 0, null);
    await expect(page.locator(codeFeedback.failingItem)).toHaveCount(0);
    await expectPassingRows(page, [
      ['clamp(5)', '5'],
      ['clamp(0)', '0'],
      ['clamp(-3)', '0'],
      ['clamp(20)', '10'],
    ]);
    await expectAttemptBadge(page, '1/1', '100');
  });

  test('B17 an early failure locks every later test, even passing ones', async ({ page }) => {
    await openClamp(page, 'b17');

    await submitAndGrade(page, SOLUTIONS.failsFirst);

    await expectSingleFailingRow(page, 'clamp(5)', '5', '0');
    // The first test failed, so no passing rows come before it.
    await expect(page.locator(codeFeedback.passingItem)).toHaveCount(0);
    // Counts still cover the three locked tests, which pass.
    await expectLadder(page, 0, 1, 3, '3 more tests · unlock when test 1 passes');
    await expectAttemptBadge(page, '1/1', '75');
  });

  test('B18 one locked test uses the singular label', async ({ page }) => {
    await openClamp(page, 'b18');

    await submitAndGrade(page, SOLUTIONS.identity);

    await expectSingleFailingRow(page, 'clamp(-3)', '0', '-3');
    await expectLadder(page, 2, 1, 1, '1 more test · unlock when test 3 passes');
    await expectPassingRows(page, [['clamp(5)', '5'], ['clamp(0)', '0']]);
  });

  test('B17b nothing is locked when only the last test fails', async ({ page }) => {
    await openClamp(page, 'b17b');

    await submitAndGrade(page, SOLUTIONS.failsLast);

    await expectSingleFailingRow(page, 'clamp(20)', '10', '20');
    await expectLadder(page, 3, 1, 0, null);
    await expectPassingRows(page, [['clamp(5)', '5'], ['clamp(0)', '0'], ['clamp(-3)', '0']]);
  });

  test('B19 a runtime error shows as an error row and locks the rest', async ({ page }) => {
    await openClamp(page, 'b19');

    await submitAndGrade(page, SOLUTIONS.divideByZero);

    const failing = page.locator(codeFeedback.failingItem);
    await expect(failing).toHaveCount(1);
    await expect(failing.locator('.test-call')).toHaveText('clamp(5)');
    await expect(failing.locator('.expected')).toHaveText('5');
    await expect(failing.locator('.actual')).toHaveClass(/is-error/);
    await expect(failing.locator('.actual')).toHaveText('integer division or modulo by zero');
    await expect(page.locator(codeFeedback.passingItem)).toHaveCount(0);
    await expectLadder(page, 0, 1, 3, '3 more tests · unlock when test 1 passes');
  });
});

// ---------------------------------------------------------------------------
// B20-B22: multiple attempts and restoring feedback
// ---------------------------------------------------------------------------

test.describe('B20-B22 attempts and returning later', () => {
  test('B20 resubmitting shows the new attempt as 2/2 at 100%', async ({ page }) => {
    await openClamp(page, 'b20');

    await submitAndGrade(page, SOLUTIONS.identity);
    await expectLadder(page, 2, 1, 1, '1 more test · unlock when test 3 passes');
    await expectAttemptBadge(page, '1/1', '50');

    await submitAndGrade(page, SOLUTIONS.correct);
    await expectLadder(page, 4, 0, 0, null);
    await expect(page.locator(codeFeedback.failingItem)).toHaveCount(0);
    await expectAttemptBadge(page, '2/2', '100');
  });

  test('B21 switching attempts restores each attempt\'s truncated feedback', async ({ page }) => {
    await openClamp(page, 'b21');

    await submitAndGrade(page, SOLUTIONS.identity);
    await submitAndGrade(page, SOLUTIONS.correct);
    await expectAttemptBadge(page, '2/2', '100');

    const trigger = page.locator(codeFeedback.attemptTrigger);
    const panel = page.locator(codeFeedback.attemptPanel);
    const attempt = (n: number) =>
      panel.locator(codeFeedback.attemptItem).filter({
        has: page.locator('.attempt-num', { hasText: new RegExp(`^${n}$`) }),
      });

    await trigger.click();
    await expect(panel).toBeVisible();
    await expect(panel.locator(codeFeedback.attemptItem)).toHaveCount(2);
    await expect(attempt(1).locator('.attempt-tests')).toHaveText('2/4');
    await expect(attempt(2).locator('.attempt-tests')).toHaveText('4/4');

    await attempt(1).click();
    await expect(panel).toBeHidden();
    await expectAttemptBadge(page, '1/2', '50');
    await expectLadder(page, 2, 1, 1, '1 more test · unlock when test 3 passes');
    await expectSingleFailingRow(page, 'clamp(-3)', '0', '-3');
    await expectPassingRows(page, [['clamp(5)', '5'], ['clamp(0)', '0']]);

    await trigger.click();
    await expect(panel).toBeVisible();
    await attempt(2).click();
    await expect(panel).toBeHidden();
    await expectAttemptBadge(page, '2/2', '100');
    await expectLadder(page, 4, 0, 0, null);
    await expect(page.locator(codeFeedback.failingItem)).toHaveCount(0);
  });

  test('B22 reloading the page restores the truncated feedback', async ({ page }) => {
    await openClamp(page, 'b22');

    await submitAndGrade(page, SOLUTIONS.identity);
    await expectLadder(page, 2, 1, 1, '1 more test · unlock when test 3 passes');

    const lastSubmission = page.waitForResponse(
      (resp) =>
        /\/api\/last-submission\/e2e-probeable-locked\/$/.test(new URL(resp.url()).pathname) &&
        resp.request().method() === 'GET',
    );
    await page.reload();
    expect((await lastSubmission).status()).toBe(200);

    await expect(page.locator(codeFeedback.ladder)).toBeVisible({ timeout: 15_000 });
    await expectLadder(page, 2, 1, 1, '1 more test · unlock when test 3 passes');
    await expectSingleFailingRow(page, 'clamp(-3)', '0', '-3');
    await expectPassingRows(page, [['clamp(5)', '5'], ['clamp(0)', '0']]);
    await expectAttemptBadge(page, '1/1', '50');
  });
});

// ---------------------------------------------------------------------------
// B23: debugger on a failing row
// ---------------------------------------------------------------------------

test.describe('B23 debugger', () => {
  test('B23 the debug button opens and closes the step-by-step debugger', async ({ page }) => {
    // Never load the external Python Tutor page; serve an empty document.
    await page.route('https://pythontutor.com/**', (route) =>
      route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><html></html>' }),
    );

    await openClamp(page, 'b23');
    await submitAndGrade(page, SOLUTIONS.identity);

    const failing = page.locator(codeFeedback.failingItem);
    await expect(failing).toHaveCount(1);

    const modal = page.locator('.modal-overlay[role="dialog"]').filter({
      has: page.locator('#modal-title', { hasText: 'Step-by-Step Debugger' }),
    });
    await expect(modal).toHaveCount(0);

    await failing.locator(codeFeedback.debugButton).click();
    await expect(modal).toBeVisible();
    const iframe = modal.locator('iframe.debugger-iframe');
    await expect(iframe).toHaveAttribute('src', /^https:\/\/pythontutor\.com\//);
    const src = (await iframe.getAttribute('src')) ?? '';
    expect(decodeURIComponent(src.replace(/\+/g, ' '))).toContain('clamp(-3)');

    await modal.locator('.close-button').click();
    await expect(modal).toHaveCount(0);
  });
});
