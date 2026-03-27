import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CorrectnessModal from '../CorrectnessModal.vue'
import en from '@/i18n/locales/en'

beforeEach(() => {
  // CorrectnessModal reads localStorage in onMounted
  vi.stubGlobal('localStorage', {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    length: 0,
    key: vi.fn(() => null),
  })
})

const cm = en.feedback.correctnessModal

function makeVariant(passing: boolean, testsPassed = 3, testsTotal = 3) {
  return {
    code: 'def foo(): pass',
    passing,
    testsPassed,
    testsTotal,
    tests: [
      { call: 'foo(1)', expected: '2', actual: passing ? '2' : '3', passed: passing },
      { call: 'foo(2)', expected: '4', actual: '4', passed: true },
      { call: 'foo(3)', expected: '6', actual: '6', passed: true },
    ],
  }
}

const stubs = {
  Teleport: true,
  Editor: { template: '<div />' },
}

describe('CorrectnessModal i18n rendering', () => {
  it('title renders correctnessModal.title value', () => {
    const wrapper = mount(CorrectnessModal, {
      props: {
        isVisible: true,
        variants: [makeVariant(true)],
      },
      global: { stubs },
    })
    expect(wrapper.find('.modal-title').text()).toBe(cm.title)
  })

  it('version badge renders interpolated versionPass', () => {
    const wrapper = mount(CorrectnessModal, {
      props: {
        isVisible: true,
        variants: [makeVariant(true), makeVariant(false, 1, 3)],
      },
      global: { stubs },
    })
    const badge = wrapper.find('.badge-level')
    // 1 passing out of 2 total
    expect(badge.text()).toContain('1')
    expect(badge.text()).toContain('2')
  })

  it('"Expected"/"Got" labels come from locale', () => {
    const wrapper = mount(CorrectnessModal, {
      props: {
        isVisible: true,
        variants: [makeVariant(true)],
      },
      global: { stubs },
    })
    const labels = wrapper.findAll('.value-label').map(el => el.text())
    expect(labels).toContain(cm.expected)
    expect(labels).toContain(cm.got)
  })

  it('summaryHeadline renders from locale when all pass (NOT hardcoded English)', () => {
    const wrapper = mount(CorrectnessModal, {
      props: {
        isVisible: true,
        variants: [makeVariant(true), makeVariant(true)],
      },
      global: { stubs },
    })
    const headline = wrapper.find('.summary-headline')
    expect(headline.text()).toBe(cm.summaryHeadlineAll)
  })

  it('summaryHeadline renders from locale when none pass', () => {
    const wrapper = mount(CorrectnessModal, {
      props: {
        isVisible: true,
        variants: [makeVariant(false, 0, 3)],
      },
      global: { stubs },
    })
    expect(wrapper.find('.summary-headline').text()).toBe(cm.summaryHeadlineNone)
  })

  it('summaryHeadline renders from locale when partially passing', () => {
    const wrapper = mount(CorrectnessModal, {
      props: {
        isVisible: true,
        variants: [makeVariant(true), makeVariant(false, 1, 3)],
      },
      global: { stubs },
    })
    expect(wrapper.find('.summary-headline').text()).toBe(cm.summaryHeadlinePartial)
  })

  it('size preset labels come from locale', () => {
    const wrapper = mount(CorrectnessModal, {
      props: {
        isVisible: true,
        variants: [makeVariant(true)],
      },
      global: { stubs },
    })
    const sizeLabel = wrapper.find('.size-label')
    expect(sizeLabel.text()).toBe(cm.sizeLabel)
  })
})
