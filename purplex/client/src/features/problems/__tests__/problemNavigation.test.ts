import { describe, expect, it } from 'vitest'
import { parseProblemQueryParam } from '../problemNavigation'
import type { LocationQuery } from 'vue-router'

describe('parseProblemQueryParam', () => {
  const problemsLength = 5 // Simulate a problem set with 5 problems

  it('returns 0 when query param is missing', () => {
    const query: LocationQuery = {}
    expect(parseProblemQueryParam(query, problemsLength)).toBe(0)
  })

  it('returns 0 when query param is undefined', () => {
    const query: LocationQuery = { p: undefined }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(0)
  })

  it('parses valid numeric index', () => {
    const query: LocationQuery = { p: '3' }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(3)
  })

  it('returns 0 for index 0 (first problem)', () => {
    const query: LocationQuery = { p: '0' }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(0)
  })

  it('parses last valid index', () => {
    const query: LocationQuery = { p: '4' }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(4)
  })

  it('handles string array (takes first value)', () => {
    const query: LocationQuery = { p: ['1', '2', '3'] }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(1)
  })

  it('returns 0 for empty array', () => {
    const query: LocationQuery = { p: [] }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(0)
  })

  it('returns 0 for negative index', () => {
    const query: LocationQuery = { p: '-1' }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(0)
  })

  it('returns 0 for out of bounds index', () => {
    const query: LocationQuery = { p: '999' }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(0)
  })

  it('returns 0 for index equal to problems length', () => {
    const query: LocationQuery = { p: '5' }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(0)
  })

  it('returns 0 for non-numeric string', () => {
    const query: LocationQuery = { p: 'abc' }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(0)
  })

  it('returns 0 for empty string', () => {
    const query: LocationQuery = { p: '' }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(0)
  })

  it('truncates decimal to integer', () => {
    const query: LocationQuery = { p: '2.7' }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(2)
  })

  it('handles zero problems length', () => {
    const query: LocationQuery = { p: '0' }
    expect(parseProblemQueryParam(query, 0)).toBe(0)
  })

  it('preserves other query params (not tested here but documented)', () => {
    // This is tested at integration level - the function only reads 'p'
    const query: LocationQuery = { p: '2', course_id: 'CS101' }
    expect(parseProblemQueryParam(query, problemsLength)).toBe(2)
  })
})
