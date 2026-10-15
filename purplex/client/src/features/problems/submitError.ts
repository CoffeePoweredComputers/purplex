/**
 * Map a failed POST /api/submit/ to the toast ProblemSet.vue shows.
 *
 * submissionService.submitActivity rethrows axios errors as a ServiceError
 * ({ error, status }), so the HTTP status and server message are read from
 * there; a raw axios error ({ response }) is still accepted.
 */

export interface SubmitErrorNotice {
  type: 'error' | 'warning'
  /** i18n key of the toast title. */
  titleKey: string
  /** Server-supplied detail text, shown as-is when present. */
  detail?: string
  /** i18n key of the detail text, used when the server sent none. */
  detailKey?: string
}

interface SubmitErrorLike {
  status?: number
  error?: string
  message?: string
  request?: unknown
  response?: { status?: number; data?: { error?: string } }
}

const NOTIFY = 'problems.problemSet.notify'

export function submitErrorNotice(err: unknown): SubmitErrorNotice {
  const e = (err ?? {}) as SubmitErrorLike
  const status = e.response?.status ?? e.status
  const serverMessage = e.response?.data?.error ?? e.error

  if (status === 0 || (status === undefined && e.request)) {
    return { type: 'error', titleKey: `${NOTIFY}.networkError`, detailKey: `${NOTIFY}.unableToReachServer` }
  }
  if (status === 500) {
    return { type: 'error', titleKey: `${NOTIFY}.serverError`, detailKey: `${NOTIFY}.aiServiceUnavailable` }
  }
  if (status === 401) {
    return { type: 'error', titleKey: `${NOTIFY}.authenticationError`, detailKey: `${NOTIFY}.pleaseLogInAgain` }
  }
  if (status === 400) {
    return serverMessage
      ? { type: 'warning', titleKey: `${NOTIFY}.invalidRequest`, detail: serverMessage }
      : { type: 'warning', titleKey: `${NOTIFY}.invalidRequest`, detailKey: `${NOTIFY}.pleaseCheckInput` }
  }
  if (status !== undefined) {
    return serverMessage
      ? { type: 'error', titleKey: 'common.error', detail: serverMessage }
      : { type: 'error', titleKey: 'common.error', detailKey: `${NOTIFY}.unknownError` }
  }
  return { type: 'error', titleKey: 'common.error', detail: e.message }
}
