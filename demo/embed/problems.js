/**
 * Demo fixtures for the SPLICE embed walkthrough.
 *
 * One problem per embeddable type, so the demo covers every adapter in
 * purplex/client/src/embed/adapters.ts, plus one deliberately unsupported
 * type to show the embed refusing it rather than rendering an input that
 * could never report a score.
 *
 * `keywords` drives the stub grader (see grade() in stub-api.js) so scores
 * respond to what is actually typed during the demo instead of being fixed.
 */

const EIPL = {
  slug: 'demo-eipl-sum-list',
  title: 'Explain: sum a list',
  description:
    'Explain, in plain language, how to add up every number in a list.\n\n' +
    'An LLM will write code from your explanation, and that code is run against ' +
    'the hidden tests. You are graded on whether your explanation was clear ' +
    'enough to reproduce the program.',
  problem_type: 'eipl',
  function_name: 'sum_list',
  function_signature: 'def sum_list(numbers):',
  reference_solution: 'def sum_list(numbers):\n    total = 0\n    for n in numbers:\n        total += n\n    return total',
  input_config: {},
  display_config: {},
  feedback_config: { show_segmentation: true },
  keywords: ['total', 'each', 'add', 'return'],
  tests: [
    { function_call: 'sum_list([1, 2, 3])', expected_output: 6 },
    { function_call: 'sum_list([])', expected_output: 0 },
    { function_call: 'sum_list([-4, 4])', expected_output: 0 },
    { function_call: 'sum_list([10])', expected_output: 10 },
  ],
};

const PROMPT = {
  slug: 'demo-prompt-word-count',
  title: 'Prompt: count the words',
  description:
    'Write a prompt that makes an LLM produce a function counting the words in a ' +
    'string.\n\nYour prompt is the submission — the generated code is what gets tested.',
  problem_type: 'prompt',
  function_name: 'count_words',
  function_signature: 'def count_words(text):',
  reference_solution: 'def count_words(text):\n    return len(text.split())',
  input_config: {},
  display_config: {},
  feedback_config: { show_segmentation: false },
  keywords: ['function', 'split', 'count', 'string'],
  tests: [
    { function_call: "count_words('hello world')", expected_output: 2 },
    { function_call: "count_words('')", expected_output: 0 },
    { function_call: "count_words('a  b   c')", expected_output: 3 },
  ],
};

const PROBEABLE_CODE = {
  slug: 'demo-probeable-code-divide',
  title: 'Probe then implement: safe divide',
  description:
    'A hidden function is behind the probe panel. Call it with inputs of your ' +
    'choosing to work out what it does — including how it handles division by ' +
    'zero — then implement it yourself.',
  problem_type: 'probeable_code',
  function_name: 'safe_divide',
  function_signature: 'def safe_divide(a, b):',
  reference_solution: 'def safe_divide(a, b):\n    if b == 0:\n        return None\n    return a / b',
  input_config: {},
  display_config: {},
  feedback_config: {},
  probe_config: {
    function_name: 'safe_divide',
    function_signature: 'def safe_divide(a: int, b: int):',
    parameters: [
      { name: 'a', type: 'int' },
      { name: 'b', type: 'int' },
    ],
  },
  keywords: ['def', 'return', 'if', '0'],
  tests: [
    { function_call: 'safe_divide(10, 2)', expected_output: 5 },
    { function_call: 'safe_divide(7, 0)', expected_output: null },
    { function_call: 'safe_divide(-9, 3)', expected_output: -3 },
  ],
  // The hidden oracle the probe panel calls.
  oracle: ({ a, b }) => (Number(b) === 0 ? null : Number(a) / Number(b)),
};

const PROBEABLE_SPEC = {
  slug: 'demo-probeable-spec-clamp',
  title: 'Probe then specify: clamp',
  description:
    'Probe the hidden function until you understand it, then write a written ' +
    'specification precise enough that an LLM can implement it from your words alone.',
  problem_type: 'probeable_spec',
  function_name: 'clamp',
  function_signature: 'def clamp(value, low, high):',
  reference_solution: 'def clamp(value, low, high):\n    return max(low, min(value, high))',
  input_config: {},
  display_config: {},
  feedback_config: { show_segmentation: true },
  probe_config: {
    function_name: 'clamp',
    function_signature: 'def clamp(value: int, low: int, high: int):',
    parameters: [
      { name: 'value', type: 'int' },
      { name: 'low', type: 'int' },
      { name: 'high', type: 'int' },
    ],
  },
  keywords: ['low', 'high', 'between', 'return'],
  tests: [
    { function_call: 'clamp(5, 1, 10)', expected_output: 5 },
    { function_call: 'clamp(-3, 0, 10)', expected_output: 0 },
    { function_call: 'clamp(42, 0, 10)', expected_output: 10 },
  ],
  oracle: ({ value, low, high }) =>
    Math.max(Number(low), Math.min(Number(value), Number(high))),
};

/** Not in the embed's supported set — used to demo the refusal path. */
const UNSUPPORTED = {
  slug: 'demo-mcq-unsupported',
  title: 'Multiple choice (not embeddable)',
  description: 'Exists only to show the embed refusing a type it has no adapter for.',
  problem_type: 'mcq',
  input_config: {},
  display_config: {},
  feedback_config: {},
  keywords: [],
  tests: [],
};

const PROBLEMS = {};
for (const p of [EIPL, PROMPT, PROBEABLE_CODE, PROBEABLE_SPEC, UNSUPPORTED]) {
  PROBLEMS[p.slug] = p;
}

module.exports = { PROBLEMS };
