// ===== CORE DOMAIN TYPES =====

export type DifficultyLevel = 'easy' | 'beginner' | 'intermediate' | 'advanced';
export type ProblemType = 'eipl' | 'function_redefinition';

// ===== PROBLEM CATEGORY TYPES =====
export interface ProblemCategory {
  readonly id: number;
  readonly name: string;
  readonly slug: string;
  readonly description: string;
  readonly icon?: string;
  readonly color: string;
  readonly order: number;
  readonly problems_count: number;
}

// ===== TEST CASE TYPES =====
export interface TestCaseInput {
  inputs: unknown[];
  expected_output: unknown;
  description?: string;
  is_hidden: boolean;
  is_sample: boolean;
  order: number;
}

export interface TestCaseDisplay extends TestCaseInput {
  readonly id?: number;
  inputsString: string;
  expectedString: string;
  error?: string | null;
}

export interface TestCaseValidation {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

// ===== PROBLEM TYPES =====
export interface BaseProblem {
  readonly slug: string;
  title: string;
  description: string;
  difficulty: DifficultyLevel;
  problem_type: ProblemType;
  function_name: string;
  function_signature: string;
  reference_solution: string;
  hints?: string;
  memory_limit: number;
  tags: string[];
  is_active: boolean;
  readonly created_at: string;
  readonly updated_at: string;
  readonly version: number;
}

export interface ProblemDetailed extends BaseProblem {
  categories: ProblemCategory[];
  category_ids: number[];
  test_cases: TestCaseDisplay[];
  test_cases_count: number;
  visible_test_cases_count: number;
  readonly created_by?: number;
  readonly created_by_name?: string;
}

export interface ProblemCreateRequest {
  title: string;
  description: string;
  difficulty: DifficultyLevel;
  problem_type: ProblemType;
  category_ids: number[];
  function_name: string;
  function_signature: string;
  reference_solution: string;
  hints?: string;
  memory_limit: number;
  tags: string[];
  is_active: boolean;
  test_cases: TestCaseInput[];
}

export interface ProblemUpdateRequest extends Partial<ProblemCreateRequest> {
  readonly slug: string;
}

// ===== API RESPONSE TYPES =====
export interface APIResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface APIError {
  error: string;
  details?: Record<string, string[]>;
  status: number;
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

// ===== TEST EXECUTION TYPES =====
export interface TestResult {
  passed: boolean;
  test_number: number;
  inputs: unknown[];
  expected_output: unknown;
  actual_output?: unknown;
  error?: string;
  execution_time?: number;
}

export interface TestExecutionResult {
  success: boolean;
  passed: number;
  total: number;
  score: number;
  results: TestResult[];
  execution_time: number;
  memory_used?: number;
}

// ===== AI GENERATION TYPES =====
export interface AIGenerationRequest {
  description: string;
  function_name: string;
  function_signature: string;
  reference_solution: string;
}

export interface AIGenerationResponse {
  test_cases: TestCaseInput[];
  generation_time: number;
  model_used: string;
}

// ===== LOADING STATES =====
export interface LoadingStates {
  problem: boolean;
  categories: boolean;
  testing: boolean;
  saving: boolean;
  generating: boolean;
}

export interface ErrorStates {
  load: string | null;
  save: string | null;
  test: string | null;
  generate: string | null;
  validation: ValidationError[];
}

// ===== NOTIFICATION TYPES =====
export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
  show: boolean;
  message: string;
  type: NotificationType;
  duration?: number;
}

// ===== ROUTE PARAMETERS =====
export interface RouteParams {
  slug?: string;
}

export interface RouterMeta {
  requiresAuth: boolean;
  requiresAdmin: boolean;
  title?: string;
}

// ===== SERVICE TYPES =====
export interface TestProblemRequest {
  title: string;
  description: string;
  function_name: string;
  reference_solution: string;
  test_cases: TestCaseInput[];
}