import { beforeEach, describe, expect, it } from 'vitest'
import VariableFadeProcessor from '../services/hintProcessors/VariableFadeProcessor'
import SubgoalHighlightProcessor from '../services/hintProcessors/SubgoalHighlightProcessor'

describe('VariableFadeProcessor', () => {
  let processor: VariableFadeProcessor

  beforeEach(() => {
    processor = new VariableFadeProcessor()
  })

  describe('processHint method', () => {
    it('should successfully process basic variable mappings', () => {
      const code = `def calculate(x, y):
    result = x + y
    return result`

      const hintData = {
        code,
        mappings: [
          { from: 'x', to: 'first_number' },
          { from: 'y', to: 'second_number' },
          { from: 'result', to: 'sum' }
        ]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toContain('first_number')
      expect(result.code).toContain('second_number')
      expect(result.code).toContain('sum')
      expect(result.code).not.toContain('x +')
      expect(result.markers).toBeDefined()
    })

    it('should handle empty mappings', () => {
      const code = 'def test(): pass'
      const hintData = {
        code,
        mappings: []
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toBe(code)
      expect(result.markers).toHaveLength(0)
    })

    it('should fail with invalid hint data structure', () => {
      const hintData: any = {
        code: 'def test(): pass'
        // Missing mappings
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(false)
      expect(result.error).toBeDefined()
    })

    it('should fail with missing mappings', () => {
      const hintData: any = {
        code: 'def test(): pass',
        mappings: null
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(false)
      expect(result.error).toBeDefined()
    })

    it('should skip invalid mappings and process valid ones', () => {
      const code = 'def test(x, y): return x + y'
      const hintData = {
        code,
        mappings: [
          { from: 'x', to: 'first' }, // Valid
          { from: '', to: 'invalid' }, // Invalid - empty from
          { from: 'y', to: '' }, // Invalid - empty to
          { from: 'y', to: 'second' } // Valid
        ] as any[]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toContain('first')
      expect(result.code).toContain('second')
      expect(result.code).not.toContain('invalid')
    })

    it('should handle Python keywords in code', () => {
      const code = `def process(list, dict, str):
    for item in list:
        if item in dict:
            return str`

      const hintData = {
        code,
        mappings: [
          { from: 'list', to: 'items' },
          { from: 'dict', to: 'lookup' },
          { from: 'str', to: 'text' },
          { from: 'item', to: 'element' }
        ]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toContain('items')
      expect(result.code).toContain('lookup')
      expect(result.code).toContain('text')
      expect(result.code).toContain('element')
    })

    it('should preserve indentation and formatting', () => {
      const code = `def complex_function(a, b, c):
    # Calculate first part
    temp = a + b

    # Apply transformation
    if temp > 0:
        result = temp * c
    else:
        result = temp - c

    return result`

      const hintData = {
        code,
        mappings: [
          { from: 'a', to: 'first_value' },
          { from: 'b', to: 'second_value' },
          { from: 'c', to: 'multiplier' },
          { from: 'temp', to: 'intermediate' },
          { from: 'result', to: 'final_output' }
        ]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toMatch(/^\s{4}# Calculate first part$/m)
      expect(result.code).toMatch(/^\s{4}if intermediate > 0:$/m)
      expect(result.code).toMatch(/^\s{8}final_output = intermediate \* multiplier$/m)
    })

    it('should handle edge cases with variable names at boundaries', () => {
      const code = 'x=1;y=x+1;return x+y'
      const hintData = {
        code,
        mappings: [
          { from: 'x', to: 'first' },
          { from: 'y', to: 'second' }
        ]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toBe('first=1;second=first+1;return first+second')
    })

    it('should not replace partial matches', () => {
      const code = 'fox = 1; x = 2; prefix_x = 3; x_suffix = 4'
      const hintData = {
        code,
        mappings: [
          { from: 'x', to: 'variable' }
        ]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toContain('fox = 1')  // Should not change
      expect(result.code).toContain('variable = 2')  // Should change
      expect(result.code).toContain('prefix_x = 3')  // Should not change
      expect(result.code).toContain('x_suffix = 4')  // Should not change
    })
  })

  describe('isValidVariableName method', () => {
    it('should validate correct Python variable names', () => {
      expect(processor.isValidVariableName('valid_name')).toBe(true)
      expect(processor.isValidVariableName('_private')).toBe(true)
      expect(processor.isValidVariableName('var123')).toBe(true)
      expect(processor.isValidVariableName('CamelCase')).toBe(true)
    })

    it('should reject invalid Python variable names', () => {
      expect(processor.isValidVariableName('123invalid')).toBe(false)
      expect(processor.isValidVariableName('with-dash')).toBe(false)
      expect(processor.isValidVariableName('with space')).toBe(false)
      expect(processor.isValidVariableName('')).toBe(false)
      expect(processor.isValidVariableName(null as any)).toBe(false)
      expect(processor.isValidVariableName(undefined as any)).toBe(false)
    })
  })
})

describe('SubgoalHighlightProcessor', () => {
  let processor: SubgoalHighlightProcessor

  beforeEach(() => {
    processor = new SubgoalHighlightProcessor()
  })

  describe('processHint method', () => {
    it('should successfully add subgoal comments', () => {
      const code = `def calculate(a, b):
    result = a + b
    return result`

      const hintData = {
        code,
        subgoals: [
          {
            line_start: 2,
            line_end: 2,
            comment: 'Add the two numbers',
            title: 'Addition step'
          }
        ]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toContain('# STEP 1: Addition step')
      expect(result.markers).toBeDefined()
      expect(result.markers?.length).toBeGreaterThan(0)
    })

    it('should handle multiple subgoals', () => {
      const code = `def process(data):
    cleaned = clean_data(data)
    analyzed = analyze(cleaned)
    return format_results(analyzed)`

      const hintData = {
        code,
        subgoals: [
          {
            line_start: 2,
            line_end: 2,
            comment: 'Clean the input data',
            title: 'Data cleaning'
          },
          {
            line_start: 3,
            line_end: 3,
            comment: 'Perform analysis',
            title: 'Analysis'
          },
          {
            line_start: 4,
            line_end: 4,
            comment: 'Format for output',
            title: 'Formatting'
          }
        ]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toContain('# STEP 1: Data cleaning')
      expect(result.code).toContain('# STEP 2: Analysis')
      expect(result.code).toContain('# STEP 3: Formatting')
    })

    it('should handle multi-line subgoals', () => {
      const code = `def complex_operation(x, y, z):
    # Initialize
    temp1 = x * 2
    temp2 = y * 3
    temp3 = z * 4

    # Combine
    result = temp1 + temp2 + temp3
    return result`

      const hintData = {
        code,
        subgoals: [
          {
            line_start: 3,
            line_end: 5,
            comment: 'Prepare temporary values',
            title: 'Initialization'
          },
          {
            line_start: 8,
            line_end: 9,
            comment: 'Combine all values',
            title: 'Combination'
          }
        ]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toContain('# STEP 1: Initialization')
      expect(result.code).toContain('# STEP 2: Combination')
      expect(result.metadata?.affectsLineNumbers).toBe(true)
    })

    it('should preserve existing comments', () => {
      const code = `def function():
    # Existing comment
    x = 1
    # Another comment
    y = 2`

      const hintData = {
        code,
        subgoals: [
          {
            line_start: 3,
            line_end: 3,
            comment: 'Set x value',
            title: 'Initialize x'
          }
        ]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      expect(result.code).toContain('# Existing comment')
      expect(result.code).toContain('# Another comment')
      expect(result.code).toContain('# STEP 1: Initialize x')
    })

    it('should fail with invalid subgoal data', () => {
      const hintData: any = {
        code: 'def test(): pass',
        subgoals: null
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(false)
      expect(result.error).toBeDefined()
    })

    it('should handle overlapping subgoals gracefully', () => {
      const code = `line1
line2
line3
line4
line5`

      const hintData = {
        code,
        subgoals: [
          {
            line_start: 2,
            line_end: 4,
            comment: 'First section',
            title: 'Section 1'
          },
          {
            line_start: 3,
            line_end: 5,
            comment: 'Overlapping section',
            title: 'Section 2'
          }
        ]
      }

      const result = processor.processHint(hintData)

      expect(result.success).toBe(true)
      // Should handle overlaps gracefully
      expect(result.code).toContain('STEP 1')
      expect(result.code).toContain('STEP 2')
    })
  })
})
