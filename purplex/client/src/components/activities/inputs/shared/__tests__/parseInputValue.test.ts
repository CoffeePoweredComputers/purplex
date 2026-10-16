import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { flushPromises } from '@vue/test-utils'
import axios from 'axios'
import {
  normalizeContainerType,
  normalizePrimitiveType,
  parseInputValue,
  parseSignatureParams,
} from '../probeArgs'
import { useProbeState } from '../useProbeState'
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
    // A quoted str is a Python string literal, single or double quotes alike
    "'abc'": 'abc',
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
    // Untyped values are Python literals, so single quotes delimit a string
    "'abc'": 'abc',
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

  it('rejects quoted str text that is not one string literal', () => {
    for (const text of ['"a" + "b"', '"abc', "'abc", `'it's'`, '"x" 1']) {
      expect(parseInputValue(text, 'str')).toEqual({ value: text, error: 'literal' })
    }
  })

  it('unquotes single- and double-quoted str literals, escapes included', () => {
    expect(parseInputValue("'x'", 'str')).toEqual({ value: 'x', error: null })
    expect(parseInputValue(`"it's"`, 'str')).toEqual({ value: "it's", error: null })
    expect(parseInputValue(`'a\\'b'`, 'str')).toEqual({ value: "a'b", error: null })
    expect(parseInputValue("''", 'str')).toEqual({ value: '', error: null })
    // Unquoted text is still taken as typed, quotes inside included
    expect(parseInputValue(`it's`, 'str')).toEqual({ value: "it's", error: null })
  })

  it('decodes Python octal and \\U escapes, and rejects \\N{...}', () => {
    expect(parseInputValue(`"\\012"`, 'str')).toEqual({ value: '\n', error: null })
    expect(parseInputValue(`"\\0"`, 'str')).toEqual({ value: '\0', error: null })
    expect(parseInputValue(`"\\1019"`, 'str')).toEqual({ value: 'A9', error: null })
    expect(parseInputValue(`"\\U0001F600"`, 'str')).toEqual({ value: '\u{1F600}', error: null })
    expect(parseInputValue(`["\\x41\\u0042"]`, 'list[str]')).toEqual({ value: ['AB'], error: null })
    expect(parseInputValue(`["\\N{EM DASH}"]`, 'list[str]').error).toBe('list')
    expect(parseInputValue(`["\\U00110000"]`, 'list[str]').error).toBe('list')
  })

  it('does not check unknown types, Optionals or unions', () => {
    for (const type of ['Any', 'Optional[int]', 'Optional[list[int]]', 'list[int] | None', 'list[int] = None', 'MyClass']) {
      expect(normalizePrimitiveType(type)).toBeNull()
      expect(normalizeContainerType(type)).toBeNull()
      expect(parseInputValue('abc', type)).toEqual({ value: 'abc', error: null })
    }
    expect(parseInputValue('False', 'Any')).toEqual({ value: false, error: null })
  })
})

describe('parseInputValue container types', () => {
  it('rejects integers in a list[str] (the item type is checked)', () => {
    expect(parseInputValue('[1, 2]', 'list[str]')).toEqual({
      value: '[1, 2]',
      error: 'listItems',
      errorParams: { kind: 'str' },
    })
    expect(parseInputValue('["a", 2]', 'list[str]').error).toBe('listItems')
    expect(parseInputValue(`['a', "b"]`, 'list[str]')).toEqual({ value: ['a', 'b'], error: null })
  })

  it('does not accept a bool or a float literal as an int item', () => {
    expect(parseInputValue('[1, True]', 'list[int]').error).toBe('listItems')
    expect(parseInputValue('[1, 2.0]', 'list[int]').error).toBe('listItems')
    expect(parseInputValue('[1, -2, +3]', 'list[int]')).toEqual({ value: [1, -2, 3], error: null })
  })

  it('accepts int items for float, as the backend does', () => {
    expect(parseInputValue('[1, 2.5, .5]', 'list[float]')).toEqual({ value: [1, 2.5, 0.5], error: null })
    expect(parseInputValue('[True]', 'list[float]').error).toBe('listItems')
  })

  it('accepts Python literals: tuples, trailing commas, True/False/None', () => {
    expect(parseInputValue('(1, 2)', 'list[int]')).toEqual({ value: [1, 2], error: null })
    expect(parseInputValue('[1, 2,]', 'list[int]')).toEqual({ value: [1, 2], error: null })
    expect(parseInputValue('(5,)', 'tuple[int, ...]')).toEqual({ value: [5], error: null })
    expect(parseInputValue('{3, 1}', 'set[int]')).toEqual({ value: [3, 1], error: null })
    expect(parseInputValue('[True, False]', 'List[bool]')).toEqual({ value: [true, false], error: null })
    expect(parseInputValue('[None, "x", 1]', 'list')).toEqual({ value: [null, 'x', 1], error: null })
  })

  it('requires a list shape for list, tuple and set types', () => {
    for (const type of ['list', 'list[int]', 'tuple', 'set[str]', 'tuple[int, str]']) {
      expect(parseInputValue('abc', type).error).toBe('list')
      expect(parseInputValue('{"a": 1}', type).error).toBe('list')
      expect(parseInputValue('[1, 2', type).error).toBe('list')
      expect(parseInputValue('5', type).error).toBe('list')
    }
  })

  it('checks dict keys and values', () => {
    expect(parseInputValue(`{'a': 1, "b": 2,}`, 'dict[str, int]')).toEqual({ value: { a: 1, b: 2 }, error: null })
    expect(parseInputValue(`{'a': 'x'}`, 'Dict[str, int]')).toEqual({
      value: `{'a': 'x'}`,
      error: 'dictItems',
      errorParams: { key: 'str', value: 'int' },
    })
    expect(parseInputValue('{1: 2}', 'dict[str, int]').error).toBe('dictItems')
    expect(parseInputValue('{1: "a"}', 'dict[int, str]')).toEqual({ value: { 1: 'a' }, error: null })
    expect(parseInputValue('{}', 'dict[str, int]')).toEqual({ value: {}, error: null })
  })

  it('requires a dict shape for dict types', () => {
    for (const type of ['dict', 'dict[str, int]']) {
      expect(parseInputValue('[1]', type).error).toBe('dict')
      expect(parseInputValue('abc', type).error).toBe('dict')
      expect(parseInputValue('{1, 2}', type).error).toBe('dict')
    }
    expect(parseInputValue(`{'a': [1, 'x']}`, 'dict')).toEqual({ value: { a: [1, 'x'] }, error: null })
  })

  it('checks only the outer shape of nested containers', () => {
    expect(parseInputValue('[[1], ["a"]]', 'list[list[int]]')).toEqual({ value: [[1], ['a']], error: null })
    expect(parseInputValue('[1]', 'dict[str, list[int]]').error).toBe('dict')
    expect(parseInputValue(`{'a': 'x'}`, 'dict[str, list[int]]')).toEqual({ value: { a: 'x' }, error: null })
  })

  it('refuses ints too large for JSON inside a container', () => {
    expect(parseInputValue('[12345678901234567891]', 'list[int]').error).toBe('intRange')
  })

  it('keeps a "__proto__" key as plain data', () => {
    const { value } = parseInputValue('{"__proto__": 1}', 'dict[str, int]')
    expect(Object.keys(value as object)).toEqual(['__proto__'])
    expect(Object.getPrototypeOf(value)).toBe(Object.prototype)
  })
})

describe('parseInputValue untyped literals', () => {
  it('rejects text that starts like a literal but does not parse', () => {
    for (const raw of ['[1, 2', '(1, 2', '{"a": 1', '"abc', "'abc", '[1 2]', '[1,, 2]']) {
      expect(parseInputValue(raw, '')).toEqual({ value: raw, error: 'literal' })
    }
  })

  it('parses Python literals and keeps other text as a string', () => {
    expect(parseInputValue('[True, None, \'x\']', 'Any')).toEqual({ value: [true, null, 'x'], error: null })
    expect(parseInputValue('(1,)', '')).toEqual({ value: [1], error: null })
    expect(parseInputValue('(1)', '')).toEqual({ value: 1, error: null })
    expect(parseInputValue(`'it\\'s'`, '')).toEqual({ value: "it's", error: null })
    expect(parseInputValue('"tab\\there"', '')).toEqual({ value: 'tab\there', error: null })
    expect(parseInputValue('hello world', '')).toEqual({ value: 'hello world', error: null })
    expect(parseInputValue('0x10', '')).toEqual({ value: '0x10', error: null })
  })
})

describe('normalizeContainerType', () => {
  it('recognises one-level containers and their primitive items', () => {
    expect(normalizeContainerType('list[str]')).toEqual({ container: 'list', item: 'str' })
    expect(normalizeContainerType('Tuple[Integer, ...]')).toEqual({ container: 'list', item: 'int' })
    expect(normalizeContainerType('tuple[int, str]')).toEqual({ container: 'list', item: null })
    expect(normalizeContainerType('set')).toEqual({ container: 'list', item: null })
    expect(normalizeContainerType('list[Any] = []')).toEqual({ container: 'list', item: null })
    expect(normalizeContainerType('dict[str, int]')).toMatchObject({ container: 'dict', key: 'str', value: 'int' })
    expect(normalizeContainerType('dict')).toMatchObject({ container: 'dict', key: null, value: null })
  })

  it('returns null for non-containers', () => {
    for (const type of ['int', 'str', 'Any', 'listing', 'Optional[list[int]]', 'dict[str, int] | None']) {
      expect(normalizeContainerType(type)).toBeNull()
    }
  })
})

describe('parseSignatureParams', () => {
  it('keeps bracketed types and defaults as one parameter (#160)', () => {
    expect(
      parseSignatureParams(
        `def schedule(tasks: list[str], weights: dict[str, int], pair: tuple[int, str] = (1, "a,b"), opts={'k': 1}) -> int`
      )
    ).toEqual([
      { name: 'tasks', type: 'list[str]' },
      { name: 'weights', type: 'dict[str, int]' },
      { name: 'pair', type: 'tuple[int, str] = (1, "a,b")' },
      { name: 'opts', type: 'Any' },
    ])
  })

  it('handles empty and trailing-comma parameter lists', () => {
    expect(parseSignatureParams('def f() -> int')).toEqual([])
    expect(parseSignatureParams('def f(x: int,) -> int')).toEqual([{ name: 'x', type: 'int' }])
    expect(parseSignatureParams('no parens')).toEqual([])
    expect(parseSignatureParams(`def f(open: str = '(', x: int) -> int`)).toEqual([
      { name: 'open', type: "str = '('" },
      { name: 'x', type: 'int' },
    ])
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

    state.setArgsLine('abc')
    await nextTick()
    expect(state.hasValidInputs.value).toBe(false)
    expect(state.inputErrors.value.x).toBe('Must be a whole number (e.g. 5)')

    state.setArgsLine('5')
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

  it('translates container errors with their expected kinds', () => {
    const state = setup('def f(tasks: list[str], weights: dict[str, int]) -> int')
    state.setArgsLine('[1, 2], [1]')
    expect(state.inputErrors.value).toEqual({
      tasks: 'Every item must be str',
      weights: 'Must be a dict, e.g. {"a": 1}',
    })
    state.setArgsLine(`[1, 2], {'a': 'b'}`)
    expect(state.inputErrors.value.weights).toBe('Keys must be str and values int')
    expect(state.hasValidInputs.value).toBe(false)
  })

  it('posts only type-valid, parsed inputs', async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: { success: true, result: 10 } })
    const state = setup('def f(x: int) -> int')
    await flushPromises()
    expect(state.canProbe.value).toBe(true)

    state.setArgsLine('abc')
    await state.executeProbe()
    expect(axios.post).not.toHaveBeenCalled()

    state.setArgsLine('5')
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
