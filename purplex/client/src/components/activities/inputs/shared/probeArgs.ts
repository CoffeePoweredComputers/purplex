/**
 * probeArgs - Parsing for the probe call line.
 *
 * Splits the argument list on top-level commas, maps positional and keyword
 * arguments onto the signature's parameters, and parses each value as a
 * Python literal checked against its declared type. Pure functions, no Vue.
 */
import type { ProbeParameter } from '../../types'
import { hasUnsafeInt, parsePythonLiteral, type PyNode, toValue } from './pythonLiteral'

/** Canonical primitive parameter types that probe inputs are validated against. */
export type PrimitiveType = 'int' | 'float' | 'bool' | 'str'

/** Error code for a probe input that does not match its declared type. */
export type ProbeInputError =
  | 'int'
  | 'intRange'
  | 'float'
  | 'bool'
  | 'list'
  | 'listItems'
  | 'dict'
  | 'dictItems'
  | 'literal'

export interface ParsedProbeInput {
  value: unknown
  error: ProbeInputError | null
  /** Interpolation values for the error message (e.g. the expected item kind). */
  errorParams?: Record<string, string>
}

/** A declared one-level container type: list/tuple/set[T] or dict[K, V]. */
export type ContainerType =
  | { container: 'list'; item: PrimitiveType | null }
  | {
      container: 'dict'
      key: PrimitiveType | null
      value: PrimitiveType | null
      keyLabel: string
      valueLabel: string
    }

// Must stay identical to _PRIMITIVE_ALIASES in
// purplex/problems_app/services/probe_service.py (issue #135).
const PRIMITIVE_ALIASES = new Map<string, PrimitiveType>([
  ['int', 'int'],
  ['integer', 'int'],
  ['float', 'float'],
  ['number', 'float'],
  ['bool', 'bool'],
  ['boolean', 'bool'],
  ['str', 'str'],
  ['string', 'str'],
])

const INT_PATTERN = /^[+-]?\d+$/
const BOOL_PATTERN = /^(true|false)$/i
// Python float literal syntax: no hex/binary/octal, which Number() would otherwise accept
const FLOAT_PATTERN = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/

const OPENERS: Record<string, string> = { '(': ')', '[': ']', '{': '}' }
const CLOSERS = new Set([')', ']', '}'])

/**
 * Split text on a separator (default a comma) that is not nested in (), [], {}
 * or inside a quoted string. Mirrors _split_top_level in probe_service.py.
 *
 * Parts are returned untrimmed; a backslash escapes the next character inside
 * quotes, and an unbalanced closer never takes the depth below zero.
 */
export function splitTopLevel(text: string, sep = ','): string[] {
  const parts: string[] = []
  let depth = 0
  let quote: string | null = null
  let current = ''
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    current += ch
    if (quote) {
      if (ch === '\\' && i + 1 < text.length) {
        current += text[++i]
      } else if (ch === quote) {
        quote = null
      }
      continue
    }
    if (ch === '"' || ch === "'") {
      quote = ch
    } else if (ch in OPENERS) {
      depth++
    } else if (CLOSERS.has(ch)) {
      depth = Math.max(depth - 1, 0)
    } else if (ch === sep && depth === 0) {
      parts.push(current.slice(0, -1))
      current = ''
    }
  }
  parts.push(current)
  return parts
}

/** Strip a trailing `= default` from a type hint; null when the default is None (implicit Optional). */
function stripTypeDefault(type: string): string | null {
  const [base, ...defaultParts] = type.split('=')
  if (defaultParts.join('=').trim() === 'None') {
    return null
  }
  return base.trim()
}

/**
 * Map a declared parameter type hint to its canonical primitive type.
 *
 * Strips a trailing ` = default`, trims, lowercases, and resolves aliases.
 * A `= None` default is an implicit Optional and is not checked.
 * Returns null for anything that is not a primitive (missing hint, Any,
 * list[int], Optional[int], dict, custom classes, ...).
 */
export function normalizePrimitiveType(type: string | null | undefined): PrimitiveType | null {
  if (!type) {
    return null
  }
  const base = stripTypeDefault(type)
  return base === null ? null : PRIMITIVE_ALIASES.get(base.toLowerCase()) ?? null
}

/**
 * Map a declared parameter type hint to a one-level container type.
 *
 * Recognises list/tuple/set (bare, [T] or tuple[T, ...]) and dict (bare or [K, V]),
 * case-insensitively. Item types that are not primitives (Any, nested containers,
 * heterogeneous tuples) are left unchecked; only the container shape is checked.
 * Returns null for everything else, including Optional[...], unions and `= None`
 * defaults. Mirrors normalize_container_type in probe_service.py.
 */
export function normalizeContainerType(type: string | null | undefined): ContainerType | null {
  if (!type) {
    return null
  }
  const base = stripTypeDefault(type)
  // Unions such as `list[int] | None` are not checked
  if (base === null || splitTopLevel(base, '|').length > 1) {
    return null
  }
  const match = base.match(/^(list|tuple|set|dict)\s*(?:\[([\s\S]*)\])?$/i)
  if (!match) {
    return null
  }
  const kind = match[1].toLowerCase()
  const args = match[2] === undefined ? [] : splitTopLevel(match[2]).map(a => a.trim())
  if (kind === 'dict') {
    const [keyLabel = 'Any', valueLabel = 'Any'] = args.length === 2 ? args : []
    return {
      container: 'dict',
      key: args.length === 2 ? normalizePrimitiveType(keyLabel) : null,
      value: args.length === 2 ? normalizePrimitiveType(valueLabel) : null,
      keyLabel,
      valueLabel,
    }
  }
  const homogeneous = args.length === 1 || (kind === 'tuple' && args.length === 2 && args[1] === '...')
  return { container: 'list', item: homogeneous ? normalizePrimitiveType(args[0]) : null }
}

/**
 * JSON with object keys sorted at every level. Python dicts are unordered, so two
 * probe inputs that differ only in key order are the same call. Lists keep order.
 */
export function stableStringify(value: unknown): string {
  return JSON.stringify(value, (_key, v: unknown) =>
    v !== null && typeof v === 'object' && !Array.isArray(v)
      ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)))
      : v
  )
}

/** Mirrors _matches_primitive: bool is not an int, an int is accepted for float. */
function matchesPrimitive(node: PyNode, kind: PrimitiveType): boolean {
  switch (kind) {
    case 'int':
      return node.k === 'int'
    case 'float':
      return node.k === 'int' || node.k === 'float'
    case 'bool':
      return node.k === 'bool'
    case 'str':
      return node.k === 'str'
  }
}

function parseContainer(text: string, spec: ContainerType): ParsedProbeInput {
  const node = parsePythonLiteral(text)
  if (spec.container === 'dict') {
    if (node?.k !== 'dict') {
      return { value: text, error: 'dict' }
    }
    if (hasUnsafeInt(node)) {
      return { value: text, error: 'intRange' }
    }
    const { key, value } = spec
    const itemsMatch = node.entries.every(
      ([k, v]) => (!key || matchesPrimitive(k, key)) && (!value || matchesPrimitive(v, value))
    )
    return itemsMatch
      ? { value: toValue(node), error: null }
      : { value: text, error: 'dictItems', errorParams: { key: spec.keyLabel, value: spec.valueLabel } }
  }
  if (node?.k !== 'list') {
    return { value: text, error: 'list' }
  }
  if (hasUnsafeInt(node)) {
    return { value: text, error: 'intRange' }
  }
  const { item } = spec
  return !item || node.items.every(n => matchesPrimitive(n, item))
    ? { value: toValue(node), error: null }
    : { value: text, error: 'listItems', errorParams: { kind: item } }
}

/**
 * Parse a raw probe input string according to its declared parameter type.
 *
 * Primitive types (int/float/bool/str) are validated strictly; a str is either a
 * quoted Python string literal or, unquoted, the bare text as typed.
 * One-level containers (list/tuple/set[T], dict[K, V]) must be Python literals of
 * that shape whose items match T (or K and V). Unknown or missing types accept any
 * Python literal and fall back to the raw text, unless the text starts like a
 * literal (a bracket or a quote) and does not parse as one.
 */
export function parseInputValue(rawValue: string, type: string | null | undefined): ParsedProbeInput {
  const text = rawValue.trim()

  switch (normalizePrimitiveType(type)) {
    case 'int':
      if (!INT_PATTERN.test(text)) {
        return { value: text, error: 'int' }
      }
      // JSON cannot carry ints above 2^53 losslessly, so refuse rather than corrupt
      return Number.isSafeInteger(Number(text))
        ? { value: Number(text), error: null }
        : { value: text, error: 'intRange' }
    case 'float': {
      const num = Number(text)
      return FLOAT_PATTERN.test(text) && Number.isFinite(num)
        ? { value: num, error: null }
        : { value: text, error: 'float' }
    }
    case 'bool':
      return BOOL_PATTERN.test(text)
        ? { value: text.toLowerCase() === 'true', error: null }
        : { value: text, error: 'bool' }
    case 'str': {
      // A quoted value is a Python string literal ('x' or "x"); bare text stays as typed
      if (!/^["']/.test(text)) {
        return { value: text, error: null }
      }
      const node = parsePythonLiteral(text)
      return node?.k === 'str' ? { value: node.v, error: null } : { value: text, error: 'literal' }
    }
    default: {
      const container = normalizeContainerType(type)
      if (container) {
        return parseContainer(text, container)
      }
      // Untyped / unchecked: any Python literal, else the raw text
      const node = parsePythonLiteral(text)
      if (node) {
        return hasUnsafeInt(node) ? { value: text, error: 'intRange' } : { value: toValue(node), error: null }
      }
      return /^[[({"']/.test(text) ? { value: text, error: 'literal' } : { value: text, error: null }
    }
  }
}

/** Line-level problem in the argument list, independent of any one parameter's value. */
export interface ArgsLineError {
  code: 'unknownKeyword' | 'duplicateArgument' | 'positionalAfterKeyword' | 'tooManyPositional' | 'emptyArgument'
  /**
   * The offending argument name ('' for tooManyPositional and emptyArgument); for
   * positionalAfterKeyword, the keyword that already took the positional's slot.
   */
  name: string
}

const KEYWORD_ARG = /^([\p{L}\p{Nl}_][\p{L}\p{Nl}\p{Mn}\p{Mc}\p{Nd}\p{Pc}]*)\s*=(?!=)([\s\S]*)$/u

/**
 * Map a call's argument list text (Python-style, positional or keyword) to raw
 * per-parameter strings.
 *
 * Positional arguments fill parameters in signature order; `name=value` sets that
 * parameter. A trailing comma is allowed. Every parameter appears in `raw`, with ''
 * when not given. The first line-level error is reported.
 */
export function parseArgsLine(
  text: string,
  paramNames: string[]
): { raw: Record<string, string>; lineError: ArgsLineError | null } {
  const raw: Record<string, string> = Object.fromEntries(paramNames.map(name => [name, '']))
  const parts = splitTopLevel(text).map(part => part.trim())
  if (parts[parts.length - 1] === '') {
    parts.pop()
  }

  const given = new Set<string>()
  let lineError: ArgsLineError | null = null
  let position = 0
  for (const part of parts) {
    if (part === '') {
      // `1,,2` is a syntax error in Python; it must not consume a positional slot
      lineError ??= { code: 'emptyArgument', name: '' }
      continue
    }
    const keyword = part.match(KEYWORD_ARG)
    let name: string
    let value: string
    if (keyword) {
      name = keyword[1]
      value = keyword[2].trim()
      if (!paramNames.includes(name)) {
        lineError ??= { code: 'unknownKeyword', name }
        continue
      }
    } else {
      if (position >= paramNames.length) {
        lineError ??= { code: 'tooManyPositional', name: '' }
        continue
      }
      name = paramNames[position++]
      value = part
      if (given.has(name)) {
        // Only a keyword can have taken a positional slot already: `x=1, 2`
        lineError ??= { code: 'positionalAfterKeyword', name }
        continue
      }
    }
    if (given.has(name)) {
      lineError ??= { code: 'duplicateArgument', name }
      continue
    }
    given.add(name)
    raw[name] = value
  }
  return { raw, lineError }
}

/**
 * Parameters of a `def name(...)` signature, splitting only on top-level commas so
 * `dict[str, int]` or a `(1, 2)` default stays one parameter (issue #160).
 *
 * The default stays on the type (e.g. "int = None") so normalizePrimitiveType can
 * see it; it is stripped from the name for untyped defaults like "x=3".
 */
export function parseSignatureParams(signature: string): ProbeParameter[] {
  const open = signature.indexOf('(')
  if (open === -1) {
    return []
  }
  // Find the matching close paren, skipping nested brackets and quoted defaults
  // (mirrors _extract_params_str in probe_service.py)
  let depth = 0
  let quote: string | null = null
  let close = -1
  for (let i = open; i < signature.length && close === -1; i++) {
    const ch = signature[i]
    if (quote) {
      if (ch === '\\') {
        i++
      } else if (ch === quote) {
        quote = null
      }
    } else if (ch === '"' || ch === "'") {
      quote = ch
    } else if (ch in OPENERS) {
      depth++
    } else if (CLOSERS.has(ch) && --depth === 0) {
      close = i
    }
  }
  const inner = signature.slice(open + 1, close === -1 ? undefined : close)
  return splitTopLevel(inner)
    .map(part => part.trim())
    .filter(part => part !== '')
    .map(part => {
      const colon = part.indexOf(':')
      const equals = part.indexOf('=')
      if (colon === -1 || (equals !== -1 && equals < colon)) {
        return { name: part.split('=')[0].trim(), type: 'Any' }
      }
      return { name: part.slice(0, colon).trim(), type: part.slice(colon + 1).trim() || 'Any' }
    })
}
