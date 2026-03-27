import type { LocationQuery } from 'vue-router'

/**
 * Parse the ?p query param to get the problem index.
 * Returns 0 if param is missing, invalid, or out of bounds.
 *
 * @param query - The route query object
 * @param problemsLength - Total number of problems in the set
 * @returns The validated problem index (0-based)
 */
export function parseProblemQueryParam(
  query: LocationQuery,
  problemsLength: number
): number {
  const problemParam = query.p
  if (!problemParam) {return 0}

  // Handle array case (e.g., ?p=1&p=2)
  const paramValue = Array.isArray(problemParam) ? problemParam[0] : problemParam
  if (!paramValue) {return 0}

  const index = parseInt(paramValue, 10)
  if (isNaN(index) || index < 0 || index >= problemsLength) {
    return 0
  }
  return index
}
