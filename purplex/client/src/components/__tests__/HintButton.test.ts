import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import HintButton from '../hints/HintButton.vue'

describe('HintButton', () => {
  it('shows locked message when attempts are insufficient', () => {
    const wrapper = mount(HintButton, {
      props: {
        problemSlug: 'two-sum',
        problemSetSlug: 'arrays',
        courseId: 'CS101',
        attempts: 1,
        requiredAttempts: 3
      }
    })

    // Check button is disabled
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
    expect(wrapper.find('button').classes()).toContain('disabled')
    
    // Check message shows remaining attempts
    expect(wrapper.text()).toContain('Need 2 more attempts')
    
    // Check tooltip
    expect(wrapper.find('button').attributes('title')).toContain('You need to make 2 more attempts')
  })

  it('shows singular form for 1 remaining attempt', () => {
    const wrapper = mount(HintButton, {
      props: {
        problemSlug: 'two-sum',
        problemSetSlug: 'arrays',
        courseId: 'CS101',
        attempts: 2,
        requiredAttempts: 3
      }
    })

    expect(wrapper.text()).toContain('Need 1 more attempt')
    expect(wrapper.find('button').attributes('title')).toContain('You need to make 1 more attempt')
  })

  it('enables button when attempts meet requirement', () => {
    const wrapper = mount(HintButton, {
      props: {
        problemSlug: 'two-sum',
        problemSetSlug: 'arrays',
        courseId: 'CS101',
        attempts: 3,
        requiredAttempts: 3
      }
    })

    // Check button is enabled
    expect(wrapper.find('button').attributes('disabled')).toBeUndefined()
    expect(wrapper.find('button').classes()).not.toContain('disabled')
    
    // Check message
    expect(wrapper.text()).toContain('Get Hint')
    
    // Check tooltip
    expect(wrapper.find('button').attributes('title')).toBe('Click to request a hint')
  })

  it('emits hint-requested event when clicked and enabled', async () => {
    const wrapper = mount(HintButton, {
      props: {
        problemSlug: 'two-sum',
        problemSetSlug: 'arrays',
        courseId: 'CS101',
        attempts: 3,
        requiredAttempts: 3
      }
    })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('hint-requested')).toBeTruthy()
    const hintRequestedEvents = wrapper.emitted('hint-requested')
    expect(hintRequestedEvents).toBeDefined()
    expect(hintRequestedEvents?.[0]).toEqual([{
      problemSlug: 'two-sum',
      problemSetSlug: 'arrays',
      courseId: 'CS101',
      attempts: 3
    }])
  })

  it('does not emit event when clicked while disabled', async () => {
    const wrapper = mount(HintButton, {
      props: {
        problemSlug: 'two-sum',
        problemSetSlug: 'arrays',
        courseId: 'CS101',
        attempts: 1,
        requiredAttempts: 3
      }
    })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('hint-requested')).toBeFalsy()
  })

  it('updates when attempts prop changes', async () => {
    const wrapper = mount(HintButton, {
      props: {
        problemSlug: 'two-sum',
        problemSetSlug: 'arrays',
        courseId: 'CS101',
        attempts: 1,
        requiredAttempts: 3
      }
    })

    expect(wrapper.text()).toContain('Need 2 more attempts')

    // Update attempts
    await wrapper.setProps({ attempts: 3 })

    expect(wrapper.text()).toContain('Get Hint')
    expect(wrapper.find('button').attributes('disabled')).toBeUndefined()
  })
})