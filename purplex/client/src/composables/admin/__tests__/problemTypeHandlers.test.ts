import { beforeEach, describe, expect, it } from 'vitest'
import { type ComposableBundle, problemTypeHandlers } from '../problemTypeHandlers'
import { useMcqOptions } from '../useMcqOptions'
import { usePromptConfig } from '../usePromptConfig'
import { useDebugFixConfig } from '../useDebugFixConfig'
import { useProbeableCodeConfig } from '../useProbeableCodeConfig'
import { useProbeableSpecConfig } from '../useProbeableSpecConfig'
import { useRefuteConfig } from '../useRefuteConfig'
import { useSegmentation } from '../useSegmentation'
import { withSetup } from '@/test/setup'
import type { ProblemDetailed } from '@/types'

/**
 * Integration tests for problemTypeHandlers registry.
 * These tests verify round-trip: load → edit → save for each problem type.
 */
describe('problemTypeHandlers', () => {
  let composables: ComposableBundle

  beforeEach(() => {
    // Create fresh composable instances for each test (inside Vue app context for i18n)
    composables = withSetup(() => ({
      mcqOptions: useMcqOptions(),
      promptConfig: usePromptConfig(),
      debugFixConfig: useDebugFixConfig(),
      probeableCodeConfig: useProbeableCodeConfig(),
      probeableSpecConfig: useProbeableSpecConfig(),
      refuteConfig: useRefuteConfig(),
      segmentation: useSegmentation(),
    }))
  })

  describe('registry completeness', () => {
    it('should have handlers for all 7 problem types', () => {
      const expectedTypes = ['mcq', 'eipl', 'prompt', 'debug_fix', 'probeable_code', 'probeable_spec', 'refute']

      for (const type of expectedTypes) {
        expect(problemTypeHandlers[type]).toBeDefined()
        expect(problemTypeHandlers[type].load).toBeTypeOf('function')
        expect(problemTypeHandlers[type].save).toBeTypeOf('function')
      }
    })
  })

  describe('MCQ handler', () => {
    it('should load MCQ data and populate mcqOptions composable', () => {
      const mockData = {
        problem_type: 'mcq',
        question_text: 'What is 2 + 2?',
        options: [
          { id: '1', text: '3', is_correct: false, explanation: '' },
          { id: '2', text: '4', is_correct: true, explanation: 'Correct!' },
          { id: '3', text: '5', is_correct: false, explanation: '' },
        ],
      } as unknown as ProblemDetailed

      problemTypeHandlers.mcq.load(mockData, composables)

      expect(composables.mcqOptions.questionText.value).toBe('What is 2 + 2?')
      expect(composables.mcqOptions.options.value).toHaveLength(3)
      expect(composables.mcqOptions.options.value[0].text).toBe('3')
      expect(composables.mcqOptions.options.value[0].is_correct).toBe(false)
      expect(composables.mcqOptions.options.value[1].text).toBe('4')
      expect(composables.mcqOptions.options.value[1].is_correct).toBe(true)
      expect(composables.mcqOptions.options.value[1].explanation).toBe('Correct!')
    })

    it('should save MCQ state back to API format', () => {
      composables.mcqOptions.setQuestionText('Test question')
      composables.mcqOptions.setOptions([
        { id: '1', text: 'Option A', is_correct: true, explanation: '' },
        { id: '2', text: 'Option B', is_correct: false, explanation: '' },
      ])

      const saved = problemTypeHandlers.mcq.save(composables)

      expect(saved.question_text).toBe('Test question')
      expect(saved.options).toHaveLength(2)
    })

    it('should round-trip MCQ: load -> edit -> save', () => {
      const originalData = {
        problem_type: 'mcq',
        question_text: 'Original question',
        options: [
          { id: '1', text: 'A', is_correct: true, explanation: '' },
          { id: '2', text: 'B', is_correct: false, explanation: '' },
        ],
      } as unknown as ProblemDetailed

      // Load
      problemTypeHandlers.mcq.load(originalData, composables)

      // Edit
      composables.mcqOptions.setQuestionText('Modified question')
      composables.mcqOptions.setCorrect(1)

      // Save
      const saved = problemTypeHandlers.mcq.save(composables)

      expect(saved.question_text).toBe('Modified question')
      expect((saved.options as Array<{is_correct: boolean}>)[0].is_correct).toBe(false)
      expect((saved.options as Array<{is_correct: boolean}>)[1].is_correct).toBe(true)
    })
  })

  describe('EiPL handler', () => {
    it('should load EiPL segmentation config', () => {
      const mockData = {
        problem_type: 'eipl',
        segmentation_config: {
          enabled: true,
          threshold: 4,
          examples: {
            relational: { prompt: '', segments: ['Seg 1'], code_lines: [[1, 2]] },
            multi_structural: { prompt: '', segments: [], code_lines: [] },
          },
        },
      } as unknown as ProblemDetailed

      problemTypeHandlers.eipl.load(mockData, composables)

      expect(composables.segmentation.isEnabled.value).toBe(true)
      expect(composables.segmentation.threshold.value).toBe(4)
      expect(composables.segmentation.relationalSegments.value).toEqual(['Seg 1'])
    })

    it('should save EiPL state with requires_highlevel_comprehension', () => {
      composables.segmentation.setEnabled(true)
      composables.segmentation.setThreshold(5)

      const saved = problemTypeHandlers.eipl.save(composables)

      expect(saved.requires_highlevel_comprehension).toBe(true)
      expect(saved.segmentation_config).toBeDefined()
      expect(saved.segmentation_threshold).toBe(5)
    })
  })

  describe('Prompt handler', () => {
    it('should load prompt config with image URL', () => {
      const mockData = {
        problem_type: 'prompt',
        prompt_config: {
          image_url: 'https://example.com/image.png',
          image_alt_text: 'Test image',
        },
      } as unknown as ProblemDetailed

      problemTypeHandlers.prompt.load(mockData, composables)

      expect(composables.promptConfig.imageUrl.value).toBe('https://example.com/image.png')
      expect(composables.promptConfig.altText.value).toBe('Test image')
    })

    it('should save prompt config', () => {
      composables.promptConfig.setImageUrl('https://new-url.com/img.jpg')
      composables.promptConfig.setAltText('New alt text')

      const saved = problemTypeHandlers.prompt.save(composables)

      expect(saved.image_url).toBe('https://new-url.com/img.jpg')
      expect(saved.image_alt_text).toBe('New alt text')
    })
  })

  describe('Debug Fix handler', () => {
    it('should load debug fix config', () => {
      const mockData = {
        problem_type: 'debug_fix',
        buggy_code: 'def broken():\n    return x',
        bug_hints: [
          { level: 1, text: 'Check line 2' },
          { level: 2, text: 'x is undefined' },
        ],
      } as unknown as ProblemDetailed

      problemTypeHandlers.debug_fix.load(mockData, composables)

      expect(composables.debugFixConfig.buggyCode.value).toBe('def broken():\n    return x')
      expect(composables.debugFixConfig.bugHints.value).toHaveLength(2)
    })

    it('should save debug fix config', () => {
      composables.debugFixConfig.setBuggyCode('def test(): pass')

      const saved = problemTypeHandlers.debug_fix.save(composables)

      expect(saved.buggy_code).toBe('def test(): pass')
    })

    it('should handle missing debug fix fields gracefully', () => {
      const mockData = {
        problem_type: 'debug_fix',
        // All fields missing
      } as unknown as ProblemDetailed

      problemTypeHandlers.debug_fix.load(mockData, composables)

      expect(composables.debugFixConfig.buggyCode.value).toBe('')
      expect(composables.debugFixConfig.bugHints.value).toHaveLength(0)
    })
  })

  describe('Probeable Code handler', () => {
    it('should load probeable code config', () => {
      const mockData = {
        problem_type: 'probeable_code',
        show_function_signature: false,
        probe_mode: 'cooldown',
        max_probes: 15,
        cooldown_attempts: 5,
        cooldown_refill: 8,
      } as unknown as ProblemDetailed

      problemTypeHandlers.probeable_code.load(mockData, composables)

      expect(composables.probeableCodeConfig.showFunctionSignature.value).toBe(false)
      expect(composables.probeableCodeConfig.probeMode.value).toBe('cooldown')
      expect(composables.probeableCodeConfig.maxProbes.value).toBe(15)
      expect(composables.probeableCodeConfig.cooldownAttempts.value).toBe(5)
      expect(composables.probeableCodeConfig.cooldownRefill.value).toBe(8)
    })

    it('should not load when probe_mode is undefined', () => {
      const mockData = {
        problem_type: 'probeable_code',
        // probe_mode is undefined - should skip loading
      } as unknown as ProblemDetailed

      // Set some values first
      composables.probeableCodeConfig.setMaxProbes(25)

      problemTypeHandlers.probeable_code.load(mockData, composables)

      // Should keep the original value since load was skipped
      expect(composables.probeableCodeConfig.maxProbes.value).toBe(25)
    })

    it('should save probeable code config', () => {
      composables.probeableCodeConfig.setProbeMode('explore')
      composables.probeableCodeConfig.setShowFunctionSignature(true)

      const saved = problemTypeHandlers.probeable_code.save(composables)

      expect(saved.probe_mode).toBe('explore')
      expect(saved.show_function_signature).toBe(true)
    })
  })

  describe('Probeable Spec handler', () => {
    it('should load both probe config and segmentation', () => {
      const mockData = {
        problem_type: 'probeable_spec',
        probe_mode: 'block',
        max_probes: 20,
        cooldown_attempts: 3,
        cooldown_refill: 5,
        show_function_signature: true,
        segmentation_config: {
          enabled: true,
          threshold: 3,
          examples: {
            relational: { prompt: '', segments: ['Test'], code_lines: [[1]] },
            multi_structural: { prompt: '', segments: [], code_lines: [] },
          },
        },
      } as unknown as ProblemDetailed

      problemTypeHandlers.probeable_spec.load(mockData, composables)

      // Probe config — all 5 fields
      expect(composables.probeableSpecConfig.showFunctionSignature.value).toBe(true)
      expect(composables.probeableSpecConfig.probeMode.value).toBe('block')
      expect(composables.probeableSpecConfig.maxProbes.value).toBe(20)
      expect(composables.probeableSpecConfig.cooldownAttempts.value).toBe(3)
      expect(composables.probeableSpecConfig.cooldownRefill.value).toBe(5)

      // Segmentation
      expect(composables.segmentation.isEnabled.value).toBe(true)
      expect(composables.segmentation.relationalSegments.value).toEqual(['Test'])
    })

    it('should save both probe config and segmentation', () => {
      composables.probeableSpecConfig.setProbeMode('cooldown')
      composables.segmentation.setEnabled(true)
      composables.segmentation.setThreshold(5)

      const saved = problemTypeHandlers.probeable_spec.save(composables)

      expect(saved.probe_mode).toBe('cooldown')
      expect(saved.segmentation_config).toBeDefined()
      expect(saved.segmentation_threshold).toBe(5)
      expect(saved.requires_highlevel_comprehension).toBe(true)
    })
  })

  describe('Refute handler', () => {
    it('should load refute config', () => {
      const mockData = {
        problem_type: 'refute',
        claim_text: 'The function always returns a positive number',
        claim_predicate: 'result > 0',
        expected_counterexample: '{"x": -1}',
      } as unknown as ProblemDetailed

      problemTypeHandlers.refute.load(mockData, composables)

      expect(composables.refuteConfig.claimText.value).toBe('The function always returns a positive number')
      expect(composables.refuteConfig.claimPredicate.value).toBe('result > 0')
      expect(composables.refuteConfig.expectedCounterexample.value).toBe('{"x": -1}')
    })

    it('should save refute config', () => {
      composables.refuteConfig.setClaimText('Test claim')
      composables.refuteConfig.setClaimPredicate('x < 0')
      composables.refuteConfig.setExpectedCounterexample('{"value": 0}')

      const saved = problemTypeHandlers.refute.save(composables)

      expect(saved.claim_text).toBe('Test claim')
      expect(saved.claim_predicate).toBe('x < 0')
      expect(saved.expected_counterexample).toBe('{"value": 0}')
    })

    it('should round-trip refute: load -> edit -> save', () => {
      const originalData = {
        problem_type: 'refute',
        claim_text: 'Original claim',
        claim_predicate: 'original > 0',
        expected_counterexample: '{}',
      } as unknown as ProblemDetailed

      // Load
      problemTypeHandlers.refute.load(originalData, composables)

      // Edit
      composables.refuteConfig.setClaimText('Modified claim that always fails')
      composables.refuteConfig.setClaimPredicate('modified > 0')

      // Save
      const saved = problemTypeHandlers.refute.save(composables)

      expect(saved.claim_text).toBe('Modified claim that always fails')
      expect(saved.claim_predicate).toBe('modified > 0')
      // expected_counterexample was not edited — verify it survived the round-trip
      expect(saved.expected_counterexample).toBe('{}')
    })

    it('should handle missing refute fields gracefully', () => {
      const mockData = {
        problem_type: 'refute',
        // All specific fields missing
      } as unknown as ProblemDetailed

      problemTypeHandlers.refute.load(mockData, composables)

      expect(composables.refuteConfig.claimText.value).toBe('')
      expect(composables.refuteConfig.claimPredicate.value).toBe('')
      expect(composables.refuteConfig.expectedCounterexample.value).toBe('')
    })
  })

  describe('defensive handling', () => {
    it('should handle MCQ with null options', () => {
      const mockData = {
        problem_type: 'mcq',
        options: null,
        question_text: undefined,
      } as unknown as ProblemDetailed

      // Should not throw
      expect(() => {
        problemTypeHandlers.mcq.load(mockData, composables)
      }).not.toThrow()
    })

    it('should handle EiPL with null segmentation config', () => {
      const mockData = {
        problem_type: 'eipl',
        segmentation_config: null,
      } as unknown as ProblemDetailed

      expect(() => {
        problemTypeHandlers.eipl.load(mockData, composables)
      }).not.toThrow()
    })

    it('should handle prompt with null prompt_config', () => {
      const mockData = {
        problem_type: 'prompt',
        prompt_config: null,
      } as unknown as ProblemDetailed

      expect(() => {
        problemTypeHandlers.prompt.load(mockData, composables)
      }).not.toThrow()
    })
  })
})
