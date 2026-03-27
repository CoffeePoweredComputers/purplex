import { beforeEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'
import { activityEventService } from '../activityEventService'

vi.mock('axios')

describe('ActivityEventService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('record', () => {
    it('sends POST to /api/activity-events/', async () => {
      vi.mocked(axios.post).mockResolvedValue({
        data: { id: 42, event_type: 'hint.track' }
      })

      const result = await activityEventService.record({
        event_type: 'hint.track',
        payload: { hint_type: 'structural' },
        problem_slug: 'two-sum',
      })

      expect(axios.post).toHaveBeenCalledWith('/api/activity-events/', {
        event_type: 'hint.track',
        payload: { hint_type: 'structural' },
        problem_slug: 'two-sum',
      })
      expect(result).toEqual({ id: 42, event_type: 'hint.track' })
    })

    it('returns response data on success', async () => {
      vi.mocked(axios.post).mockResolvedValue({
        data: { id: 7, event_type: 'session.start' }
      })

      const result = await activityEventService.record({
        event_type: 'session.start',
        payload: { page: '/' },
      })

      expect(result).not.toBeNull()
      expect(result!.id).toBe(7)
      expect(result!.event_type).toBe('session.start')
    })

    it('returns null on network error without throwing', async () => {
      vi.mocked(axios.post).mockRejectedValue(new Error('Network Error'))

      const result = await activityEventService.record({
        event_type: 'hint.track',
      })

      expect(result).toBeNull()
    })

    it('returns null on 403 (consent denied) without throwing', async () => {
      const error = {
        response: { status: 403, data: { error: 'Behavioral tracking consent required' } }
      }
      vi.mocked(axios.post).mockRejectedValue(error)

      const result = await activityEventService.record({
        event_type: 'session.start',
      })

      expect(result).toBeNull()
    })

    it('returns null on 400 (validation error) without throwing', async () => {
      const error = {
        response: { status: 400, data: { error: 'event_type is required' } }
      }
      vi.mocked(axios.post).mockRejectedValue(error)

      const result = await activityEventService.record({
        event_type: '',
      })

      expect(result).toBeNull()
    })
  })
})
