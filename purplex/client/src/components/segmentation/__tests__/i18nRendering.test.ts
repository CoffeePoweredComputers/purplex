import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import SegmentMapping from '../SegmentMapping.vue'
import SegmentAnalysisModal from '../SegmentAnalysisModal.vue'
import en from '@/i18n/locales/en'

beforeEach(() => {
  // SegmentAnalysisModal reads localStorage in onMounted
  vi.stubGlobal('localStorage', {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    length: 0,
    key: vi.fn(() => null),
  })
})

const segmentModal = en.feedback.segmentModal
const segmentMapping = en.feedback.segmentMapping

describe('SegmentMapping i18n rendering', () => {
  const baseProps = {
    segments: [
      { id: 1, text: 'Finds the maximum', code_lines: [1, 2] },
    ],
    referenceCode: 'def find_max(lst):\n  return max(lst)',
    userPrompt: 'Find the largest element',
  }

  it('renders panel titles from locale keys', () => {
    const wrapper = mount(SegmentMapping, { props: baseProps })
    const text = wrapper.text()
    expect(text).toContain(segmentMapping.yourExplanation)
    expect(text).toContain(segmentMapping.referenceCode)
  })
})

describe('SegmentAnalysisModal i18n rendering', () => {
  const relationalProps = {
    isVisible: true,
    segmentation: {
      segments: [{ id: 1, text: 'Finds the maximum', code_lines: [1, 2] }],
      segment_count: 1,
      comprehension_level: 'relational' as const,
      feedback: 'Great work!',
      threshold: 2,
    },
    referenceCode: 'def find_max(lst):\n  return max(lst)',
  }

  const multiStructuralProps = {
    ...relationalProps,
    segmentation: {
      ...relationalProps.segmentation,
      comprehension_level: 'multi_structural' as const,
      segment_count: 5,
      segments: Array.from({ length: 5 }, (_, i) => ({
        id: i + 1,
        text: `Step ${i + 1}`,
        code_lines: [i + 1],
      })),
      feedback: 'Too detailed',
    },
  }

  const stubs = { Teleport: true }

  it('relational feedback renders i18n-t with count slot', () => {
    const wrapper = mount(SegmentAnalysisModal, {
      props: relationalProps,
      global: { stubs },
    })
    const feedbackMsg = wrapper.find('.feedback-message')
    // The i18n-t component interpolates the count into the message.
    // Check that the rendered text contains the key fragments.
    expect(feedbackMsg.text()).toContain('1')
    // i18n-t splits the message around {count}, so check for a fragment of the locale value
    const localeParts = segmentModal.relationalFeedback.split('{count}')
    expect(feedbackMsg.text()).toContain(localeParts[0].trim())
  })

  it('multi-structural feedback renders i18n-t with count and goal slots', () => {
    const wrapper = mount(SegmentAnalysisModal, {
      props: multiStructuralProps,
      global: { stubs },
    })
    const feedbackMsg = wrapper.find('.feedback-message')
    expect(feedbackMsg.text()).toContain('5')
    const localeParts = segmentModal.multiStructuralFeedback.split('{count}')
    expect(feedbackMsg.text()).toContain(localeParts[0].trim())
  })

  it('formatLevel("relational") renders levelExcellent from locale', () => {
    const wrapper = mount(SegmentAnalysisModal, {
      props: relationalProps,
      global: { stubs },
    })
    const badge = wrapper.find('.badge-level')
    expect(badge.text()).toContain(segmentModal.levelExcellent)
  })

  it('getExplanation() renders from locale, not hardcoded English', () => {
    const wrapper = mount(SegmentAnalysisModal, {
      props: relationalProps,
      global: { stubs },
    })
    const explanation = wrapper.find('.feedback-explanation')
    expect(explanation.text()).toBe(segmentModal.explanationRelational)
  })

  it('getExplanation() for multi_structural renders from locale', () => {
    const wrapper = mount(SegmentAnalysisModal, {
      props: multiStructuralProps,
      global: { stubs },
    })
    const explanation = wrapper.find('.feedback-explanation')
    expect(explanation.text()).toBe(segmentModal.explanationMultiStructural)
  })

  it('size preset labels come from locale', () => {
    const wrapper = mount(SegmentAnalysisModal, {
      props: relationalProps,
      global: { stubs },
    })
    const buttons = wrapper.findAll('.size-btn')
    // There should be 4 size preset buttons
    expect(buttons.length).toBe(4)
    // Size label should come from locale
    const sizeLabel = wrapper.find('.size-label')
    expect(sizeLabel.text()).toBe(segmentModal.sizeLabel)
  })
})
