import { beforeEach, describe, expect, it } from 'vitest'
import { VariableFadeProcessor } from '../services/hintProcessors/VariableFadeProcessor.js'
import { SubgoalHighlightProcessor } from '../services/hintProcessors/SubgoalHighlightProcessor.js'

describe('VariableFadeProcessor', () => {
  describe('process method', () => {
    it('should successfully process basic variable mappings', () => {
      const code = `def calculate(x, y):
    result = x + y
    return result`

      const hintData = {
        content: {
          mappings: [
            { from: 'x', to: 'first_number' },
            { from: 'y', to: 'second_number' },
            { from: 'result', to: 'sum' }
          ]
        }
      }

      const result = VariableFadeProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      expect(result.code).toContain('first_number')
      expect(result.code).toContain('second_number') 
      expect(result.code).toContain('sum')
      expect(result.code).not.toContain('x +')
      expect(result.transformations).toHaveLength(3)
    })

    it('should handle empty mappings', () => {
      const code = 'def test(): pass'
      const hintData = {
        content: {
          mappings: []
        }
      }

      const result = VariableFadeProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      expect(result.code).toBe(code)
      expect(result.transformations).toHaveLength(0)
    })

    it('should fail with invalid hint data structure', () => {
      const code = 'def test(): pass'
      const hintData = {}

      const result = VariableFadeProcessor.process(code, hintData)

      expect(result.success).toBe(false)
      expect(result.error).toContain('Invalid variable fade hint data')
    })

    it('should fail with missing mappings', () => {
      const code = 'def test(): pass'
      const hintData = {
        content: {}
      }

      const result = VariableFadeProcessor.process(code, hintData)

      expect(result.success).toBe(false)
      expect(result.error).toContain('Invalid variable fade hint data')
    })

    it('should skip invalid mappings and process valid ones', () => {
      const code = 'def test(x, y): return x + y'
      const hintData = {
        content: {
          mappings: [
            { from: 'x', to: 'first' }, // Valid
            { from: '', to: 'invalid' }, // Invalid - empty from
            { from: 'y' }, // Invalid - missing to
            { to: 'invalid' }, // Invalid - missing from
            { from: 'y', to: 'second' } // Valid
          ]
        }
      }

      const result = VariableFadeProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      expect(result.transformations).toHaveLength(2) // Only valid mappings
      expect(result.code).toContain('first')
      expect(result.code).toContain('second')
    })

    it('should handle word boundaries correctly', () => {
      const code = 'x = 1\nmax_x = 2\nx_value = 3'
      const hintData = {
        content: {
          mappings: [
            { from: 'x', to: 'count' }
          ]
        }
      }

      const result = VariableFadeProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      // Should only replace standalone 'x', not 'x' within other variable names
      expect(result.code).toContain('count = 1')
      expect(result.code).toContain('max_x = 2') // Should not be changed
      expect(result.code).toContain('x_value = 3') // Should not be changed
    })

    it('should handle special regex characters in variable names', () => {
      const code = 'test_var = 1\nother_var = 2'
      const hintData = {
        content: {
          mappings: [
            { from: 'test_var', to: 'counter' },
            { from: 'other_var', to: 'value' }
          ]
        }
      }

      const result = VariableFadeProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      expect(result.code).toContain('counter = 1')
      expect(result.code).toContain('value = 2')
    })

    it('should validate variable names', () => {
      const code = 'x = 1'
      const hintData = {
        content: {
          mappings: [
            { from: '123invalid', to: 'valid' }, // Invalid - starts with number
            { from: 'valid', to: '456invalid' } // Invalid - starts with number
          ]
        }
      }

      const result = VariableFadeProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      expect(result.transformations).toHaveLength(0) // No valid mappings
    })

    it('should generate correct markers for highlighting', () => {
      const code = 'def func(x):\n    return x * 2'
      const hintData = {
        content: {
          mappings: [
            { from: 'x', to: 'number' }
          ]
        }
      }

      const result = VariableFadeProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      expect(result.markers).toBeInstanceOf(Array)
      expect(result.markers.length).toBeGreaterThan(0)
      
      const marker = result.markers[0]
      expect(marker).toHaveProperty('startLine')
      expect(marker).toHaveProperty('endLine')
      expect(marker).toHaveProperty('startColumn')
      expect(marker).toHaveProperty('endColumn')
      expect(marker).toHaveProperty('className')
      expect(marker.className).toContain('variable-fade-highlight')
    })
  })

  describe('isValidVariableName method', () => {
    it('should validate correct Python variable names', () => {
      expect(VariableFadeProcessor.isValidVariableName('valid_name')).toBe(true)
      expect(VariableFadeProcessor.isValidVariableName('_private')).toBe(true)
      expect(VariableFadeProcessor.isValidVariableName('var123')).toBe(true)
      expect(VariableFadeProcessor.isValidVariableName('CamelCase')).toBe(true)
    })

    it('should reject invalid Python variable names', () => {
      expect(VariableFadeProcessor.isValidVariableName('123invalid')).toBe(false)
      expect(VariableFadeProcessor.isValidVariableName('with-dash')).toBe(false)
      expect(VariableFadeProcessor.isValidVariableName('with space')).toBe(false)
      expect(VariableFadeProcessor.isValidVariableName('')).toBe(false)
      expect(VariableFadeProcessor.isValidVariableName(null)).toBe(false)
      expect(VariableFadeProcessor.isValidVariableName(undefined)).toBe(false)
    })
  })

  describe('checkConflicts method', () => {
    it('should detect duplicate targets', () => {
      const mappings = [
        { from: 'x', to: 'count' },
        { from: 'y', to: 'count' } // Duplicate target
      ]

      const conflicts = VariableFadeProcessor.checkConflicts(mappings)

      expect(conflicts).toHaveLength(1)
      expect(conflicts[0].type).toBe('duplicate_target')
      expect(conflicts[0].message).toContain('Multiple variables mapping to \'count\'')
    })

    it('should detect duplicate sources', () => {
      const mappings = [
        { from: 'x', to: 'count' },
        { from: 'x', to: 'number' } // Duplicate source
      ]

      const conflicts = VariableFadeProcessor.checkConflicts(mappings)

      expect(conflicts).toHaveLength(1)
      expect(conflicts[0].type).toBe('duplicate_source')
      expect(conflicts[0].message).toContain('Variable \'x\' mapped multiple times')
    })

    it('should detect circular mappings', () => {
      const mappings = [
        { from: 'x', to: 'y' },
        { from: 'y', to: 'x' } // Circular mapping
      ]

      const conflicts = VariableFadeProcessor.checkConflicts(mappings)

      expect(conflicts).toHaveLength(1)
      expect(conflicts[0].type).toBe('circular_mapping')
      expect(conflicts[0].message).toContain('Circular mapping detected')
    })
  })

  describe('reverse method', () => {
    it('should reverse transformations correctly', () => {
      const originalCode = 'def func(x, y): return x + y'
      const transformations = [
        { original: 'x', replacement: 'first_number' },
        { original: 'y', replacement: 'second_number' }
      ]
      
      const transformedCode = 'def func(first_number, second_number): return first_number + second_number'
      const reversedCode = VariableFadeProcessor.reverse(transformedCode, transformations)

      expect(reversedCode).toBe(originalCode)
    })
  })
})

describe('SubgoalHighlightProcessor', () => {
  describe('process method', () => {
    it('should successfully process basic subgoals', () => {
      const code = `def calculate(a, b):
    result = a + b
    return result`

      const hintData = {
        content: {
          subgoals: [
            {
              line_start: 1,
              line_end: 1,
              title: 'Function definition',
              explanation: 'Define the function with parameters'
            },
            {
              line_start: 2,
              line_end: 2,
              title: 'Calculate sum',
              explanation: 'Add the two numbers'
            },
            {
              line_start: 3,
              line_end: 3,
              title: 'Return result',
              explanation: 'Return the calculated sum'
            }
          ]
        }
      }

      const result = SubgoalHighlightProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      expect(result.markers).toHaveLength(6) // 3 comment markers + 3 subgoal markers
      expect(result.annotations).toHaveLength(3)
      expect(result.tooltips).toHaveLength(3)
      expect(result.code).toContain('# Step 1: Function definition')
      expect(result.code).toContain('# Step 2: Calculate sum')
      expect(result.code).toContain('# Step 3: Return result')
    })

    it('should fail with invalid hint data structure', () => {
      const code = 'def test(): pass'
      const hintData = {}

      const result = SubgoalHighlightProcessor.process(code, hintData)

      expect(result.success).toBe(false)
      expect(result.error).toContain('Invalid subgoal highlight hint data')
    })

    it('should fail with missing subgoals', () => {
      const code = 'def test(): pass'
      const hintData = {
        content: {}
      }

      const result = SubgoalHighlightProcessor.process(code, hintData)

      expect(result.success).toBe(false)
      expect(result.error).toContain('Invalid subgoal highlight hint data')
    })

    it('should skip invalid subgoals and process valid ones', () => {
      const code = `line1
line2
line3`

      const hintData = {
        content: {
          subgoals: [
            {
              line_start: 1,
              line_end: 1,
              title: 'Valid subgoal',
              explanation: 'This is valid'
            },
            {
              // Missing required fields
              line_start: 2
            },
            {
              line_start: 3,
              line_end: 3,
              title: 'Another valid',
              explanation: 'This is also valid'
            }
          ]
        }
      }

      const result = SubgoalHighlightProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      expect(result.markers).toHaveLength(4) // 2 comment + 2 subgoal markers
      expect(result.tooltips).toHaveLength(2)
    })

    it('should generate correct markers with proper line indexing', () => {
      const code = 'line1\nline2'
      const hintData = {
        content: {
          subgoals: [
            {
              line_start: 2,
              line_end: 2,
              title: 'Second line',
              explanation: 'Process second line'
            }
          ]
        }
      }

      const result = SubgoalHighlightProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      
      const subgoalMarker = result.adjustedMarkers.find(m => m.hintType === 'subgoal_highlight')
      expect(subgoalMarker).toBeDefined()
      expect(subgoalMarker.stepNumber).toBe(1)
      expect(subgoalMarker.stepTitle).toBe('Second line')
    })

    it('should handle overlapping subgoals correctly', () => {
      const code = `line1
line2
line3
line4`

      const hintData = {
        content: {
          subgoals: [
            {
              line_start: 1,
              line_end: 3,
              title: 'First block',
              explanation: 'Lines 1-3'
            },
            {
              line_start: 2,
              line_end: 4,
              title: 'Second block',
              explanation: 'Lines 2-4'
            }
          ]
        }
      }

      const result = SubgoalHighlightProcessor.process(code, hintData)

      expect(result.success).toBe(true)
      // Should process both subgoals despite overlap
      expect(result.markers).toHaveLength(4) // 2 comment + 2 subgoal markers
    })
  })

  describe('validateSubgoal method', () => {
    it('should validate correct subgoals', () => {
      const validSubgoal = {
        line_start: 1,
        line_end: 3,
        title: 'Valid title',
        explanation: 'Valid explanation'
      }

      expect(SubgoalHighlightProcessor.validateSubgoal(validSubgoal, 10)).toBe(true)
    })

    it('should reject subgoals with missing fields', () => {
      const invalidSubgoals = [
        { line_start: 1, line_end: 3, title: 'Missing explanation' },
        { line_start: 1, line_end: 3, explanation: 'Missing title' },
        { line_start: 1, title: 'Title', explanation: 'Missing line_end' },
        { line_end: 3, title: 'Title', explanation: 'Missing line_start' }
      ]

      invalidSubgoals.forEach(subgoal => {
        expect(SubgoalHighlightProcessor.validateSubgoal(subgoal, 10)).toBe(false)
      })
    })

    it('should reject subgoals with invalid line numbers', () => {
      const invalidSubgoals = [
        { line_start: 0, line_end: 1, title: 'Title', explanation: 'Start < 1' },
        { line_start: 3, line_end: 2, title: 'Title', explanation: 'End < Start' },
        { line_start: 1, line_end: 15, title: 'Title', explanation: 'End > total lines' },
        { line_start: 'not_number', line_end: 3, title: 'Title', explanation: 'Non-integer start' }
      ]

      invalidSubgoals.forEach(subgoal => {
        expect(SubgoalHighlightProcessor.validateSubgoal(subgoal, 10)).toBe(false)
      })
    })
  })

  describe('detectOverlaps method', () => {
    it('should detect overlapping subgoals', () => {
      const subgoals = [
        { line_start: 1, line_end: 3, title: 'First', explanation: 'First block' },
        { line_start: 2, line_end: 4, title: 'Second', explanation: 'Second block' },
        { line_start: 5, line_end: 6, title: 'Third', explanation: 'No overlap' }
      ]

      const overlaps = SubgoalHighlightProcessor.detectOverlaps(subgoals)

      expect(overlaps).toHaveLength(1)
      expect(overlaps[0].subgoal1.title).toBe('First')
      expect(overlaps[0].subgoal2.title).toBe('Second')
      expect(overlaps[0].overlapType).toBe('partial')
    })

    it('should detect identical subgoals', () => {
      const subgoals = [
        { line_start: 1, line_end: 3, title: 'First', explanation: 'Block' },
        { line_start: 1, line_end: 3, title: 'Duplicate', explanation: 'Same block' }
      ]

      const overlaps = SubgoalHighlightProcessor.detectOverlaps(subgoals)

      expect(overlaps).toHaveLength(1)
      expect(overlaps[0].overlapType).toBe('identical')
    })

    it('should detect containment relationships', () => {
      const subgoals = [
        { line_start: 1, line_end: 5, title: 'Outer', explanation: 'Contains inner' },
        { line_start: 2, line_end: 3, title: 'Inner', explanation: 'Contained' }
      ]

      const overlaps = SubgoalHighlightProcessor.detectOverlaps(subgoals)

      expect(overlaps).toHaveLength(1)
      expect(overlaps[0].overlapType).toBe('contains')
    })
  })

  describe('generateProgressiveSequence method', () => {
    it('should generate progressive sequence correctly', () => {
      const subgoals = [
        { line_start: 1, line_end: 1, title: 'Step 1', explanation: 'First' },
        { line_start: 2, line_end: 2, title: 'Step 2', explanation: 'Second' },
        { line_start: 3, line_end: 3, title: 'Step 3', explanation: 'Third' }
      ]

      const markers = SubgoalHighlightProcessor.generateProgressiveSequence(subgoals, 1)

      expect(markers).toHaveLength(2) // Steps 0 and 1
      expect(markers[0].isCompleted).toBe(true)
      expect(markers[0].isCurrentStep).toBe(false)
      expect(markers[1].isCompleted).toBe(false)
      expect(markers[1].isCurrentStep).toBe(true)
    })
  })

  describe('sortSubgoals method', () => {
    it('should sort subgoals by line position', () => {
      const subgoals = [
        { line_start: 5, line_end: 6, title: 'Last', explanation: 'End' },
        { line_start: 1, line_end: 2, title: 'First', explanation: 'Start' },
        { line_start: 3, line_end: 4, title: 'Middle', explanation: 'Center' }
      ]

      const sorted = SubgoalHighlightProcessor.sortSubgoals(subgoals)

      expect(sorted[0].title).toBe('First')
      expect(sorted[1].title).toBe('Middle')
      expect(sorted[2].title).toBe('Last')
    })

    it('should sort by end line when start lines are equal', () => {
      const subgoals = [
        { line_start: 1, line_end: 5, title: 'Longer', explanation: 'Spans more' },
        { line_start: 1, line_end: 2, title: 'Shorter', explanation: 'Spans less' }
      ]

      const sorted = SubgoalHighlightProcessor.sortSubgoals(subgoals)

      expect(sorted[0].title).toBe('Shorter') // Shorter ranges first
      expect(sorted[1].title).toBe('Longer')
    })
  })
})