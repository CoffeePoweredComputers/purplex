import { Page, expect } from '@playwright/test';
import { setAceEditorValue } from './ace-editor';
import { codeFeedback } from './selectors';

/**
 * Code-submission helpers for probeable_code problems.
 *
 * In the E2E stack (CELERY_EAGER=true) POST /api/submit/ grades the whole
 * submission synchronously in the Docker sandbox, then the SSE stream reports
 * completion. ProblemSet.vue clears the previous feedback before it sends the
 * request, so once the submit response is back, a visible summary bar can only
 * belong to the new result.
 */

const SUBMIT_URL = /\/api\/submit\/$/;

/**
 * Put `code` in the editor, submit it, and wait until the graded result's
 * summary bar is visible. Throws if the submit request is not accepted.
 */
export async function submitCodeAndWait(
  page: Page,
  code: string,
  timeout = 60_000,
): Promise<void> {
  await setAceEditorValue(page, '#codeEditor', code);

  const submitButton = page.locator('#submitButton');
  await expect(submitButton).toBeEnabled();

  const responsePromise = page.waitForResponse(
    (resp) => SUBMIT_URL.test(new URL(resp.url()).pathname) && resp.request().method() === 'POST',
    { timeout },
  );
  await submitButton.click();
  const response = await responsePromise;
  if (!response.ok()) {
    throw new Error(
      `submitCodeAndWait: POST /api/submit/ returned ${response.status()}: ${await response.text()}`,
    );
  }

  await expect(page.locator(codeFeedback.summaryBar)).toBeVisible({ timeout });
}

/**
 * Submit code that the API rejects as invalid (e.g. a syntax error) and return
 * the message the user sees.
 *
 * The probeable_code handler rejects uncompilable code with 400
 * {"error": "Syntax error: <msg> (line N)"} before any submission exists.
 * ProblemSet.vue's submit() catch shows it as a warning toast titled
 * "Invalid Request" whose .notification-details is the server's error text.
 * This asserts that toast and returns the details text.
 */
export async function submitSyntaxErrorAndReadMessage(page: Page, code: string): Promise<string> {
  await setAceEditorValue(page, '#codeEditor', code);

  const submitButton = page.locator('#submitButton');
  await expect(submitButton).toBeEnabled();

  const responsePromise = page.waitForResponse(
    (resp) => SUBMIT_URL.test(new URL(resp.url()).pathname) && resp.request().method() === 'POST',
  );
  await submitButton.click();
  const response = await responsePromise;
  if (response.status() !== 400) {
    throw new Error(
      `submitSyntaxErrorAndReadMessage: expected 400 from POST /api/submit/, got ${response.status()}`,
    );
  }

  const body = await response.json();
  if (typeof body?.error !== 'string' || body.error === '') {
    throw new Error(`submitSyntaxErrorAndReadMessage: 400 without an error message: ${JSON.stringify(body)}`);
  }

  // Match the toast to this response (an older toast may still be on screen).
  // Toasts auto-dismiss after 4-5 s, so read the text as soon as it shows.
  const toast = page
    .locator('.notification-container .notification.warning')
    .filter({ has: page.locator('.notification-details', { hasText: body.error }) })
    .last();
  await expect(toast).toBeVisible();
  await expect(toast.locator('.notification-message')).toHaveText('Invalid Request');
  return ((await toast.locator('.notification-details').textContent()) ?? '').trim();
}
