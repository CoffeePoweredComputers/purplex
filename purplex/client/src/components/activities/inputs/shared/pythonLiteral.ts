/**
 * pythonLiteral - Parse a Python literal (or JSON) typed in the probe call line.
 *
 * Keeps int vs float apart so probeArgs can check container item types, and
 * converts the result to the JSON value the probe API receives. Pure functions.
 */

/** A parsed Python literal, keeping int vs float so item types can be checked. */
export type PyNode =
  | { k: 'int'; v: number }
  | { k: 'float'; v: number }
  | { k: 'str'; v: string }
  | { k: 'bool'; v: boolean }
  | { k: 'none' }
  | { k: 'list'; items: PyNode[] }
  | { k: 'dict'; entries: [PyNode, PyNode][] }

const NAME_LITERALS: Record<string, PyNode> = {
  True: { k: 'bool', v: true },
  False: { k: 'bool', v: false },
  None: { k: 'none' },
  // JSON spellings, accepted as before
  true: { k: 'bool', v: true },
  false: { k: 'bool', v: false },
  null: { k: 'none' },
}

const STRING_ESCAPES: Record<string, string> = {
  n: '\n', t: '\t', r: '\r', b: '\b', f: '\f', v: '\v', a: '\x07', '\\': '\\', "'": "'", '"': '"', '/': '/',
}

const OCTAL_ESCAPE = /[0-7]{1,3}/y

const NUMBER_TOKEN = /[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?/y
// Python identifiers are Unicode (PEP 3131), so `número` is a valid name
const NAME_TOKEN = /[\p{L}\p{Nl}_][\p{L}\p{Nl}\p{Mn}\p{Mc}\p{Nd}\p{Pc}]*/uy

/**
 * Parse a Python literal (or JSON): numbers, quoted strings, True/False/None,
 * lists, tuples and sets (all become lists), and dicts with scalar keys.
 * Trailing commas are accepted. Returns null when the text is not a literal.
 */
export function parsePythonLiteral(text: string): PyNode | null {
  let pos = 0

  const skipSpace = () => {
    while (pos < text.length && /\s/.test(text[pos])) {
      pos++
    }
  }

  const parseString = (): PyNode | null => {
    const quote = text[pos++]
    let out = ''
    while (pos < text.length) {
      const ch = text[pos++]
      if (ch === quote) {
        return { k: 'str', v: out }
      }
      if (ch !== '\\') {
        out += ch
        continue
      }
      const esc = text[pos++]
      if (esc === undefined) {
        return null
      }
      if (esc === 'N') {
        // \N{NAME} needs Python's Unicode name table; reject rather than mis-decode
        return null
      }
      if (/[0-7]/.test(esc)) {
        // \0 .. \377: one to three octal digits, as in Python
        OCTAL_ESCAPE.lastIndex = pos - 1
        const octal = OCTAL_ESCAPE.exec(text)?.[0] ?? esc
        out += String.fromCharCode(parseInt(octal, 8))
        pos += octal.length - 1
        continue
      }
      const hexLength = esc === 'U' ? 8 : esc === 'u' ? 4 : esc === 'x' ? 2 : 0
      if (hexLength) {
        const hex = text.slice(pos, pos + hexLength)
        if (!new RegExp(`^[0-9a-fA-F]{${hexLength}}$`).test(hex)) {
          return null
        }
        const code = parseInt(hex, 16)
        if (code > 0x10ffff) {
          return null
        }
        out += String.fromCodePoint(code)
        pos += hexLength
      } else {
        // Python keeps unknown escapes verbatim
        out += STRING_ESCAPES[esc] ?? `\\${esc}`
      }
    }
    return null
  }

  // Items up to `close`, separated by commas, trailing comma allowed
  const parseItems = (close: string, first: PyNode[] = []): { items: PyNode[]; sawComma: boolean } | null => {
    const items = first
    // Called with a first item only once its trailing comma is consumed
    let sawComma = first.length > 0
    for (;;) {
      skipSpace()
      if (text[pos] === close) {
        pos++
        return { items, sawComma }
      }
      if (items.length > 0 && !sawComma) {
        return null
      }
      const item = parseValue()
      if (!item) {
        return null
      }
      items.push(item)
      skipSpace()
      if (text[pos] === ',') {
        pos++
        sawComma = true
      } else if (text[pos] !== close) {
        return null
      } else {
        sawComma = false
      }
    }
  }

  const parseBrace = (): PyNode | null => {
    pos++
    skipSpace()
    if (text[pos] === '}') {
      pos++
      return { k: 'dict', entries: [] }
    }
    const first = parseValue()
    if (!first) {
      return null
    }
    skipSpace()
    if (text[pos] !== ':') {
      // A set literal: the first item is parsed, continue as a sequence
      if (text[pos] === ',') {
        pos++
        const rest = parseItems('}', [first])
        return rest && { k: 'list', items: rest.items }
      }
      return text[pos++] === '}' ? { k: 'list', items: [first] } : null
    }
    const entries: [PyNode, PyNode][] = []
    let key: PyNode | null = first
    for (;;) {
      // Keys must be scalars: a JSON object can only carry those
      if (!key || key.k === 'list' || key.k === 'dict') {
        return null
      }
      skipSpace()
      if (text[pos++] !== ':') {
        return null
      }
      const value = parseValue()
      if (!value) {
        return null
      }
      entries.push([key, value])
      skipSpace()
      const sep = text[pos++]
      if (sep === '}') {
        return { k: 'dict', entries }
      }
      if (sep !== ',') {
        return null
      }
      skipSpace()
      if (text[pos] === '}') {
        pos++
        return { k: 'dict', entries }
      }
      key = parseValue()
    }
  }

  const parseValue = (): PyNode | null => {
    skipSpace()
    const ch = text[pos]
    if (ch === '"' || ch === "'") {
      return parseString()
    }
    if (ch === '[') {
      pos++
      const seq = parseItems(']')
      return seq && { k: 'list', items: seq.items }
    }
    if (ch === '(') {
      pos++
      const seq = parseItems(')')
      if (!seq) {
        return null
      }
      // (x) is just x; (x,) and () are tuples
      return seq.items.length === 1 && !seq.sawComma ? seq.items[0] : { k: 'list', items: seq.items }
    }
    if (ch === '{') {
      return parseBrace()
    }
    NUMBER_TOKEN.lastIndex = pos
    const num = NUMBER_TOKEN.exec(text)
    if (num) {
      pos = NUMBER_TOKEN.lastIndex
      const v = Number(num[0])
      if (num[1].includes('.') || num[2]) {
        return Number.isFinite(v) ? { k: 'float', v } : null
      }
      return { k: 'int', v }
    }
    NAME_TOKEN.lastIndex = pos
    const name = NAME_TOKEN.exec(text)
    if (name && Object.prototype.hasOwnProperty.call(NAME_LITERALS, name[0])) {
      pos = NAME_TOKEN.lastIndex
      return NAME_LITERALS[name[0]]
    }
    return null
  }

  const node = parseValue()
  skipSpace()
  return node && pos === text.length ? node : null
}

/** Whether any int in the literal is too large to survive JSON losslessly. */
export function hasUnsafeInt(node: PyNode): boolean {
  switch (node.k) {
    case 'int':
      return !Number.isSafeInteger(node.v)
    case 'list':
      return node.items.some(hasUnsafeInt)
    case 'dict':
      return node.entries.some(([key, value]) => hasUnsafeInt(key) || hasUnsafeInt(value))
    default:
      return false
  }
}

/** Python json.dumps spelling of a scalar dict key. */
function keyToString(node: PyNode): string {
  if (node.k === 'none') {
    return 'null'
  }
  return 'v' in node ? String(node.v) : ''
}

export function toValue(node: PyNode): unknown {
  switch (node.k) {
    case 'none':
      return null
    case 'list':
      return node.items.map(toValue)
    case 'dict':
      // fromEntries defines own properties, so a "__proto__" key stays data
      return Object.fromEntries(node.entries.map(([key, value]) => [keyToString(key), toValue(value)]))
    default:
      return node.v
  }
}
