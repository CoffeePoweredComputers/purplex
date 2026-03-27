import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ConsentForm from '../ConsentForm.vue'

function mountConsentForm() {
  return mount(ConsentForm)
}

describe('ConsentForm', () => {
  it('renders required consent checkboxes', () => {
    const wrapper = mountConsentForm()
    const required = wrapper.findAll('.consent-item--required')
    expect(required.length).toBe(2) // privacy_policy + terms_of_service
  })

  it('submit button disabled without required consents', () => {
    const wrapper = mountConsentForm()
    const btn = wrapper.find('.consent-form__submit')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
  })

  it('submit button enabled when both required checked', async () => {
    const wrapper = mountConsentForm()
    const checkboxes = wrapper.findAll('.consent-item--required input[type="checkbox"]')
    await checkboxes[0].setValue(true)
    await checkboxes[1].setValue(true)

    const btn = wrapper.find('.consent-form__submit')
    expect((btn.element as HTMLButtonElement).disabled).toBe(false)
  })

  it('emits consent-granted with all consent values', async () => {
    const wrapper = mountConsentForm()
    const checkboxes = wrapper.findAll('.consent-item--required input[type="checkbox"]')
    await checkboxes[0].setValue(true)
    await checkboxes[1].setValue(true)
    await wrapper.find('.consent-form__submit').trigger('click')

    const emitted = wrapper.emitted('consent-granted')
    expect(emitted).toBeTruthy()
    const consents = emitted![0][0] as Record<string, boolean>
    expect(consents.privacy_policy).toBe(true)
    expect(consents.terms_of_service).toBe(true)
  })

  it('includes optional consents in emitted data', async () => {
    const wrapper = mountConsentForm()
    // Check required
    const required = wrapper.findAll('.consent-item--required input[type="checkbox"]')
    await required[0].setValue(true)
    await required[1].setValue(true)
    // Check an optional
    const allCheckboxes = wrapper.findAll('input[type="checkbox"]')
    // Third checkbox is ai_processing (first optional)
    await allCheckboxes[2].setValue(true)
    await wrapper.find('.consent-form__submit').trigger('click')

    const emitted = wrapper.emitted('consent-granted')
    const consents = emitted![0][0] as Record<string, boolean>
    expect(consents.ai_processing).toBe(true)
  })

  it('shows error when submitting without required consents', async () => {
    const wrapper = mountConsentForm()
    // Force click without checking required
    // The button is disabled, so we call submitConsent directly
    const vm = wrapper.vm as unknown as {
      consents: Record<string, boolean>
      submitConsent: () => void
    }
    vm.consents.privacy_policy = false
    vm.consents.terms_of_service = false
    vm.submitConsent()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.consent-form__error').exists()).toBe(true)
    expect(wrapper.text()).toContain('must accept')
  })
})
