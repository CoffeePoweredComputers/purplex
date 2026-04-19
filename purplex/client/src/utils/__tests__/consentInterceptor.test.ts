import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import type { AxiosError } from 'axios'
import axios from 'axios'
import { createStore, type Store } from 'vuex'
import { consentPrompt, type ConsentPromptState } from '../../store/consentPrompt.module'

// Build a minimal store that exposes only the consentPrompt module. Importing
// the real `../store` would transitively pull in auth.module.ts which reads
// localStorage at module load and breaks the test environment.
const store: Store<{ consentPrompt: ConsentPromptState }> = createStore({
  modules: { consentPrompt },
})

vi.mock('../../store', () => ({ default: store }))

vi.mock('../logger', () => ({
  log: { error: vi.fn(), info: vi.fn(), debug: vi.fn() },
}))

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios')
  // Keep the real default export structure but make the top-level function
  // callable via the same import used inside the interceptor (`axios(config)`).
  const mockFn = vi.fn() as unknown as typeof axios
  return {
    ...actual,
    default: Object.assign(mockFn, actual.default),
  }
})

// Must be imported AFTER the mocks above.
const { handleConsentRequired, isConsentRequiredError } = await import('../consentInterceptor')

function consentError(config: { url?: string; _consentRetried?: boolean } = {}) {
  return {
    config: { url: '/api/submit/', ...config },
    response: {
      status: 403,
      data: {
        error: 'AI processing consent not granted',
        code: 'consent_required',
        purpose: 'ai_processing',
      },
    },
  } as unknown as AxiosError<{ error: string; code: string; purpose: string }>
}

describe('isConsentRequiredError', () => {
  it('returns true for 403 + consent_required + purpose=ai_processing', () => {
    expect(isConsentRequiredError(consentError())).toBe(true)
  })

  it('returns false for 403 without consent_required code', () => {
    const err = {
      response: { status: 403, data: { code: 'forbidden' } },
    } as unknown as AxiosError
    expect(isConsentRequiredError(err)).toBe(false)
  })

  it('returns false for non-403 status', () => {
    const err = {
      response: { status: 500, data: { code: 'consent_required' } },
    } as unknown as AxiosError
    expect(isConsentRequiredError(err)).toBe(false)
  })

  it('returns false when response is missing (network error)', () => {
    expect(isConsentRequiredError({} as AxiosError)).toBe(false)
  })

  it('returns false for consent_required without a purpose field', () => {
    // The generic consent_required code is used by non-AI gates
    // (e.g. behavioral_tracking in activity_event_views) that don't set purpose.
    const err = {
      response: { status: 403, data: { code: 'consent_required' } },
    } as unknown as AxiosError
    expect(isConsentRequiredError(err)).toBe(false)
  })

  it('returns false for consent_required with a non-AI purpose', () => {
    const err = {
      response: {
        status: 403,
        data: { code: 'consent_required', purpose: 'behavioral_tracking' },
      },
    } as unknown as AxiosError
    expect(isConsentRequiredError(err)).toBe(false)
  })
})

describe('handleConsentRequired', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Module-scope promise plumbing leaks across tests. resolveDecision
    // clears both Vuex state AND the module-level resolver/promise; the
    // older `commit('hide')` only cleared Vuex state, leaving the module
    // globals set and tripping the new purpose-collision guard.
    store.dispatch('consentPrompt/resolveDecision', false)
  })

  it('retries the original request when the user grants consent', async () => {
    const retryResponse = { status: 200, data: { ok: true } }
    ;(axios as unknown as Mock).mockResolvedValue(retryResponse)

    const handlerPromise = handleConsentRequired(consentError())

    // Simulate the user clicking Grant.
    await Promise.resolve() // let the action register the promise first
    store.dispatch('consentPrompt/resolveDecision', true)

    const result = await handlerPromise
    expect(result).toEqual(retryResponse)
    expect((axios as unknown as Mock)).toHaveBeenCalledTimes(1)
  })

  it('rejects with the original error when the user declines', async () => {
    const err = consentError()
    const handlerPromise = handleConsentRequired(err)

    await Promise.resolve()
    store.dispatch('consentPrompt/resolveDecision', false)

    await expect(handlerPromise).rejects.toBe(err)
    expect((axios as unknown as Mock)).not.toHaveBeenCalled()
  })

  it('deduplicates concurrent requests so one modal serves many 403s', async () => {
    ;(axios as unknown as Mock).mockResolvedValue({ status: 200, data: {} })

    const first = handleConsentRequired(consentError({ url: '/api/submit/' }))
    const second = handleConsentRequired(consentError({ url: '/api/submit/' }))
    await Promise.resolve()

    // Only one prompt is visible — both requests are waiting on the same promise.
    expect(store.state.consentPrompt.visible).toBe(true)

    store.dispatch('consentPrompt/resolveDecision', true)

    await first
    await second
    expect((axios as unknown as Mock)).toHaveBeenCalledTimes(2)
  })

  it('does not loop when a retried request also returns consent_required', async () => {
    const retriedError = consentError({ _consentRetried: true })
    await expect(handleConsentRequired(retriedError)).rejects.toBe(retriedError)
    expect((axios as unknown as Mock)).not.toHaveBeenCalled()
    // Modal should never have been shown for a retry-loop case.
    expect(store.state.consentPrompt.visible).toBe(false)
  })

  it('rejects without prompting when the error has no purpose field', async () => {
    const err = {
      config: { url: '/api/submit/' },
      response: { status: 403, data: { code: 'consent_required' } },
    } as unknown as AxiosError<{ code: string }>
    await expect(handleConsentRequired(err as unknown as AxiosError)).rejects.toBe(err)
    expect(store.state.consentPrompt.visible).toBe(false)
  })
})
