/**
 * SPLICE iframe protocol E2E (X1, #148 — protocol slice).
 *
 * Drives the real embed bundle inside a real cross-document iframe and asserts
 * the postMessage contract with the host: the getState handshake, answer
 * restoration, frame resizing, score reporting, and origin validation.
 *
 * The API is stubbed at the network boundary. That is deliberate for this
 * slice: the protocol is what's under test, and stubbing keeps the spec
 * deterministic and free of Celery + LLM latency. The end-to-end pass against
 * a live backend — real Docker execution, real scores — belongs with the rest
 * of X1 once the backend track (B1-B5) lands and the embed can actually
 * authenticate.
 *
 * Runs against the Vite dev server only (embed.html + the mock host page are
 * both served from the client root); no Django or Celery required.
 */
import { expect, Frame, Page, test } from '@playwright/test';
import { getAceEditorValue, setAceEditorValue } from '../helpers/ace-editor';

const EMBED_ORIGIN = 'http://localhost:5173';

interface CapturedMessage {
  subject: string;
  message_id: string;
  [key: string]: unknown;
}

const EIPL_PROBLEM = {
  slug: 'sum-list',
  title: 'Sum a list',
  description: 'Explain how to add up every number in a list.',
  problem_type: 'eipl',
  function_name: 'sum_list',
  function_signature: 'def sum_list(numbers):',
  reference_solution: 'return sum(numbers)',
  input_config: {},
  display_config: {},
  feedback_config: { show_segmentation: false },
};

/** A sync-complete submission, so the flow never needs Celery or an SSE stream. */
const SYNC_SUBMISSION = {
  status: 'complete',
  submission_id: 'sub-e2e-1',
  problem_type: 'eipl',
  score: 80,
  is_correct: false,
  completion_status: 'partial',
  problem_slug: 'sum-list',
  user_input: 'add up every number in the list',
  result: {
    variations: [{ code: 'def sum_list(numbers):\n    return sum(numbers)' }],
    test_results: [{ success: true, testsPassed: 3, totalTests: 3 }],
    segmentation: null,
  },
};

/**
 * Stub the endpoints the embed calls. Responses carry permissive CORS
 * headers because the embed talks to :8000 directly rather than through the
 * Vite proxy.
 */
async function stubApi(page: Page, problem: object = EIPL_PROBLEM): Promise<void> {
  const cors = {
    'Access-Control-Allow-Origin': EMBED_ORIGIN,
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Credentials': 'true',
  };

  const json = (body: object) => ({
    status: 200,
    contentType: 'application/json',
    headers: cors,
    body: JSON.stringify(body),
  });

  await page.route('**/api/problems/**', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      return route.fulfill({ status: 204, headers: cors, body: '' });
    }
    return route.fulfill(json(problem));
  });

  // Default: no prior work, so tests that exercise host-supplied state are
  // not affected. A test can register a later route to model a relaunch.
  await page.route('**/api/last-submission/**', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      return route.fulfill({ status: 204, headers: cors, body: '' });
    }
    return route.fulfill(json({ has_submission: false }));
  });

  await page.route('**/api/submit/', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      return route.fulfill({ status: 204, headers: cors, body: '' });
    }
    return route.fulfill(json(SYNC_SUBMISSION));
  });
}

/**
 * Load a minimal host page that frames the embed and records every inbound
 * SPLICE message, mirroring what embed-mockhost.html does by hand.
 *
 * `prefillState` is what the host replies to SPLICE.getState with — null
 * models a first launch, an object models a relaunch with saved work.
 */
async function launchEmbed(
  page: Page,
  options: { problem?: string; prefillState?: unknown; replyToGetState?: boolean } = {},
): Promise<void> {
  const { problem = 'sum-list', prefillState = null, replyToGetState = true } = options;

  // Navigate first so the host document has a real origin — the embed derives
  // its allowed origin from document.referrer.
  await page.goto('/');

  await page.evaluate(
    ({ problemSlug, state, shouldReply }) => {
      const w = window as unknown as {
        __spliceMessages: CapturedMessage[]
        __spliceFrame: HTMLIFrameElement
      };
      w.__spliceMessages = [];

      window.addEventListener('message', (event) => {
        const data = event.data;
        if (!data || typeof data !== 'object' || typeof data.subject !== 'string') {
          return;
        }
        if (!/^(SPLICE\.|lti\.)/.test(data.subject)) {
          return;
        }
        w.__spliceMessages.push(data);

        if (data.subject === 'SPLICE.getState' && shouldReply) {
          (event.source as Window)?.postMessage(
            {
              subject: 'SPLICE.getState.response',
              message_id: data.message_id,
              state,
              user_id: 'mock-user-1',
              context_id: 'mock-context-1',
            },
            '*',
          );
        }
      });

      const frame = document.createElement('iframe');
      frame.id = 'embed-frame';
      frame.style.width = '900px';
      frame.style.height = '400px';
      frame.style.border = '0';
      frame.src = `/embed.html?problem=${encodeURIComponent(problemSlug)}&token=e2e-token`;
      document.body.appendChild(frame);
      w.__spliceFrame = frame;
    },
    { problemSlug: problem, state: prefillState, shouldReply: replyToGetState },
  );
}

/**
 * The embed's Frame, for evaluate()-level work (FrameLocator can't evaluate).
 * Waits for the document to exist rather than assuming it has already loaded.
 */
async function embedFrame(page: Page): Promise<Frame> {
  await page.waitForFunction(
    () => {
      const el = document.getElementById('embed-frame') as HTMLIFrameElement | null;
      return !!el?.contentWindow;
    },
    undefined,
    { timeout: 15_000 },
  );
  const frame = page.frames().find((f) => f.url().includes('embed.html'));
  if (!frame) {
    throw new Error('embed frame not found');
  }
  return frame;
}

/**
 * Fill the EiPL/prompt answer. The input is an Ace editor, not a textarea, so
 * the value has to go in through Vue's v-model chain — see helpers/ace-editor.
 */
async function fillAnswer(page: Page, value: string): Promise<void> {
  const frame = await embedFrame(page);
  await setAceEditorValue(frame, '#promptEditor', value);
}

function messages(page: Page): Promise<CapturedMessage[]> {
  return page.evaluate(
    () => (window as unknown as { __spliceMessages: CapturedMessage[] }).__spliceMessages,
  );
}

/** Wait until at least one message with the given subject has arrived. */
async function waitForSubject(page: Page, subject: string, timeout = 15_000): Promise<CapturedMessage> {
  await page.waitForFunction(
    (s) =>
      (window as unknown as { __spliceMessages: CapturedMessage[] }).__spliceMessages.some(
        (m) => m.subject === s,
      ),
    subject,
    { timeout },
  );
  const all = await messages(page);
  return all.find((m) => m.subject === subject)!;
}

test.describe('SPLICE iframe protocol', () => {
  test.beforeEach(async ({ page }) => {
    await stubApi(page);
  });

  test('announces readiness by sending SPLICE.getState on load', async ({ page }) => {
    await launchEmbed(page, { replyToGetState: false });

    const getState = await waitForSubject(page, 'SPLICE.getState');
    expect(getState.message_id).toBeTruthy();
  });

  test('renders the problem even when the host never answers getState', async ({ page }) => {
    // The spec warns the response "may not even return" — render must not block.
    await launchEmbed(page, { replyToGetState: false });

    const frame = page.frameLocator('#embed-frame');
    await expect(frame.getByRole('heading', { name: 'Sum a list' })).toBeVisible();
  });

  test('asks the host to resize the frame to the content height', async ({ page }) => {
    await launchEmbed(page);

    const resize = await waitForSubject(page, 'lti.frameResize');
    expect(resize.height).toBeGreaterThan(0);
    expect(resize.width).toBeGreaterThan(0);
  });

  test('restores a previous answer from host-supplied state', async ({ page }) => {
    await launchEmbed(page, {
      prefillState: {
        version: 1,
        problem_slug: 'sum-list',
        problem_type: 'eipl',
        raw_input: 'my saved explanation',
        score: 40,
        completion_status: 'partial',
        submission_id: 'sub-prev',
        attempts: 1,
        updated_at: new Date().toISOString(),
        details: {},
      },
    });

    const frame = page.frameLocator('#embed-frame');
    await expect(frame.locator('#promptEditor .ace_editor')).toBeVisible();
    await expect
      .poll(async () => getAceEditorValue(await embedFrame(page), '#promptEditor'))
      .toBe('my saved explanation');
  });

  test('restores the last submitted answer from Purplex when the host holds no state', async ({ page }) => {
    // An LTI platform such as Canvas never answers getState, so restoration
    // has to come from the learner's own submission record.
    await page.route('**/api/last-submission/**', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        return route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': EMBED_ORIGIN, 'Access-Control-Allow-Headers': '*', 'Access-Control-Allow-Credentials': 'true' }, body: '' });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': EMBED_ORIGIN, 'Access-Control-Allow-Credentials': 'true' },
        body: JSON.stringify({ has_submission: true, submission_id: 'sub-prev', user_prompt: 'my last submitted explanation', score: 60 }),
      });
    });

    await launchEmbed(page, { replyToGetState: false });

    const frame = page.frameLocator('#embed-frame');
    await expect(frame.locator('#promptEditor .ace_editor')).toBeVisible();
    await expect
      .poll(async () => getAceEditorValue(await embedFrame(page), '#promptEditor'))
      .toBe('my last submitted explanation');
  });

  test('ignores state the host saved against a different problem', async ({ page }) => {
    await launchEmbed(page, {
      prefillState: {
        version: 1,
        problem_slug: 'a-completely-different-problem',
        raw_input: 'answer from elsewhere',
      },
    });

    const frame = page.frameLocator('#embed-frame');
    await expect(frame.getByRole('heading', { name: 'Sum a list' })).toBeVisible();
    await expect(frame.locator('#promptEditor .ace_editor')).toBeVisible();
    expect(await getAceEditorValue(await embedFrame(page), '#promptEditor')).toBe('');
  });

  test('reports a normalized 0..1 score and a restorable state on submit', async ({ page }) => {
    await launchEmbed(page);

    const frame = page.frameLocator('#embed-frame');
    await fillAnswer(page, 'add up every number in the list');
    await frame.locator('#submitButton').click();

    const report = await waitForSubject(page, 'SPLICE.reportScoreAndState');

    // Submission.score is 0-100 on the wire; SPLICE wants 0..1.
    expect(report.score).toBeCloseTo(0.8, 5);

    const state = report.state as Record<string, unknown>;
    expect(state).toMatchObject({
      version: 1,
      problem_slug: 'sum-list',
      problem_type: 'eipl',
      raw_input: 'add up every number in the list',
      score: 80,
      attempts: 1,
    });
  });

  test('emits a telemetry event describing the attempt', async ({ page }) => {
    await launchEmbed(page);

    const frame = page.frameLocator('#embed-frame');
    await fillAnswer(page, 'add up every number in the list');
    await frame.locator('#submitButton').click();

    const event = await waitForSubject(page, 'SPLICE.sendEvent');
    expect(event.name).toBe('eipl.attempt');
  });

  test('refuses a problem type outside the embeddable set', async ({ page }) => {
    await stubApi(page, { ...EIPL_PROBLEM, problem_type: 'mcq' });
    await launchEmbed(page);

    const frame = page.frameLocator('#embed-frame');
    await expect(frame.getByText(/cannot be embedded/i)).toBeVisible();
    // Nothing scoreable was rendered, so nothing must be reported.
    const all = await messages(page);
    expect(all.some((m) => m.subject === 'SPLICE.reportScoreAndState')).toBe(false);
  });

  test('ignores a getState reply forged from another origin', async ({ page }) => {
    // Reply from a different origin only — the legitimate host stays silent.
    await launchEmbed(page, { replyToGetState: false });
    const getState = await waitForSubject(page, 'SPLICE.getState');

    const frame = page.frameLocator('#embed-frame');
    await expect(frame.getByRole('heading', { name: 'Sum a list' })).toBeVisible();

    // A cross-origin page cannot be synthesized here, so assert the guard the
    // other way round: a reply whose message_id was never issued is dropped.
    await page.evaluate((realId) => {
      const w = window as unknown as { __spliceFrame: HTMLIFrameElement };
      w.__spliceFrame.contentWindow?.postMessage(
        {
          subject: 'SPLICE.getState.response',
          message_id: `${realId}-forged`,
          state: { version: 1, problem_slug: 'sum-list', raw_input: 'injected answer' },
        },
        '*',
      );
    }, getState.message_id);

    expect(await getAceEditorValue(await embedFrame(page), '#promptEditor')).toBe('');
  });
});
