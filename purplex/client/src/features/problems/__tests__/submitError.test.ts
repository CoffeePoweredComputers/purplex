import { describe, expect, it } from 'vitest'
import { ServiceError } from '@/services/submissionService'
import { submitErrorNotice } from '../submitError'

const NOTIFY = 'problems.problemSet.notify'

describe('submitErrorNotice', () => {
  it('shows a 400 ServiceError as an Invalid Request warning with the server text', () => {
    const err = new ServiceError('Syntax error: unexpected EOF (line 2)', 400)
    expect(submitErrorNotice(err)).toEqual({
      type: 'warning',
      titleKey: `${NOTIFY}.invalidRequest`,
      detail: 'Syntax error: unexpected EOF (line 2)',
    })
  })

  it('maps ServiceError statuses to their toasts', () => {
    expect(submitErrorNotice(new ServiceError('x', 500))).toMatchObject({
      type: 'error',
      titleKey: `${NOTIFY}.serverError`,
    })
    expect(submitErrorNotice(new ServiceError('x', 401))).toMatchObject({
      type: 'error',
      titleKey: `${NOTIFY}.authenticationError`,
    })
    expect(submitErrorNotice(new ServiceError('Problem set is locked', 403))).toEqual({
      type: 'error',
      titleKey: 'common.error',
      detail: 'Problem set is locked',
    })
    expect(submitErrorNotice(new ServiceError('Failed to submit activity solution', 0))).toEqual({
      type: 'error',
      titleKey: `${NOTIFY}.networkError`,
      detailKey: `${NOTIFY}.unableToReachServer`,
    })
  })

  it('still accepts a raw axios error', () => {
    expect(submitErrorNotice({ response: { status: 400, data: {} } })).toEqual({
      type: 'warning',
      titleKey: `${NOTIFY}.invalidRequest`,
      detailKey: `${NOTIFY}.pleaseCheckInput`,
    })
  })

  it('falls back to the message of a non-HTTP error', () => {
    expect(submitErrorNotice(new Error('boom'))).toEqual({
      type: 'error',
      titleKey: 'common.error',
      detail: 'boom',
    })
  })
})
