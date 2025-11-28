import { beforeEach, describe, expect, it, Mock, vi } from 'vitest'
import axios from 'axios'
import submissionService from '../submissionService'
import { log } from '../../utils/logger'

// Mock dependencies
vi.mock('axios')
vi.mock('../../utils/logger', () => ({
  log: {
    info: vi.fn(),
    error: vi.fn()
  }
}))

describe('SubmissionService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('submitActivity', () => {
    it('should submit activity successfully', async () => {
      const mockResponse = {
        task_id: 'task-123',
        status: 'processing',
        stream_url: '/api/tasks/task-123/stream/',
        message: 'Processing submission'
      };
      (axios.post as Mock).mockResolvedValue({ data: mockResponse })

      const result = await submissionService.submitActivity({
        problem_slug: 'two-sum',
        raw_input: 'def solution(): pass',
        problem_set_slug: 'arrays'
      })

      expect(axios.post).toHaveBeenCalledWith('/api/submit/', {
        problem_slug: 'two-sum',
        raw_input: 'def solution(): pass',
        problem_set_slug: 'arrays'
      })
      expect(result).toEqual(mockResponse)
      expect(log.info).toHaveBeenCalledWith('Submitting activity solution', { problemSlug: 'two-sum' })
    })

    it('should handle errors when submitting activity', async () => {
      const mockError = {
        response: {
          data: { error: 'Validation error' },
          status: 400
        }
      };
      (axios.post as Mock).mockRejectedValue(mockError)

      await expect(submissionService.submitActivity({
        problem_slug: 'two-sum',
        raw_input: 'invalid'
      })).rejects.toEqual({
        error: 'Validation error',
        status: 400
      })
      expect(log.error).toHaveBeenCalled()
    })
  })

  describe('getSubmissionHistory', () => {
    it('should fetch submission history successfully', async () => {
      const mockResponse = {
        problem_slug: 'two-sum',
        total_attempts: 5,
        best_score: 100,
        best_attempt_id: 'attempt-1',
        submissions: []
      };
      (axios.get as Mock).mockResolvedValue({ data: mockResponse })

      const result = await submissionService.getSubmissionHistory('two-sum', 'arrays', 'course-1')

      expect(axios.get).toHaveBeenCalledWith('/api/submissions/history/two-sum/', {
        params: {
          problem_set_slug: 'arrays',
          course_id: 'course-1'
        }
      })
      expect(result).toEqual(mockResponse)
    })

    it('should handle optional parameters', async () => {
      const mockResponse = { problem_slug: 'two-sum', total_attempts: 0, submissions: [] };
      (axios.get as Mock).mockResolvedValue({ data: mockResponse })

      await submissionService.getSubmissionHistory('two-sum')

      expect(axios.get).toHaveBeenCalledWith('/api/submissions/history/two-sum/', {
        params: {}
      })
    })

    it('should handle errors when fetching history', async () => {
      const mockError = new Error('Network error');
      (axios.get as Mock).mockRejectedValue(mockError)

      await expect(submissionService.getSubmissionHistory('two-sum')).rejects.toThrow('Network error')
      expect(log.error).toHaveBeenCalled()
    })
  })
})
