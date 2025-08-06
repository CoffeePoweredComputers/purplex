import type { 
  ProblemCategory, 
  ProblemDetailed,
  ProblemSummary,
  TestCaseDisplay,
  BaseSubmission,
  SubmissionTestResult,
  HintConfig,
  User
} from '../../types'

/**
 * Factory functions for creating test data
 * These ensure consistent test data across all test files
 */

export const createMockCategory = (overrides: Partial<ProblemCategory> = {}): ProblemCategory => ({
  id: 1,
  name: 'Arrays',
  slug: 'arrays',
  description: 'Array manipulation problems',
  color: '#3b82f6',
  order: 1,
  problems_count: 5,
  ...overrides
})

export const createMockTestCase = (overrides: Partial<TestCaseDisplay> = {}): TestCaseDisplay => ({
  id: 1,
  inputs: '[[2, 7, 11, 15], 9]',
  expected_output: '[0, 1]',
  is_visible: true,
  order: 1,
  ...overrides
})

export const createMockProblem = (overrides: Partial<ProblemDetailed> = {}): ProblemDetailed => ({
  id: 1,
  slug: 'two-sum',
  title: 'Two Sum',
  description: 'Find two numbers that add up to target',
  difficulty: 'medium',
  problem_type: 'eipl',
  categories: [createMockCategory()],
  category_ids: [1],
  function_name: 'two_sum',
  function_signature: 'def two_sum(nums: List[int], target: int) -> List[int]:',
  reference_solution: 'return [0, 1]',
  tags: ['array', 'hash-table'],
  test_cases: [createMockTestCase()],
  test_cases_count: 1,
  visible_test_cases_count: 1,
  created_at: '2025-08-05T10:00:00Z',
  updated_at: '2025-08-05T10:00:00Z',
  ...overrides
})

export const createMockProblemSummary = (overrides: Partial<ProblemSummary> = {}): ProblemSummary => ({
  id: 1,
  slug: 'two-sum',
  title: 'Two Sum',
  difficulty: 'medium',
  category: createMockCategory(),
  problem_set_position: 1,
  user_progress: {
    status: 'not_started',
    best_score: 0,
    attempts: 0,
    last_attempt: null
  },
  ...overrides
})

export const createMockSubmission = (overrides: Partial<BaseSubmission> = {}): BaseSubmission => ({
  id: 1,
  problem_id: 1,
  user_id: 1,
  code_variations: [
    { code: 'def two_sum(nums, target): return [0, 1]', variation_id: 1 }
  ],
  total_variations: 1,
  passing_variations: 1,
  test_results: [
    createMockTestResult({ pass: true })
  ],
  created_at: '2025-08-05T10:00:00Z',
  score: 100,
  ...overrides
})

export const createMockTestResult = (overrides: Partial<SubmissionTestResult> = {}): SubmissionTestResult => ({
  pass: true,
  expected: '[0, 1]',
  actual: '[0, 1]',
  test_case_id: 1,
  execution_time: 0.01,
  ...overrides
})

export const createMockHintConfig = (
  type: 'variable_fade' | 'subgoal_highlight' | 'suggested_trace' = 'variable_fade',
  overrides: Partial<HintConfig> = {}
): HintConfig => {
  const defaultContent = {
    variable_fade: {
      code: 'def two_sum():\n    x = 1\n    y = 2',
      mappings: [{ from: 'x', to: 'first_num' }]
    },
    subgoal_highlight: {
      code: 'def two_sum():\n    # Step 1: Initialize\n    pass',
      subgoals: [
        { id: 1, description: 'Initialize variables', startLine: 2, endLine: 2 }
      ]
    },
    suggested_trace: {
      trace: [
        { line: 1, variables: { nums: '[2, 7]', target: '9' } }
      ]
    }
  }

  return {
    type,
    content: defaultContent[type],
    min_attempts: 3,
    ...overrides
  }
}

export const createMockUser = (overrides: Partial<User> = {}): User => ({
  uid: 'test-uid',
  email: 'test@example.com',
  displayName: 'Test User',
  emailVerified: true,
  isAnonymous: false,
  metadata: {
    creationTime: '2025-08-05T10:00:00Z',
    lastSignInTime: '2025-08-05T10:00:00Z'
  },
  providerData: [],
  refreshToken: 'test-refresh-token',
  tenantId: null,
  phoneNumber: null,
  photoURL: null,
  providerId: 'firebase',
  delete: vi.fn(),
  getIdToken: vi.fn(),
  getIdTokenResult: vi.fn(),
  reload: vi.fn(),
  toJSON: vi.fn(),
  ...overrides
} as unknown as User)

// Error response factories
export const createAPIError = (message: string, status: number = 400, details?: any) => ({
  response: {
    data: { error: message, details },
    status
  }
})

export const createNetworkError = () => ({
  request: {},
  message: 'Network Error'
})

// Vue Router factories
export const createMockRoute = (overrides: any = {}) => ({
  path: '/',
  name: 'home',
  params: {},
  query: {},
  hash: '',
  fullPath: '/',
  matched: [],
  redirectedFrom: undefined,
  meta: {},
  ...overrides
})

// Vuex store factories
export const createMockAuthState = (overrides: any = {}) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  ...overrides
})

export const createMockCoursesState = (overrides: any = {}) => ({
  courses: [],
  enrollments: [],
  currentCourse: null,
  isLoading: false,
  error: null,
  ...overrides
})