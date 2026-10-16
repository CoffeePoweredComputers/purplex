import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ProbeableFeedback from '../ProbeableFeedback.vue'

const row = (isSuccessful: boolean, i: number, error?: string) => ({
  isSuccessful,
  function_call: `f(${i})`,
  expected_output: i,
  actual_output: isSuccessful ? i : -1,
  error,
})

const CODE = 'def f(x):\n    return x'
const EXPLANATION = 'Returns its argument unchanged.'

function mountFeedback(entry: Record<string, unknown>, props: Record<string, unknown> = {}) {
  return mount(ProbeableFeedback, {
    props: {
      codeResults: [CODE],
      testResults: [entry] as never,
      ...props,
    },
    global: {
      stubs: { Editor: true, PyTutorModal: true, SegmentAnalysisModal: true },
    },
  })
}

function mountSpec(entry: Record<string, unknown>, props: Record<string, unknown> = {}) {
  return mountFeedback(entry, {
    problemType: 'probeable_spec',
    userPrompt: EXPLANATION,
    ...props,
  })
}

function pipClasses(wrapper: ReturnType<typeof mountFeedback>): string[] {
  return wrapper.findAll('.pip').map(p => (p.classes('pass') ? 'pass' : p.classes('fail') ? 'fail' : 'lock'))
}

describe('ProbeableFeedback ladder (probeable_code)', () => {
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
    // Two-line diff: the "got" line precedes the "expected" line
    expect(failing.findAll('.diff-label').map((l) => l.text())).toEqual(['got', 'expected'])
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

  it('passed rows always show their result and nothing in the ladder toggles', () => {
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
    expect(rows).toHaveLength(2)
    expect(rows[0].find('.test-call').text()).toBe('f(0)')
    expect(rows[0].find('.result').text()).toBe('0')
    expect(rows[1].find('.result').text()).toBe('1')
    // No buttons, no expand/collapse state, no pressed pips
    expect(wrapper.findAll('.test-ladder button').map((b) => b.classes())).toEqual([['debug-btn']])
    expect(wrapper.find('[aria-expanded]').exists()).toBe(false)
    expect(wrapper.find('[aria-pressed]').exists()).toBe(false)
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

const segmentation = {
  segment_count: 1,
  comprehension_level: 'relational',
  passed: true,
  threshold: 2,
  segments: [{ id: 1, text: EXPLANATION, code_lines: [2] }],
}

const failingEntry = () => {
  const visible = [row(true, 0), row(false, 1)]
  return {
    success: false,
    testsPassed: 1,
    totalTests: 4,
    test_results: visible,
    results: visible,
    lockedCount: 2,
    visibleCount: 2,
  }
}

const passingEntry = () => {
  const visible = [row(true, 0), row(true, 1)]
  return {
    success: true,
    testsPassed: 2,
    totalTests: 2,
    test_results: visible,
    results: visible,
    lockedCount: 0,
    visibleCount: 2,
  }
}

describe('ProbeableFeedback (probeable_code) top panel', () => {
  it('shows the submitted code, no explanation and no abstraction card', () => {
    const wrapper = mountFeedback(failingEntry(), { segmentation, segmentationEnabled: true })

    expect(wrapper.find('.code-section').exists()).toBe(true)
    expect(wrapper.find('.explanation-section').exists()).toBe(false)
    expect(wrapper.find('.metric-card').exists()).toBe(false)
    expect(wrapper.find('.ledger-row.fail .debug-btn').exists()).toBe(true)
  })
})

describe('ProbeableFeedback (probeable_spec)', () => {
  it('quotes the explanation instead of the code editor', () => {
    const wrapper = mountSpec(failingEntry())

    expect(wrapper.find('.code-section').exists()).toBe(false)
    expect(wrapper.find('.explanation-section .explanation-text').text()).toBe(EXPLANATION)
  })

  it('has no debug button on the failing row', () => {
    const wrapper = mountSpec(failingEntry())

    expect(wrapper.find('.ledger-row.fail').exists()).toBe(true)
    expect(wrapper.find('.debug-btn').exists()).toBe(false)
  })

  it('renders the same ladder as probeable_code for the same rows', () => {
    const code = mountFeedback(failingEntry())
    const spec = mountSpec(failingEntry())

    expect(pipClasses(spec)).toEqual(['pass', 'fail', 'lock', 'lock'])
    expect(pipClasses(spec)).toEqual(pipClasses(code))
    expect(spec.find('.ledger-row.lock').text()).toBe(code.find('.ledger-row.lock').text())
    expect(spec.findAll('.ledger-row.pass').map((r) => r.text())).toEqual(
      code.findAll('.ledger-row.pass').map((r) => r.text()),
    )
    const specFail = spec.find('.ledger-row.fail')
    const codeFail = code.find('.ledger-row.fail')
    for (const sel of ['.test-call', '.expected', '.actual']) {
      expect(specFail.find(sel).text()).toBe(codeFail.find(sel).text())
    }
  })

  it('shows an unlocked abstraction card below the ladder when the version passes', () => {
    const wrapper = mountSpec(passingEntry(), { segmentation, segmentationEnabled: true })

    const card = wrapper.find('.metric-card')
    expect(card.exists()).toBe(true)
    expect(card.classes()).toContain('status-success')
    expect(card.attributes('aria-disabled')).toBe('false')
    // The card follows the ladder
    const html = wrapper.html()
    expect(html.indexOf('test-ladder')).toBeLessThan(html.indexOf('metric-card'))
  })

  it('locks the abstraction card when the version fails a test', () => {
    const wrapper = mountSpec(failingEntry(), { segmentation, segmentationEnabled: true })

    const card = wrapper.find('.metric-card')
    expect(card.classes()).toContain('status-locked')
    expect(card.attributes('aria-disabled')).toBe('true')
  })

  it('has no abstraction card without segmentation data', () => {
    const wrapper = mountSpec(passingEntry(), { segmentation: null, segmentationEnabled: true })

    expect(wrapper.find('.metric-card').exists()).toBe(false)
  })

  it('has no abstraction card when segmentation is disabled', () => {
    const wrapper = mountSpec(passingEntry(), { segmentation, segmentationEnabled: false })

    expect(wrapper.find('.metric-card').exists()).toBe(false)
  })
})
