import { beforeEach, describe, expect, it } from 'vitest'
import { useDebugFixConfig, type DebugFixConfig, type BugHint } from '../useDebugFixConfig'
import { withSetup } from '@/test/setup'

describe('useDebugFixConfig', () => {
  let debugFix: ReturnType<typeof useDebugFixConfig>

  beforeEach(() => {
    debugFix = withSetup(() => useDebugFixConfig())
  })

  describe('initial state', () => {
    it('should initialize with empty values', () => {
      expect(debugFix.buggyCode.value).toBe('')
      expect(debugFix.bugHints.value).toHaveLength(0)
      expect(debugFix.allowCompleteRewrite.value).toBe(false)
      expect(debugFix.hasBuggyCode.value).toBe(false)
    })
  })

  describe('loadConfig', () => {
    it('should load buggy code and hints', () => {
      const config: DebugFixConfig = {
        buggy_code: 'def broken():\n    return x + 1',
        bug_hints: [
          { level: 1, text: 'Check the variable name' },
          { level: 2, text: 'x is undefined' },
        ],
        allow_complete_rewrite: true,
      }

      debugFix.loadConfig(config)

      expect(debugFix.buggyCode.value).toBe('def broken():\n    return x + 1')
      expect(debugFix.bugHints.value).toHaveLength(2)
      expect(debugFix.bugHints.value[0].level).toBe(1)
      expect(debugFix.bugHints.value[0].text).toBe('Check the variable name')
      expect(debugFix.allowCompleteRewrite.value).toBe(true)
      expect(debugFix.hasBuggyCode.value).toBe(true)
    })

    it('should validate hint levels on load (1-3 range)', () => {
      const config: Partial<DebugFixConfig> = {
        buggy_code: 'def test(): pass',
        bug_hints: [
          { level: 0 as 1 | 2 | 3, text: 'Invalid low level' },
          { level: 5 as 1 | 2 | 3, text: 'Invalid high level' },
          { level: 2, text: 'Valid level' },
          { level: -1 as 1 | 2 | 3, text: 'Negative level' },
        ],
      }

      debugFix.loadConfig(config)

      // Invalid levels should be coerced to 1
      expect(debugFix.bugHints.value[0].level).toBe(1)
      expect(debugFix.bugHints.value[1].level).toBe(1) // 5 is out of range
      expect(debugFix.bugHints.value[2].level).toBe(2) // Valid
      expect(debugFix.bugHints.value[3].level).toBe(1) // -1 is out of range
    })

    it('should handle null config gracefully', () => {
      debugFix.setBuggyCode('some code')
      debugFix.loadConfig(null)

      expect(debugFix.buggyCode.value).toBe('')
      expect(debugFix.bugHints.value).toHaveLength(0)
    })

    it('should handle config with non-array bug_hints', () => {
      const config = {
        buggy_code: 'def test(): pass',
        bug_hints: null,
      } as unknown as Partial<DebugFixConfig>

      debugFix.loadConfig(config)

      expect(debugFix.bugHints.value).toHaveLength(0)
    })
  })

  describe('codesDiffer', () => {
    it('should detect code differences correctly', () => {
      debugFix.setBuggyCode('def broken(): return x')

      expect(debugFix.codesDiffer('def broken(): return y')).toBe(true)
      expect(debugFix.codesDiffer('def broken(): return x')).toBe(false)
    })

    it('should trim whitespace for comparison', () => {
      debugFix.setBuggyCode('  def test()  ')

      expect(debugFix.codesDiffer('def test()')).toBe(false)
      expect(debugFix.codesDiffer('  def test()  ')).toBe(false)
    })

    it('should handle empty reference solution', () => {
      debugFix.setBuggyCode('def test(): pass')

      expect(debugFix.codesDiffer('')).toBe(true)
      expect(debugFix.codesDiffer(null as unknown as string)).toBe(true)
    })
  })

  describe('sortHintsByLevel', () => {
    it('should sort hints by level', () => {
      debugFix.loadConfig({
        buggy_code: 'test',
        bug_hints: [
          { level: 3, text: 'Level 3 hint' },
          { level: 1, text: 'Level 1 hint' },
          { level: 2, text: 'Level 2 hint' },
        ],
        allow_complete_rewrite: false,
      })

      debugFix.sortHintsByLevel()

      expect(debugFix.bugHints.value[0].level).toBe(1)
      expect(debugFix.bugHints.value[1].level).toBe(2)
      expect(debugFix.bugHints.value[2].level).toBe(3)
    })
  })

  describe('validate', () => {
    it('should validate configuration - require buggy code', () => {
      debugFix.setBuggyCode('')

      const result = debugFix.validate('def correct(): pass')

      expect(result.valid).toBe(false)
      expect(result.errors).toContain('Buggy code is required')
    })

    it('should validate configuration - require difference from solution', () => {
      debugFix.setBuggyCode('def same(): pass')

      const result = debugFix.validate('def same(): pass')

      expect(result.valid).toBe(false)
      expect(result.errors).toContain('Buggy code must be different from the reference solution')
    })

    it('should validate hint text', () => {
      debugFix.setBuggyCode('def broken(): return x')
      debugFix.addHint({ level: 1, text: 'Valid hint' })
      // Can't add empty hint directly due to validation in addHint
      // So we load with empty text
      debugFix.loadConfig({
        buggy_code: 'def broken(): return x',
        bug_hints: [
          { level: 1, text: '' },
        ],
        allow_complete_rewrite: false,
      })

      const result = debugFix.validate('def correct(): return y')

      expect(result.valid).toBe(false)
      expect(result.errors).toContain('Hint 1 has empty text')
    })

    it('should return valid for correct configuration', () => {
      debugFix.loadConfig({
        buggy_code: 'def broken(): return x',
        bug_hints: [
          { level: 1, text: 'Check variable' },
        ],
        allow_complete_rewrite: false,
      })

      const result = debugFix.validate('def correct(): return y')

      expect(result.valid).toBe(true)
      expect(result.errors).toHaveLength(0)
    })
  })

  describe('hint management', () => {
    it('should add hints with validation', () => {
      debugFix.addHint({ level: 2, text: 'A helpful hint' })

      expect(debugFix.bugHints.value).toHaveLength(1)
      expect(debugFix.bugHints.value[0].level).toBe(2)
      expect(debugFix.bugHints.value[0].text).toBe('A helpful hint')
    })

    it('should not add empty hints', () => {
      debugFix.addHint({ level: 1, text: '' })
      debugFix.addHint({ level: 1, text: '   ' })

      expect(debugFix.bugHints.value).toHaveLength(0)
    })

    it('should not add hints with invalid levels', () => {
      debugFix.addHint({ level: 0 as 1 | 2 | 3, text: 'Invalid' })
      debugFix.addHint({ level: 4 as 1 | 2 | 3, text: 'Invalid' })

      expect(debugFix.bugHints.value).toHaveLength(0)
    })

    it('should remove hints by index', () => {
      debugFix.addHint({ level: 1, text: 'Hint 1' })
      debugFix.addHint({ level: 2, text: 'Hint 2' })
      debugFix.addHint({ level: 3, text: 'Hint 3' })

      debugFix.removeHint(1)

      expect(debugFix.bugHints.value).toHaveLength(2)
      expect(debugFix.bugHints.value[0].text).toBe('Hint 1')
      expect(debugFix.bugHints.value[1].text).toBe('Hint 3')
    })

    it('should update hints', () => {
      debugFix.addHint({ level: 1, text: 'Original' })

      debugFix.updateHint(0, { text: 'Updated' })
      expect(debugFix.bugHints.value[0].text).toBe('Updated')

      debugFix.updateHint(0, { level: 3 })
      expect(debugFix.bugHints.value[0].level).toBe(3)
    })
  })

  describe('getConfigForApi', () => {
    it('should return config with trimmed hint text', () => {
      debugFix.setBuggyCode('def test(): pass')
      debugFix.loadConfig({
        buggy_code: 'def test(): pass',
        bug_hints: [
          { level: 1, text: '  Hint with spaces  ' },
        ],
        allow_complete_rewrite: true,
      })

      const apiConfig = debugFix.getConfigForApi()

      expect(apiConfig.buggy_code).toBe('def test(): pass')
      expect(apiConfig.bug_hints[0].text).toBe('Hint with spaces')
      expect(apiConfig.allow_complete_rewrite).toBe(true)
    })
  })

  describe('reset', () => {
    it('should reset to initial state', () => {
      debugFix.loadConfig({
        buggy_code: 'def test(): pass',
        bug_hints: [{ level: 1, text: 'Hint' }],
        allow_complete_rewrite: true,
      })

      debugFix.reset()

      expect(debugFix.buggyCode.value).toBe('')
      expect(debugFix.bugHints.value).toHaveLength(0)
      expect(debugFix.allowCompleteRewrite.value).toBe(false)
    })
  })
})
