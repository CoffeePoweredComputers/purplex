import { beforeEach, describe, expect, it } from 'vitest'
import { type RefuteConfig, useRefuteConfig } from '../useRefuteConfig'
import { withSetup } from '@/test/setup'

describe('useRefuteConfig', () => {
  let refute: ReturnType<typeof useRefuteConfig>

  beforeEach(() => {
    refute = withSetup(() => useRefuteConfig())
  })

  describe('initial state', () => {
    it('should initialize with empty values', () => {
      expect(refute.claimText.value).toBe('')
      expect(refute.claimPredicate.value).toBe('')
      expect(refute.expectedCounterexample.value).toBe('')
      expect(refute.hasClaim.value).toBe(false)
      expect(refute.hasPredicate.value).toBe(false)
    })

    it('should consider empty JSON as valid', () => {
      expect(refute.isValidJson.value).toBe(true)
      expect(refute.jsonError.value).toBe(null)
    })
  })

  describe('loadConfig', () => {
    it('should load config with all fields', () => {
      const config: RefuteConfig = {
        claim_text: 'This function always returns a positive number',
        claim_predicate: 'result > 0',
        expected_counterexample: '{"x": -1}',
      }

      refute.loadConfig(config)

      expect(refute.claimText.value).toBe('This function always returns a positive number')
      expect(refute.claimPredicate.value).toBe('result > 0')
      expect(refute.expectedCounterexample.value).toBe('{"x": -1}')
    })

    it('should convert JSON object to string on load', () => {
      const config = {
        claim_text: 'Test claim',
        claim_predicate: 'x > 0',
        expected_counterexample: { x: -1, y: 0 },
      } as unknown as Partial<RefuteConfig>

      refute.loadConfig(config)

      // Should be converted to pretty-printed JSON string
      expect(refute.expectedCounterexample.value).toBe('{\n  "x": -1,\n  "y": 0\n}')
    })

    it('should handle null config gracefully', () => {
      refute.setClaimText('Some claim')
      refute.loadConfig(null)

      expect(refute.claimText.value).toBe('')
      expect(refute.claimPredicate.value).toBe('')
      expect(refute.expectedCounterexample.value).toBe('')
    })

    it('should handle undefined config gracefully', () => {
      refute.setClaimText('Some claim')
      refute.loadConfig(undefined)

      expect(refute.claimText.value).toBe('')
    })
  })

  describe('JSON parsing', () => {
    it('should parse valid JSON counterexample', () => {
      refute.setExpectedCounterexample('{"x": -1, "y": "test"}')

      expect(refute.isValidJson.value).toBe(true)
      expect(refute.parsedCounterexample.value).toEqual({ x: -1, y: 'test' })
      expect(refute.jsonError.value).toBe(null)
    })

    it('should handle invalid JSON gracefully', () => {
      refute.setExpectedCounterexample('{invalid json}')

      expect(refute.isValidJson.value).toBe(false)
      expect(refute.parsedCounterexample.value).toBe(null)
      expect(refute.jsonError.value).toContain('Invalid JSON')
    })

    it('should reject non-object JSON', () => {
      refute.setExpectedCounterexample('"just a string"')

      expect(refute.isValidJson.value).toBe(false)
      expect(refute.parsedCounterexample.value).toBe(null)
      expect(refute.jsonError.value).toBe('Expected counterexample must be a JSON object')
    })

    it('should accept empty string as valid', () => {
      refute.setExpectedCounterexample('')

      expect(refute.isValidJson.value).toBe(true)
      expect(refute.parsedCounterexample.value).toBe(null)
      expect(refute.jsonError.value).toBe(null)
    })

    it('should accept valid complex JSON', () => {
      refute.setExpectedCounterexample('{"list": [1, 2, 3], "nested": {"a": 1}}')

      expect(refute.isValidJson.value).toBe(true)
      expect(refute.parsedCounterexample.value).toEqual({
        list: [1, 2, 3],
        nested: { a: 1 },
      })
    })
  })

  describe('claim pattern detection', () => {
    it('should detect good claim patterns with "always"', () => {
      refute.setClaimText('This function always returns true')
      expect(refute.hasGoodClaimPattern.value).toBe(true)
      expect(refute.claimWarning.value).toBe(null)
    })

    it('should detect good claim patterns with "never"', () => {
      refute.setClaimText('The result will never be negative')
      expect(refute.hasGoodClaimPattern.value).toBe(true)
    })

    it('should detect good claim patterns with "for all"', () => {
      refute.setClaimText('For all inputs, the output is positive')
      expect(refute.hasGoodClaimPattern.value).toBe(true)
    })

    it('should detect good claim patterns with "every"', () => {
      refute.setClaimText('Every element in the list is sorted')
      expect(refute.hasGoodClaimPattern.value).toBe(true)
    })

    it('should warn when claim lacks universal terms', () => {
      refute.setClaimText('The function returns a positive number')

      expect(refute.hasGoodClaimPattern.value).toBe(false)
      expect(refute.claimWarning.value).toContain('Consider using absolute terms')
    })

    it('should not warn on empty claims', () => {
      refute.setClaimText('')

      expect(refute.hasGoodClaimPattern.value).toBe(true)
      expect(refute.claimWarning.value).toBe(null)
    })
  })

  describe('predicate validation', () => {
    it('should accept valid predicates', () => {
      refute.setClaimPredicate('result > 0')
      expect(refute.predicateError.value).toBe(null)

      refute.setClaimPredicate('len(x) == 5')
      expect(refute.predicateError.value).toBe(null)
    })

    it('should reject predicates with import statements', () => {
      refute.setClaimPredicate('import os; result > 0')
      expect(refute.predicateError.value).toContain('cannot contain import')
    })

    it('should reject predicates with dunder methods', () => {
      refute.setClaimPredicate('x.__class__ == int')
      expect(refute.predicateError.value).toContain('dunder methods')
    })

    it('should detect mismatched parentheses', () => {
      refute.setClaimPredicate('(x > 0')
      expect(refute.predicateError.value).toContain('Mismatched parentheses')

      refute.setClaimPredicate('x > 0)')
      expect(refute.predicateError.value).toContain('Mismatched parentheses')
    })

    it('should accept empty predicate', () => {
      refute.setClaimPredicate('')
      expect(refute.predicateError.value).toBe(null)
    })
  })

  describe('getConfigForApi', () => {
    it('should return trimmed values', () => {
      refute.setClaimText('  Claim with spaces  ')
      refute.setClaimPredicate('  result > 0  ')
      refute.setExpectedCounterexample('  {"x": 1}  ')

      const config = refute.getConfigForApi()

      expect(config.claim_text).toBe('Claim with spaces')
      expect(config.claim_predicate).toBe('result > 0')
      expect(config.expected_counterexample).toBe('{"x": 1}')
    })

    it('should return empty strings for unset values', () => {
      const config = refute.getConfigForApi()

      expect(config.claim_text).toBe('')
      expect(config.claim_predicate).toBe('')
      expect(config.expected_counterexample).toBe('')
    })
  })

  describe('setters', () => {
    it('should set claim text', () => {
      refute.setClaimText('New claim')
      expect(refute.claimText.value).toBe('New claim')
      expect(refute.hasClaim.value).toBe(true)
    })

    it('should set claim predicate', () => {
      refute.setClaimPredicate('x > 0')
      expect(refute.claimPredicate.value).toBe('x > 0')
      expect(refute.hasPredicate.value).toBe(true)
    })

    it('should set expected counterexample', () => {
      refute.setExpectedCounterexample('{"x": -1}')
      expect(refute.expectedCounterexample.value).toBe('{"x": -1}')
    })
  })

  describe('reset', () => {
    it('should reset to initial state', () => {
      refute.setClaimText('Test claim')
      refute.setClaimPredicate('x > 0')
      refute.setExpectedCounterexample('{"x": 1}')

      refute.reset()

      expect(refute.claimText.value).toBe('')
      expect(refute.claimPredicate.value).toBe('')
      expect(refute.expectedCounterexample.value).toBe('')
      expect(refute.hasClaim.value).toBe(false)
    })
  })
})
