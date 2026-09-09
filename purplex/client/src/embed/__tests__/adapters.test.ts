import { describe, expect, it } from 'vitest'
import type { ActivityProblem } from '@/components/activities/types'
import type { UnifiedSubmissionResult } from '@/types'
import {
  buildEmbedState,
  EMBED_STATE_VERSION,
  getEmbedAdapter,
  isEmbeddableType,
  restoreInputFromState,
} from '../adapters'

function makeProblem(overrides: Partial<ActivityProblem> = {}): ActivityProblem {
  return {
    slug: 'sum-list',
    title: 'Sum a list',
    description: '',
    problem_type: 'eipl',
    function_name: 'sum_list',
    function_signature: 'def sum_list(xs):',
    reference_solution: 'return sum(xs)',
    ...overrides,
  } as ActivityProblem
}

function makeResult(overrides: Partial<UnifiedSubmissionResult> = {}): UnifiedSubmissionResult {
  return {
    submission_id: 'sub-1',
    problem_type: 'eipl',
    score: 75,
    is_correct: false,
    completion_status: 'partial',
    problem_slug: 'sum-list',
    user_input: 'add up every number in the list',
    result: {},
    ...overrides,
  } as unknown as UnifiedSubmissionResult
}

/** Two variations: one perfect (3/3), one partial (1/3). */
const VARIATION_PAYLOAD = {
  variations: [{ code: 'a' }, { code: 'b' }],
  test_results: [
    { success: true, testsPassed: 3, totalTests: 3 },
    { success: false, testsPassed: 1, totalTests: 3 },
  ],
  segmentation: null,
}

describe('embed adapters', () => {
  describe('type scoping', () => {
    it('accepts exactly the four types the embed is scoped to', () => {
      expect(isEmbeddableType('eipl')).toBe(true)
      expect(isEmbeddableType('prompt')).toBe(true)
      expect(isEmbeddableType('probeable_spec')).toBe(true)
      expect(isEmbeddableType('probeable_code')).toBe(true)
    })

    it('rejects activity types outside that scope', () => {
      expect(isEmbeddableType('mcq')).toBe(false)
      expect(isEmbeddableType('refute')).toBe(false)
      expect(isEmbeddableType('debug_fix')).toBe(false)
      expect(getEmbedAdapter('mcq')).toBeUndefined()
    })
  })

  describe('variation-shaped types (eipl / prompt / probeable_spec)', () => {
    it('maps variation source into codeResults and counts perfect variations', () => {
      const adapter = getEmbedAdapter('eipl')!
      const feedback = adapter.mapFeedback(
        makeResult({ result: VARIATION_PAYLOAD as never }),
        makeProblem(),
        'raw',
      )

      expect(feedback.codeResults).toEqual(['a', 'b'])
      // promptCorrectness drives notches: perfect variations, not a percentage.
      expect(feedback.promptCorrectness).toBe(1)
      expect(feedback.testResults).toHaveLength(2)
    })

    it('falls back to legacy top-level fields when result is empty', () => {
      const adapter = getEmbedAdapter('prompt')!
      const feedback = adapter.mapFeedback(
        makeResult({
          result: {} as never,
          variations: ['legacy-a'],
          test_results: [{ success: true, testsPassed: 2, totalTests: 2 }],
        }),
        makeProblem({ problem_type: 'prompt' }),
        'raw',
      )

      expect(feedback.codeResults).toEqual(['legacy-a'])
      expect(feedback.promptCorrectness).toBe(1)
    })

    it('withholds segmentation unless the problem config enables it', () => {
      const adapter = getEmbedAdapter('eipl')!
      const withSegmentation = {
        ...VARIATION_PAYLOAD,
        segmentation: { passed: true, segment_count: 3 },
      }

      const hidden = adapter.mapFeedback(
        makeResult({ result: withSegmentation as never }),
        makeProblem({ feedback_config: { show_segmentation: false } as never }),
        'raw',
      )
      expect(hidden.segmentationData).toBeNull()

      const shown = adapter.mapFeedback(
        makeResult({ result: withSegmentation as never }),
        makeProblem({ feedback_config: { show_segmentation: true } as never }),
        'raw',
      )
      expect(shown.segmentationData).toEqual({ passed: true, segment_count: 3 })
    })

    it('summarizes segmentation in state without the bulky segment data', () => {
      const adapter = getEmbedAdapter('eipl')!
      const details = adapter.buildStateDetails(
        makeResult({
          result: {
            ...VARIATION_PAYLOAD,
            segmentation: {
              passed: true,
              segment_count: 3,
              comprehension_level: 'relational',
              segments: [{ id: 1, text: 'x'.repeat(5000) }],
              code_mappings: { huge: true },
            },
          } as never,
        }),
        makeProblem(),
      )

      expect(details.segmentation_passed).toBe(true)
      expect(details.segment_count).toBe(3)
      expect(details.comprehension_level).toBe('relational')
      expect(details).not.toHaveProperty('segments')
      expect(details).not.toHaveProperty('code_mappings')
    })

    it('reports variation and test tallies as telemetry', () => {
      const adapter = getEmbedAdapter('probeable_spec')!
      const { name, data } = adapter.telemetry(
        makeResult({ problem_type: 'probeable_spec', result: VARIATION_PAYLOAD as never }),
        makeProblem({ problem_type: 'probeable_spec' }),
      )

      expect(name).toBe('probeable_spec.attempt')
      expect(data).toMatchObject({
        variations_total: 2,
        variations_passed: 1,
        tests_passed: 4,
        tests_run: 6,
        pass_rate: 67,
      })
    })
  })

  describe('probeable_code', () => {
    const payload = {
      student_code: 'def f(x): return x + 1',
      test_results: [{ success: false, testsPassed: 2, totalTests: 4 }],
    }

    it('wraps the single code body rather than emitting a bare string', () => {
      const adapter = getEmbedAdapter('probeable_code')!
      const feedback = adapter.mapFeedback(
        makeResult({ problem_type: 'probeable_code', result: payload as never }),
        makeProblem({ problem_type: 'probeable_code' }),
        'raw',
      )

      expect(feedback.codeResults).toEqual([{ code: 'def f(x): return x + 1' }])
      // No LLM round-trip, so the score is the submission score, not a notch count.
      expect(feedback.promptCorrectness).toBe(75)
      expect(feedback.segmentationData).toBeNull()
    })

    it('reports the test pass rate as telemetry', () => {
      const adapter = getEmbedAdapter('probeable_code')!
      const { name, data } = adapter.telemetry(
        makeResult({ problem_type: 'probeable_code', result: payload as never }),
        makeProblem({ problem_type: 'probeable_code' }),
      )

      expect(name).toBe('probeable_code.attempt')
      expect(data).toMatchObject({ tests_passed: 2, tests_run: 4, pass_rate: 50 })
    })
  })

  describe('buildEmbedState', () => {
    it('carries the fields a relaunch needs and stays structured-cloneable', () => {
      const state = buildEmbedState({
        result: makeResult({ result: VARIATION_PAYLOAD as never }),
        problem: makeProblem(),
        rawInput: 'typed answer',
        attempts: 2,
      })

      expect(state.version).toBe(EMBED_STATE_VERSION)
      expect(state.problem_slug).toBe('sum-list')
      expect(state.problem_type).toBe('eipl')
      expect(state.raw_input).toBe('add up every number in the list')
      expect(state.score).toBe(75)
      expect(state.completion_status).toBe('partial')
      expect(state.attempts).toBe(2)
      expect(() => structuredClone(state)).not.toThrow()
    })

    it('falls back to the typed input when the server echoes none back', () => {
      const state = buildEmbedState({
        result: makeResult({ user_input: undefined as never }),
        problem: makeProblem(),
        rawInput: 'typed answer',
        attempts: 1,
      })

      expect(state.raw_input).toBe('typed answer')
    })
  })

  describe('restoreInputFromState', () => {
    const validState = {
      version: EMBED_STATE_VERSION,
      problem_slug: 'sum-list',
      raw_input: 'my previous answer',
    }

    it('restores the previous answer', () => {
      expect(restoreInputFromState(validState, 'sum-list')).toBe('my previous answer')
    })

    it('rejects state the host saved against a different problem', () => {
      expect(restoreInputFromState(validState, 'other-problem')).toBeNull()
    })

    it('rejects state written by an incompatible version', () => {
      expect(restoreInputFromState({ ...validState, version: 999 }, 'sum-list')).toBeNull()
    })

    it('rejects junk the host may hand back', () => {
      expect(restoreInputFromState(null)).toBeNull()
      expect(restoreInputFromState('a string')).toBeNull()
      expect(restoreInputFromState({ version: EMBED_STATE_VERSION })).toBeNull()
      expect(restoreInputFromState({ ...validState, raw_input: 42 })).toBeNull()
    })
  })
})
