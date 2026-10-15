import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ProbeableCodeFeedback from '../ProbeableCodeFeedback.vue'

const row = (isSuccessful: boolean, i: number) => ({
  isSuccessful,
  function_call: `f(${i})`,
  expected_output: i,
  actual_output: isSuccessful ? i : -1,
})

function mountFeedback(testResults: unknown[]) {
  return mount(ProbeableCodeFeedback, {
    props: {
      codeResults: ['def f(x):\n    return x'],
      testResults: testResults as never,
    },
    global: {
      stubs: { Editor: true, PyTutorModal: true },
    },
  })
}

describe('ProbeableCodeFeedback', () => {
  it('shows the locked count after the first failure', () => {
    const visible = [row(true, 0), row(false, 1)]
    const wrapper = mountFeedback([
      {
        success: false,
        testsPassed: 1,
        totalTests: 4,
        test_results: visible,
        results: visible,
        lockedCount: 2,
        visibleCount: 2,
      },
    ])

    expect(wrapper.find('.count-item.passing').text()).toContain('1')
    expect(wrapper.find('.count-item.failing').text()).toContain('3')

    const locked = wrapper.find('.count-item.locked')
    expect(locked.exists()).toBe(true)
    expect(locked.text()).toContain('2')
    expect(locked.text()).toContain('tests')
    expect(wrapper.find('.locked-note').exists()).toBe(true)
  })

  it('counts passes and failures over every test, not just the visible rows', () => {
    // Test #1 fails; the 9 tests after it pass but are locked.
    const visible = [row(false, 0)]
    const wrapper = mountFeedback([
      {
        success: false,
        testsPassed: 9,
        totalTests: 10,
        test_results: visible,
        results: visible,
        lockedCount: 9,
        visibleCount: 1,
      },
    ])

    expect(wrapper.find('.count-item.passing').text()).toContain('9')
    expect(wrapper.find('.count-item.failing').text()).toContain('1')
    expect(wrapper.find('.count-item.locked').text()).toContain('9')
  })

  it('uses the singular when exactly one test is locked', () => {
    const visible = [row(true, 0), row(false, 1)]
    const wrapper = mountFeedback([
      {
        success: false,
        testsPassed: 1,
        totalTests: 3,
        test_results: visible,
        results: visible,
        lockedCount: 1,
        visibleCount: 2,
      },
    ])

    const locked = wrapper.find('.count-item.locked').text()
    expect(locked).toContain('1')
    expect(locked).not.toContain('tests')
  })

  it('hides the locked indicators when nothing is locked', () => {
    const visible = [row(true, 0), row(true, 1)]
    const wrapper = mountFeedback([
      {
        success: true,
        testsPassed: 2,
        totalTests: 2,
        test_results: visible,
        results: visible,
      },
    ])

    expect(wrapper.find('.count-item.locked').exists()).toBe(false)
    expect(wrapper.find('.locked-note').exists()).toBe(false)
  })
})
