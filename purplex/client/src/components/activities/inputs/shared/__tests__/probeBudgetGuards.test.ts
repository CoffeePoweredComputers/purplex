import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import axios from 'axios'
import { useProbeState } from '../useProbeState'
import ProbePanel from '../ProbePanel.vue'
import type { ActivityProblem } from '../../../types'
import { withSetup } from '@/test/setup'

vi.mock('axios')

const problem = {
  slug: 'guard-probe',
  probe_config: { function_signature: 'def f(x: int) -> int' },
} as unknown as ActivityProblem

afterEach(() => {
  vi.clearAllMocks()
})

describe('useProbeState budget guards', () => {
  it('does not post a probe for inputs that were already probed', async () => {
    vi.mocked(axios.get).mockResolvedValue({ data: { can_probe: true, mode: 'block', remaining: 3 } })
    vi.mocked(axios.post).mockResolvedValue({ data: { success: true, result: 10 } })
    const state = withSetup(() => useProbeState(problem))
    await flushPromises()

    state.updateProbeInput('x', '5')
    await state.executeProbe()
    expect(axios.post).toHaveBeenCalledTimes(1)

    await nextTick()
    expect(state.isDuplicate.value).toBe(true)
    await state.executeProbe()
    expect(axios.post).toHaveBeenCalledTimes(1)
  })

  it('re-fetches probe status when a submission finishes', async () => {
    const exhausted = { mode: 'cooldown', remaining: 0, can_probe: false, submissions_to_next_refill: 1 }
    const refilled = { mode: 'cooldown', remaining: 2, can_probe: true }
    vi.mocked(axios.get).mockResolvedValue({ data: exhausted })
    const submitting = ref(false)
    const state = withSetup(() => useProbeState(problem, { isSubmitting: () => submitting.value }))
    await flushPromises()
    expect(state.canProbe.value).toBe(false)

    vi.mocked(axios.get).mockClear()
    vi.mocked(axios.get).mockResolvedValue({ data: refilled })
    submitting.value = true
    await flushPromises()
    expect(axios.get).not.toHaveBeenCalled()

    submitting.value = false
    await flushPromises()
    expect(axios.get).toHaveBeenCalledWith('/api/problems/guard-probe/probe/status/')
    expect(state.canProbe.value).toBe(true)
    expect(state.probeCountDisplay.value).toBe('2 left')
  })
})

function mountPanel(overrides: Record<string, unknown>) {
  return mount(ProbePanel, {
    props: {
      functionName: 'f',
      probeStatusClass: 'status-available',
      probeCountDisplay: '2 left',
      probeStatusText: '',
      probeParams: [{ name: 'x', type: 'int' }],
      probeInputs: { x: '5' },
      canProbe: true,
      isExecuting: false,
      hasValidInputs: true,
      inputErrors: {},
      probeHistory: [{ input: { x: 5 }, output: 10, timestamp: '' }],
      probeError: null,
      isDuplicate: true,
      cachedResult: 10,
      formatFunctionCall: (input: Record<string, unknown>) => `f(${Object.values(input).join(', ')})`,
      formatOutput: (output: unknown) => JSON.stringify(output),
      ...overrides,
    },
  })
}

describe('ProbePanel duplicate and exhausted states', () => {
  it('does not emit a probe when Enter is pressed on a duplicate input', async () => {
    const wrapper = mountPanel({})
    await wrapper.find('#probe-x').trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('execute-probe')).toBeUndefined()

    await wrapper.setProps({ isDuplicate: false, cachedResult: null })
    await wrapper.find('#probe-x').trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('execute-probe')).toHaveLength(1)
  })

  it('shows the duplicate state while probes remain', () => {
    const button = mountPanel({}).find('.probe-btn')
    expect(button.text()).toContain('Already probed')
    expect(button.classes()).toContain('is-duplicate')
    expect(button.find('.probe-count-badge').exists()).toBe(false)
  })

  it('shows the exhausted badge instead of the duplicate state when no probes remain', () => {
    const wrapper = mountPanel({
      canProbe: false,
      probeStatusClass: 'status-exhausted',
      probeCountDisplay: '0 left',
    })
    const button = wrapper.find('.probe-btn')
    expect(button.text()).not.toContain('Already probed')
    expect(button.classes()).not.toContain('is-duplicate')
    expect(button.attributes('disabled')).toBeDefined()
    const badge = button.find('.probe-count-badge')
    expect(badge.text()).toBe('· 0 left')
    expect(badge.classes()).toContain('status-exhausted')
    expect(button.attributes('title')).toBe(wrapper.vm.$t('problems.probe.tooltipExhausted'))
    // The cached result is still shown for the probed inputs
    expect(wrapper.find('.fn-result').classes()).toContain('is-cached')
  })
})
