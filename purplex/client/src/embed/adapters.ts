/**
 * Per-type embed adapters (F4 #146 / F5 #147).
 *
 * The SPLICE bridge and the submit->SSE orchestration are problem-type-agnostic.
 * Everything that *is* type-specific lives here: the extra detail stashed in the
 * SPLICE state payload, the telemetry event describing an attempt, and the
 * mapping from a UnifiedSubmissionResult onto FeedbackSelector's props.
 *
 * The feedback mappings deliberately mirror the per-type branches in
 * ProblemSet.vue (~1410-1660) so an embedded problem renders identically to the
 * same problem in the main SPA. Where that code is inconsistent — `codeResults`
 * is a string[] of variation source for the LLM-backed types but a
 * [{ code }] singleton for probeable_code — the inconsistency is reproduced
 * rather than fixed, because the feedback components are written against it.
 */
import type { ActivityProblem } from '@/components/activities/types'
import type { UnifiedSubmissionResult } from '@/types'

/** Bumped whenever the state payload shape changes incompatibly. */
export const EMBED_STATE_VERSION = 1

/**
 * The payload handed to the host via SPLICE.reportScoreAndState and handed back
 * on the next launch via SPLICE.getState.response. Must stay structured-cloneable.
 */
export interface EmbedState {
  version: number
  problem_slug: string
  problem_type: string
  /** Verbatim learner input, so a relaunch can restore the editor. */
  raw_input: string
  /** Raw 0-100 Submission.score. The bridge normalizes to 0..1 separately. */
  score: number | null
  completion_status: string | null
  submission_id: string | null
  attempts: number
  updated_at: string
  /** Type-specific extras from the adapter. */
  details: Record<string, unknown>
}

/** Loosely typed because the shape differs per activity type (see file header). */
export interface EmbedFeedbackProps {
  codeResults: unknown[]
  testResults: unknown[]
  promptCorrectness: number
  comprehensionResults: string
  userPrompt: string
  segmentationData: Record<string, unknown> | null
}

export interface EmbedTelemetry {
  name: string
  data: Record<string, unknown>
}

export interface EmbedAdapter {
  /** Type-specific extras merged into EmbedState.details. */
  buildStateDetails(result: UnifiedSubmissionResult, problem: ActivityProblem): Record<string, unknown>
  /** Map a completed submission onto FeedbackSelector's props. */
  mapFeedback(result: UnifiedSubmissionResult, problem: ActivityProblem, rawInput: string): EmbedFeedbackProps
  /** Telemetry event describing the attempt, sent via SPLICE.sendEvent. */
  telemetry(result: UnifiedSubmissionResult, problem: ActivityProblem): EmbedTelemetry
}

// ===== SHARED HELPERS =====

interface VariationTally {
  testsPassed: number
  testsRun: number
  perfectVariations: number
}

/**
 * Sum test outcomes across variations. Mirrors the tally loops in ProblemSet.vue —
 * `success` marks a variation that passed every test, and drives the notch count.
 */
function tallyVariations(testResults: unknown[]): VariationTally {
  const tally: VariationTally = { testsPassed: 0, testsRun: 0, perfectVariations: 0 }

  for (const entry of testResults ?? []) {
    const r = entry as { testsPassed?: number; totalTests?: number; success?: boolean }
    tally.testsPassed += r.testsPassed ?? 0
    tally.testsRun += r.totalTests ?? 0
    if (r.success) {
      tally.perfectVariations += 1
    }
  }

  return tally
}

/** Percentage of individual test cases passed, 0 when nothing ran. */
function testPassRate(tally: VariationTally): number {
  return tally.testsRun > 0 ? Math.round((tally.testsPassed / tally.testsRun) * 100) : 0
}

/** Narrow the untyped handler payload without scattering casts through the adapters. */
function resultData(result: UnifiedSubmissionResult): Record<string, unknown> {
  return (result.result ?? {}) as unknown as Record<string, unknown>
}

/**
 * Shared body for the three types whose handlers serialize
 * { variations, test_results, segmentation } — eipl, prompt, probeable_spec.
 * Legacy top-level fallbacks match ProblemSet.vue's defensive extraction.
 */
function mapVariationFeedback(
  result: UnifiedSubmissionResult,
  problem: ActivityProblem,
  rawInput: string,
): EmbedFeedbackProps {
  const data = resultData(result)
  const variations = (data.variations as Array<{ code: string }> | undefined)?.map((v) => v.code)
    ?? (result.variations as string[] | undefined)
    ?? []
  const testResults = (data.test_results as unknown[] | undefined)
    ?? (result.test_results as unknown[] | undefined)
    ?? []
  const segmentation = (data.segmentation as Record<string, unknown> | null | undefined)
    ?? (result.segmentation as Record<string, unknown> | null | undefined)
    ?? null

  const tally = tallyVariations(testResults)

  return {
    codeResults: variations,
    testResults,
    // Not a percentage: the progress bar renders perfect variations as notches.
    promptCorrectness: tally.perfectVariations,
    comprehensionResults: '',
    userPrompt: result.user_input ?? rawInput,
    // Only surface segmentation when the handler config says this problem shows it.
    segmentationData: problem.feedback_config?.show_segmentation && segmentation ? segmentation : null,
  }
}

function variationStateDetails(result: UnifiedSubmissionResult): Record<string, unknown> {
  const data = resultData(result)
  const testResults = (data.test_results as unknown[] | undefined) ?? []
  const variations = (data.variations as unknown[] | undefined) ?? []
  const tally = tallyVariations(testResults)

  return {
    variations_total: variations.length,
    variations_passed: tally.perfectVariations,
    tests_passed: tally.testsPassed,
    tests_run: tally.testsRun,
  }
}

/**
 * Segmentation summary for the state payload. Only the verdict is kept —
 * the full segment/code-mapping data is large and belongs in the submission
 * record, not in a postMessage payload under a size cap.
 */
function segmentationStateDetails(result: UnifiedSubmissionResult): Record<string, unknown> {
  const segmentation = resultData(result).segmentation as Record<string, unknown> | null | undefined
  if (!segmentation) {
    return {}
  }

  return {
    segmentation_passed: segmentation.passed ?? null,
    segment_count: segmentation.segment_count ?? null,
    comprehension_level: segmentation.comprehension_level ?? null,
  }
}

// ===== ADAPTERS =====

/**
 * EiPL: learner explains code in plain language, an LLM regenerates code from
 * that explanation, and the regenerated variations are tested. Segmentation
 * (comprehension analysis) gates completion alongside the test score.
 */
const eiplAdapter: EmbedAdapter = {
  buildStateDetails(result) {
    return { ...variationStateDetails(result), ...segmentationStateDetails(result) }
  },
  mapFeedback: mapVariationFeedback,
  telemetry(result) {
    const details = variationStateDetails(result)
    return {
      name: 'eipl.attempt',
      data: {
        ...details,
        ...segmentationStateDetails(result),
        pass_rate: testPassRate(tallyVariations((resultData(result).test_results as unknown[]) ?? [])),
      },
    }
  },
}

/**
 * Prompt: learner writes a natural-language prompt that an LLM turns into code.
 * Same serialized shape as EiPL; segmentation is typically off.
 */
const promptAdapter: EmbedAdapter = {
  buildStateDetails(result) {
    return variationStateDetails(result)
  },
  mapFeedback: mapVariationFeedback,
  telemetry(result) {
    return {
      name: 'prompt.attempt',
      data: {
        ...variationStateDetails(result),
        pass_rate: testPassRate(tallyVariations((resultData(result).test_results as unknown[]) ?? [])),
      },
    }
  },
}

/**
 * Probeable spec: learner probes a hidden oracle, then writes a specification
 * that an LLM implements. Serializes exactly like EiPL.
 */
const probeableSpecAdapter: EmbedAdapter = {
  buildStateDetails(result) {
    return { ...variationStateDetails(result), ...segmentationStateDetails(result) }
  },
  mapFeedback: mapVariationFeedback,
  telemetry(result) {
    return {
      name: 'probeable_spec.attempt',
      data: {
        ...variationStateDetails(result),
        pass_rate: testPassRate(tallyVariations((resultData(result).test_results as unknown[]) ?? [])),
      },
    }
  },
}

/**
 * Probeable code: learner probes a hidden oracle, then writes the implementation
 * directly. No LLM round-trip, so there is a single code body rather than
 * variations, and the score is the straight test pass rate.
 */
const probeableCodeAdapter: EmbedAdapter = {
  buildStateDetails(result) {
    const tally = tallyVariations((resultData(result).test_results as unknown[]) ?? [])
    return {
      tests_passed: tally.testsPassed,
      tests_run: tally.testsRun,
    }
  },

  mapFeedback(result, _problem, rawInput) {
    const data = resultData(result)
    const studentCode = (data.student_code as string | undefined) ?? ''
    const testResults = (data.test_results as unknown[] | undefined) ?? []

    return {
      // Singleton wrapper object, not a bare string — see file header.
      codeResults: [{ code: studentCode }],
      testResults,
      promptCorrectness: result.score ?? 0,
      comprehensionResults: '',
      userPrompt: result.user_input ?? rawInput,
      segmentationData: null,
    }
  },

  telemetry(result) {
    const tally = tallyVariations((resultData(result).test_results as unknown[]) ?? [])
    return {
      name: 'probeable_code.attempt',
      data: {
        tests_passed: tally.testsPassed,
        tests_run: tally.testsRun,
        pass_rate: testPassRate(tally),
      },
    }
  },
}

const ADAPTERS: Record<string, EmbedAdapter> = {
  eipl: eiplAdapter,
  prompt: promptAdapter,
  probeable_spec: probeableSpecAdapter,
  probeable_code: probeableCodeAdapter,
}

/** Whether this activity type is in the embed's supported set. */
export function isEmbeddableType(problemType: string): boolean {
  return problemType in ADAPTERS
}

/** Returns the adapter for a type, or undefined if the type isn't embeddable. */
export function getEmbedAdapter(problemType: string): EmbedAdapter | undefined {
  return ADAPTERS[problemType]
}

// ===== STATE BUILD / RESTORE =====

export function buildEmbedState(params: {
  result: UnifiedSubmissionResult
  problem: ActivityProblem
  rawInput: string
  attempts: number
}): EmbedState {
  const { result, problem, rawInput, attempts } = params
  const adapter = getEmbedAdapter(problem.problem_type)

  return {
    version: EMBED_STATE_VERSION,
    problem_slug: problem.slug,
    problem_type: problem.problem_type,
    raw_input: result.user_input ?? rawInput,
    score: result.score ?? null,
    completion_status: result.completion_status ?? null,
    submission_id: result.submission_id ?? null,
    attempts,
    updated_at: new Date().toISOString(),
    details: adapter?.buildStateDetails(result, problem) ?? {},
  }
}

/**
 * Pull the learner's previous input back out of host-supplied state.
 *
 * Rehydration is type-agnostic — every supported type round-trips a single
 * `raw_input` string. Hosts are free to hand back anything at all (or a state
 * written by an older version), so this validates rather than trusts.
 */
export function restoreInputFromState(state: unknown, problemSlug?: string): string | null {
  if (!state || typeof state !== 'object') {
    return null
  }

  const candidate = state as Partial<EmbedState>
  if (candidate.version !== EMBED_STATE_VERSION) {
    return null
  }
  // Guard against a host replaying state saved for a different problem.
  if (problemSlug && candidate.problem_slug && candidate.problem_slug !== problemSlug) {
    return null
  }
  if (typeof candidate.raw_input !== 'string') {
    return null
  }

  return candidate.raw_input
}
