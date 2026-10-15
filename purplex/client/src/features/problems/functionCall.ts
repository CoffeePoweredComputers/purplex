/**
 * Display formatting for test-case calls when an earlier attempt is reloaded
 * from /api/submissions/history/. Mirrors the backend's
 * BaseHandler._format_function_call used by the live and last-submission paths:
 * top-level string arguments use json.dumps, every other value uses repr().
 *
 * Values arrive as JSON, so a Python float with an integral value (2.0) reaches
 * the browser as the number 2 and is shown as 2; that is the one case the
 * backend text (2.0) cannot be reproduced.
 */

function hex(code: number, width: number): string {
  return code.toString(16).padStart(width, '0')
}

/** Python json.dumps(str) with the default ensure_ascii=True. */
function jsonDumpsString(value: string): string {
  let out = '"'
  for (const ch of value) {
    for (let i = 0; i < ch.length; i++) {
      const code = ch.charCodeAt(i)
      const c = ch[i]
      if (c === '"') {out += '\\"'}
      else if (c === '\\') {out += '\\\\'}
      else if (c === '\n') {out += '\\n'}
      else if (c === '\r') {out += '\\r'}
      else if (c === '\t') {out += '\\t'}
      else if (c === '\b') {out += '\\b'}
      else if (c === '\f') {out += '\\f'}
      else if (code < 0x20 || code > 0x7e) {out += code === 0x7f ? c : `\\u${hex(code, 4)}`}
      else {out += c}
    }
  }
  return out + '"'
}

/** Python repr(str) for printable text: single quotes unless only ' appears. */
function reprString(value: string): string {
  const quote = value.includes("'") && !value.includes('"') ? '"' : "'"
  let out = quote
  for (const c of value) {
    const code = c.codePointAt(0) ?? 0
    if (c === quote || c === '\\') {out += '\\' + c}
    else if (c === '\n') {out += '\\n'}
    else if (c === '\r') {out += '\\r'}
    else if (c === '\t') {out += '\\t'}
    else if (code < 0x20 || code === 0x7f) {out += `\\x${hex(code, 2)}`}
    else {out += c}
  }
  return out + quote
}

/** Python repr() of a JSON-decoded value. */
function pythonRepr(value: unknown): string {
  if (value === null) {return 'None'}
  if (value === undefined) {return 'undefined'}
  if (typeof value === 'string') {return reprString(value)}
  if (typeof value === 'boolean') {return value ? 'True' : 'False'}
  if (typeof value === 'number') {return value.toString()}
  if (Array.isArray(value)) {
    return '[' + value.map(pythonRepr).join(', ') + ']'
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    return '{' + entries.map(([k, v]) => `${reprString(k)}: ${pythonRepr(v)}`).join(', ') + '}'
  }
  return String(value)
}

/** Format one top-level argument the way _format_function_call does. */
export function formatTestValue(value: unknown): string {
  return typeof value === 'string' ? jsonDumpsString(value) : pythonRepr(value)
}

/**
 * Build the call text for a stored test result.
 *
 * TestExecution.input_values is the positional argument list, so an array is
 * rendered as the arguments themselves: [-3] -> clamp(-3), [1, 2] -> add(1, 2).
 */
export function reconstructFunctionCall(functionName: string, inputs: unknown): string {
  if (inputs === undefined || inputs === null) {
    return `${functionName}(...)`
  }
  if (typeof inputs === 'string') {
    return `${functionName}(${inputs})`
  }
  if (Array.isArray(inputs)) {
    return `${functionName}(${inputs.map(formatTestValue).join(', ')})`
  }
  return `${functionName}(${formatTestValue(inputs)})`
}
