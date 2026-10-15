/**
 * E2E Tests: probing the oracle on probeable problems (workflow group A).
 *
 * Problem set e2e-probeable (seed_e2e_data._seed_probeable_workflows):
 *   p=2 e2e-probeable-locked  clamp(n: int) -> max(0, min(n, 10)), explore mode
 *   p=3 e2e-probeable-errors  recip(x: int) -> 10 // x, block mode, 3 probes
 *   p=4 e2e-probeable-hidden  recip(x) with the signature hidden, explore mode
 *
 * Probe budgets and history live in Redis per (problem, user) with no reset,
 * so every test runs as a fresh student.
 */

import { test, expect, Page, Request } from '@playwright/test';
import { apiAsUser, navigateAsFreshStudent, FreshUser } from '../helpers/users';
import { probe } from '../helpers/selectors';

const SET_PATH = '/courses/CS101-2024/problem-set/e2e-probeable';
const PROBE_POST_PATH = /^\/api\/problems\/[^/]+\/probe\/$/;

function isProbePost(req: Request): boolean {
  return req.method() === 'POST' && PROBE_POST_PATH.test(new URL(req.url()).pathname);
}

/** Open problem `index` of e2e-probeable as a fresh student and wait for probe status. */
async function openAsFreshStudent(
  page: Page,
  label: string,
  index: number,
  functionName: string,
): Promise<FreshUser> {
  const user = await navigateAsFreshStudent(page, label, `${SET_PATH}?p=${index}`);
  await expect(page.locator(probe.panel)).toBeVisible();
  await expect(page.locator('.probe-panel .fn-name')).toHaveText(functionName);
  // The badge renders once /probe/status/ has loaded
  await expect(page.locator(probe.badge)).toBeVisible();
  return user;
}

/**
 * Fill one parameter, trigger a probe (button click or Enter in the field),
 * and return the probe response body. Fails unless the API answers 200.
 */
async function probeWith(
  page: Page,
  param: string,
  value: string,
  via: 'click' | 'enter' = 'click',
): Promise<any> {
  const input = page.locator(probe.paramInput(param));
  await input.fill(value);
  const responsePromise = page.waitForResponse((resp) => isProbePost(resp.request()));
  if (via === 'enter') {
    await input.press('Enter');
  } else {
    await page.locator(probe.button).click();
  }
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  return response.json();
}

test.describe('A Probing the oracle', () => {
  test('A1 first probe shows the result, the explore badge and History (1)', async ({ page }) => {
    await openAsFreshStudent(page, 'a1-first-probe', 2, 'clamp');

    const input = page.locator(probe.paramInput('n'));
    const result = page.locator(probe.result);
    const button = page.locator(probe.button);

    // Fresh state: empty input, no result, no history, unlimited badge
    await expect(input).toHaveValue('');
    await expect(input).toHaveAttribute('placeholder', 'int');
    await expect(result).toHaveText('?');
    await expect(result).not.toHaveClass(/has-result/);
    await expect(page.locator(probe.historyButton)).toHaveCount(0);
    await expect(page.locator(probe.badge)).toHaveText('· ∞');
    await expect(page.locator(probe.badge)).toHaveClass(/status-explore/);
    // No value yet: nothing to probe
    await expect(button).toBeDisabled();

    const body = await probeWith(page, 'n', '7');
    expect(body.success).toBe(true);
    expect(body.result).toBe(7);
    expect(body.probe_status.mode).toBe('explore');

    await expect(result).toHaveText('7');
    await expect(result).toHaveClass(/has-result/);
    await expect(page.locator(probe.historyButton)).toHaveText('History (1)');
    await expect(page.locator(probe.error)).toHaveCount(0);

    // A new value brings the Probe button back with the unlimited badge
    await input.fill('8');
    await expect(button).toBeEnabled();
    await expect(page.locator(probe.badge)).toHaveText('· ∞');
  });

  test('A2 repeat probe with a new input (Enter key) replaces the result', async ({ page }) => {
    await openAsFreshStudent(page, 'a2-repeat-probe', 2, 'clamp');

    await probeWith(page, 'n', '7');
    await expect(page.locator(probe.result)).toHaveText('7');
    await expect(page.locator(probe.historyButton)).toHaveText('History (1)');

    // Enter in the field triggers the probe
    const body = await probeWith(page, 'n', '20', 'enter');
    expect(body.success).toBe(true);
    expect(body.result).toBe(10);

    await expect(page.locator(probe.result)).toHaveText('10');
    await expect(page.locator(probe.historyButton)).toHaveText('History (2)');
  });

  test('A3 duplicate probe returns the cached result without a request', async ({ page }) => {
    await openAsFreshStudent(page, 'a3-duplicate-probe', 2, 'clamp');

    await probeWith(page, 'n', '7');
    await probeWith(page, 'n', '20');
    await expect(page.locator(probe.result)).toHaveText('10');
    await expect(page.locator(probe.historyButton)).toHaveText('History (2)');

    const probePosts: string[] = [];
    page.on('request', (req) => {
      if (isProbePost(req)) {
        probePosts.push(req.postData() ?? '');
      }
    });

    const input = page.locator(probe.paramInput('n'));
    const result = page.locator(probe.result);
    const button = page.locator(probe.button);

    await input.fill('7');
    await expect(result).toHaveClass(/is-cached/);
    await expect(result).toHaveText('7');
    await expect(button).toHaveClass(/is-duplicate/);
    await expect(button).toContainText('Already probed');
    await expect(button).toBeDisabled();
    await expect(page.locator(probe.badge)).toHaveCount(0);

    // Enter in the field is the other way to probe; it must not re-send either
    await input.press('Enter');

    // A real probe afterwards orders the request stream: if the duplicate had
    // been sent, it would be recorded before this one.
    const body = await probeWith(page, 'n', '3');
    expect(body.result).toBe(3);
    expect(probePosts).toEqual([JSON.stringify({ input: { n: 3 } })]);
    await expect(page.locator(probe.historyButton)).toHaveText('History (3)');
  });

  test('A4 invalid type shows a field error and blocks probing until fixed', async ({ page }) => {
    await openAsFreshStudent(page, 'a4-invalid-type', 2, 'clamp');

    let probePosts = 0;
    page.on('request', (req) => {
      if (isProbePost(req)) {
        probePosts += 1;
      }
    });

    const input = page.locator(probe.paramInput('n'));
    const button = page.locator(probe.button);
    const fieldError = page.locator(probe.fieldError('n'));

    await input.fill('abc');
    await expect(fieldError).toHaveText('n: Must be a whole number (e.g. 5)');
    await expect(input).toHaveClass(/has-error/);
    await expect(input).toHaveAttribute('aria-invalid', 'true');
    await expect(input).toHaveAttribute('aria-describedby', 'probe-err-n');
    await expect(button).toBeDisabled();
    // Enter with an invalid value sends nothing
    await input.press('Enter');

    await input.fill('3');
    await expect(fieldError).toHaveCount(0);
    await expect(input).not.toHaveClass(/has-error/);
    await expect(button).toBeEnabled();

    const body = await probeWith(page, 'n', '3');
    expect(body.result).toBe(3);
    expect(probePosts).toBe(1);
    await expect(page.locator(probe.result)).toHaveText('3');
  });

  test('A5 history modal lists every probe, most recent first, and closes', async ({ page }) => {
    await openAsFreshStudent(page, 'a5-history-modal', 2, 'clamp');

    await probeWith(page, 'n', '7');
    await probeWith(page, 'n', '20');
    await probeWith(page, 'n', '-3');
    await expect(page.locator(probe.result)).toHaveText('0');

    const historyButton = page.locator(probe.historyButton);
    await expect(historyButton).toHaveText('History (3)');
    await historyButton.click();

    const modal = page.locator(probe.historyModal);
    await expect(modal).toBeVisible();
    await expect(modal.locator('#history-modal-title')).toHaveText('Probe History');

    const rows = page.locator(probe.historyRow);
    await expect(rows).toHaveCount(3);
    await expect(rows.locator('.modal-index')).toHaveText(['#3', '#2', '#1']);
    await expect(rows.locator('.modal-call')).toHaveText(['clamp(-3)', 'clamp(20)', 'clamp(7)']);
    await expect(rows.locator('.modal-result')).toHaveText(['0', '10', '7']);

    await page.locator(probe.close).click();
    await expect(page.locator('.modal-overlay')).toHaveCount(0);
    await expect(historyButton).toHaveText('History (3)');
  });

  test('A6 reload restores the probe history from the server', async ({ page }) => {
    const user = await openAsFreshStudent(page, 'a6-reload', 2, 'clamp');

    await probeWith(page, 'n', '7');
    await probeWith(page, 'n', '20');
    await expect(page.locator(probe.historyButton)).toHaveText('History (2)');

    const server = await apiAsUser(
      page,
      user,
      'GET',
      '/api/problems/e2e-probeable-locked/probe/history/',
    );
    expect(server.status).toBe(200);
    expect(server.data.history.map((e: any) => [e.input, e.output])).toEqual([
      [{ n: 20 }, 10],
      [{ n: 7 }, 7],
    ]);

    const historyLoaded = page.waitForResponse(
      (resp) =>
        new URL(resp.url()).pathname === '/api/problems/e2e-probeable-locked/probe/history/' &&
        resp.status() === 200,
    );
    await page.reload();
    await historyLoaded;
    await expect(page.locator(probe.panel)).toBeVisible();

    // Both probes restored from the server, the latest result shown, inputs cleared
    await expect(page.locator(probe.historyButton)).toHaveText('History (2)');
    await expect(page.locator(probe.result)).toHaveText('10');
    await expect(page.locator(probe.paramInput('n'))).toHaveValue('');
    await expect(page.locator(probe.badge)).toHaveText('· ∞');

    await page.locator(probe.historyButton).click();
    const rows = page.locator(probe.historyRow);
    await expect(rows.locator('.modal-call')).toHaveText(['clamp(20)', 'clamp(7)']);
    await expect(rows.locator('.modal-result')).toHaveText(['10', '7']);
    await page.locator(probe.close).click();

    // Re-entering a value probed before the reload is still recognised
    await page.locator(probe.paramInput('n')).fill('7');
    await expect(page.locator(probe.result)).toHaveClass(/is-cached/);
    await expect(page.locator(probe.result)).toHaveText('7');
    await expect(page.locator(probe.button)).toContainText('Already probed');
  });

  test('A7 explore mode never runs out of probes', async ({ page }) => {
    await openAsFreshStudent(page, 'a7-explore', 2, 'clamp');

    const badge = page.locator(probe.badge);
    await expect(badge).toHaveText('· ∞');
    await expect(badge).toHaveClass(/status-explore/);

    for (let n = 1; n <= 15; n += 1) {
      const body = await probeWith(page, 'n', String(n));
      expect(body.success).toBe(true);
      expect(body.result).toBe(Math.min(n, 10));
      expect(body.probe_status.mode).toBe('explore');
      expect(body.probe_status.can_probe).toBe(true);
      await expect(page.locator(probe.result)).toHaveText(String(Math.min(n, 10)));
    }

    await expect(page.locator(probe.historyButton)).toHaveText('History (15)');

    const input = page.locator(probe.paramInput('n'));
    await input.fill('16');
    await expect(input).toBeEnabled();
    await expect(page.locator(probe.button)).toBeEnabled();
    await expect(badge).toHaveText('· ∞');
    await expect(badge).toHaveClass(/status-explore/);
    await expect(page.locator(probe.hint)).toHaveCount(0);

    const body = await probeWith(page, 'n', '16');
    expect(body.success).toBe(true);
    expect(body.result).toBe(10);
    await expect(page.locator(probe.historyButton)).toHaveText('History (16)');
  });

  test('A10 hidden signature hides types and sanitises oracle errors', async ({ page }) => {
    const user = await openAsFreshStudent(page, 'a10-hidden', 4, 'recip');

    const input = page.locator(probe.paramInput('x'));
    await expect(page.locator('.probe-panel .param-name')).toHaveText(['x']);
    await expect(input).toHaveAttribute('placeholder', 'value — quote text: "abc"');
    await expect(input).toHaveAttribute('aria-label', 'Enter value for x');

    // The types never reach the browser: the problem payload the page loads
    // carries no signature, untyped parameters and no oracle source.
    const { status, data } = await apiAsUser(page, user, 'GET', '/api/problem-sets/e2e-probeable/');
    expect(status).toBe(200);
    const hidden = data.problems.find((p: { slug: string }) => p.slug === 'e2e-probeable-hidden');
    expect(hidden.function_signature).toBeNull();
    expect(hidden.probe_config.function_signature).toBeNull();
    expect(hidden.probe_config.parameters).toEqual([{ name: 'x', type: '' }]);
    expect(hidden.reference_solution).toBeNull();
    await expect(page.locator(probe.badge)).toHaveText('· ∞');

    const failed = await probeWith(page, 'x', '0');
    expect(failed.success).toBe(false);
    const error = page.locator(probe.error);
    await expect(error).toHaveText('These inputs could not be evaluated. Try different values.');
    await expect(error).not.toContainText('division');
    await expect(page.locator(probe.result)).toHaveText('?');
    await expect(page.locator(probe.historyButton)).toHaveCount(0);

    const ok = await probeWith(page, 'x', '5');
    expect(ok.success).toBe(true);
    expect(ok.result).toBe(2);
    await expect(page.locator(probe.result)).toHaveText('2');
    await expect(error).toHaveCount(0);
    await expect(page.locator(probe.historyButton)).toHaveText('History (1)');
  });

  test('A11 visible-signature oracle error is shown and not charged', async ({ page }) => {
    await openAsFreshStudent(page, 'a11-oracle-error', 3, 'recip');

    const badge = page.locator(probe.badge);
    await expect(badge).toHaveText('· 3 left');
    await expect(badge).toHaveClass(/status-available/);

    const failed = await probeWith(page, 'x', '0');
    expect(failed.success).toBe(false);
    expect(failed.probe_status.remaining).toBe(3);
    // Exactly the exception text, nothing else (no traceback, no type name).
    // The oracle runs under the server's interpreter (oracle_sandbox.py uses
    // sys.executable): Python <= 3.13 says "integer division or modulo by
    // zero" for `10 // 0`, 3.14 says "division by zero".
    await expect(page.locator(probe.error)).toHaveText(
      /^(integer division or modulo|division) by zero$/,
    );
    await expect(badge).toHaveText('· 3 left');
    await expect(page.locator(probe.result)).toHaveText('?');
    await expect(page.locator(probe.historyButton)).toHaveCount(0);

    const ok = await probeWith(page, 'x', '5');
    expect(ok.success).toBe(true);
    expect(ok.result).toBe(2);
    expect(ok.probe_status.remaining).toBe(2);
    await expect(page.locator(probe.result)).toHaveText('2');
    await expect(page.locator(probe.error)).toHaveCount(0);
    await expect(page.locator(probe.historyButton)).toHaveText('History (1)');

    // The input still holds the probed value (duplicate state hides the badge);
    // a new value shows the charged budget
    await page.locator(probe.paramInput('x')).fill('6');
    await expect(badge).toHaveText('· 2 left');
    await expect(badge).toHaveClass(/status-available/);
  });
});
