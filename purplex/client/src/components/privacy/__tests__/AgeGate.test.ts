import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AgeGate from '../AgeGate.vue'

function mountAgeGate() {
  return mount(AgeGate)
}

describe('AgeGate', () => {
  it('renders date input', () => {
    const wrapper = mountAgeGate()
    expect(wrapper.find('input[type="date"]').exists()).toBe(true)
  })

  it('submit button is disabled without date', () => {
    const wrapper = mountAgeGate()
    const btn = wrapper.find('.age-gate__submit')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
  })

  it('emits age-verified for adult date', async () => {
    const wrapper = mountAgeGate()
    const input = wrapper.find('input[type="date"]')
    await input.setValue('1990-05-15')
    await wrapper.find('.age-gate__submit').trigger('click')

    const emitted = wrapper.emitted('age-verified')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toMatchObject({
      date_of_birth: '1990-05-15',
      is_minor: false,
      is_child: false,
    })
  })

  it('emits under-age for child date (under 13)', async () => {
    const wrapper = mountAgeGate()
    const input = wrapper.find('input[type="date"]')
    // Set a date that makes user under 13
    const childDate = new Date()
    childDate.setFullYear(childDate.getFullYear() - 10)
    const dateStr = childDate.toISOString().split('T')[0]

    await input.setValue(dateStr)
    await wrapper.find('.age-gate__submit').trigger('click')

    const emitted = wrapper.emitted('under-age')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toMatchObject({ is_child: true })
  })

  it('shows COPPA warning for child', async () => {
    const wrapper = mountAgeGate()
    const input = wrapper.find('input[type="date"]')
    const childDate = new Date()
    childDate.setFullYear(childDate.getFullYear() - 10)
    await input.setValue(childDate.toISOString().split('T')[0])
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('parental or guardian consent')
  })

  it('shows DPDPA warning for minor (under 18)', async () => {
    const wrapper = mountAgeGate()
    const input = wrapper.find('input[type="date"]')
    const minorDate = new Date()
    minorDate.setFullYear(minorDate.getFullYear() - 16)
    await input.setValue(minorDate.toISOString().split('T')[0])
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('additional privacy protections')
  })

  it('shows no message for adult', async () => {
    const wrapper = mountAgeGate()
    const input = wrapper.find('input[type="date"]')
    await input.setValue('1990-01-01')
    await wrapper.vm.$nextTick()

    // No warning messages for adults
    expect(wrapper.find('.age-gate__message').exists()).toBe(false)
  })
})
