/**
 * E2E Tests: AI Consent Modal Flow (issue #121)
 *
 * Covers the in-app grant experience for users without AI processing consent.
 *
 * Flow:
 *   1. Test starts by withdrawing student's AI_PROCESSING consent via API.
 *   2. Student attempts an EiPL submission.
 *   3. The backend returns 403 + code=consent_required + purpose=ai_processing.
 *   4. The axios interceptor routes to the AIConsentModal.
 *   5. Clicking "Enable AI features" calls POST /api/users/me/consents/ with
 *      consent_method=in_app, then retries the original submission.
 *   6. Clicking "Not now" rejects the submission cleanly.
 *
 * Prerequisites (same as submission-eipl.spec.ts):
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true
 *   2. Celery worker
 *   3. Vite dev server on :5173
 *   4. python manage.py create_test_users && python manage.py seed_e2e_data
 */

import { test, expect, Page } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';
import { apiAs } from '../helpers/api';

const EIPL_PATH = '/courses/CS101-2024/problem-set/e2e-basics?p=1';
const VALID_EXPLANATION =
  'This function adds up all the numbers in the input list and returns the total.';

async function withdrawAIConsent(page: Page) {
  await page.goto('/', { waitUntil: 'commit' });
  await apiAs(page, 'student', 'DELETE', '/api/users/me/consents/ai_processing/');
}

async function ensureAIConsentGranted(page: Page) {
  // Safety net: runs after each test so a failure mid-flow doesn't leave the
  // student in a withdrawn-consent state that breaks later EiPL tests.
  await page.goto('/', { waitUntil: 'commit' });
  await apiAs(page, 'student', 'POST', '/api/users/me/consents/', {
    consent_type: 'ai_processing',
  });
}

async function typeInEditor(page: Page, text: string) {
  const editorTextarea = page.locator('#promptEditor .ace_text-input').first();
  await editorTextarea.focus();
  await page.keyboard.press('Control+a');
  await page.keyboard.press('Backspace');
  await page.keyboard.type(text, { delay: 10 });
}

test.describe('AI Consent Modal', () => {
  test.beforeEach(async ({ page }) => {
    await withdrawAIConsent(page);
  });

  test.afterEach(async ({ page }) => {
    await ensureAIConsentGranted(page);
  });

  test('submitting without AI consent surfaces the grant modal', async ({ page }) => {
    await navigateAs(page, 'student', EIPL_PATH);
    await page
      .locator('#promptEditor, .description-input, .prompt-editor-wrapper')
      .first()
      .waitFor({ state: 'visible', timeout: 15000 });

    await typeInEditor(page, VALID_EXPLANATION);
    await page.locator('#submitButton').click();

    // The modal is a Teleport to body with role="alertdialog".
    const modal = page.getByRole('alertdialog');
    await expect(modal).toBeVisible({ timeout: 10000 });
    await expect(modal).toContainText(/AI features/i);
  });

  test('granting from the modal retries the submission with audit=in_app', async ({ page }) => {
    await navigateAs(page, 'student', EIPL_PATH);
    await page
      .locator('#promptEditor, .description-input, .prompt-editor-wrapper')
      .first()
      .waitFor({ state: 'visible', timeout: 15000 });

    await typeInEditor(page, VALID_EXPLANATION);
    await page.locator('#submitButton').click();

    const modal = page.getByRole('alertdialog');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Track the POST to the consent endpoint and its payload so we can assert
    // the modal tagged the audit record correctly.
    const [consentPost] = await Promise.all([
      page.waitForRequest(
        (req) =>
          req.url().includes('/api/users/me/consents/') && req.method() === 'POST',
        { timeout: 10000 },
      ),
      modal.getByRole('button', { name: /Enable AI features/i }).click(),
    ]);
    const postedBody = consentPost.postDataJSON() as Record<string, unknown>;
    expect(postedBody.consent_type).toBe('ai_processing');
    expect(postedBody.consent_method).toBe('in_app');

    // The modal closes after the grant completes.
    await expect(modal).toBeHidden({ timeout: 10000 });

    // The original submission is retried automatically — the submit button
    // should go back to its loading/disabled state (proof the retry fired).
    const submitBtn = page.locator('#submitButton');
    await expect(submitBtn).toBeDisabled({ timeout: 5000 });
  });

  test('declining dismisses the modal and does not retry', async ({ page }) => {
    await navigateAs(page, 'student', EIPL_PATH);
    await page
      .locator('#promptEditor, .description-input, .prompt-editor-wrapper')
      .first()
      .waitFor({ state: 'visible', timeout: 15000 });

    await typeInEditor(page, VALID_EXPLANATION);
    await page.locator('#submitButton').click();

    const modal = page.getByRole('alertdialog');
    await expect(modal).toBeVisible({ timeout: 10000 });
    await modal.getByRole('button', { name: /Not now/i }).click();

    await expect(modal).toBeHidden({ timeout: 5000 });

    // After decline, the student should still lack AI consent.
    const listRes = await apiAs(page, 'student', 'GET', '/api/users/me/consents/');
    expect(listRes.data.ai_processing?.granted).toBeFalsy();
  });
});
