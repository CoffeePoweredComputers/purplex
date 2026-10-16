import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import Feedback from '../Feedback.vue'

const passing = { success: true, testsPassed: 1, totalTests: 1, results: [] }
const failing = { success: false, testsPassed: 0, totalTests: 1, results: [] }

const segmentation = {
  segment_count: 4,
  comprehension_level: 'multi_structural',
  threshold: 2,
  segments: [],
}

function mountFeedback(testResults: unknown[]) {
  return mount(Feedback, {
    props: {
      codeResults: testResults.map(() => 'def f(x):\n    return x'),
      testResults: testResults as never,
      userPrompt: 'Returns its argument.',
      segmentation,
      segmentationEnabled: true,
    },
    global: {
      stubs: { CorrectnessModal: true, PyTutorModal: true, SegmentAnalysisModal: true },
    },
  })
}

describe('Feedback (EiPL) explanation and abstraction', () => {
  it('quotes the explanation and locks abstraction until every version passes', () => {
    const wrapper = mountFeedback([passing, failing])

    expect(wrapper.find('.explanation-text').text()).toBe('Returns its argument.')
    const cards = wrapper.findAll('.metric-card')
    expect(cards).toHaveLength(2)
    expect(cards[1].classes()).toContain('status-locked')
  })

  it('the next-step button opens the segment analysis when the explanation is too detailed', async () => {
    const wrapper = mountFeedback([passing, passing])
    const modal = () => wrapper.findComponent({ name: 'SegmentAnalysisModal' })

    expect(wrapper.findAll('.metric-card')[1].classes()).toContain('status-error')
    expect(modal().props('isVisible')).toBe(false)

    await wrapper.find('.banner-button').trigger('click')
    expect(modal().props('isVisible')).toBe(true)
  })
})
