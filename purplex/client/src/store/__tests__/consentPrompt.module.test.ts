import { beforeEach, describe, expect, it } from 'vitest'
import { createStore, type Store } from 'vuex'
import { consentPrompt, type ConsentPromptState } from '../consentPrompt.module'

function freshStore(): Store<{ consentPrompt: ConsentPromptState }> {
  return createStore({ modules: { consentPrompt } })
}

describe('consentPrompt store module', () => {
  let store: Store<{ consentPrompt: ConsentPromptState }>

  beforeEach(() => {
    store = freshStore()
    // Module-scope promise state leaks across tests — resolve any prior
    // pending decision so the next test starts from a clean slate.
    store.dispatch('consentPrompt/resolveDecision', false).catch(() => undefined)
  })

  describe('requestDecision concurrent behavior', () => {
    it('shares the same resolution across repeated same-purpose calls', async () => {
      // Vuex dispatch wraps each call in its own outer promise, so identity
      // check isn't meaningful. What we care about: both calls resolve to
      // the same user decision, and only one modal is shown.
      const first = store.dispatch('consentPrompt/requestDecision', 'ai_processing')
      const second = store.dispatch('consentPrompt/requestDecision', 'ai_processing')

      expect(store.state.consentPrompt.visible).toBe(true)
      expect(store.state.consentPrompt.purpose).toBe('ai_processing')

      store.dispatch('consentPrompt/resolveDecision', true)
      await expect(first).resolves.toBe(true)
      await expect(second).resolves.toBe(true)
    })

    it('rejects a collision call for a different purpose without clobbering the pending one', async () => {
      const original = store.dispatch('consentPrompt/requestDecision', 'ai_processing')
      const conflicting = store.dispatch(
        'consentPrompt/requestDecision',
        'behavioral_tracking',
      )

      // The conflicting call must reject synchronously — the original must NOT
      // be affected. This is the whole point of the guard: previously, the
      // original resolver got overwritten and its awaiters hung forever.
      await expect(conflicting).rejects.toThrow(/already pending/)

      // Original is still pending and still resolvable.
      expect(store.state.consentPrompt.visible).toBe(true)
      expect(store.state.consentPrompt.purpose).toBe('ai_processing')

      store.dispatch('consentPrompt/resolveDecision', true)
      await expect(original).resolves.toBe(true)
    })
  })

  describe('resolveDecision', () => {
    it('resolves the pending decision and hides the modal', async () => {
      const pending = store.dispatch('consentPrompt/requestDecision', 'ai_processing')
      store.dispatch('consentPrompt/resolveDecision', true)

      await expect(pending).resolves.toBe(true)
      expect(store.state.consentPrompt.visible).toBe(false)
      expect(store.state.consentPrompt.purpose).toBeNull()
    })

    it('allows a new decision after the previous one is resolved', async () => {
      const first = store.dispatch('consentPrompt/requestDecision', 'ai_processing')
      store.dispatch('consentPrompt/resolveDecision', false)
      await first

      const second = store.dispatch('consentPrompt/requestDecision', 'ai_processing')
      expect(store.state.consentPrompt.visible).toBe(true)
      store.dispatch('consentPrompt/resolveDecision', true)
      await expect(second).resolves.toBe(true)
    })
  })
})
