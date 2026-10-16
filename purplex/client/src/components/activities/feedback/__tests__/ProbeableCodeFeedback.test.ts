import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ProbeableCodeFeedback from '../ProbeableCodeFeedback.vue'

const row = (isSuccessful: boolean, i: number, error?: string) => ({
  isSuccessful,
  function_call: `f(${i})`,
  expected_output: i,
  actual_output: isSuccessful ? i : -1,
  error,
})

function mountFeedback(entry: Record<string, unknown>) {
  return mount(ProbeableCodeFeedback, {
    props: {
      codeResults: ['def f(x):\n    return x'],
      testResults: [entry] as never,
    },
    global: {
      stubs: { Editor: true, PyTutorModal: true },
    },
  })
}

function pipClasses(wrapper: ReturnType<typeof mountFeedback>): string[] {
  return wrapper.findAll('.pip').map(p => (p.classes('pass') ? 'pass' : p.classes('fail') ? 'fail' : 'lock'))
}

describe('ProbeableCodeFeedback ladder', () => {
  it('shows one pip per test and locks everything after the first failure', () => {
    const visible = [row(true, 0), row(false, 1)]
    const wrapper = mountFeedback({
      success: false,
      testsPassed: 1,
      totalTests: 4,
      test_results: visible,
      results: visible,
      lockedCount: 2,
      visibleCount: 2,
    })

    expect(pipClasses(wrapper)).toEqual(['pass', 'fail', 'lock', 'lock'])
    expect(wrapper.find('.ledger-row.lock').text()).toContain('2 more tests')
    expect(wrapper.find('.ledger-row.lock').text()).toContain('test 2 passes')

    const failing = wrapper.find('.ledger-row.fail')
    expect(failing.find('.test-call').text()).toBe('f(1)')
    expect(failing.find('.expected').text()).toBe('1')
    expect(failing.find('.actual').text()).toBe('-1')
    expect(failing.find('.actual').classes()).not.toContain('is-error')
  })

  it('never reveals how the locked tests fared', () => {
    // Test #1 fails; the 9 tests after it pass but are locked.
    const visible = [row(false, 0)]
    const wrapper = mountFeedback({
      success: false,
      testsPassed: 9,
      totalTests: 10,
      test_results: visible,
      results: visible,
      lockedCount: 9,
      visibleCount: 1,
    })

    expect(pipClasses(wrapper)).toEqual(['fail', ...Array(9).fill('lock')])
    expect(wrapper.findAll('.ledger-row.pass')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('9 Passing')
  })

  it('uses the singular when exactly one test is locked', () => {
    const visible = [row(true, 0), row(false, 1)]
    const wrapper = mountFeedback({
      success: false,
      testsPassed: 1,
      totalTests: 3,
      test_results: visible,
      results: visible,
      lockedCount: 1,
      visibleCount: 2,
    })

    const locked = wrapper.find('.ledger-row.lock').text()
    expect(locked).toContain('1 more test')
    expect(locked).not.toContain('tests')
  })

  it('shows all-green pips and no locked row when every test passes', () => {
    const visible = [row(true, 0), row(true, 1)]
    const wrapper = mountFeedback({
      success: true,
      testsPassed: 2,
      totalTests: 2,
      test_results: visible,
      results: visible,
    })

    expect(pipClasses(wrapper)).toEqual(['pass', 'pass'])
    expect(wrapper.find('.ledger-row.lock').exists()).toBe(false)
    expect(wrapper.find('.ledger-row.fail').exists()).toBe(false)
    expect(wrapper.findAll('.ledger-row.pass')).toHaveLength(2)
  })

  it('passed rows start closed and open from the row or its pip', async () => {
    const visible = [row(true, 0), row(true, 1), row(false, 2)]
    const wrapper = mountFeedback({
      success: false,
      testsPassed: 2,
      totalTests: 3,
      test_results: visible,
      results: visible,
      lockedCount: 0,
    })

    const rows = wrapper.findAll('.ledger-row.pass')
    expect(rows[0].classes()).toContain('closed')
    expect(rows[0].attributes('aria-expanded')).toBe('false')

    await rows[0].trigger('click')
    expect(wrapper.findAll('.ledger-row.pass')[0].classes()).toContain('open')
    expect(wrapper.findAll('.ledger-row.pass')[0].find('.result').text()).toBe('0')
    expect(wrapper.findAll('.pip.pass')[0].attributes('aria-pressed')).toBe('true')

    await wrapper.findAll('.pip.pass')[1].trigger('click')
    expect(wrapper.findAll('.ledger-row.pass')[1].classes()).toContain('open')

    await wrapper.findAll('.pip.pass')[0].trigger('click')
    expect(wrapper.findAll('.ledger-row.pass')[0].classes()).toContain('closed')
  })

  it('marks a runtime error on the failing row', () => {
    const visible = [row(false, 0, 'ZeroDivisionError: division by zero')]
    const wrapper = mountFeedback({
      success: false,
      testsPassed: 0,
      totalTests: 2,
      test_results: visible,
      results: visible,
      lockedCount: 1,
    })

    const actual = wrapper.find('.ledger-row.fail .actual')
    expect(actual.classes()).toContain('is-error')
    expect(actual.text()).toBe('ZeroDivisionError: division by zero')
  })
})
