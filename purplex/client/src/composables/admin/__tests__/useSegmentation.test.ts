import { beforeEach, describe, expect, it } from 'vitest'
import { type SegmentationConfig, useSegmentation } from '../useSegmentation'

describe('useSegmentation', () => {
  let segmentation: ReturnType<typeof useSegmentation>

  beforeEach(() => {
    segmentation = useSegmentation()
  })

  describe('initial state', () => {
    it('should initialize with disabled segmentation', () => {
      expect(segmentation.isEnabled.value).toBe(false)
      expect(segmentation.threshold.value).toBe(3)
    })

    it('should initialize with empty examples', () => {
      expect(segmentation.relationalSegments.value).toHaveLength(0)
      expect(segmentation.relationalCodeLines.value).toHaveLength(0)
      expect(segmentation.multiStructuralSegments.value).toHaveLength(0)
      expect(segmentation.multiStructuralCodeLines.value).toHaveLength(0)
    })
  })

  describe('parseLineRange', () => {
    it('should parse single numbers', () => {
      expect(segmentation.parseLineRange('5')).toEqual([5])
      expect(segmentation.parseLineRange('1')).toEqual([1])
    })

    it('should parse ranges: "1-3" to [1,2,3]', () => {
      expect(segmentation.parseLineRange('1-3')).toEqual([1, 2, 3])
      expect(segmentation.parseLineRange('5-8')).toEqual([5, 6, 7, 8])
    })

    it('should parse comma-separated values', () => {
      expect(segmentation.parseLineRange('1,3,5')).toEqual([1, 3, 5])
      expect(segmentation.parseLineRange('2, 4, 6')).toEqual([2, 4, 6])
    })

    it('should parse mixed ranges and numbers', () => {
      expect(segmentation.parseLineRange('1-3, 5, 7-9')).toEqual([1, 2, 3, 5, 7, 8, 9])
    })

    it('should return empty array for empty input', () => {
      expect(segmentation.parseLineRange('')).toEqual([])
      expect(segmentation.parseLineRange('   ')).toEqual([])
    })

    it('should deduplicate and sort results', () => {
      expect(segmentation.parseLineRange('3, 1, 2, 1')).toEqual([1, 2, 3])
    })
  })

  describe('validateLineRange', () => {
    it('should validate correct formats', () => {
      expect(segmentation.validateLineRange('1')).toBe(true)
      expect(segmentation.validateLineRange('1-3')).toBe(true)
      expect(segmentation.validateLineRange('1,2,3')).toBe(true)
      expect(segmentation.validateLineRange('1-3, 5, 7-9')).toBe(true)
    })

    it('should accept empty as valid', () => {
      expect(segmentation.validateLineRange('')).toBe(true)
      expect(segmentation.validateLineRange('   ')).toBe(true)
    })

    it('should reject invalid formats', () => {
      expect(segmentation.validateLineRange('abc')).toBe(false)
      expect(segmentation.validateLineRange('1-')).toBe(false)
      expect(segmentation.validateLineRange('-3')).toBe(false)
      expect(segmentation.validateLineRange('1..3')).toBe(false)
    })
  })

  describe('formatLineRange', () => {
    it('should format single numbers', () => {
      expect(segmentation.formatLineRange([1])).toBe('1')
      expect(segmentation.formatLineRange([5])).toBe('5')
    })

    it('should format consecutive numbers as ranges', () => {
      expect(segmentation.formatLineRange([1, 2, 3])).toBe('1-3')
      expect(segmentation.formatLineRange([5, 6, 7, 8])).toBe('5-8')
    })

    it('should format array to compact string', () => {
      expect(segmentation.formatLineRange([1, 2, 3, 5, 6, 7])).toBe('1-3, 5-7')
      expect(segmentation.formatLineRange([1, 3, 5])).toBe('1, 3, 5')
    })

    it('should return empty string for empty/null arrays', () => {
      expect(segmentation.formatLineRange([])).toBe('')
      expect(segmentation.formatLineRange(null as unknown as number[])).toBe('')
    })

    it('should handle unsorted input', () => {
      expect(segmentation.formatLineRange([3, 1, 2])).toBe('1-3')
      expect(segmentation.formatLineRange([5, 1, 3, 2, 4])).toBe('1-5')
    })
  })

  describe('loadConfig', () => {
    it('should handle parallel arrays correctly on load', () => {
      const config: SegmentationConfig = {
        enabled: true,
        threshold: 4,
        examples: {
          relational: {
            prompt: 'Relational prompt',
            segments: ['Segment 1', 'Segment 2'],
            code_lines: [[1, 2], [3, 4, 5]],
          },
          multi_structural: {
            prompt: 'Multi-structural prompt',
            segments: ['MS Segment 1'],
            code_lines: [[6, 7]],
          },
        },
      }

      segmentation.loadConfig(config)

      expect(segmentation.isEnabled.value).toBe(true)
      expect(segmentation.threshold.value).toBe(4)
      expect(segmentation.relationalSegments.value).toEqual(['Segment 1', 'Segment 2'])
      expect(segmentation.relationalCodeLines.value).toEqual([[1, 2], [3, 4, 5]])
      expect(segmentation.multiStructuralSegments.value).toEqual(['MS Segment 1'])
      expect(segmentation.multiStructuralCodeLines.value).toEqual([[6, 7]])
    })

    it('should handle null config gracefully', () => {
      segmentation.setEnabled(true)
      segmentation.setThreshold(5)

      segmentation.loadConfig(null)

      expect(segmentation.isEnabled.value).toBe(false)
      expect(segmentation.threshold.value).toBe(3)
    })

    it('should handle config with missing examples', () => {
      const config = {
        enabled: true,
        threshold: 5,
        examples: {},
      } as unknown as SegmentationConfig

      segmentation.loadConfig(config)

      expect(segmentation.isEnabled.value).toBe(true)
      expect(segmentation.relationalSegments.value).toEqual([])
      expect(segmentation.multiStructuralSegments.value).toEqual([])
    })
  })

  describe('formatForApi', () => {
    it('should filter empty segments on save', () => {
      const config: SegmentationConfig = {
        enabled: true,
        threshold: 3,
        examples: {
          relational: {
            prompt: 'Test prompt',
            segments: ['Valid segment', '', '   ', 'Another valid'],
            code_lines: [[1], [2], [3], [4]],
          },
          multi_structural: {
            prompt: '',
            segments: [],
            code_lines: [],
          },
        },
      }

      segmentation.loadConfig(config)
      const apiConfig = segmentation.formatForApi()

      expect(apiConfig.examples.relational.segments).toEqual(['Valid segment', 'Another valid'])
      expect(apiConfig.examples.relational.code_lines).toEqual([[1], [4]])
    })

    it('should return empty structure when disabled', () => {
      segmentation.setEnabled(false)
      segmentation.addRelationalSegment()
      segmentation.updateRelationalSegmentText(0, 'Test segment')

      const apiConfig = segmentation.formatForApi()

      expect(apiConfig.enabled).toBe(false)
      expect(apiConfig.examples.relational.segments).toEqual([])
      expect(apiConfig.examples.multi_structural.segments).toEqual([])
    })

    it('should always return a valid config object', () => {
      const apiConfig = segmentation.formatForApi()

      expect(apiConfig).toBeDefined()
      expect(apiConfig.enabled).toBeDefined()
      expect(apiConfig.examples).toBeDefined()
      expect(apiConfig.examples.relational).toBeDefined()
      expect(apiConfig.examples.multi_structural).toBeDefined()
    })

    it('should NOT include threshold in API output (saved via DB field)', () => {
      segmentation.setEnabled(true)
      segmentation.setThreshold(5)
      const apiConfig = segmentation.formatForApi()

      // threshold is saved separately via segmentation_threshold DB field,
      // not in the segmentation_config JSON
      expect('threshold' in apiConfig).toBe(false)
    })
  })

  describe('segment management', () => {
    it('should add relational segments with parallel code_lines', () => {
      segmentation.addRelationalSegment()
      segmentation.addRelationalSegment()

      expect(segmentation.relationalSegments.value).toHaveLength(2)
      expect(segmentation.relationalCodeLines.value).toHaveLength(2)
    })

    it('should remove segments and code_lines in parallel', () => {
      segmentation.addRelationalSegment()
      segmentation.addRelationalSegment()
      segmentation.updateRelationalSegmentText(0, 'First')
      segmentation.updateRelationalSegmentText(1, 'Second')
      segmentation.updateRelationalSegmentCodeLines(0, [1, 2])
      segmentation.updateRelationalSegmentCodeLines(1, [3, 4])

      segmentation.removeRelationalSegment(0)

      expect(segmentation.relationalSegments.value).toEqual(['Second'])
      expect(segmentation.relationalCodeLines.value).toEqual([[3, 4]])
    })
  })

  describe('reset', () => {
    it('should reset to initial state', () => {
      segmentation.setEnabled(true)
      segmentation.setThreshold(7)
      segmentation.addRelationalSegment()
      segmentation.updateRelationalSegmentText(0, 'Test')

      segmentation.reset()

      expect(segmentation.isEnabled.value).toBe(false)
      expect(segmentation.threshold.value).toBe(3)
      expect(segmentation.relationalSegments.value).toHaveLength(0)
    })
  })

  describe('threshold limits', () => {
    it('should clamp threshold between 1 and 10', () => {
      segmentation.setThreshold(0)
      expect(segmentation.threshold.value).toBe(1)

      segmentation.setThreshold(15)
      expect(segmentation.threshold.value).toBe(10)

      segmentation.setThreshold(5)
      expect(segmentation.threshold.value).toBe(5)
    })
  })
})
