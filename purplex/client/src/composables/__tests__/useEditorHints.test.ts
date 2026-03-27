import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref, type Ref } from 'vue'
import { useEditorHints } from '../useEditorHints'

interface MockEditor {
  setHintMarkers: ReturnType<typeof vi.fn>
  clearHintMarkers: ReturnType<typeof vi.fn>
}

describe('useEditorHints composable', () => {
  let editorRef: Ref<MockEditor>
  let originalCode: Ref<string>
  let composable: ReturnType<typeof useEditorHints>

  beforeEach(() => {
    // Mock editor ref
    editorRef = ref({
      setHintMarkers: vi.fn(),
      clearHintMarkers: vi.fn()
    })

    // Original code
    originalCode = ref('def calculate(x, y):\n    result = x + y\n    return result')

    // Initialize composable
    composable = useEditorHints(editorRef, originalCode)
  })

  describe('Initial state', () => {
    it('should have correct initial values', () => {
      expect(composable.hasActiveHints.value).toBe(false)
      expect(composable.activeHints.value).toEqual([])
      expect(composable.modifiedCode.value).toBe(originalCode.value)
      expect(composable.processingState.value).toBe(false)
      expect(composable.errorState.value).toBeNull()
    })
  })

  describe('applyHint method', () => {
    it('should apply variable fade hint successfully', async () => {
      const hintData = {
        content: {
          mappings: [
            { from: 'x', to: 'first_number' },
            { from: 'y', to: 'second_number' },
            { from: 'result', to: 'sum' }
          ]
        }
      }

      const result = await composable.applyHint('variable_fade', hintData)

      expect(result).toBe(true)
      expect(composable.hasActiveHints.value).toBe(true)
      expect(composable.activeHints.value).toHaveLength(1)
      expect(composable.modifiedCode.value).toContain('first_number')
      expect(composable.modifiedCode.value).toContain('second_number')
      expect(composable.modifiedCode.value).toContain('sum')
      expect(composable.modifiedCode.value).not.toContain('x +')
    })

    it('should apply subgoal highlight hint successfully', async () => {
      const hintData = {
        content: {
          subgoals: [
            {
              line_start: 2,
              line_end: 2,
              title: 'Addition step',
              explanation: 'Addition step'
            }
          ]
        }
      }

      const result = await composable.applyHint('subgoal_highlight', hintData)

      expect(result).toBe(true)
      expect(composable.hasActiveHints.value).toBe(true)
      expect(composable.modifiedCode.value).toContain('# STEP 1: Addition step')
    })

    it('should prevent applying duplicate hints', async () => {
      const hintData = {
        content: {
          mappings: [{ from: 'x', to: 'first' }]
        }
      }

      // Apply once
      await composable.applyHint('variable_fade', hintData)

      // Try to apply again
      const result = await composable.applyHint('variable_fade', hintData)

      expect(result).toBe(false)
      expect(composable.errorState.value).toContain('already active')
      expect(composable.activeHints.value).toHaveLength(1)
    })

    it('should handle invalid hint type', async () => {
      const result = await composable.applyHint('invalid_type', {})

      expect(result).toBe(false)
      expect(composable.errorState.value).toContain('No processor found')
    })

    it('should handle missing hint data', async () => {
      const result = await composable.applyHint('', null as unknown as Parameters<typeof composable.applyHint>[1])

      expect(result).toBe(false)
      expect(composable.errorState.value).toContain('Invalid hint type or data')
    })
  })

  describe('removeHint method', () => {
    it('should remove active hint successfully', async () => {
      // First apply a hint
      const hintData = {
        content: {
          mappings: [{ from: 'x', to: 'first' }]
        }
      }
      await composable.applyHint('variable_fade', hintData)

      // Then remove it
      const result = await composable.removeHint('variable_fade')

      expect(result).toBe(true)
      expect(composable.hasActiveHints.value).toBe(false)
      expect(composable.activeHints.value).toHaveLength(0)
      expect(composable.modifiedCode.value).toBe(originalCode.value)
    })

    it('should handle removing non-existent hint', async () => {
      const result = await composable.removeHint('variable_fade')

      expect(result).toBe(false)
      expect(composable.errorState.value).toContain('is not active')
    })
  })

  describe('toggleHint method', () => {
    it('should apply hint when not active', async () => {
      const hintData = {
        hintType: 'variable_fade',
        content: {
          mappings: [{ from: 'x', to: 'first' }]
        }
      }

      const result = await composable.toggleHint(hintData)

      expect(result).toBe(true)
      expect(composable.isHintActive('variable_fade')).toBe(true)
    })

    it('should remove hint when active', async () => {
      const hintData = {
        hintType: 'variable_fade',
        content: {
          mappings: [{ from: 'x', to: 'first' }]
        }
      }

      // Apply first
      await composable.toggleHint(hintData)
      expect(composable.isHintActive('variable_fade')).toBe(true)

      // Toggle again to remove
      const result = await composable.toggleHint(hintData)

      expect(result).toBe(true)
      expect(composable.isHintActive('variable_fade')).toBe(false)
    })
  })

  describe('removeAllHints method', () => {
    it('should remove all active hints', async () => {
      // Apply multiple hints
      await composable.applyHint('variable_fade', {
        content: { mappings: [{ from: 'x', to: 'first' }] }
      })
      await composable.applyHint('subgoal_highlight', {
        content: {
          subgoals: [{
            line_start: 1,
            line_end: 1,
            title: 'Test',
            explanation: 'Test'
          }]
        }
      })

      expect(composable.activeHints.value).toHaveLength(2)

      // Remove all
      const result = await composable.removeAllHints()

      expect(result).toBe(true)
      expect(composable.hasActiveHints.value).toBe(false)
      expect(composable.activeHints.value).toHaveLength(0)
      expect(composable.modifiedCode.value).toBe(originalCode.value)
    })
  })

  describe('State management', () => {
    it('should track hint history', async () => {
      const hintData = {
        content: { mappings: [{ from: 'x', to: 'first' }] }
      }

      await composable.applyHint('variable_fade', hintData)
      await composable.removeHint('variable_fade')

      // Check history through stats
      const stats = composable.getHintStats()
      expect(stats.historyCount).toBeGreaterThan(0)
    })

    it('should save and restore state', async () => {
      // Apply hints
      await composable.applyHint('variable_fade', {
        content: { mappings: [{ from: 'x', to: 'first' }] }
      })

      // Save state
      const state = composable.saveState()
      expect(state.hasHints).toBe(true)
      expect(state.activeHints).toHaveLength(1)

      // Clear and restore
      await composable.removeAllHints()
      expect(composable.hasActiveHints.value).toBe(false)

      await composable.restoreState(state)
      expect(composable.hasActiveHints.value).toBe(true)
      expect(composable.activeHints.value).toHaveLength(1)
    })
  })

  describe('Multiple hints interaction', () => {
    it('should layer hints correctly', async () => {
      // Apply variable fade first
      await composable.applyHint('variable_fade', {
        content: {
          mappings: [{ from: 'result', to: 'sum' }]
        }
      })

      expect(composable.modifiedCode.value).toContain('sum')

      // Apply subgoal highlight on top
      await composable.applyHint('subgoal_highlight', {
        content: {
          subgoals: [{
            line_start: 2,
            line_end: 2,
            title: 'Calculate sum',
            explanation: 'Calculate sum'
          }]
        }
      })

      // Should have both modifications
      expect(composable.modifiedCode.value).toContain('sum')
      expect(composable.modifiedCode.value).toContain('# STEP 1: Calculate sum')
      expect(composable.activeHints.value).toHaveLength(2)
    })

    it('should survive removing first hint (subgoal then variable_fade then remove subgoal)', async () => {
      // Apply subgoal first
      await composable.applyHint('subgoal_highlight', {
        content: {
          subgoals: [{
            line_start: 2,
            line_end: 2,
            title: 'Addition step',
            explanation: 'Addition step'
          }]
        }
      })
      expect(composable.modifiedCode.value).toContain('# STEP 1: Addition step')

      // Apply variable fade on top
      await composable.applyHint('variable_fade', {
        content: {
          mappings: [{ from: 'result', to: 'sum' }]
        }
      })
      expect(composable.modifiedCode.value).toContain('# STEP 1')
      expect(composable.modifiedCode.value).toContain('sum')
      expect(composable.activeHints.value).toHaveLength(2)

      // Remove subgoal (the first-applied hint)
      await composable.removeHint('subgoal_highlight')

      // Variable fade should still be active with correct code
      expect(composable.activeHints.value).toHaveLength(1)
      expect(composable.hasActiveHints.value).toBe(true)
      expect(composable.modifiedCode.value).toContain('sum')
      expect(composable.modifiedCode.value).not.toContain('# STEP')
      expect(composable.modifiedCode.value.length).toBeGreaterThan(0)
    })

    it('should survive removing first hint (variable_fade then subgoal then remove variable_fade)', async () => {
      // Apply variable fade first
      await composable.applyHint('variable_fade', {
        content: {
          mappings: [{ from: 'result', to: 'sum' }]
        }
      })
      expect(composable.modifiedCode.value).toContain('sum')

      // Apply subgoal on top
      await composable.applyHint('subgoal_highlight', {
        content: {
          subgoals: [{
            line_start: 2,
            line_end: 2,
            title: 'Addition step',
            explanation: 'Addition step'
          }]
        }
      })
      expect(composable.activeHints.value).toHaveLength(2)

      // Remove variable fade (the first-applied hint)
      await composable.removeHint('variable_fade')

      // Subgoal should still be active with correct code
      expect(composable.activeHints.value).toHaveLength(1)
      expect(composable.hasActiveHints.value).toBe(true)
      expect(composable.modifiedCode.value).toContain('# STEP 1: Addition step')
      expect(composable.modifiedCode.value).not.toContain('sum')
      expect(composable.modifiedCode.value.length).toBeGreaterThan(0)
    })
  })

  describe('Error handling', () => {
    it('should handle processor errors gracefully', async () => {
      // Apply hint with invalid data that will cause processor to fail
      const result = await composable.applyHint('variable_fade', {
        content: {} // Missing mappings
      })

      expect(result).toBe(false)
      expect(composable.errorState.value).toBeTruthy()
      expect(composable.hasActiveHints.value).toBe(false)
    })
  })

  describe('Subgoal markers', () => {
    it('should expose subgoalMarkers when subgoal hint is active', async () => {
      const hintData = {
        content: {
          subgoals: [{
            line_start: 2,
            line_end: 2,
            title: 'Addition step',
            explanation: 'Addition step'
          }]
        }
      }

      // No markers before applying
      expect(composable.subgoalMarkers.value).toEqual([])

      await composable.applyHint('subgoal_highlight', hintData)

      // Should have markers after applying
      const markers = composable.subgoalMarkers.value
      expect(markers.length).toBeGreaterThan(0)
      expect(markers.some(m => m.className === 'ace_subgoal-comment')).toBe(true)
      expect(markers.some(m => m.className === 'ace_subgoal-highlight')).toBe(true)
    })

    it('should clear subgoalMarkers when hint is removed', async () => {
      await composable.applyHint('subgoal_highlight', {
        content: {
          subgoals: [{
            line_start: 2,
            line_end: 2,
            title: 'Test',
            explanation: 'Test'
          }]
        }
      })

      expect(composable.subgoalMarkers.value.length).toBeGreaterThan(0)

      await composable.removeHint('subgoal_highlight')

      expect(composable.subgoalMarkers.value).toEqual([])
    })

    it('should return empty markers when no subgoal hint is active', async () => {
      // Apply a non-subgoal hint
      await composable.applyHint('variable_fade', {
        content: { mappings: [{ from: 'x', to: 'first' }] }
      })

      expect(composable.subgoalMarkers.value).toEqual([])
    })
  })
})
