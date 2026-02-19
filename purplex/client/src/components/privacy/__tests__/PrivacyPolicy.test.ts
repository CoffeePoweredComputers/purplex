import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PrivacyPolicy from '../PrivacyPolicy.vue'

describe('PrivacyPolicy', () => {
  it('renders the privacy policy page', () => {
    const wrapper = mount(PrivacyPolicy)
    expect(wrapper.find('h1').text()).toBe('Privacy Policy')
  })

  it('contains required regulatory sections', () => {
    const wrapper = mount(PrivacyPolicy)
    const text = wrapper.text()
    expect(text).toContain('Data We Collect')
    expect(text).toContain('Your Rights')
    expect(text).toContain('Data Retention')
    expect(text).toContain("Children's Privacy")
    expect(text).toContain('Third-Party')
    expect(text).toContain('Cookies')
  })
})
