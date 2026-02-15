import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TermsOfService from '../TermsOfService.vue'

describe('TermsOfService', () => {
  it('renders the terms of service page', () => {
    const wrapper = mount(TermsOfService)
    expect(wrapper.find('h1').text()).toBe('Terms of Service')
  })

  it('contains required legal sections', () => {
    const wrapper = mount(TermsOfService)
    const text = wrapper.text()
    expect(text).toContain('AI Processing Disclosure')
    expect(text).toContain('Age Restrictions')
    expect(text).toContain('Intellectual Property')
    expect(text).toContain('FERPA Notice')
    expect(text).toContain('Account Termination')
  })
})
