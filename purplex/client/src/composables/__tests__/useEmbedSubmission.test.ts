import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type App, createApp, defineComponent, nextTick, ref } from 'vue'
import { testI18n } from '@/test/setup'
import type { ActivityProblem } from '@/components/activities/types'
import type { UnifiedSubmissionResult } from '@/types'

const submitActivity = vi.fn()
const connectToSubmission = vi.fn()

vi.mock('@/services/submissionService', async () => {
  const actual = await vi.importActual<typeof import('@/services/submissionService')>(
    '@/services/submissionService',
  )
  return {
    ...actual,
    submissionService: { submitActivity },
  }
})

vi.mock('@/services/sseService', () => ({
  sseService: { connectToSubmission },
}))

const { useEmbedSubmission } = await import('../useEmbedSubmission')

let activeApps: App[] = []

function mount<T>(composable: () => T): T {
  let result!: T
  const app = createApp(defineComponent({
    setup() {
      result = composable()
      return () => null
    },
  }))
  app.use(testI18n)
  app.mount(document.createElement('div'))
  activeApps.push(app)
  return result
}

const problem = {
  slug: 'sum-list',
  title: 'Sum a list',
  description: '',
  problem_type: 'eipl',
  function_name: 'sum_list',
  function_signature: 'def sum_list(xs):',
  reference_solution: 'return sum(xs)',
} as ActivityProblem

const COMPLETED_RESULT = {
  submission_id: 'sub-1',
  problem_type: 'eipl',
  score: 80,
  is_correct: false,
  completion_status: 'partial',
  problem_slug: 'sum-list',
  user_input: 'add up the numbers',
  result: {
    variations: [{ code: 'a' }],
    test_results: [{ success: true, testsPassed: 4, totalTests: 5 }],
    segmentation: null,
  },
} as unknown as UnifiedSubmissionResult

/** Async submissions accepted; the caller then opens an SSE stream. */
function acceptAsync(taskId = 'task-1') {
  submitActivity.mockResolvedValue({
    status: 'processing',
    task_id: taskId,
    request_id: taskId,
    problem_type: 'eipl',
    stream_url: `/api/tasks/${taskId}/stream/`,
    message: 'queued',
  })
}

/** Capture the SSE callbacks so tests can drive completion/error by hand. */
function captureStream() {
  const captured: {
    onSuccess?: (r: UnifiedSubmissionResult) => void
    options?: { onError?: (p: { error: string }) => void; onTimeout?: () => void }
    disconnect: ReturnType<typeof vi.fn>
  } = { disconnect: vi.fn() }

  connectToSubmission.mockImplementation((_taskId, onSuccess, options) => {
    captured.onSuccess = onSuccess
    captured.options = options
    return Promise.resolve(captured.disconnect)
  })

  return captured
}

function setup(overrides: Record<string, unknown> = {}) {
  const onCompleted = vi.fn()
  const onTelemetry = vi.fn()
  const onFailed = vi.fn()
  const composable = mount(() =>
    useEmbedSubmission({
      problem: ref(problem),
      onCompleted,
      onTelemetry,
      onFailed,
      ...overrides,
    }),
  )
  return { ...composable, onCompleted, onTelemetry, onFailed }
}

describe('useEmbedSubmission', () => {
  beforeEach(() => {
    submitActivity.mockReset()
    connectToSubmission.mockReset()
  })

  afterEach(() => {
    activeApps.forEach((app) => app.unmount())
    activeApps = []
  })

  it('submits the raw input against the loaded problem', async () => {
    acceptAsync()
    captureStream()
    const { submit } = setup()

    await submit('add up the numbers')

    expect(submitActivity).toHaveBeenCalledWith({
      problem_slug: 'sum-list',
      raw_input: 'add up the numbers',
    })
  })

  // Submission.problem_set is a non-null FK, so a launch that knows its problem
  // set has to pass it through or the submit fails at the database.
  it('forwards the launch problem set when the host supplied one', async () => {
    acceptAsync()
    captureStream()
    const { submit } = setup({ problemSetSlug: 'demo-problems' })

    await submit('add up the numbers')

    expect(submitActivity).toHaveBeenCalledWith({
      problem_slug: 'sum-list',
      raw_input: 'add up the numbers',
      problem_set_slug: 'demo-problems',
    })
  })

  it('omits the problem set key entirely when the launch did not name one', async () => {
    acceptAsync()
    captureStream()
    const { submit } = setup({ problemSetSlug: null })

    await submit('add up the numbers')

    expect(submitActivity).toHaveBeenCalledWith({
      problem_slug: 'sum-list',
      raw_input: 'add up the numbers',
    })
  })

  it('opens an SSE stream for an async submission and stays pending until it completes', async () => {
    acceptAsync('task-42')
    const stream = captureStream()
    const { submit, submitting, hasResult } = setup()

    await submit('answer')

    expect(connectToSubmission).toHaveBeenCalledWith('task-42', expect.any(Function), expect.any(Object))
    expect(submitting.value).toBe(true)
    expect(hasResult.value).toBe(false)

    stream.onSuccess!(COMPLETED_RESULT)
    await nextTick()

    expect(submitting.value).toBe(false)
    expect(hasResult.value).toBe(true)
  })

  it('reports the raw 0-100 score and a state payload to the caller on completion', async () => {
    acceptAsync()
    const stream = captureStream()
    const { submit, onCompleted } = setup()

    await submit('answer')
    stream.onSuccess!(COMPLETED_RESULT)

    expect(onCompleted).toHaveBeenCalledTimes(1)
    const [result, state] = onCompleted.mock.calls[0]
    // Normalizing to SPLICE's 0..1 is the bridge's job, not this composable's.
    expect(result.score).toBe(80)
    expect(state).toMatchObject({
      problem_slug: 'sum-list',
      problem_type: 'eipl',
      raw_input: 'add up the numbers',
      score: 80,
      attempts: 1,
    })
  })

  it('emits the adapter telemetry event for the attempt', async () => {
    acceptAsync()
    const stream = captureStream()
    const { submit, onTelemetry } = setup()

    await submit('answer')
    stream.onSuccess!(COMPLETED_RESULT)

    expect(onTelemetry).toHaveBeenCalledWith({
      name: 'eipl.attempt',
      data: expect.objectContaining({ variations_total: 1, variations_passed: 1 }),
    })
  })

  it('maps the result through the per-type adapter for display', async () => {
    acceptAsync()
    const stream = captureStream()
    const { submit, feedback } = setup()

    await submit('answer')
    stream.onSuccess!(COMPLETED_RESULT)

    expect(feedback.value.codeResults).toEqual(['a'])
    expect(feedback.value.userPrompt).toBe('add up the numbers')
  })

  it('completes without a stream when the endpoint returns a sync result', async () => {
    submitActivity.mockResolvedValue({
      status: 'complete',
      submission_id: 'sub-sync',
      problem_type: 'eipl',
      score: 100,
      is_correct: true,
      completion_status: 'complete',
      problem_slug: 'sum-list',
      user_input: 'answer',
      result: { variations: [], test_results: [], segmentation: null },
    })
    const { submit, onCompleted, submitting, hasResult } = setup()

    await submit('answer')

    expect(connectToSubmission).not.toHaveBeenCalled()
    expect(submitting.value).toBe(false)
    expect(hasResult.value).toBe(true)
    expect(onCompleted.mock.calls[0][1]).toMatchObject({ score: 100, attempts: 1 })
  })

  it('surfaces an SSE error and clears the pending state', async () => {
    acceptAsync()
    const stream = captureStream()
    const { submit, submitting, error, onFailed } = setup()

    await submit('answer')
    stream.options!.onError!({ error: 'Execution failed' })

    expect(error.value).toBe('Execution failed')
    expect(submitting.value).toBe(false)
    expect(onFailed).toHaveBeenCalledWith('Execution failed')
    expect(stream.disconnect).toHaveBeenCalled()
  })

  it('surfaces an SSE timeout as a failure', async () => {
    acceptAsync()
    const stream = captureStream()
    const { submit, error, onFailed } = setup()

    await submit('answer')
    stream.options!.onTimeout!()

    expect(error.value).toMatch(/timed out/i)
    expect(onFailed).toHaveBeenCalled()
  })

  it('fails cleanly when the submit call itself rejects', async () => {
    submitActivity.mockRejectedValue(new Error('Network down'))
    const { submit, error, submitting, onFailed } = setup()

    await submit('answer')

    expect(error.value).toBe('Network down')
    expect(submitting.value).toBe(false)
    expect(onFailed).toHaveBeenCalledWith('Network down')
  })

  it('fails when an async response carries no task id', async () => {
    submitActivity.mockResolvedValue({ status: 'processing', task_id: '' })
    const { submit, error } = setup()

    await submit('answer')

    expect(error.value).toMatch(/task id/i)
    expect(connectToSubmission).not.toHaveBeenCalled()
  })

  it('ignores a submit while one is already in flight', async () => {
    acceptAsync()
    captureStream()
    const { submit } = setup()

    await submit('first')
    await submit('second')

    expect(submitActivity).toHaveBeenCalledTimes(1)
  })

  it('tears down the previous stream when resubmitting', async () => {
    acceptAsync()
    const stream = captureStream()
    const { submit } = setup()

    await submit('first')
    stream.onSuccess!(COMPLETED_RESULT)
    expect(stream.disconnect).toHaveBeenCalledTimes(1)

    await submit('second')
    stream.onSuccess!(COMPLETED_RESULT)

    expect(stream.disconnect).toHaveBeenCalledTimes(2)
  })

  it('counts attempts across submissions', async () => {
    acceptAsync()
    const stream = captureStream()
    const { submit, onCompleted } = setup()

    await submit('first')
    stream.onSuccess!(COMPLETED_RESULT)
    await submit('second')
    stream.onSuccess!(COMPLETED_RESULT)

    expect(onCompleted.mock.calls[1][1]).toMatchObject({ attempts: 2 })
  })

  it('disconnects an in-flight stream on unmount', async () => {
    acceptAsync()
    const stream = captureStream()
    const { submit } = setup()

    await submit('answer')
    expect(stream.disconnect).not.toHaveBeenCalled()

    activeApps.forEach((app) => app.unmount())
    activeApps = []

    expect(stream.disconnect).toHaveBeenCalled()
  })

  it('refuses a problem type with no adapter rather than reporting a bogus score', async () => {
    acceptAsync()
    const stream = captureStream()
    const { submit, error, onCompleted } = setup({
      problem: ref({ ...problem, problem_type: 'mcq' } as ActivityProblem),
    })

    await submit('answer')
    stream.onSuccess!({ ...COMPLETED_RESULT, problem_type: 'mcq' } as UnifiedSubmissionResult)

    expect(error.value).toMatch(/unsupported/i)
    expect(onCompleted).not.toHaveBeenCalled()
  })

  it('does nothing when no problem has loaded', async () => {
    const { submit } = setup({ problem: ref(null) })

    await submit('answer')

    expect(submitActivity).not.toHaveBeenCalled()
  })
})
