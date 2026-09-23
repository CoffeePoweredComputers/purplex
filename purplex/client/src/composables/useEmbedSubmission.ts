/**
 * Embed submit -> SSE -> completion orchestration (F3, #145).
 *
 * A local re-implementation of the flow that lives inline in ProblemSet.vue
 * (~1359-1404). It is re-implemented rather than imported because the
 * ProblemSet version is entangled with routing, Vuex progress, the submission
 * cache, hint tracking and toast notifications — none of which exist in the
 * chromeless embed. What is preserved is the parts that matter for correctness:
 * the sync-vs-async branch, the SSE connect/disconnect lifecycle, and the
 * per-type result mapping (delegated to the adapters).
 *
 * Reporting to the SPLICE host is left to the caller via the `onCompleted` /
 * `onTelemetry` hooks, which keeps this composable free of postMessage concerns
 * and testable without a host.
 */
import { onUnmounted, type Ref, ref } from 'vue'
import { sseService } from '@/services/sseService'
import {
  isSyncResponse,
  submissionService,
  type SyncSubmissionResponse,
} from '@/services/submissionService'
import type { ActivityProblem } from '@/components/activities/types'
import type { UnifiedSubmissionResult } from '@/types'
import {
  buildEmbedState,
  type EmbedFeedbackProps,
  type EmbedState,
  type EmbedTelemetry,
  getEmbedAdapter,
} from '@/embed/adapters'
import { log } from '@/utils/logger'
import { i18n } from '@/i18n'

const logger = log.createComponentLogger('useEmbedSubmission')

const EMPTY_FEEDBACK: EmbedFeedbackProps = {
  codeResults: [],
  testResults: [],
  promptCorrectness: 0,
  comprehensionResults: '',
  userPrompt: '',
  segmentationData: null,
}

export interface UseEmbedSubmissionOptions {
  /** The problem being attempted. Null until it has loaded. */
  problem: Ref<ActivityProblem | null>
  /**
   * Problem set the launch belongs to, from the `problem_set` launch param.
   *
   * Submission.problem_set is a non-null FK (submissions/models.py), so the
   * submit endpoint cannot record a bare single-problem attempt — it fails at
   * the database with a not-null violation. The host therefore has to say which
   * assignment it is launching. B1-B5 should resolve this from the LTI context
   * rather than a query param; until then it rides the launch URL.
   */
  problemSetSlug?: string | null
  /** Called once a submission completes, with the state payload for the host. */
  onCompleted?: (result: UnifiedSubmissionResult, state: EmbedState) => void
  /** Called with the adapter's telemetry event for the attempt. */
  onTelemetry?: (event: EmbedTelemetry) => void
  /** Called when a submission fails, for host-side error telemetry. */
  onFailed?: (message: string) => void
}

export function useEmbedSubmission(options: UseEmbedSubmissionOptions) {
  const { problem } = options

  const submitting = ref(false)
  const error = ref('')
  const attempts = ref(0)
  const feedback = ref<EmbedFeedbackProps>({ ...EMPTY_FEEDBACK })
  const hasResult = ref(false)

  // Held so an in-flight stream can be torn down on unmount or on resubmit.
  let disconnectSse: (() => void) | null = null

  function closeStream(): void {
    if (disconnectSse) {
      disconnectSse()
      disconnectSse = null
    }
  }

  function fail(message: string): void {
    error.value = message
    submitting.value = false
    closeStream()
    options.onFailed?.(message)
  }

  /**
   * Shared completion path for both the sync and async branches: map the result
   * for display, build the host state payload, and hand both to the caller.
   */
  function handleResult(result: UnifiedSubmissionResult, rawInput: string): void {
    const current = problem.value
    if (!current) {
      return
    }

    const adapter = getEmbedAdapter(current.problem_type)
    if (!adapter) {
      fail(i18n.global.t('embed.error.unsupportedType', { type: current.problem_type }))
      return
    }

    attempts.value += 1
    feedback.value = adapter.mapFeedback(result, current, rawInput)
    hasResult.value = true
    submitting.value = false
    closeStream()

    const state = buildEmbedState({
      result,
      problem: current,
      rawInput,
      attempts: attempts.value,
    })

    logger.info('Embed submission completed', {
      problemSlug: current.slug,
      score: result.score,
      completionStatus: result.completion_status,
    })

    options.onTelemetry?.(adapter.telemetry(result, current))
    options.onCompleted?.(result, state)
  }

  /**
   * Normalize a synchronous submission response into the unified shape the
   * async path already produces, so completion handling has a single body.
   */
  function normalizeSyncResponse(
    response: SyncSubmissionResponse,
    rawInput: string,
  ): UnifiedSubmissionResult {
    return {
      submission_id: response.submission_id,
      problem_type: response.problem_type,
      score: response.score,
      is_correct: response.is_correct,
      completion_status: response.completion_status,
      problem_slug: response.problem_slug,
      user_input: response.user_input ?? rawInput,
      result: response.result,
      selected_option: response.selected_option,
      correct_option: response.correct_option,
    } as unknown as UnifiedSubmissionResult
  }

  async function submit(rawInput: string): Promise<void> {
    const current = problem.value
    if (!current || submitting.value) {
      return
    }

    // A resubmit while a previous stream is still open would otherwise leak it.
    closeStream()
    submitting.value = true
    error.value = ''

    try {
      const response = await submissionService.submitActivity({
        problem_slug: current.slug,
        raw_input: rawInput,
        ...(options.problemSetSlug ? { problem_set_slug: options.problemSetSlug } : {}),
      })

      // Sync path: some activity types return a scored result inline, with no
      // task to stream. None of the four embeddable types do today, but the
      // endpoint is shared, so the branch is handled rather than assumed away.
      if (isSyncResponse(response)) {
        handleResult(normalizeSyncResponse(response, rawInput), rawInput)
        return
      }

      if (!response.task_id) {
        fail(i18n.global.t('embed.error.noTaskId'))
        return
      }

      logger.info('Async submission accepted, connecting to SSE stream', {
        taskId: response.task_id,
      })

      disconnectSse = await sseService.connectToSubmission(
        response.task_id,
        (unifiedResult) => handleResult(unifiedResult, rawInput),
        {
          onError: (payload) => {
            logger.error('SSE reported a submission error', payload)
            fail(payload.error)
          },
          onTimeout: () => fail(i18n.global.t('embed.error.timeout')),
        },
      )
    } catch (err) {
      logger.error('Embed submission failed', err)
      fail(err instanceof Error ? err.message : String(err))
    }
  }

  onUnmounted(closeStream)

  return {
    submitting,
    error,
    attempts,
    feedback,
    hasResult,
    submit,
  }
}
