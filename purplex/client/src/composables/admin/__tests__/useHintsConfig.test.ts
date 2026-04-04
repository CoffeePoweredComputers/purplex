import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useHintsConfig } from '../useHintsConfig'

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key: string) => key }),
}))

// Mock problemService (used by load/save)
vi.mock('@/services/problemService', () => ({
  problemService: {
    getProblemHints: vi.fn().mockResolvedValue([]),
    updateHints: vi.fn().mockResolvedValue({}),
  },
}))

describe('useHintsConfig', () => {
  let hints: ReturnType<typeof useHintsConfig>

  beforeEach(() => {
    hints = useHintsConfig()
  })

  describe('initial state', () => {
    it('should initialize with all hints disabled', () => {
      expect(hints.hints.variable_fade.is_enabled).toBe(false)
      expect(hints.hints.subgoal_highlight.is_enabled).toBe(false)
      expect(hints.hints.suggested_trace.is_enabled).toBe(false)
    })

    it('should initialize with empty content', () => {
      expect(hints.hints.variable_fade.content.mappings).toEqual([])
      expect(hints.hints.subgoal_highlight.content.subgoals).toEqual([])
      expect(hints.hints.suggested_trace.content.suggested_call).toBe('')
    })

    it('should default to variable_fade tab', () => {
      expect(hints.activeTab.value).toBe('variable_fade')
    })
  })

  describe('variable fade', () => {
    it('should enable/disable via setEnabled', () => {
      hints.variableFade.setEnabled(true)
      expect(hints.hints.variable_fade.is_enabled).toBe(true)

      hints.variableFade.setEnabled(false)
      expect(hints.hints.variable_fade.is_enabled).toBe(false)
    })

    it('should add and remove mappings', () => {
      hints.variableFade.addMapping('total', 'x')
      expect(hints.hints.variable_fade.content.mappings).toHaveLength(1)
      expect(hints.hints.variable_fade.content.mappings[0]).toEqual({ from: 'total', to: 'x' })

      hints.variableFade.addMapping('count', 'y')
      expect(hints.hints.variable_fade.content.mappings).toHaveLength(2)

      hints.variableFade.removeMapping(0)
      expect(hints.hints.variable_fade.content.mappings).toHaveLength(1)
      expect(hints.hints.variable_fade.content.mappings[0].from).toBe('count')
    })

    it('should validate Python variable names', () => {
      expect(hints.variableFade.validateName('total')).toBe(true)
      expect(hints.variableFade.validateName('_private')).toBe(true)
      expect(hints.variableFade.validateName('var1')).toBe(true)
      expect(hints.variableFade.validateName('1bad')).toBe(false)
      expect(hints.variableFade.validateName('')).toBe(false)
      expect(hints.variableFade.validateName('has space')).toBe(false)
    })

    it('should set min_attempts', () => {
      hints.variableFade.setMinAttempts(5)
      expect(hints.hints.variable_fade.min_attempts).toBe(5)
    })
  })

  describe('subgoal highlight', () => {
    it('should enable/disable', () => {
      hints.subgoalHighlight.setEnabled(true)
      expect(hints.hints.subgoal_highlight.is_enabled).toBe(true)
    })

    it('should add and remove subgoals', () => {
      hints.subgoalHighlight.addSubgoal({
        line_start: 1,
        line_end: 3,
        title: 'Init',
        explanation: 'Setup variables',
      })
      expect(hints.hints.subgoal_highlight.content.subgoals).toHaveLength(1)

      hints.subgoalHighlight.removeSubgoal(0)
      expect(hints.hints.subgoal_highlight.content.subgoals).toHaveLength(0)
    })
  })

  describe('suggested trace', () => {
    it('should enable/disable', () => {
      hints.suggestedTrace.setEnabled(true)
      expect(hints.hints.suggested_trace.is_enabled).toBe(true)
    })

    it('should set the suggested call', () => {
      hints.suggestedTrace.setCall('foo(1, 2)')
      expect(hints.hints.suggested_trace.content.suggested_call).toBe('foo(1, 2)')
    })
  })

  describe('setHints', () => {
    it('should update state from API response using Object.assign', () => {
      hints.setHints([
        {
          type: 'variable_fade',
          is_enabled: true,
          min_attempts: 3,
          content: { mappings: [{ from: 'a', to: 'b' }] },
        },
        {
          type: 'subgoal_highlight',
          is_enabled: true,
          min_attempts: 2,
          content: { subgoals: [] },
        },
      ])

      expect(hints.hints.variable_fade.is_enabled).toBe(true)
      expect(hints.hints.variable_fade.min_attempts).toBe(3)
      expect(hints.hints.variable_fade.content.mappings).toHaveLength(1)
      expect(hints.hints.subgoal_highlight.is_enabled).toBe(true)
      // Suggested trace should remain at defaults (not in input)
      expect(hints.hints.suggested_trace.is_enabled).toBe(false)
    })

    it('should preserve reactivity after setHints (v-model compatibility)', () => {
      // This test verifies the Object.assign fix — the same reactive
      // object reference must be maintained so v-model bindings work
      const refBefore = hints.hints.variable_fade

      hints.setHints([
        { type: 'variable_fade', is_enabled: true, min_attempts: 5, content: { mappings: [] } },
      ])

      // Same reference — Object.assign mutates in-place
      expect(hints.hints.variable_fade).toBe(refBefore)
      expect(hints.hints.variable_fade.is_enabled).toBe(true)
    })
  })

  describe('getHintsArray', () => {
    it('should return all three hint types', () => {
      const arr = hints.getHintsArray()
      expect(arr).toHaveLength(3)
      expect(arr.map(h => h.type)).toEqual(['variable_fade', 'subgoal_highlight', 'suggested_trace'])
    })

    it('should reflect current state', () => {
      hints.variableFade.setEnabled(true)
      hints.variableFade.setMinAttempts(5)

      const arr = hints.getHintsArray()
      const vf = arr.find(h => h.type === 'variable_fade')!
      expect(vf.is_enabled).toBe(true)
      expect(vf.min_attempts).toBe(5)
    })
  })

  describe('reset', () => {
    it('should restore initial state', () => {
      hints.variableFade.setEnabled(true)
      hints.variableFade.addMapping('a', 'b')
      hints.subgoalHighlight.setEnabled(true)

      hints.reset()

      expect(hints.hints.variable_fade.is_enabled).toBe(false)
      expect(hints.hints.variable_fade.content.mappings).toEqual([])
      expect(hints.hints.subgoal_highlight.is_enabled).toBe(false)
    })
  })

  describe('mutable state (v-model compatibility)', () => {
    it('should allow direct property writes (not readonly)', () => {
      // This verifies the fix: hints.hints is NOT wrapped in readonly()
      // so v-model="hints.variable_fade.is_enabled" can write through
      hints.hints.variable_fade.is_enabled = true
      expect(hints.hints.variable_fade.is_enabled).toBe(true)

      // getHintsArray should also reflect the direct write
      const arr = hints.getHintsArray()
      expect(arr.find(h => h.type === 'variable_fade')!.is_enabled).toBe(true)
    })
  })
})
