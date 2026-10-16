import { describe, expect, it } from 'vitest'
import { reconstructFunctionCall } from '../functionCall'

describe('reconstructFunctionCall', () => {
  it('renders a stored argument list as the call arguments', () => {
    expect(reconstructFunctionCall('clamp', [-3])).toBe('clamp(-3)')
    expect(reconstructFunctionCall('add', [1, 2])).toBe('add(1, 2)')
    expect(reconstructFunctionCall('f', [])).toBe('f()')
  })

  it('keeps list arguments bracketed inside the argument list', () => {
    expect(reconstructFunctionCall('total', [[1, 2], 'x', true, null])).toBe('total([1, 2], "x", True, None)')
  })

  it('keeps pre-formatted strings and the missing-input fallback', () => {
    expect(reconstructFunctionCall('f', '1, 2')).toBe('f(1, 2)')
    expect(reconstructFunctionCall('f', undefined)).toBe('f(...)')
    expect(reconstructFunctionCall('f', null)).toBe('f(...)')
  })

  // Expected strings are BaseHandler._format_function_call's output for the
  // same arguments (json.dumps for top-level str, repr() for everything else).
  it('formats nested strings and dicts with Python repr like the backend', () => {
    expect(reconstructFunctionCall('f', [[['a']], { k: 1, v: ['x', null, true] }])).toBe(
      "f([['a']], {'k': 1, 'v': ['x', None, True]})",
    )
    expect(reconstructFunctionCall('h', [{}, [], -3, 0.5])).toBe('h({}, [], -3, 0.5)')
  })

  it('escapes top-level strings like json.dumps and nested ones like repr', () => {
    const BACKSLASH = String.fromCharCode(92)
    expect(
      reconstructFunctionCall('g', ['it\'s "q"\n', ["it's"], 'caf' + String.fromCharCode(0xe9), ['tab\there', 'b\\s']]),
    ).toBe(String.raw`g("it's \"q\"\n", ["it's"], "caf${BACKSLASH}u00e9", ['tab\there', 'b\\s'])`)
  })
})
