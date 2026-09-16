/**
 * Stub backend for the SPLICE embed demo. Zero dependencies — plain Node http.
 *
 * WHY THIS EXISTS
 * ---------------
 * The embed's frontend track (F1-F5, X1) is complete; the backend track that
 * would serve it (B1-B5: LTI launch, embed auth, embed-scoped problem and
 * submit endpoints, embed SSE tokens) has not landed. The real Django stack
 * therefore cannot authenticate an embed launch yet, so it cannot drive this
 * demo.
 *
 * This server stands in for exactly the endpoints the embed calls, on the port
 * Vite already proxies /api to (8000). Everything in front of it — the SPLICE
 * bridge, submit -> SSE orchestration, the per-type adapters, the input and
 * feedback components — is the real production code, unmodified.
 *
 * What is faked: problem storage, the LLM round-trip, Docker execution, and
 * scoring. Scores are keyword-derived so they respond to what is typed during
 * the demo rather than being a fixed constant.
 *
 * Usage:  node demo/embed/stub-api.js  [--port 8000]
 */
'use strict';

const http = require('http');
const { PROBLEMS } = require('./problems');

const PORT = (() => {
  const i = process.argv.indexOf('--port');
  return i !== -1 ? Number(process.argv[i + 1]) : 8000;
})();

// How long the fake "LLM + Docker" stage runs, so the demo actually shows the
// streaming path rather than completing before the spinner paints.
const WORK_MS = 2600;

/** task_id -> everything needed to build the result when the stream opens. */
const tasks = new Map();
/** problem slug -> probe attempts, so the probe panel's counter behaves. */
const probeHistories = new Map();

let counter = 0;
const nextId = (prefix) => `${prefix}-${Date.now()}-${++counter}`;

// ===== HTTP HELPERS =====

/**
 * CORS headers for a credentialed cross-origin caller.
 *
 * The embed is served from Vite (:5173) but talks to the API origin directly
 * rather than through the Vite proxy (embed-main.ts sets axios.defaults.baseURL
 * from VITE_API_URL), and it sends `withCredentials` plus an Authorization
 * header. That combination forbids wildcards: the origin must be echoed back
 * exactly, and the allowed headers listed by name.
 */
function cors(req) {
  return {
    'Access-Control-Allow-Origin': req.headers.origin ?? 'http://localhost:5173',
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Headers':
      req.headers['access-control-request-headers'] ?? 'Authorization,Content-Type',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    Vary: 'Origin',
  };
}

function sendJson(req, res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    ...cors(req),
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
    'Cache-Control': 'no-store',
  });
  res.end(payload);
}

function readJson(req) {
  return new Promise((resolve) => {
    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
    });
    req.on('end', () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch {
        resolve({});
      }
    });
  });
}

/** Strip server-only fields before handing a problem to the client. */
function publicProblem(problem) {
  const { oracle: _oracle, keywords: _keywords, tests: _tests, ...rest } = problem;
  return rest;
}

// ===== STUB GRADER =====

/**
 * Score an answer by how many of the problem's keywords it mentions.
 *
 * Crude on purpose: it is not modelling the real LLM grader, only making the
 * demo responsive — a thorough answer scores well, a lazy one does not, and
 * the difference is visible in the host's score log.
 */
function grade(problem, rawInput) {
  const keywords = problem.keywords ?? [];
  if (keywords.length === 0) {
    return { ratio: 0, matched: [] };
  }

  const haystack = String(rawInput ?? '').toLowerCase();
  const matched = keywords.filter((k) => haystack.includes(k.toLowerCase()));
  return { ratio: matched.length / keywords.length, matched };
}

/**
 * Build one variation's test block in the nested shape Feedback.vue reads:
 * a per-variation tally wrapping the individual test cases.
 */
function buildTestBlock(problem, ratio) {
  const cases = problem.tests ?? [];
  const passCount = Math.round(ratio * cases.length);

  const results = cases.map((testCase, index) => {
    const passed = index < passCount;
    return {
      function_call: testCase.function_call,
      expected_output: testCase.expected_output,
      actual_output: passed ? testCase.expected_output : 'None',
      isSuccessful: passed,
      error: passed ? undefined : 'AssertionError: output did not match',
    };
  });

  return {
    success: passCount === cases.length && cases.length > 0,
    testsPassed: passCount,
    totalTests: cases.length,
    test_results: results,
  };
}

/** Comprehension analysis, mirroring the EiPL segmentation payload's shape. */
function buildSegmentation(problem, rawInput, ratio) {
  const sentences = String(rawInput ?? '')
    .split(/[.\n]+/)
    .map((s) => s.trim())
    .filter(Boolean);

  return {
    segments: sentences.map((text, index) => ({
      id: index + 1,
      text,
      code_lines: [index + 1],
    })),
    segment_count: sentences.length,
    comprehension_level: ratio >= 0.75 ? 'relational' : 'multi_structural',
    passed: ratio >= 0.75,
    threshold: 0.75,
    confidence_score: Number(ratio.toFixed(2)),
    feedback_message:
      ratio >= 0.75
        ? 'Your explanation describes the algorithm as a whole, not just isolated steps.'
        : 'Your explanation lists steps but does not connect them into one idea.',
    suggested_improvements:
      ratio >= 0.75 ? [] : ['Say what the accumulated value means once the loop ends.'],
  };
}

/**
 * Assemble the UnifiedSubmissionResult the SSE `completed` event carries.
 *
 * The `result` body differs by type exactly as the real handlers' does —
 * variations + test_results + segmentation for the LLM-backed types, a single
 * student_code for probeable_code — because the adapters are written against
 * that difference.
 */
function buildResult(problem, rawInput, submissionId) {
  const { ratio } = grade(problem, rawInput);
  const score = Math.round(ratio * 100);

  const base = {
    submission_id: submissionId,
    problem_type: problem.problem_type,
    problem_slug: problem.slug,
    score,
    is_correct: ratio === 1,
    completion_status: ratio === 1 ? 'completed' : ratio > 0 ? 'partial' : 'attempted',
    user_input: rawInput,
  };

  if (problem.problem_type === 'probeable_code') {
    return {
      ...base,
      result: {
        student_code: rawInput,
        test_results: [buildTestBlock(problem, ratio)],
      },
    };
  }

  // LLM-backed types: three regenerated variations, the later ones weaker, so
  // the "perfect variations" notch count is visibly less than the total.
  const variationRatios = [ratio, Math.max(0, ratio - 0.25), Math.max(0, ratio - 0.5)];

  return {
    ...base,
    result: {
      variations: variationRatios.map((r, i) => ({
        code:
          '# variation ' + (i + 1) + " — generated from the learner's submission\n" +
          (r >= 0.99
            ? problem.reference_solution
            : problem.function_signature +
              '\n    # incomplete: the submission left this ambiguous\n    return None'),
      })),
      test_results: variationRatios.map((r) => buildTestBlock(problem, r)),
      segmentation: problem.feedback_config?.show_segmentation
        ? buildSegmentation(problem, rawInput, ratio)
        : null,
    },
  };
}

// ===== ROUTES =====

function probeStatusFor(slug) {
  return {
    mode: 'explore',
    remaining: null,
    used: (probeHistories.get(slug) ?? []).length,
    can_probe: true,
    message: 'Explore mode — probe as often as you like.',
  };
}

async function handleProbe(req, res, problem) {
  const body = await readJson(req);
  const input = body.input ?? {};

  if (typeof problem.oracle !== 'function') {
    return sendJson(req, res, 400, { success: false, error: 'This problem has no oracle.' });
  }

  let result;
  try {
    result = problem.oracle(input);
  } catch (err) {
    return sendJson(req, res, 200, { success: false, error: String(err) });
  }

  const history = probeHistories.get(problem.slug) ?? [];
  history.unshift({ input, output: result, timestamp: new Date().toISOString() });
  probeHistories.set(problem.slug, history);

  sendJson(req, res, 200, {
    success: true,
    result,
    probe_status: probeStatusFor(problem.slug),
  });
}

async function handleSubmit(req, res) {
  const body = await readJson(req);
  const problem = PROBLEMS[body.problem_slug];

  if (!problem) {
    return sendJson(req, res, 404, { error: 'Unknown problem: ' + body.problem_slug });
  }

  // Every embeddable type takes the async path in the real backend, so the
  // demo always exercises submit -> SSE rather than the sync shortcut.
  const taskId = nextId('task');
  tasks.set(taskId, { problem, rawInput: body.raw_input ?? '' });

  console.log('  submit  ' + problem.slug + ' -> task ' + taskId);
  sendJson(req, res, 202, {
    status: 'processing',
    task_id: taskId,
    problem_type: problem.problem_type,
  });
}

/**
 * Stream a task to completion, in the event shape sseService.ts listens for:
 * `connected`, then `update` progress ticks, then `completed` carrying the
 * UnifiedSubmissionResult.
 */
function handleStream(req, res, taskId) {
  const task = tasks.get(taskId);

  res.writeHead(200, {
    ...cors(req),
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  const send = (event, data) => {
    res.write('event: ' + event + '\ndata: ' + JSON.stringify(data) + '\n\n');
  };

  send('connected', { task_id: taskId });

  if (!task) {
    send('failed', { error: 'Unknown task: ' + taskId });
    return res.end();
  }

  const stages = [
    [0.25, 'Generating code from your submission...'],
    [0.6, 'Running the generated code against the test suite...'],
    [0.85, 'Analysing your explanation...'],
  ];

  const timers = stages.map(([progress, message], i) =>
    setTimeout(
      () => send('update', { progress, message }),
      (WORK_MS / (stages.length + 1)) * (i + 1),
    ),
  );

  const finish = setTimeout(() => {
    const result = buildResult(task.problem, task.rawInput, nextId('sub'));
    console.log('  stream  ' + taskId + ' completed, score=' + result.score);
    send('completed', { result });
    tasks.delete(taskId);
    res.end();
  }, WORK_MS);

  req.on('close', () => {
    timers.forEach(clearTimeout);
    clearTimeout(finish);
  });
}

// ===== SERVER =====

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost:' + PORT);
  const path = url.pathname;
  console.log(req.method + ' ' + path);

  // The embed reaches this through the Vite proxy (same origin), but a demo
  // driven from a standalone host page may not, so answer preflights anyway.
  if (req.method === 'OPTIONS') {
    res.writeHead(204, cors(req));
    return res.end();
  }

  // The embed mints an SSE token before opening the stream (embedService.ts).
  // B5 will make this a real embed-scoped endpoint; the wire shape is fixed.
  if (path === '/api/auth/sse-token/' && req.method === 'POST') {
    return sendJson(req, res, 200, { sse_token: nextId('sse') });
  }

  if (path === '/api/submit/' && req.method === 'POST') {
    return handleSubmit(req, res);
  }

  const streamMatch = path.match(/^\/api\/tasks\/([^/]+)\/stream\/$/);
  if (streamMatch) {
    return handleStream(req, res, streamMatch[1]);
  }

  const probeMatch = path.match(/^\/api\/problems\/([^/]+)\/probe\/(status|history)?\/?$/);
  if (probeMatch) {
    const problem = PROBLEMS[probeMatch[1]];
    if (!problem) {
      return sendJson(req, res, 404, { error: 'Unknown problem' });
    }
    if (probeMatch[2] === 'status') {
      return sendJson(req, res, 200, probeStatusFor(problem.slug));
    }
    if (probeMatch[2] === 'history') {
      return sendJson(req, res, 200, {
        history: probeHistories.get(problem.slug) ?? [],
        probe_status: probeStatusFor(problem.slug),
      });
    }
    return handleProbe(req, res, problem);
  }

  const problemMatch = path.match(/^\/api\/problems\/([^/]+)\/$/);
  if (problemMatch) {
    const problem = PROBLEMS[problemMatch[1]];
    if (!problem) {
      return sendJson(req, res, 404, { error: 'Unknown problem: ' + problemMatch[1] });
    }
    return sendJson(req, res, 200, publicProblem(problem));
  }

  sendJson(req, res, 404, { error: 'No stub route for ' + path });
});

server.listen(PORT, () => {
  console.log('\nSPLICE embed demo — stub backend on http://localhost:' + PORT);
  console.log('Serving these demo problems:\n');
  for (const problem of Object.values(PROBLEMS)) {
    console.log('  ' + problem.slug.padEnd(30) + problem.problem_type);
  }
  console.log('\nOpen the mock host: http://localhost:5173/embed-mockhost.html\n');
});
