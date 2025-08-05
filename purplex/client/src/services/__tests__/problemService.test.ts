import { describe, it, expect, vi, beforeEach, Mock } from 'vitest'
import axios from 'axios'
import { problemService } from '../problemService'
import type { 
  ProblemCategory, 
  ProblemDetailed, 
  ProblemCreateRequest,
  ProblemUpdateRequest,
  TestExecutionResult,
  HintConfig,
  TestCaseDisplay
} from '../../types'

// Mock axios
vi.mock('axios')

// Mock data
const mockCategory: ProblemCategory = {
  id: 1,
  name: 'Arrays',
  slug: 'arrays',
  description: 'Array manipulation problems',
  color: '#3b82f6',
  order: 1,
  problems_count: 5
}

const mockTestCase: TestCaseDisplay = {
  id: 1,
  inputs: '[[2, 7, 11, 15], 9]',
  expected_output: '[0, 1]',
  is_visible: true,
  order: 1
}

const mockProblem: ProblemDetailed = {
  id: 1,
  slug: 'two-sum',
  title: 'Two Sum',
  description: 'Find two numbers that add up to target',
  difficulty: 'medium',
  problem_type: 'eipl',
  categories: [mockCategory],
  category_ids: [1],
  function_name: 'two_sum',
  function_signature: 'def two_sum(nums: List[int], target: int) -> List[int]:',
  reference_solution: 'return [0, 1]',
  tags: ['array', 'hash-table'],
  test_cases: [mockTestCase],
  test_cases_count: 1,
  visible_test_cases_count: 1,
  created_at: '2025-08-05T10:00:00Z',
  updated_at: '2025-08-05T10:00:00Z'
}

const mockHintConfig: HintConfig = {
  type: 'variable_fade',
  content: {
    code: 'def two_sum():\n    x = 1\n    y = 2',
    mappings: [{ from: 'x', to: 'first_num' }]
  },
  min_attempts: 3
}

const mockTestResult: TestExecutionResult = {
  success: true,
  testsPassed: 5,
  totalTests: 5,
  score: 100,
  results: [
    {
      test_number: 1,
      isSuccessful: true,
      inputs: [[2, 7, 11, 15], 9],
      expected_output: [0, 1],
      actual_output: [0, 1],
      execution_time: 0.01,
      function_call: 'two_sum([2, 7, 11, 15], 9)'
    }
  ],
  execution_time: 0.05
}

describe('ProblemService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Problem CRUD Operations', () => {
    describe('loadProblem', () => {
      it('should load problem successfully', async () => {
        (axios.get as Mock).mockResolvedValue({ data: mockProblem })

        const result = await problemService.loadProblem('two-sum')

        expect(axios.get).toHaveBeenCalledWith('/api/admin/problems/two-sum/')
        expect(result).toEqual(mockProblem)
      })

      it('should handle load errors', async () => {
        const error = { response: { data: { error: 'Not found' }, status: 404 } };
        (axios.get as Mock).mockRejectedValue(error)

        await expect(problemService.loadProblem('invalid-slug'))
          .rejects.toEqual({
            error: 'Not found',
            status: 404
          })
      })
    })

    describe('createProblem', () => {
      const validCreateData: ProblemCreateRequest = {
        title: 'New Problem',
        slug: 'new-problem',
        description: 'Description',
        difficulty: 'easy',
        problem_type: 'eipl',
        category_ids: [1],
        function_name: 'solve',
        function_signature: 'def solve():',
        reference_solution: 'return 42',
        test_cases: [
          {
            inputs: '[1, 2]',
            expected_output: '3',
            is_visible: true
          }
        ]
      }

      it('should create problem successfully', async () => {
        (axios.post as Mock).mockResolvedValue({ data: mockProblem })

        const result = await problemService.createProblem(validCreateData)

        expect(axios.post).toHaveBeenCalledWith(
          '/api/admin/problems/',
          validCreateData
        )
        expect(result).toEqual(mockProblem)
      })

      it('should validate required fields', async () => {
        const invalidData = { ...validCreateData, title: '' }

        await expect(problemService.createProblem(invalidData))
          .rejects.toMatchObject({
            error: expect.stringContaining('Title is required'),
            status: -1
          })
      })

      it('should validate function name format', async () => {
        const invalidData = { ...validCreateData, function_name: '123invalid' }

        await expect(problemService.createProblem(invalidData))
          .rejects.toMatchObject({
            error: expect.stringContaining('Function name must be a valid Python identifier'),
            status: -1
          })
      })

      it('should require at least one test case', async () => {
        const invalidData = { ...validCreateData, test_cases: [] }

        await expect(problemService.createProblem(invalidData))
          .rejects.toMatchObject({
            error: expect.stringContaining('At least one test case is required'),
            status: -1
          })
      })

      it('should handle multiple validation errors', async () => {
        const invalidData = {
          ...validCreateData,
          title: '',
          function_name: '',
          reference_solution: '',
          test_cases: []
        }

        await expect(problemService.createProblem(invalidData))
          .rejects.toMatchObject({
            error: expect.stringContaining('Title is required'),
            status: -1
          })
      })
    })

    describe('updateProblem', () => {
      const updateData: ProblemUpdateRequest = {
        title: 'Updated Title',
        description: 'Updated description'
      }

      it('should update problem successfully', async () => {
        (axios.put as Mock).mockResolvedValue({ data: mockProblem })

        const result = await problemService.updateProblem('two-sum', updateData)

        expect(axios.put).toHaveBeenCalledWith(
          '/api/admin/problems/two-sum/',
          updateData
        )
        expect(result).toEqual(mockProblem)
      })

      it('should handle update errors', async () => {
        const error = { response: { data: { error: 'Forbidden' }, status: 403 } };
        (axios.put as Mock).mockRejectedValue(error)

        await expect(problemService.updateProblem('two-sum', updateData))
          .rejects.toEqual({
            error: 'Forbidden',
            status: 403
          })
      })
    })

    describe('deleteProblem', () => {
      it('should delete problem successfully', async () => {
        (axios.delete as Mock).mockResolvedValue({})

        await problemService.deleteProblem('two-sum')

        expect(axios.delete).toHaveBeenCalledWith('/api/admin/problems/two-sum/')
      })

      it('should handle deletion errors', async () => {
        const error = { response: { data: { error: 'Cannot delete' }, status: 400 } };
        (axios.delete as Mock).mockRejectedValue(error)

        await expect(problemService.deleteProblem('two-sum'))
          .rejects.toEqual({
            error: 'Cannot delete',
            status: 400
          })
      })
    })
  })

  describe('Problem Testing', () => {
    describe('testProblem', () => {
      const testData = {
        problem_id: 1,
        reference_solution: 'def solve(): return 42',
        test_cases: [
          { inputs: '[1, 2]', expected_output: '3' }
        ]
      }

      it('should test problem successfully', async () => {
        (axios.post as Mock).mockResolvedValue({ data: mockTestResult })

        const result = await problemService.testProblem(testData)

        expect(axios.post).toHaveBeenCalledWith(
          '/api/admin/test-problem/',
          testData
        )
        expect(result).toEqual(mockTestResult)
      })

      it('should handle test execution errors', async () => {
        const error = { 
          response: { 
            data: { 
              error: 'Syntax error in solution',
              details: 'Line 1: invalid syntax'
            }, 
            status: 400 
          } 
        };
        (axios.post as Mock).mockRejectedValue(error)

        await expect(problemService.testProblem(testData))
          .rejects.toEqual({
            error: 'Syntax error in solution',
            details: 'Line 1: invalid syntax',
            status: 400
          })
      })
    })
  })

  describe('Category Management', () => {
    describe('loadCategories', () => {
      it('should load categories successfully', async () => {
        const categories = [mockCategory];
        (axios.get as Mock).mockResolvedValue({ data: categories })

        const result = await problemService.loadCategories()

        expect(axios.get).toHaveBeenCalledWith('/api/admin/categories/')
        expect(result).toEqual(categories)
      })

      it('should handle empty categories', async () => {
        (axios.get as Mock).mockResolvedValue({ data: [] })

        const result = await problemService.loadCategories()

        expect(result).toEqual([])
      })
    })

    describe('createCategory', () => {
      const categoryData = {
        name: 'Dynamic Programming',
        color: '#ef4444',
        description: 'DP problems'
      }

      it('should create category successfully', async () => {
        (axios.post as Mock).mockResolvedValue({ data: mockCategory })

        const result = await problemService.createCategory(categoryData)

        expect(axios.post).toHaveBeenCalledWith(
          '/api/admin/categories/',
          categoryData
        )
        expect(result).toEqual(mockCategory)
      })

      it('should handle category creation errors', async () => {
        const error = { 
          response: { 
            data: { error: 'Category already exists' }, 
            status: 400 
          } 
        };
        (axios.post as Mock).mockRejectedValue(error)

        await expect(problemService.createCategory(categoryData))
          .rejects.toEqual({
            error: 'Category already exists',
            status: 400
          })
      })
    })
  })

  describe('Hint Management', () => {
    describe('getHints', () => {
      const mockHintsResponse = {
        available_hints: [
          {
            type: 'variable_fade' as const,
            unlocked: true,
            title: 'Variable Fade',
            description: 'Shows variable mappings'
          }
        ],
        hints_used: [],
        current_attempts: 5
      }

      it('should get hints without context', async () => {
        (axios.get as Mock).mockResolvedValue({ data: mockHintsResponse })

        const result = await problemService.getHints('two-sum')

        expect(axios.get).toHaveBeenCalledWith(
          '/api/problems/two-sum/hints/',
          { params: {} }
        )
        expect(result).toEqual(mockHintsResponse)
      })

      it('should get hints with course context', async () => {
        (axios.get as Mock).mockResolvedValue({ data: mockHintsResponse })

        const result = await problemService.getHints('two-sum', {
          courseId: 'cs101',
          problemSetSlug: 'week-1'
        })

        expect(axios.get).toHaveBeenCalledWith(
          '/api/problems/two-sum/hints/',
          { 
            params: {
              course_id: 'cs101',
              problem_set_slug: 'week-1'
            }
          }
        )
        expect(result).toEqual(mockHintsResponse)
      })
    })

    describe('getHintContent', () => {
      const mockHintContent = {
        type: 'variable_fade',
        content: {
          code: 'def solve():\n    x = 1',
          mappings: [{ from: 'x', to: 'value' }]
        },
        min_attempts: 3
      }

      it('should get specific hint content', async () => {
        (axios.get as Mock).mockResolvedValue({ data: mockHintContent })

        const result = await problemService.getHintContent('two-sum', 'variable_fade')

        expect(axios.get).toHaveBeenCalledWith(
          '/api/problems/two-sum/hints/variable_fade/'
        )
        expect(result).toEqual(mockHintContent)
      })

      it('should handle hint not found', async () => {
        const error = { response: { data: { error: 'Hint not found' }, status: 404 } };
        (axios.get as Mock).mockRejectedValue(error)

        await expect(problemService.getHintContent('two-sum', 'variable_fade'))
          .rejects.toEqual({
            error: 'Hint not found',
            status: 404
          })
      })
    })

    describe('updateHints', () => {
      const hintsData = [mockHintConfig]

      it('should update hints successfully', async () => {
        const response = {
          problem_slug: 'two-sum',
          hints: hintsData.map(h => ({ ...h, created: true }))
        };
        (axios.put as Mock).mockResolvedValue({ data: response })

        const result = await problemService.updateHints('two-sum', hintsData)

        expect(axios.put).toHaveBeenCalledWith(
          '/api/admin/problems/two-sum/hints/',
          { hints: hintsData }
        )
        expect(result).toEqual(response)
      })
    })

    describe('getProblemHints', () => {
      it('should get problem hints successfully', async () => {
        const response = { hints: [mockHintConfig] };
        (axios.get as Mock).mockResolvedValue({ data: response })

        const result = await problemService.getProblemHints('two-sum')

        expect(axios.get).toHaveBeenCalledWith('/api/admin/problems/two-sum/hints/')
        expect(result).toEqual([mockHintConfig])
      })

      it('should return empty array for 404', async () => {
        const error = { response: { status: 404 } };
        (axios.get as Mock).mockRejectedValue(error)

        const result = await problemService.getProblemHints('two-sum')

        expect(result).toEqual([])
      })

      it('should throw for other errors', async () => {
        const error = { response: { data: { error: 'Server error' }, status: 500 } };
        (axios.get as Mock).mockRejectedValue(error)

        await expect(problemService.getProblemHints('two-sum'))
          .rejects.toEqual({
            error: 'Server error',
            status: 500
          })
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      const error = { request: {} };
      (axios.get as Mock).mockRejectedValue(error)

      await expect(problemService.loadProblem('two-sum'))
        .rejects.toEqual({
          error: 'Network error - please check your connection',
          status: 0
        })
    })

    it('should handle generic errors', async () => {
      const error = new Error('Unknown error');
      (axios.get as Mock).mockRejectedValue(error)

      await expect(problemService.loadProblem('two-sum'))
        .rejects.toEqual({
          error: 'Unknown error',
          status: -1
        })
    })

    it('should use default message for errors without message', async () => {
      const error = {};
      (axios.get as Mock).mockRejectedValue(error)

      await expect(problemService.loadProblem('two-sum'))
        .rejects.toEqual({
          error: 'Failed to load problem: two-sum',
          status: -1
        })
    })
  })
})