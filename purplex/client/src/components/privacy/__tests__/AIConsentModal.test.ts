import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createStore } from 'vuex'
import AIConsentModal from '../AIConsentModal.vue'
import { consentPrompt } from '../../../store/consentPrompt.module'

const grantConsentMock = vi.fn()

vi.mock('../../../services/privacyService', () => ({
  default: {
    grantConsent: (...args: unknown[]) => grantConsentMock(...args),
  },
}))

vi.mock('../../../utils/logger', () => ({
  log: { info: vi.fn(), error: vi.fn(), debug: vi.fn() },
}))

function mountModal() {
  const store = createStore({ modules: { consentPrompt } })
  const wrapper = mount(AIConsentModal, {
    global: { plugins: [store], stubs: { Teleport: true, Transition: false } },
  })
  return { wrapper, store }
}

describe('AIConsentModal', () => {
  beforeEach(() => {
    grantConsentMock.mockReset()
  })

  it('is hidden when consent prompt is not visible', () => {
    const { wrapper } = mountModal()
    expect(wrapper.find('[role="alertdialog"]').exists()).toBe(false)
  })

  it('renders with grant and decline buttons when shown', async () => {
    const { wrapper, store } = mountModal()
    store.dispatch('consentPrompt/requestDecision', 'ai_processing')
    await flushPromises()

    expect(wrapper.find('[role="alertdialog"]').exists()).toBe(true)
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBe(2)
  })

  it('grants with consent_method=in_app then resolves the decision promise', async () => {
    grantConsentMock.mockResolvedValue({ consent_type: 'ai_processing', granted: true })
    const { wrapper, store } = mountModal()
    const decision = store.dispatch('consentPrompt/requestDecision', 'ai_processing')
    await flushPromises()

    await wrapper.findAll('button')[1].trigger('click') // grant button
    await flushPromises()

    expect(grantConsentMock).toHaveBeenCalledWith('ai_processing', {
      consent_method: 'in_app',
    })
    await expect(decision).resolves.toBe(true)
    expect(store.state.consentPrompt.visible).toBe(false)
  })

  it('resolves decision with false when the user declines', async () => {
    const { wrapper, store } = mountModal()
    const decision = store.dispatch('consentPrompt/requestDecision', 'ai_processing')
    await flushPromises()

    await wrapper.findAll('button')[0].trigger('click') // decline button
    await flushPromises()

    expect(grantConsentMock).not.toHaveBeenCalled()
    await expect(decision).resolves.toBe(false)
    expect(store.state.consentPrompt.visible).toBe(false)
  })

  it('keeps modal open and shows inline error when grant fails', async () => {
    grantConsentMock.mockRejectedValue(new Error('network'))
    const { wrapper, store } = mountModal()
    store.dispatch('consentPrompt/requestDecision', 'ai_processing')
    await flushPromises()

    await wrapper.findAll('button')[1].trigger('click') // grant button
    await flushPromises()

    expect(store.state.consentPrompt.visible).toBe(true)
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })
})
