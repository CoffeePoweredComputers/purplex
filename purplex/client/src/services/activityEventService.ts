import axios from 'axios'
import { log } from '../utils/logger'

const logger = log.createComponentLogger('ActivityEventService')

export interface ActivityEventRequest {
  event_type: string
  payload?: Record<string, unknown>
  problem_slug?: string
  course_id?: string
  idempotency_key?: string
}

interface ActivityEventResponse {
  id: number
  event_type: string
}

class ActivityEventService {
  /**
   * Record a single activity event. Fire-and-forget — failures
   * are logged but never propagated to the caller.
   */
  async record(event: ActivityEventRequest): Promise<ActivityEventResponse | null> {
    try {
      const response = await axios.post<ActivityEventResponse>(
        '/api/activity-events/',
        event
      )
      logger.debug('Event recorded', { type: event.event_type, id: response.data.id })
      return response.data
    } catch (error) {
      logger.warn('Failed to record activity event', { type: event.event_type, error })
      return null
    }
  }
}

export const activityEventService = new ActivityEventService()
