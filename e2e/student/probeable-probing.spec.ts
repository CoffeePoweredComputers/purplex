/**
 * E2E Tests: probing the oracle on probeable problems (workflow group A).
 *
 * Problem set e2e-probeable (seed_e2e_data._seed_probeable_workflows):
 *   p=2 e2e-probeable-locked  clamp(n: int) -> max(0, min(n, 10)), explore mode
 *   p=3 e2e-probeable-errors  recip(x: int) -> 10 // x, block mode, 3 probes
 *   p=4 e2e-probeable-hidden  recip(x) with the signature hidden, explore mode
 *   p=7 e2e-probeable-list    tag(items: list[str], prefix: str), explore mode
 *
 * Probe budgets and history live in Redis per (problem, user) with no reset,
 * so every test runs as a fresh student.
 *
 * The probe panel is a call line: `name(` and `)` are fixed text and the
 * student types the argument list (#probe-args), positional or keyword.
 */

import { test, expect, Page, Request } from '@playwright/test';
import { apiAsUser, navigateAsFreshStudent, FreshUser } from '../helpers/users';
import { probe } from '../helpers/selectors';
import {
  expectArgError,
  expectArgsEditable,
  fillProbeArgs,
  readArgsPlaceholder,
  readBadge,
} from '../helpers/probe';

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
 * Type the argument list, trigger a probe (button click or Enter in the call
 * line), and return the probe response body. Fails unless the API answers 200.
 */
async function probeWith(page: Page, args: string, via: 'click' | 'enter' = 'click'): Promise<any> {
  await fillProbeArgs(page, args);
  const responsePromise = page.waitForResponse((resp) => isProbePost(resp.request()));
  if (via === 'enter') {
    await page.locator(probe.argsLine).press('Enter');
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

    const line = page.locator(probe.argsLine);
    const result = page.locator(probe.result);
    const button = page.locator(probe.button);

    // Fresh state: empty call line showing the parameter name and its declared
    // type (the signature is visible here; A10 covers names only), no result,
    // no history, unlimited badge
    await expect(line).toHaveJSProperty('textContent', '');
    await expect(line).toHaveAttribute('role', 'textbox');
    await expect(line).toHaveAttribute('aria-label', 'Arguments for clamp');
    expect(await readArgsPlaceholder(page)).toBe('n: int');
    await expect(result).toHaveText('?');
    await expect(result).not.toHaveClass(/has-result/);
    await expect(page.locator(probe.historyButton)).toHaveCount(0);
    await expect(page.locator(probe.badge)).toHaveText('· ∞');
    await expect(page.locator(probe.badge)).toHaveClass(/status-explore/);
    // No value yet: nothing to probe
    await expect(button).toBeDisabled();

    const body = await probeWith(page, '7');
    expect(body.success).toBe(true);
    expect(body.result).toBe(7);
    expect(body.probe_status.mode).toBe('explore');

    await expect(result).toHaveText('7');
    await expect(result).toHaveClass(/has-result/);
    await expect(page.locator(probe.historyButton)).toHaveText('History (1)');
    await expect(page.locator(probe.error)).toHaveCount(0);

    // A new value brings the Probe button back with the unlimited badge
    await fillProbeArgs(page, '8');
    await expect(button).toBeEnabled();
    await expect(page.locator(probe.badge)).toHaveText('· ∞');
  });

  test('A2 repeat probe with a new input (Enter key) replaces the result', async ({ page }) => {
    await openAsFreshStudent(page, 'a2-repeat-probe', 2, 'clamp');

    await probeWith(page, '7');
    await expect(page.locator(probe.result)).toHaveText('7');
    await expect(page.locator(probe.historyButton)).toHaveText('History (1)');

    // Enter in the call line triggers the probe
    const body = await probeWith(page, '20', 'enter');
    expect(body.success).toBe(true);
    expect(body.result).toBe(10);

    await expect(page.locator(probe.result)).toHaveText('10');
    await expect(page.locator(probe.historyButton)).toHaveText('History (2)');
  });

  test('A3 duplicate probe returns the cached result without a request', async ({ page }) => {
    await openAsFreshStudent(page, 'a3-duplicate-probe', 2, 'clamp');

    await probeWith(page, '7');
    await probeWith(page, '20');
    await expect(page.locator(probe.result)).toHaveText('10');
    await expect(page.locator(probe.historyButton)).toHaveText('History (2)');

    const probePosts: string[] = [];
    page.on('request', (req) => {
      if (isProbePost(req)) {
        probePosts.push(req.postData() ?? '');
      }
    });

    const line = page.locator(probe.argsLine);
    const result = page.locator(probe.result);
    const button = page.locator(probe.button);

    await fillProbeArgs(page, '7');
    await expect(result).toHaveClass(/is-cached/);
    await expect(result).toHaveText('7');
    await expect(button).toHaveClass(/is-duplicate/);
    await expect(button).toContainText('Already probed');
    await expect(button).toBeDisabled();
    await expect(page.locator(probe.badge)).toHaveCount(0);

    // Enter in the call line is the other way to probe; it must not re-send either
    await line.press('Enter');

    // A real probe afterwards orders the request stream: if the duplicate had
    // been sent, it would be recorded before this one.
    const body = await probeWith(page, '3');
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

    const line = page.locator(probe.argsLine);
    const shell = page.locator(probe.callShell);
    const button = page.locator(probe.button);
    const fieldError = page.locator(probe.fieldError('n'));

    await fillProbeArgs(page, 'abc');
    await expectArgError(page, 'n', 'n: Must be a whole number (e.g. 5)');
    await expect(shell).toHaveClass(/has-error/);
    await expect(line).toHaveAttribute('aria-invalid', 'true');
    await expect(line).toHaveAttribute('aria-describedby', 'probe-field-errors probe-args-help');
    await expect(button).toBeDisabled();
    // Enter with an invalid value sends nothing
    await line.press('Enter');

    await fillProbeArgs(page, '3');
    await expect(fieldError).toHaveCount(0);
    await expect(shell).not.toHaveClass(/has-error/);
    await expect(line).not.toHaveAttribute('aria-invalid', 'true');
    await expect(button).toBeEnabled();

    const body = await probeWith(page, '3');
    expect(body.result).toBe(3);
    expect(probePosts).toBe(1);
    await expect(page.locator(probe.result)).toHaveText('3');
  });

  test('A5 history modal lists every probe, most recent first, and closes', async ({ page }) => {
    await openAsFreshStudent(page, 'a5-history-modal', 2, 'clamp');

    await probeWith(page, '7');
    await probeWith(page, '20');
    await probeWith(page, '-3');
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

    await probeWith(page, '7');
    await probeWith(page, '20');
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

    // Both probes restored from the server, the latest result shown, call line cleared
    await expect(page.locator(probe.historyButton)).toHaveText('History (2)');
    await expect(page.locator(probe.result)).toHaveText('10');
    await expect(page.locator(probe.argsLine)).toHaveJSProperty('textContent', '');
    await expect(page.locator(probe.badge)).toHaveText('· ∞');

    await page.locator(probe.historyButton).click();
    const rows = page.locator(probe.historyRow);
    await expect(rows.locator('.modal-call')).toHaveText(['clamp(20)', 'clamp(7)']);
    await expect(rows.locator('.modal-result')).toHaveText(['10', '7']);
    await page.locator(probe.close).click();

    // Re-entering a value probed before the reload is still recognised
    await fillProbeArgs(page, '7');
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
      const body = await probeWith(page, String(n));
      expect(body.success).toBe(true);
      expect(body.result).toBe(Math.min(n, 10));
      expect(body.probe_status.mode).toBe('explore');
      expect(body.probe_status.can_probe).toBe(true);
      await expect(page.locator(probe.result)).toHaveText(String(Math.min(n, 10)));
    }

    await expect(page.locator(probe.historyButton)).toHaveText('History (15)');

    await fillProbeArgs(page, '16');
    await expectArgsEditable(page, true);
    await expect(page.locator(probe.button)).toBeEnabled();
    await expect(badge).toHaveText('· ∞');
    await expect(badge).toHaveClass(/status-explore/);
    await expect(page.locator(probe.hint)).toHaveCount(0);

    const body = await probeWith(page, '16');
    expect(body.success).toBe(true);
    expect(body.result).toBe(10);
    await expect(page.locator(probe.historyButton)).toHaveText('History (16)');
  });

  test('A10 hidden signature hides types and sanitises oracle errors', async ({ page }) => {
    const user = await openAsFreshStudent(page, 'a10-hidden', 4, 'recip');

    // Parameter names are not secret: the empty call line still shows them
    const line = page.locator(probe.argsLine);
    expect(await readArgsPlaceholder(page)).toBe('x');
    await expect(line).toHaveAttribute('aria-label', 'Arguments for recip');

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

    // Without the types the browser cannot pre-check 'abc', so only the backend
    // can reject it: a 400 (not charged) whose generic message reaches the UI
    const error = page.locator(probe.error);
    await fillProbeArgs(page, 'abc');
    await expect(page.locator(probe.fieldError('x'))).toHaveCount(0);
    const rejectedPromise = page.waitForResponse((resp) => isProbePost(resp.request()));
    await page.locator(probe.button).click();
    const rejected = await rejectedPromise;
    expect(rejected.status()).toBe(400);
    await expect(error).toHaveText("That value is not valid for parameter 'x'");
    await expect(error).not.toContainText('int');
    await expect(page.locator(probe.historyButton)).toHaveCount(0);
    await expect(page.locator(probe.badge)).toHaveText('· ∞');

    const failed = await probeWith(page, '0');
    expect(failed.success).toBe(false);
    await expect(error).toHaveText('These inputs could not be evaluated. Try different values.');
    await expect(error).not.toContainText('division');
    await expect(page.locator(probe.result)).toHaveText('?');
    await expect(page.locator(probe.historyButton)).toHaveCount(0);

    const ok = await probeWith(page, '5');
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

    const failed = await probeWith(page, '0');
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

    const ok = await probeWith(page, '5');
    expect(ok.success).toBe(true);
    expect(ok.result).toBe(2);
    expect(ok.probe_status.remaining).toBe(2);
    await expect(page.locator(probe.result)).toHaveText('2');
    await expect(page.locator(probe.error)).toHaveCount(0);
    await expect(page.locator(probe.historyButton)).toHaveText('History (1)');

    // The call line still holds the probed value (duplicate state hides the
    // badge); a new value shows the charged budget
    await fillProbeArgs(page, '6');
    await expect(badge).toHaveText('· 2 left');
    await expect(badge).toHaveClass(/status-available/);
  });

  test('A12 list[str] given integers shows the item-type error and disables Probe', async ({
    page,
  }) => {
    await openAsFreshStudent(page, 'a12-list-items', 7, 'tag');

    const probePosts: string[] = [];
    page.on('request', (req) => {
      if (isProbePost(req)) {
        probePosts.push(req.postData() ?? '');
      }
    });

    const line = page.locator(probe.argsLine);
    const button = page.locator(probe.button);

    // Integers are not str: the item type is checked, not just the list shape
    await fillProbeArgs(page, '[1, 2, 3], "x"');
    await expectArgError(page, 'items', 'items: Every item must be str');
    await expect(page.locator(probe.fieldError('prefix'))).toHaveCount(0);
    await expect(page.locator(probe.callShell)).toHaveClass(/has-error/);
    await expect(button).toBeDisabled();
    // Enter with an invalid value sends nothing
    await line.press('Enter');

    await fillProbeArgs(page, '["a", "b"], "x"');
    await expect(page.locator(`${probe.fieldErrors} li`)).toHaveCount(0);
    await expect(button).toBeEnabled();
    await expect.poll(() => readBadge(page)).toBe('· ∞');

    const body = await probeWith(page, '["a", "b"], "x"');
    expect(body.success).toBe(true);
    expect(body.result).toEqual(['xa', 'xb']);
    await expect(page.locator(probe.result)).toHaveText('["xa","xb"]');
    expect(probePosts).toEqual([JSON.stringify({ input: { items: ['a', 'b'], prefix: 'x' } })]);
  });

  test('A13 keyword and positional arguments map onto the signature', async ({ page }) => {
    await openAsFreshStudent(page, 'a13-arg-mapping', 2, 'clamp');

    const probePosts: string[] = [];
    page.on('request', (req) => {
      if (isProbePost(req)) {
        probePosts.push(req.postData() ?? '');
      }
    });

    const result = page.locator(probe.result);
    const button = page.locator(probe.button);
    const lineError = page.locator(probe.lineError);

    // Positional: the first argument is n
    const body = await probeWith(page, '7');
    expect(body.result).toBe(7);
    await expect(result).toHaveText('7');

    // Keyword: n=7 is the same call, so the cached result answers it
    await fillProbeArgs(page, 'n=7');
    await expect(lineError).toHaveCount(0);
    await expect(result).toHaveClass(/is-cached/);
    await expect(result).toHaveText('7');
    await expect(button).toContainText('Already probed');

    await fillProbeArgs(page, 'n=7, n=8');
    await expectArgError(page, 'line', 'Argument n given twice');
    await expect(page.locator(probe.callShell)).toHaveClass(/has-error/);
    await expect(button).toBeDisabled();

    await fillProbeArgs(page, 'm=7');
    await expectArgError(page, 'line', 'Unknown argument m');
    await expect(button).toBeDisabled();

    await fillProbeArgs(page, '7, 8');
    await expectArgError(page, 'line', 'Too many arguments for clamp');
    await expect(button).toBeDisabled();

    // A clean line clears the line error
    await fillProbeArgs(page, 'n=8');
    await expect(lineError).toHaveCount(0);
    await expect(button).toBeEnabled();

    // Only the one positional probe reached the server, as {"n": 7}
    expect(probePosts).toEqual([JSON.stringify({ input: { n: 7 } })]);
  });

  test('A14 Enter probes, Shift+Enter does nothing, and Tab leaves the line', async ({ page }) => {
    await openAsFreshStudent(page, 'a14-keys', 7, 'tag');

    const line = page.locator(probe.argsLine);
    await fillProbeArgs(page, 'items=["a", "b"], prefix="x"');
    await line.focus();
    await page.keyboard.press('End');
    // Shift+Enter inserts nothing: the call is one logical line
    await page.keyboard.press('Shift+Enter');
    await expect(line).toHaveJSProperty('textContent', 'items=["a", "b"], prefix="x"');
    await expect(line).toBeFocused();

    const responsePromise = page.waitForResponse((resp) => isProbePost(resp.request()));
    await page.keyboard.press('Enter');
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    expect(response.request().postData()).toBe(
      JSON.stringify({ input: { items: ['a', 'b'], prefix: 'x' } }),
    );
    await expect(page.locator(probe.result)).toHaveText('["xa","xb"]');
    // Enter probes; it never adds a line break
    await expect(line).toHaveJSProperty('textContent', 'items=["a", "b"], prefix="x"');
    // Focus comes back to the line, so the next probe needs no Tab back
    await expect(line).toBeFocused();
    await expect(line).toHaveAttribute('contenteditable', 'plaintext-only');

    // Tab is ordinary focus navigation: it leaves the line and changes nothing,
    // so the editable is never a keyboard trap
    await page.keyboard.press('Tab');
    await expect(line).not.toBeFocused();
    await expect(line).toHaveJSProperty('textContent', 'items=["a", "b"], prefix="x"');
  });

  test('A15 the closing parenthesis trails the arguments', async ({ page }) => {
    await openAsFreshStudent(page, 'a15-close-paren', 7, 'tag');

    const words = Array.from({ length: 40 }, (_, i) => `"word${String(i).padStart(2, '0')}"`);
    const args = `[${words.join(', ')}], "x"`;
    await fillProbeArgs(page, args);
    await expect(page.locator(probe.button)).toBeEnabled();

    const line = page.locator(probe.argsLine);
    const lineRects = await line.evaluate((el) =>
      Array.from(el.getClientRects()).map((r) => ({
        top: r.top,
        bottom: r.bottom,
        right: r.right,
      })),
    );
    // The long argument list wraps over several lines
    expect(lineRects.length).toBeGreaterThan(1);
    const last = lineRects[lineRects.length - 1];

    const paren = await page.locator(probe.closeParen).boundingBox();
    expect(paren).not.toBeNull();
    await expect(page.locator(probe.closeParen)).toHaveText(')');
    // ')' sits on the editable's last line, right after its last character
    const parenMiddle = paren!.y + paren!.height / 2;
    expect(parenMiddle).toBeGreaterThan(last.top);
    expect(parenMiddle).toBeLessThan(last.bottom);
    expect(paren!.x).toBeGreaterThanOrEqual(last.right - 1);
  });

  test('A16 the backend rejects a list[str] with integers too', async ({ page }) => {
    const user = await openAsFreshStudent(page, 'a16-backend-list', 7, 'tag');

    const { status, data } = await apiAsUser(
      page,
      user,
      'POST',
      '/api/problems/e2e-probeable-list/probe/',
      { input: { items: [1, 2], prefix: 'x' } },
    );
    expect(status).toBe(400);
    expect(data.error).toBe("Parameter 'items' must be a list of str");
  });

  test('A17 a quoted str argument is a Python string literal', async ({ page }) => {
    await openAsFreshStudent(page, 'a17-str-quotes', 7, 'tag');

    const probePosts: string[] = [];
    page.on('request', (req) => {
      if (isProbePost(req)) {
        probePosts.push(req.postData() ?? '');
      }
    });
    const button = page.locator(probe.button);

    // An unterminated quote is not a string: error, and Probe stays disabled
    await fillProbeArgs(page, `['a'], "abc`);
    await expectArgError(page, 'prefix', 'prefix: Not a valid Python value');
    await expect(button).toBeDisabled();
    await page.locator(probe.argsLine).press('Enter');

    // An empty argument between commas is a line error, not a skipped parameter
    await fillProbeArgs(page, `['a'],, 'x'`);
    await expectArgError(page, 'line', 'Empty argument between commas');
    await expect(button).toBeDisabled();

    // Single quotes delimit the str exactly as double quotes do
    const body = await probeWith(page, `['a', 'b'], 'x'`, 'enter');
    expect(body.success).toBe(true);
    expect(body.result).toEqual(['xa', 'xb']);
    await expect(page.locator(probe.result)).toHaveText('["xa","xb"]');
    expect(probePosts).toEqual([JSON.stringify({ input: { items: ['a', 'b'], prefix: 'x' } })]);
  });

  test('A18 on a narrow screen History wraps below the call line', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await openAsFreshStudent(page, 'a18-narrow', 7, 'tag');

    await probeWith(page, '["a"], "x"');
    await expect(page.locator(probe.historyButton)).toHaveText('History (1)');

    const row = await page.locator(probe.row).boundingBox();
    const shell = await page.locator(probe.callShell).boundingBox();
    const history = await page.locator(probe.historyButton).boundingBox();
    expect(row && shell && history).toBeTruthy();
    // The call line gets the full row width; History sits on a line of its own
    expect(shell!.width).toBeGreaterThanOrEqual(row!.width - 1);
    expect(history!.y).toBeGreaterThanOrEqual(shell!.y + shell!.height);
  });
});
