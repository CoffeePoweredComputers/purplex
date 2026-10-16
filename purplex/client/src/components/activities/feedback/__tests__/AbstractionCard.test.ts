import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AbstractionCard from '../AbstractionCard.vue'

const segmentation = (segment_count: number) => ({
  segment_count,
  comprehension_level: segment_count <= 2 ? 'relational' : 'multi_structural',
  threshold: 2,
  segments: [],
})

function mountCard(props: Record<string, unknown>) {
  return mount(AbstractionCard, {
    props: props as never,
    global: { stubs: { SegmentAnalysisModal: true } },
  })
}

describe('AbstractionCard', () => {
  it('locked: inert, no segment count, click does not open the analysis', async () => {
    const wrapper = mountCard({ segmentation: segmentation(1), locked: true })
    const card = wrapper.find('.metric-card')

    expect(card.classes()).toContain('status-locked')
    expect(card.attributes('aria-disabled')).toBe('true')
    expect(wrapper.find('.status-metric').exists()).toBe(false)
    expect(wrapper.find('.card-action').exists()).toBe(false)

    await card.trigger('click')
    expect(wrapper.findComponent({ name: 'SegmentAnalysisModal' }).props('isVisible')).toBe(false)
  })

  it('high-level explanation: success state with the segment count', () => {
    const wrapper = mountCard({ segmentation: segmentation(2), locked: false })
    const card = wrapper.find('.metric-card')

    expect(card.classes()).toContain('status-success')
    expect(wrapper.find('.progress-bar-fill').attributes('style')).toContain('width: 100%')
    expect(wrapper.find('.status-metric').text()).toContain('2')
    expect(wrapper.find('.metric-hint').exists()).toBe(false)
  })

  it('too detailed: error state with the threshold hint', () => {
    const wrapper = mountCard({ segmentation: segmentation(4), locked: false })

    expect(wrapper.find('.metric-card').classes()).toContain('status-error')
    expect(wrapper.find('.progress-bar-fill').attributes('style')).toContain('width: 60%')
    expect(wrapper.find('.metric-hint').exists()).toBe(true)
  })

  it('opens the segment analysis on click and via open()', async () => {
    const wrapper = mountCard({ segmentation: segmentation(1), locked: false })
    const modal = () => wrapper.findComponent({ name: 'SegmentAnalysisModal' })

    await wrapper.find('.metric-card').trigger('click')
    expect(modal().props('isVisible')).toBe(true)

    modal().vm.$emit('close')
    await wrapper.vm.$nextTick()
    expect(modal().props('isVisible')).toBe(false)

    ;(wrapper.vm as unknown as { open: () => void }).open()
    await wrapper.vm.$nextTick()
    expect(modal().props('isVisible')).toBe(true)
  })
})
