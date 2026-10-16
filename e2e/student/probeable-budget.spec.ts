/**
 * E2E Tests: probe budgets on probeable_code problems.
 *
 * Problem set e2e-probeable (seed_e2e_data._seed_probeable_workflows):
 *   p=0 e2e-probeable-block    add(a, b), probe_mode "block",    max_probes 3
 *   p=1 e2e-probeable-cooldown add(a, b), probe_mode "cooldown", max_probes 2,
 *                              refill 2 probes after 1 submission
 *   p=6 e2e-probeable-cooldown-2 add(a, b), probe_mode "cooldown", max_probes 1,
 *                              refill 1 probe after 2 submissions
 *
 * Budgets live in Redis per (problem, user) with no reset, so every test runs
 * as a fresh student (e2e/helpers/users.ts).
 *
 * UI facts this spec relies on (ProbePanel.vue / useProbeState.ts):
 *   - The remaining-count badge is rendered inside the Probe button only while
 *     the current inputs are not a previous probe. After a probe the inputs
 *     keep their values, so the button switches to "Already probed"; the spec
 *     enters new values before it reads the badge.
 *   - A duplicate input is answered from the client-side history: no request.
 */

import { test, expect, Page, Response } from '@playwright/test';
import { navigateAsFreshStudent, freshStudent, injectUser, enrollUser } from '../helpers/users';
import { submitCodeAndWait } from '../helpers/submission';
import { probe } from '../helpers/selectors';

const SET_URL = '/courses/CS101-2024/problem-set/e2e-probeable';
const BLOCK_URL = `${SET_URL}?p=0`;
const COOLDOWN_URL = `${SET_URL}?p=1`;
const COOLDOWN_2_URL = `${SET_URL}?p=6`;
const ADD_SOLUTION = 'def add(a, b):\n    return a + b';

function isProbePost(resp: Response, slug: string): boolean {
  return (
    resp.request().method() === 'POST' &&
    new URL(resp.url()).pathname === `/api/problems/${slug}/probe/`
  );
}

/** Wait until the probe panel and its add(a, b) inputs are on screen. */
async function waitForProbePanel(page: Page): Promise<void> {
  await expect(page.locator(probe.panel)).toBeVisible({ timeout: 15_000 });
  await expect(page.locator(probe.paramInput('a'))).toBeVisible();
  await expect(page.locator(probe.paramInput('b'))).toBeVisible();
}

async function fillArgs(page: Page, a: string, b: string): Promise<void> {
  await page.locator(probe.paramInput('a')).fill(a);
  await page.locator(probe.paramInput('b')).fill(b);
}

/**
 * Probe add(a, b) through the UI, assert the inline result, and return the
 * probe POST response body.
 */
async function probeAdd(
  page: Page,
  slug: string,
  a: string,
  b: string,
  expected: string,
): Promise<any> {
  await fillArgs(page, a, b);
  const button = page.locator(probe.button);
  await expect(button).toBeEnabled();
  const responsePromise = page.waitForResponse((resp) => isProbePost(resp, slug));
  await button.click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.success).toBe(true);
  expect(body.result).toBe(Number(expected));
  await expect(page.locator(probe.result)).toHaveText(expected);
  await expect(page.locator(probe.result)).toHaveClass(/has-result/);
  return body;
}

/** Assert the badge reads `· N left` with the given status class. */
async function expectBadge(page: Page, remaining: number, statusClass: string): Promise<void> {
  const badge = page.locator(probe.badge);
  await expect(badge).toHaveText(`· ${remaining} left`);
  await expect(badge).toHaveClass(new RegExp(`\\b${statusClass}\\b`));
}

// ---------------------------------------------------------------------------
// A8: block mode
// ---------------------------------------------------------------------------
test.describe('Probe budget: block mode', () => {
  test('A8 block mode spends the budget and blocks probing, and a fresh load shows the exhausted state', async ({
    page,
  }) => {
    const slug = 'e2e-probeable-block';
    await navigateAsFreshStudent(page, 'a8-block', BLOCK_URL);
    await waitForProbePanel(page);

    const probePosts: string[] = [];
    page.on('request', (req) => {
      if (req.method() === 'POST' && new URL(req.url()).pathname === `/api/problems/${slug}/probe/`) {
        probePosts.push(req.postData() ?? '');
      }
    });

    // Fresh user: full budget, no hint, no history.
    await expectBadge(page, 3, 'status-available');
    await expect(page.locator(probe.hint)).toHaveCount(0);
    await expect(page.locator(probe.historyButton)).toHaveCount(0);
    await expect(page.locator(probe.result)).toHaveText('?');

    // Probe 1: add(1, 2) -> 3
    const first = await probeAdd(page, slug, '1', '2', '3');
    expect(first.probe_status.remaining).toBe(2);
    expect(first.probe_status.can_probe).toBe(true);

    // Probe 2: add(2, 2) -> 4. The badge is visible once the inputs are new.
    await fillArgs(page, '2', '2');
    await expectBadge(page, 2, 'status-available');
    const second = await probeAdd(page, slug, '2', '2', '4');
    expect(second.probe_status.remaining).toBe(1);

    // A duplicate of (1, 2) shows the cached result and sends nothing.
    const postsBeforeDuplicate = probePosts.length;
    await fillArgs(page, '1', '2');
    const button = page.locator(probe.button);
    await expect(button).toHaveText(/Already probed/);
    await expect(button).toHaveClass(/is-duplicate/);
    await expect(button).toBeDisabled();
    await expect(page.locator(probe.result)).toHaveText('3');
    await expect(page.locator(probe.result)).toHaveClass(/is-cached/);

    // Confirming the duplicate from the keyboard must not probe either.
    await page.locator(probe.paramInput('b')).press('Enter');

    // The duplicate was free: one probe is still left.
    await fillArgs(page, '3', '3');
    await expectBadge(page, 1, 'status-available');
    expect(probePosts.length).toBe(postsBeforeDuplicate);

    // Probe 3: add(3, 3) -> 6 exhausts the budget.
    const third = await probeAdd(page, slug, '3', '3', '6');
    expect(third.probe_status.can_probe).toBe(false);
    expect(third.probe_status.remaining).toBe(0);
    expect(third.probe_status.mode).toBe('block');

    // Exhausted state without a reload.
    await expect(page.locator(probe.hint)).toHaveText('No probes remaining.');
    await expect(page.locator(probe.button)).toBeDisabled();
    await expect(page.locator(probe.paramInput('a'))).toBeDisabled();
    await expect(page.locator(probe.paramInput('b'))).toBeDisabled();
    await expect(page.locator(probe.historyButton)).toHaveText('History (3)');

    // Server-side state survives a fresh load (second tab, same student).
    // Checked before the in-page badge so it is verified even if that fails.
    const freshTab = await page.context().newPage();
    try {
      await freshTab.goto(BLOCK_URL, { waitUntil: 'networkidle' });
      await waitForProbePanel(freshTab);
      await expectBadge(freshTab, 0, 'status-exhausted');
      await expect(freshTab.locator(probe.hint)).toHaveText('No probes remaining.');
      await expect(freshTab.locator(probe.button)).toBeDisabled();
      await expect(freshTab.locator(probe.paramInput('a'))).toBeDisabled();
      await expect(freshTab.locator(probe.paramInput('b'))).toBeDisabled();
      await expect(freshTab.locator(probe.result)).toHaveText('6');

      // Earlier results stay readable from the history after exhaustion.
      await freshTab.locator(probe.historyButton).click();
      await expect(freshTab.locator(probe.historyModal)).toBeVisible();
      const rows = freshTab.locator(probe.historyRow);
      await expect(rows).toHaveCount(3);
      await expect(rows.locator('.modal-call')).toHaveText(['add(3, 3)', 'add(2, 2)', 'add(1, 2)']);
      await expect(rows.locator('.modal-result')).toHaveText(['6', '4', '3']);
      await freshTab.locator(probe.close).click();
      await expect(freshTab.locator(probe.historyModal)).toHaveCount(0);
    } finally {
      await freshTab.close();
    }

    // Only the three real probes reached the server.
    expect(probePosts.length).toBe(3);

    // The page the student probed from must also show the exhausted count.
    await expectBadge(page, 0, 'status-exhausted');
  });

  test('A8 a duplicate probe confirmed with Enter sends no request and spends no budget', async ({
    page,
  }) => {
    const slug = 'e2e-probeable-block';
    await navigateAsFreshStudent(page, 'a8-dup-enter', BLOCK_URL);
    await waitForProbePanel(page);

    const probePosts: string[] = [];
    page.on('request', (req) => {
      if (req.method() === 'POST' && new URL(req.url()).pathname === `/api/problems/${slug}/probe/`) {
        probePosts.push(req.postData() ?? '');
      }
    });

    const first = await probeAdd(page, slug, '1', '2', '3');
    expect(first.probe_status.remaining).toBe(2);
    expect(probePosts.length).toBe(1);

    // The inputs still hold (1, 2): the panel shows the cached result.
    const button = page.locator(probe.button);
    await expect(button).toHaveText(/Already probed/);
    await expect(button).toBeDisabled();
    await expect(page.locator(probe.result)).toHaveClass(/is-cached/);
    await expect(page.locator(probe.result)).toHaveText('3');

    // Enter in a parameter field is the keyboard path to "Probe". On a
    // duplicate it must do nothing, like the disabled button.
    await page.locator(probe.paramInput('b')).press('Enter');

    // Budget is server-side: a fresh load shows whether anything was spent.
    await page.reload({ waitUntil: 'networkidle' });
    await waitForProbePanel(page);
    await expectBadge(page, 2, 'status-available');
    await expect(page.locator(probe.historyButton)).toHaveText('History (1)');
    expect(probePosts.length).toBe(1);
  });

  test('A8b block budgets are per user: a second student starts with the full budget', async ({
    page,
    browser,
  }) => {
    const slug = 'e2e-probeable-block';
    await navigateAsFreshStudent(page, 'a8b-first', BLOCK_URL);
    await waitForProbePanel(page);
    await expectBadge(page, 3, 'status-available');
    const first = await probeAdd(page, slug, '5', '6', '11');
    expect(first.probe_status.remaining).toBe(2);
    await fillArgs(page, '7', '8');
    await expectBadge(page, 2, 'status-available');

    // A different student, in a separate browser context, on the same problem.
    const otherContext = await browser.newContext();
    try {
      const otherPage = await otherContext.newPage();
      const other = freshStudent('a8b-second');
      await injectUser(otherPage, other);
      await enrollUser(otherPage, other);
      await otherPage.goto(BLOCK_URL, { waitUntil: 'networkidle' });
      await waitForProbePanel(otherPage);
      await expectBadge(otherPage, 3, 'status-available');
      await expect(otherPage.locator(probe.hint)).toHaveCount(0);
      await expect(otherPage.locator(probe.historyButton)).toHaveCount(0);
      await expect(otherPage.locator(probe.result)).toHaveText('?');
    } finally {
      await otherContext.close();
    }

    // The first student's budget is unchanged by the second student.
    await page.reload({ waitUntil: 'networkidle' });
    await waitForProbePanel(page);
    await expectBadge(page, 2, 'status-available');
  });
});

// ---------------------------------------------------------------------------
// A9: cooldown mode
// ---------------------------------------------------------------------------
test.describe('Probe budget: cooldown mode', () => {
  test('A9 cooldown mode refills the budget after a submission', async ({ page }) => {
    // Grading runs the submission in the Docker sandbox.
    test.setTimeout(90_000);
    const slug = 'e2e-probeable-cooldown';
    const refillHint = 'No probes remaining. Submit 1 more time to unlock more probes.';
    await navigateAsFreshStudent(page, 'a9-cooldown', COOLDOWN_URL);
    await waitForProbePanel(page);

    await expectBadge(page, 2, 'status-available');
    await expect(page.locator(probe.hint)).toHaveCount(0);

    const first = await probeAdd(page, slug, '1', '2', '3');
    expect(first.probe_status.remaining).toBe(1);

    await fillArgs(page, '2', '2');
    await expectBadge(page, 1, 'status-available');
    const second = await probeAdd(page, slug, '2', '2', '4');
    expect(second.probe_status.can_probe).toBe(false);
    expect(second.probe_status.remaining).toBe(0);
    expect(second.probe_status.mode).toBe('cooldown');
    expect(second.probe_status.submissions_to_next_refill).toBe(1);

    await expect(page.locator(probe.hint)).toHaveText(refillHint);
    await expect(page.locator(probe.button)).toBeDisabled();
    await expect(page.locator(probe.paramInput('a'))).toBeDisabled();
    await expect(page.locator(probe.paramInput('b'))).toBeDisabled();

    // One submission earns the refill.
    await submitCodeAndWait(page, ADD_SOLUTION);

    // A fresh load of the same problem (second tab, same student) shows the
    // server-side refill. Checked first so it is documented even if the
    // in-page state below is stale.
    const freshTab = await page.context().newPage();
    try {
      await freshTab.goto(COOLDOWN_URL, { waitUntil: 'networkidle' });
      await waitForProbePanel(freshTab);
      await expectBadge(freshTab, 2, 'status-available');
      await expect(freshTab.locator(probe.hint)).toHaveCount(0);
      await expect(freshTab.locator(probe.paramInput('a'))).toBeEnabled();
      await expect(freshTab.locator(probe.paramInput('b'))).toBeEnabled();
    } finally {
      await freshTab.close();
    }

    // Without a reload, the page the student submitted from must show the
    // refilled budget too.
    await expect(page.locator(probe.hint)).toHaveCount(0);
    await expect(page.locator(probe.paramInput('a'))).toBeEnabled();
    await expect(page.locator(probe.paramInput('b'))).toBeEnabled();
    await fillArgs(page, '3', '3');
    await expectBadge(page, 2, 'status-available');

    // A further probe works and spends from the refilled budget.
    const third = await probeAdd(page, slug, '3', '3', '6');
    expect(third.probe_status.can_probe).toBe(true);
    expect(third.probe_status.remaining).toBe(1);
    await fillArgs(page, '4', '4');
    await expectBadge(page, 1, 'status-available');
  });

  test('A9b the refill hint counts down the submissions still needed', async ({ page }) => {
    // Two graded submissions in the Docker sandbox.
    test.setTimeout(120_000);
    const slug = 'e2e-probeable-cooldown-2';
    await navigateAsFreshStudent(page, 'a9b-cooldown-2', COOLDOWN_2_URL);
    await waitForProbePanel(page);

    await expectBadge(page, 1, 'status-available');
    await expect(page.locator(probe.hint)).toHaveCount(0);

    const only = await probeAdd(page, slug, '1', '2', '3');
    expect(only.probe_status.can_probe).toBe(false);
    expect(only.probe_status.remaining).toBe(0);
    expect(only.probe_status.submissions_to_next_refill).toBe(2);
    await expect(page.locator(probe.hint)).toHaveText(
      'No probes remaining. Submit 2 more times to unlock more probes.',
    );
    await expect(page.locator(probe.paramInput('a'))).toBeDisabled();

    // First submission: one more is still needed, and the budget stays empty.
    await submitCodeAndWait(page, ADD_SOLUTION);
    await expect(page.locator(probe.hint)).toHaveText(
      'No probes remaining. Submit 1 more time to unlock more probes.',
    );
    await expect(page.locator(probe.paramInput('a'))).toBeDisabled();
    await expect(page.locator(probe.button)).toBeDisabled();
    await expectBadge(page, 0, 'status-exhausted');

    // Second submission earns the refill.
    await submitCodeAndWait(page, ADD_SOLUTION);
    await expect(page.locator(probe.hint)).toHaveCount(0);
    await expect(page.locator(probe.paramInput('a'))).toBeEnabled();
    await fillArgs(page, '2', '2');
    await expectBadge(page, 1, 'status-available');

    const refilled = await probeAdd(page, slug, '2', '2', '4');
    expect(refilled.probe_status.remaining).toBe(0);
    expect(refilled.probe_status.submissions_to_next_refill).toBe(2);
    await expect(page.locator(probe.hint)).toHaveText(
      'No probes remaining. Submit 2 more times to unlock more probes.',
    );
  });
});
