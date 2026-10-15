import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { flushPromises } from '@vue/test-utils'
import axios from 'axios'
import { normalizePrimitiveType, parseInputValue, useProbeState } from '../useProbeState'
import type { ActivityProblem } from '../../../types'
import { withSetup } from '@/test/setup'

vi.mock('axios')

const INPUTS = ['5', 'abc', '"abc"', "'abc'", 'True', 'None', '1.5', '[1,2]'] as const

const ERR = Symbol('error')

/** Expected parsed value per declared type; ERR means the input must be rejected. */
const EXPECTED: Record<string, Record<(typeof INPUTS)[number], unknown>> = {
  int: {
    '5': 5,
    abc: ERR,
    '"abc"': ERR,
    "'abc'": ERR,
    True: ERR,
    None: ERR,
    '1.5': ERR,
    '[1,2]': ERR,
  },
  str: {
    '5': '5',
    abc: 'abc',
    '"abc"': 'abc',
    "'abc'": "'abc'",
    True: 'True',
    None: 'None',
    '1.5': '1.5',
    '[1,2]': '[1,2]',
  },
  bool: {
    '5': ERR,
    abc: ERR,
    '"abc"': ERR,
    "'abc'": ERR,
    True: true,
    None: ERR,
    '1.5': ERR,
    '[1,2]': ERR,
  },
  float: {
    '5': 5,
    abc: ERR,
    '"abc"': ERR,
    "'abc'": ERR,
    True: ERR,
    None: ERR,
    '1.5': 1.5,
    '[1,2]': ERR,
  },
  '': {
    '5': 5,
    abc: 'abc',
    '"abc"': 'abc',
    "'abc'": "'abc'",
    True: true,
    None: null,
    '1.5': 1.5,
    '[1,2]': [1, 2],
  },
}

const MATRIX = Object.entries(EXPECTED).flatMap(([type, byInput]) =>
  INPUTS.map(raw => [raw, type, byInput[raw]] as const)
)

describe('parseInputValue', () => {
  it.each(MATRIX)('parses %j as type %j', (raw, type, expected) => {
    const result = parseInputValue(raw, type)
    if (expected === ERR) {
      expect(result.error).toBe(normalizePrimitiveType(type))
    } else {
      expect(result.error).toBeNull()
      expect(result.value).toEqual(expected)
    }
  })

  it('accepts type aliases case-insensitively', () => {
    expect(parseInputValue('7', 'Integer')).toEqual({ value: 7, error: null })
    expect(parseInputValue('2.5', 'NUMBER')).toEqual({ value: 2.5, error: null })
    expect(parseInputValue('FALSE', 'Boolean')).toEqual({ value: false, error: null })
    expect(parseInputValue('5', 'String')).toEqual({ value: '5', error: null })
    expect(parseInputValue('x', 'integer').error).toBe('int')
  })

  it('checks types that carry a default value', () => {
    expect(parseInputValue('4', 'int = 3')).toEqual({ value: 4, error: null })
    expect(parseInputValue('abc', 'int = 3').error).toBe('int')
  })

  it('treats a None default as implicit Optional and does not check it', () => {
    expect(normalizePrimitiveType('int = None')).toBeNull()
    expect(parseInputValue('null', 'int = None')).toEqual({ value: null, error: null })
    expect(parseInputValue('None', 'int = None')).toEqual({ value: null, error: null })
    expect(parseInputValue('4', 'int = None')).toEqual({ value: 4, error: null })
  })

  it('trims surrounding whitespace before validating', () => {
    expect(parseInputValue('  42  ', 'int')).toEqual({ value: 42, error: null })
    expect(parseInputValue(' true ', 'bool')).toEqual({ value: true, error: null })
    expect(parseInputValue('  hi  ', 'str')).toEqual({ value: 'hi', error: null })
  })

  it('accepts signed ints and rejects decimals', () => {
    expect(parseInputValue('-7', 'int')).toEqual({ value: -7, error: null })
    expect(parseInputValue('+7', 'int')).toEqual({ value: 7, error: null })
    expect(parseInputValue('5.0', 'int').error).toBe('int')
    expect(parseInputValue('1e3', 'int').error).toBe('int')
  })

  it('accepts -0 as an int', () => {
    const result = parseInputValue('-0', 'int')
    expect(result.error).toBeNull()
    expect(result.value === 0).toBe(true)
  })

  it('rejects ints outside the safe-integer range', () => {
    expect(parseInputValue('12345678901234567891', 'int').error).toBe('intRange')
    expect(parseInputValue('9007199254740991', 'int')).toEqual({ value: 9007199254740991, error: null })
  })

  it('accepts Python float literal forms and rejects hex/binary/octal', () => {
    expect(parseInputValue('.5', 'float')).toEqual({ value: 0.5, error: null })
    expect(parseInputValue('5.', 'float')).toEqual({ value: 5, error: null })
    expect(parseInputValue('0x10', 'float').error).toBe('float')
    expect(parseInputValue('0b11', 'float').error).toBe('float')
  })

  it('accepts exponent floats but rejects non-finite ones', () => {
    expect(parseInputValue('1e3', 'float')).toEqual({ value: 1000, error: null })
    expect(parseInputValue('1e400', 'float').error).toBe('float')
    expect(parseInputValue('Infinity', 'float').error).toBe('float')
  })

  it('rejects empty input for numeric and bool types', () => {
    expect(parseInputValue('', 'int').error).toBe('int')
    expect(parseInputValue('   ', 'float').error).toBe('float')
    expect(parseInputValue('', 'bool').error).toBe('bool')
    expect(parseInputValue('', 'str')).toEqual({ value: '', error: null })
  })

  it('keeps malformed quoted strings as raw text', () => {
    expect(parseInputValue('"a" + "b"', 'str')).toEqual({ value: '"a" + "b"', error: null })
  })

  it('does not check unknown or compound types', () => {
    for (const type of ['Any', 'list', 'list[int]', 'Optional[int]', 'dict', 'MyClass']) {
      expect(normalizePrimitiveType(type)).toBeNull()
      expect(parseInputValue('abc', type)).toEqual({ value: 'abc', error: null })
    }
    expect(parseInputValue('False', 'Any')).toEqual({ value: false, error: null })
  })
})

describe('normalizePrimitiveType', () => {
  it('maps the alias table to canonical types', () => {
    expect(normalizePrimitiveType('int')).toBe('int')
    expect(normalizePrimitiveType('integer')).toBe('int')
    expect(normalizePrimitiveType('float')).toBe('float')
    expect(normalizePrimitiveType('number')).toBe('float')
    expect(normalizePrimitiveType('bool')).toBe('bool')
    expect(normalizePrimitiveType('boolean')).toBe('bool')
    expect(normalizePrimitiveType('str')).toBe('str')
    expect(normalizePrimitiveType('string')).toBe('str')
  })

  it('strips defaults and whitespace, and returns null for missing hints', () => {
    expect(normalizePrimitiveType('  Int = 3 ')).toBe('int')
    expect(normalizePrimitiveType('')).toBeNull()
    expect(normalizePrimitiveType(undefined)).toBeNull()
    expect(normalizePrimitiveType('constructor')).toBeNull()
  })
})

describe('useProbeState input validation', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  function setup(signature: string) {
    vi.mocked(axios.get).mockResolvedValue({ data: { can_probe: true, mode: 'explore' } })
    const problem = {
      slug: 'typed-probe',
      probe_config: { function_signature: signature },
    } as unknown as ActivityProblem
    return withSetup(() => useProbeState(problem))
  }

  it('flags a non-integer value for an int parameter and clears once fixed', async () => {
    const state = setup('def f(x: int) -> int')

    state.updateProbeInput('x', 'abc')
    await nextTick()
    expect(state.hasValidInputs.value).toBe(false)
    expect(state.inputErrors.value.x).toBe('Must be a whole number (e.g. 5)')

    state.updateProbeInput('x', '5')
    await nextTick()
    expect(state.hasValidInputs.value).toBe(true)
    expect(state.inputErrors.value).toEqual({})
  })

  it('does not report errors for empty fields but still requires a value', () => {
    const state = setup('def f(x: int) -> int')
    expect(state.inputErrors.value).toEqual({})
    expect(state.hasValidInputs.value).toBe(false)
  })

  it('keeps type defaults but strips name defaults in the fallback signature parser', () => {
    const state = setup('def f(n: int = 3, label=2) -> int')
    expect(state.parameters.value).toEqual([
      { name: 'n', type: 'int = 3' },
      { name: 'label', type: 'Any' },
    ])
  })

  it('posts only type-valid, parsed inputs', async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: { success: true, result: 10 } })
    const state = setup('def f(x: int) -> int')
    await flushPromises()
    expect(state.canProbe.value).toBe(true)

    state.updateProbeInput('x', 'abc')
    await state.executeProbe()
    expect(axios.post).not.toHaveBeenCalled()

    state.updateProbeInput('x', '5')
    await state.executeProbe()
    expect(axios.post).toHaveBeenCalledWith('/api/problems/typed-probe/probe/', { input: { x: 5 } })
  })
})

describe('useProbeState status display', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  function setup(status: Record<string, unknown>) {
    vi.mocked(axios.get).mockResolvedValue({ data: status })
    const problem = {
      slug: 'status-probe',
      probe_config: { function_signature: 'def f(x: int) -> int' },
    } as unknown as ActivityProblem
    return withSetup(() => useProbeState(problem))
  }

  it('shows the backend remaining count in block mode without a hint', async () => {
    const state = setup({
      mode: 'block',
      remaining: 7,
      used: 3,
      can_probe: true,
      message: '7 probes remaining',
    })
    await flushPromises()
    expect(state.probeCountDisplay.value).toBe('7 left')
    expect(state.probeStatusHint.value).toBe('')
  })

  it('shows a translated cooldown refill hint when exhausted', async () => {
    const state = setup({
      mode: 'cooldown',
      remaining: 0,
      used: 10,
      can_probe: false,
      message: 'backend English text',
      submissions_to_next_refill: 2,
    })
    await flushPromises()
    expect(state.probeCountDisplay.value).toBe('0 left')
    expect(state.probeStatusHint.value).toBe(
      'No probes remaining. Submit 2 more times to unlock more probes.'
    )
  })

  it('uses the singular refill hint for one remaining submission', async () => {
    const state = setup({
      mode: 'cooldown',
      remaining: 0,
      used: 10,
      can_probe: false,
      message: 'backend English text',
      submissions_to_next_refill: 1,
    })
    await flushPromises()
    expect(state.probeStatusHint.value).toBe(
      'No probes remaining. Submit 1 more time to unlock more probes.'
    )
  })

  it('shows the translated exhausted hint in block mode', async () => {
    const state = setup({
      mode: 'block',
      remaining: 0,
      used: 10,
      can_probe: false,
      message: 'backend English text',
    })
    await flushPromises()
    expect(state.probeStatusHint.value).toBe('No probes remaining.')
  })
})
