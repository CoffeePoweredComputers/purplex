import { describe, it, expect, vi, beforeEach, Mock } from 'vitest'
import axios from 'axios'
import submissionService, { 
  SubmissionSummary, 
  ProblemSetProgress, 
  SubmissionRequest,
  SubmissionResponse 
} from '../submissionService'
import { log } from '../../utils/logger'
import type { BaseSubmission, SubmissionTestResult } from '../../types'

// Mock dependencies
vi.mock('axios')
vi.mock('../../utils/logger', () => ({
  log: {
    error: vi.fn()
  }
}))

// Mock data
const mockSubmissionSummary: SubmissionSummary = {
  problem_slug: 'two-sum',
  problem_title: 'Two Sum',
  problem_set_slug: 'arrays',
  problem_set_title: 'Array Problems',
  best_score: 85,
  total_attempts: 3,
  last_attempt: '2025-08-05T10:00:00Z',
  completed: true
}

const mockProblemSetProgress: ProblemSetProgress = {
  slug: 'arrays',
  title: 'Array Problems',
  completed_problems: 5,
  total_problems: 10,
  average_score: 75,
  percentage: 50,
  last_activity: '2025-08-05T10:00:00Z'
}

const mockSubmissionRequest: SubmissionRequest = {
  problem_slug: 'two-sum',
  user_code: 'def two_sum(nums, target): return [0, 1]',
  prompt: 'Find two numbers that add up to target',
  time_spent: 300
}

const mockSubmissionResponse: SubmissionResponse = {
  success: true,
  score: 100,
  total_tests: 5,
  passed_tests: 5,
  execution_time: 0.05,
  submission_id: 123,
  message: 'All tests passed!'
}

const mockBaseSubmission: BaseSubmission = {
  id: 1,
  problem_id: 1,
  user_id: 1,
  code_variations: [
    { code: 'def two_sum(nums, target): return [0, 1]', variation_id: 1 },
    { code: 'def two_sum(nums, target): return [1, 2]', variation_id: 2 }
  ],
  total_variations: 2,
  passing_variations: 1,
  test_results: [
    { pass: true, expected: '[0, 1]', actual: '[0, 1]' } as SubmissionTestResult,
    { pass: false, expected: '[1, 2]', actual: '[0, 1]' } as SubmissionTestResult
  ],
  created_at: '2025-08-05T10:00:00Z',
  score: 50
}

describe('SubmissionService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('API Methods', () => {
    describe('getSubmissionsSummary', () => {
      it('should fetch submissions summary successfully', async () => {
        const mockData = [mockSubmissionSummary];
        (axios.get as Mock).mockResolvedValue({ data: mockData })

        const result = await submissionService.getSubmissionsSummary()

        expect(axios.get).toHaveBeenCalledWith('/api/submissions/summary/')
        expect(result).toEqual(mockData)
      })

      it('should handle errors when fetching submissions summary', async () => {
        const mockError = new Error('Network error');
        (axios.get as Mock).mockRejectedValue(mockError)

        await expect(submissionService.getSubmissionsSummary()).rejects.toThrow('Network error')
        expect(log.error).toHaveBeenCalledWith('Failed to fetch submissions summary', mockError)
      })
    })

    describe('getProblemSetsProgress', () => {
      it('should fetch problem sets progress successfully', async () => {
        const mockData = [mockProblemSetProgress];
        (axios.get as Mock).mockResolvedValue({ data: mockData })

        const result = await submissionService.getProblemSetsProgress()

        expect(axios.get).toHaveBeenCalledWith('/api/submissions/problem-sets-progress/')
        expect(result).toEqual(mockData)
      })

      it('should handle errors when fetching problem sets progress', async () => {
        const mockError = new Error('Server error');
        (axios.get as Mock).mockRejectedValue(mockError)

        await expect(submissionService.getProblemSetsProgress()).rejects.toThrow('Server error')
        expect(log.error).toHaveBeenCalledWith('Failed to fetch problem sets progress', mockError)
      })
    })

    describe('getProblemSetProgress', () => {
      it('should fetch specific problem set progress successfully', async () => {
        (axios.get as Mock).mockResolvedValue({ data: mockProblemSetProgress })

        const result = await submissionService.getProblemSetProgress('arrays')

        expect(axios.get).toHaveBeenCalledWith('/api/submissions/problem-sets/arrays/progress/')
        expect(result).toEqual(mockProblemSetProgress)
      })

      it('should handle errors with context', async () => {
        const mockError = new Error('Not found');
        (axios.get as Mock).mockRejectedValue(mockError)

        await expect(submissionService.getProblemSetProgress('arrays')).rejects.toThrow('Not found')
        expect(log.error).toHaveBeenCalledWith(
          'Failed to fetch progress for problem set', 
          { problemSetSlug: 'arrays', error: mockError }
        )
      })
    })

    describe('submitSolution', () => {
      it('should submit solution successfully', async () => {
        (axios.post as Mock).mockResolvedValue({ data: mockSubmissionResponse })

        const result = await submissionService.submitSolution(mockSubmissionRequest)

        expect(axios.post).toHaveBeenCalledWith('/api/submissions/', mockSubmissionRequest)
        expect(result).toEqual(mockSubmissionResponse)
      })

      it('should handle submission errors', async () => {
        const mockError = new Error('Code execution failed');
        (axios.post as Mock).mockRejectedValue(mockError)

        await expect(submissionService.submitSolution(mockSubmissionRequest)).rejects.toThrow('Code execution failed')
        expect(log.error).toHaveBeenCalledWith('Failed to submit solution', mockError)
      })
    })

    describe('testSolution', () => {
      it('should test solution without saving', async () => {
        const mockTestResult = { success: true, output: 'Test passed' };
        (axios.post as Mock).mockResolvedValue({ data: mockTestResult })

        const result = await submissionService.testSolution('two-sum', 'def two_sum(): pass')

        expect(axios.post).toHaveBeenCalledWith('/api/test-solution/', {
          problem_slug: 'two-sum',
          user_code: 'def two_sum(): pass'
        })
        expect(result).toEqual(mockTestResult)
      })

      it('should handle test errors', async () => {
        const mockError = new Error('Syntax error');
        (axios.post as Mock).mockRejectedValue(mockError)

        await expect(submissionService.testSolution('two-sum', 'invalid code')).rejects.toThrow('Syntax error')
        expect(log.error).toHaveBeenCalledWith('Failed to test solution', mockError)
      })
    })

    describe('getProblemSubmissions', () => {
      it('should fetch problem submissions with params', async () => {
        const mockData = [mockSubmissionSummary];
        (axios.get as Mock).mockResolvedValue({ data: mockData })

        const result = await submissionService.getProblemSubmissions('two-sum')

        expect(axios.get).toHaveBeenCalledWith('/api/submissions/', {
          params: { problem_slug: 'two-sum' }
        })
        expect(result).toEqual(mockData)
      })
    })

    describe('getProblemBestScore', () => {
      it('should return best score from submissions', async () => {
        const submissions = [
          { ...mockSubmissionSummary, best_score: 60 },
          { ...mockSubmissionSummary, best_score: 85 },
          { ...mockSubmissionSummary, best_score: 75 }
        ];
        (axios.get as Mock).mockResolvedValue({ data: submissions })

        const result = await submissionService.getProblemBestScore('two-sum')

        expect(result).toBe(85)
      })

      it('should return 0 for no submissions', async () => {
        (axios.get as Mock).mockResolvedValue({ data: [] })

        const result = await submissionService.getProblemBestScore('two-sum')

        expect(result).toBe(0)
      })

      it('should return 0 on error', async () => {
        (axios.get as Mock).mockRejectedValue(new Error('Network error'))

        const result = await submissionService.getProblemBestScore('two-sum')

        expect(result).toBe(0)
        expect(log.error).toHaveBeenCalled()
      })
    })
  })

  describe('Utility Methods', () => {
    describe('calculateProgressPercentage', () => {
      it('should calculate percentage correctly', () => {
        expect(submissionService.calculateProgressPercentage(5, 10)).toBe(50)
        expect(submissionService.calculateProgressPercentage(3, 4)).toBe(75)
        expect(submissionService.calculateProgressPercentage(10, 10)).toBe(100)
      })

      it('should handle edge cases', () => {
        expect(submissionService.calculateProgressPercentage(0, 10)).toBe(0)
        expect(submissionService.calculateProgressPercentage(0, 0)).toBe(0)
      })
    })

    describe('isProblemCompleted', () => {
      it('should check completion with default threshold', () => {
        expect(submissionService.isProblemCompleted(100)).toBe(true)
        expect(submissionService.isProblemCompleted(99)).toBe(false)
      })

      it('should check completion with custom threshold', () => {
        expect(submissionService.isProblemCompleted(80, 80)).toBe(true)
        expect(submissionService.isProblemCompleted(79, 80)).toBe(false)
      })
    })

    describe('formatSubmissionForDisplay', () => {
      it('should format submission data correctly', () => {
        const formatted = submissionService.formatSubmissionForDisplay(mockSubmissionSummary)

        expect(formatted).toMatchObject({
          ...mockSubmissionSummary,
          completion_status: 'in_progress', // 85 < 100
          last_activity: expect.any(String),
          progress_text: '85% (3 attempts)'
        })
      })

      it('should handle completed submissions', () => {
        const completedSubmission = { ...mockSubmissionSummary, best_score: 100 }
        const formatted = submissionService.formatSubmissionForDisplay(completedSubmission)

        expect(formatted.completion_status).toBe('completed')
      })

      it('should handle null last_attempt', () => {
        const noAttemptSubmission = { ...mockSubmissionSummary, last_attempt: null as any }
        const formatted = submissionService.formatSubmissionForDisplay(noAttemptSubmission)

        expect(formatted.last_activity).toBeNull()
      })
    })

    describe('getPrimaryCode', () => {
      it('should get code from first variation object', () => {
        const result = submissionService.getPrimaryCode(mockBaseSubmission)
        expect(result).toBe('def two_sum(nums, target): return [0, 1]')
      })

      it('should handle string variations', () => {
        const submission = {
          ...mockBaseSubmission,
          code_variations: ['code string 1', 'code string 2']
        } as any
        const result = submissionService.getPrimaryCode(submission)
        expect(result).toBe('code string 1')
      })

      it('should return empty string for no variations', () => {
        const submission = { ...mockBaseSubmission, code_variations: [] } as BaseSubmission
        expect(submissionService.getPrimaryCode(submission)).toBe('')
      })

      it('should handle null/undefined variations', () => {
        const submission = { ...mockBaseSubmission, code_variations: null } as any
        expect(submissionService.getPrimaryCode(submission)).toBe('')
      })
    })

    describe('calculateSuccessRate', () => {
      it('should calculate success rate correctly', () => {
        expect(submissionService.calculateSuccessRate(mockBaseSubmission)).toBe(50) // 1/2
      })

      it('should handle zero total variations', () => {
        const submission = { 
          ...mockBaseSubmission, 
          passing_variations: 0, 
          total_variations: 0 
        } as BaseSubmission
        expect(submissionService.calculateSuccessRate(submission)).toBe(0)
      })

      it('should handle undefined values', () => {
        const submission = {} as BaseSubmission
        expect(submissionService.calculateSuccessRate(submission)).toBe(0)
      })
    })

    describe('getTestResultsSummary', () => {
      it('should summarize test results correctly', () => {
        const summary = submissionService.getTestResultsSummary(mockBaseSubmission)
        expect(summary).toBe('1/2 tests passed (50%)')
      })

      it('should handle all tests passing', () => {
        const submission = {
          ...mockBaseSubmission,
          test_results: [
            { pass: true } as SubmissionTestResult,
            { pass: true } as SubmissionTestResult
          ]
        } as BaseSubmission
        const summary = submissionService.getTestResultsSummary(submission)
        expect(summary).toBe('2/2 tests passed (100%)')
      })

      it('should handle no test results', () => {
        const submission = { ...mockBaseSubmission, test_results: [] } as BaseSubmission
        expect(submissionService.getTestResultsSummary(submission)).toBe('0/0 tests passed (0%)')
      })

      it('should handle missing test results', () => {
        const submission = {} as BaseSubmission
        expect(submissionService.getTestResultsSummary(submission)).toBe('No test results available')
      })
    })
  })
})