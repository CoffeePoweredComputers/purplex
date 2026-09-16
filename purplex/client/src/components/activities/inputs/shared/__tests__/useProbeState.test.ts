/**
 * Probe input parsing.
 *
 * The oracle runs the learner's inputs as real Python, so a value that reaches
 * it with the wrong type fails inside the sandbox rather than in validation.
 * Typing "1, 2, 3" for a list[int] parameter used to send the literal string
 * and surface as "'>' not supported between instances of 'str' and 'int'".
 */
import { describe, expect, it } from 'vitest'
import { parseProbeInputValue } from '../useProbeState'

describe('parseProbeInputValue', () => {
  describe('JSON input', () => {
    it('parses a bracketed list', () => {
      expect(parseProbeInputValue('[1, 2, 3]', 'list[int]')).toEqual([1, 2, 3])
    })

    it('parses nested structures', () => {
      expect(parseProbeInputValue('[[1, 2], [3]]', 'list[list[int]]')).toEqual([[1, 2], [3]])
    })

    it('parses a bare number', () => {
      expect(parseProbeInputValue('42', 'int')).toBe(42)
    })
  })

  describe('containers typed without brackets', () => {
    it('parses a comma-separated list of ints', () => {
      expect(parseProbeInputValue('1, 2, 3', 'list[int]')).toEqual([1, 2, 3])
    })

    it('parses without spaces', () => {
      expect(parseProbeInputValue('1,2,3', 'list[int]')).toEqual([1, 2, 3])
    })

    it('parses floats by element type', () => {
      expect(parseProbeInputValue('1.5, 2.5', 'list[float]')).toEqual([1.5, 2.5])
    })

    it('keeps strings as strings', () => {
      expect(parseProbeInputValue('a, b', 'list[str]')).toEqual(['a', 'b'])
    })

    it('infers element types for an unannotated container', () => {
      expect(parseProbeInputValue('1, true, x', 'list')).toEqual([1, true, 'x'])
    })

    it('handles tuple and set annotations the same way', () => {
      expect(parseProbeInputValue('1, 2', 'tuple[int]')).toEqual([1, 2])
      expect(parseProbeInputValue('1, 2', 'set[int]')).toEqual([1, 2])
    })

    it('tolerates an unclosed bracket, which is a typo not a different intent', () => {
      expect(parseProbeInputValue('[1, 2, 3', 'list[int]')).toEqual([1, 2, 3])
    })

    it('returns an empty list for empty input', () => {
      expect(parseProbeInputValue('', 'list[int]')).toEqual([])
    })

    it('is case-insensitive about the annotation', () => {
      expect(parseProbeInputValue('1, 2', 'List[int]')).toEqual([1, 2])
    })
  })

  describe('scalars', () => {
    it('parses ints and floats', () => {
      expect(parseProbeInputValue('7', 'int')).toBe(7)
      expect(parseProbeInputValue('2.5', 'float')).toBe(2.5)
    })

    it('parses booleans written the Python way', () => {
      expect(parseProbeInputValue('True', 'bool')).toBe(true)
      expect(parseProbeInputValue('false', 'bool')).toBe(false)
    })

    it('leaves a non-numeric value alone rather than producing NaN', () => {
      expect(parseProbeInputValue('abc', 'int')).toBe('abc')
    })

    it('keeps an unquoted string as a string', () => {
      expect(parseProbeInputValue('hello', 'str')).toBe('hello')
    })
  })

  describe('the reported failure', () => {
    it('never hands a list[int] parameter a bare string', () => {
      // The exact input that produced the Python TypeError.
      const parsed = parseProbeInputValue('1, 2, 3', 'list[int]')

      expect(typeof parsed).not.toBe('string')
      expect(parsed).toEqual([1, 2, 3])
    })
  })
})
