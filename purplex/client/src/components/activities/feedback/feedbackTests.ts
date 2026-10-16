/**
 * Shared shapes and formatting for the per-test rows shown in code feedback.
 */

/** One graded test as the feedback components receive it (backend row, flattened). */
export interface FeedbackTestRow {
  function_call: string
  expected_output: unknown
  actual_output: unknown
  isSuccessful: boolean
  error?: string
  /** Legacy field */
  pass?: boolean
}

export function isPassingRow(test: FeedbackTestRow): boolean {
  return Boolean(test.isSuccessful || test.pass)
}

/** Render a test value the way Python would print a literal. */
export function formatTestValue(value: unknown): string {
  if (value === null) {return 'None'}
  if (value === undefined) {return 'undefined'}
  if (typeof value === 'string') {return `"${value}"`}
  if (Array.isArray(value)) {return JSON.stringify(value)}
  if (typeof value === 'object') {return JSON.stringify(value)}
  return String(value)
}
