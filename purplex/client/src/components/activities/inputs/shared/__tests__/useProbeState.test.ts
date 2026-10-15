import { describe, expect, it, vi } from 'vitest'
import { useProbeState } from '../useProbeState'
import type { ActivityProblem, ProbeStatus } from '../../../types'

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key: string) => key }),
}))

// Mock axios: status and history loads resolve to nothing, so each test sets probeStatus itself
vi.mock('axios', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: {} }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  },
}))

const problem = { slug: 'probe-me', function_name: 'f' } as unknown as ActivityProblem

function status(overrides: Partial<ProbeStatus>): ProbeStatus {
  return {
    mode: 'block',
    remaining: 0,
    used: 0,
    can_probe: true,
    message: '',
    ...overrides,
  }
}

describe('useProbeState', () => {
  describe('probeCountDisplay', () => {
    it('shows the remaining budget of a block-mode problem', () => {
      const probe = useProbeState(problem)
      probe.probeStatus.value = status({ mode: 'block', remaining: 7, message: '7 probes remaining' })
      expect(probe.probeCountDisplay.value).toBe('7 left')
    })

    it('shows the remaining budget of a cooldown-mode problem', () => {
      const probe = useProbeState(problem)
      probe.probeStatus.value = status({ mode: 'cooldown', remaining: 3 })
      expect(probe.probeCountDisplay.value).toBe('3 left')
    })

    it('shows 0 left once the budget is spent', () => {
      const probe = useProbeState(problem)
      probe.probeStatus.value = status({ mode: 'block', remaining: 0, can_probe: false })
      expect(probe.probeCountDisplay.value).toBe('0 left')
    })

    it('shows infinity in explore mode', () => {
      const probe = useProbeState(problem)
      probe.probeStatus.value = status({ mode: 'explore', remaining: null })
      expect(probe.probeCountDisplay.value).toBe('∞')
    })
  })

  describe('probeStatusText', () => {
    it('is the backend message', () => {
      const probe = useProbeState(problem)
      const message = 'No probes remaining. Submit 2 more times to unlock more probes.'
      probe.probeStatus.value = status({ mode: 'cooldown', can_probe: false, message })
      expect(probe.probeStatusText.value).toBe(message)
    })
  })
})
