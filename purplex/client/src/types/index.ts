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
  pass: boolean;
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


// ===== LOADING STATES =====
export interface LoadingStates {
  problem: boolean;
  categories: boolean;
  testing: boolean;
  saving: boolean;
}

export interface ErrorStates {
  load: string | null;
  save: string | null;
  test: string | null;
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

// ===== PYTHON TUTOR TYPES =====
export interface PythonTutorConfig {
  readonly BASE_URL: string;
  readonly EMBED_PATH: string;
  readonly REGULAR_PATH: string;
  readonly DEFAULT_OPTIONS: PythonTutorOptions;
}

export interface PythonTutorOptions {
  cumulative: string;
  curInstr: string;
  heapPrimitives: string;
  mode: string;
  origin: string;
  py: string;
  rawInputLstJSON: string;
  textReferences: string;
  code?: string;
}

export interface TestCaseFormatted {
  function_call?: string;
  expected_output?: unknown;
}

// ===== HINT TYPES =====
export type HintType = 'variable_fade' | 'subgoal_highlight' | 'suggested_trace';

export interface BaseHintConfig {
  type: HintType;
  is_enabled: boolean;
  min_attempts: number;
  content: Record<string, unknown>;
}

export interface VariableFadeMapping {
  from: string;
  to: string;
}

export interface VariableFadeHint extends BaseHintConfig {
  type: 'variable_fade';
  content: {
    mappings: VariableFadeMapping[];
  };
}

export interface SubgoalHighlight {
  line_start: number;
  line_end: number;
  title: string;
  explanation: string;
}

export interface SubgoalHighlightHint extends BaseHintConfig {
  type: 'subgoal_highlight';
  content: {
    subgoals: SubgoalHighlight[];
  };
}

export interface SuggestedTraceHint extends BaseHintConfig {
  type: 'suggested_trace';
  content: {
    suggested_call: string;
    explanation?: string;
  };
}

export type HintConfig = VariableFadeHint | SubgoalHighlightHint | SuggestedTraceHint;

export interface HintUpdateRequest {
  hints: HintConfig[];
}

// ===== PROGRESS TRACKING TYPES =====
export type ProgressStatus = 'not_started' | 'in_progress' | 'completed';

export interface ProgressUpdate {
  status?: ProgressStatus;
  score?: number;
  attempts?: number;
  time_spent?: number;
  isOptimistic?: boolean;
  timestamp?: number;
}

export interface OptimisticProgressUpdate extends ProgressUpdate {
  isOptimistic: true;
  timestamp: number;
}

// ===== GLOBAL NOTIFICATION TYPES =====
export interface NotificationPayload {
  type: NotificationType;
  message: string;
  details?: string | null;
  duration: number;
}

declare global {
  interface Window {
    $notify?: (payload: NotificationPayload) => void;
  }
}

// ===== AUTH TYPES =====
export interface User {
  uid?: string;
  email: string;
  displayName?: string;
  password?: string;
  role: 'admin' | 'user' | 'instructor';
  isAdmin: boolean;
}

export interface AuthStatus {
  loggedIn: boolean;
}

export interface AuthState {
  status: AuthStatus;
  user: User | null;
  debug: boolean;
}

// ===== SUBMISSION TYPES =====
export interface CodeVariation {
  code: string;
  description?: string;
  is_correct?: boolean;
}

export interface SubmissionTestResult {
  variation_index: number;
  pass: boolean;
  score: number;
  test_number: number;
  inputs: unknown[];
  expected_output: unknown;
  actual_output?: unknown;
  error?: string;
  execution_time?: number;
}

export interface BaseSubmission {
  readonly id: number;
  user: string;
  problem: string;
  problem_set: string;
  course?: string;
  score: number;
  status: 'passed' | 'partial' | 'failed' | 'pending';
  readonly submitted_at: string;
  prompt: string;
  execution_time?: number;
  time_spent?: string;
  
  // New submission fields
  code_variations: CodeVariation[] | string[];
  test_results: SubmissionTestResult[];
  passing_variations: number;
  total_variations: number;
  
}

export interface SubmissionDetailed extends BaseSubmission {
  problem_details?: {
    title: string;
    slug: string;
    difficulty: DifficultyLevel;
  };
  problem_set_details?: {
    title: string;
    slug: string;
  };
  course_details?: {
    name: string;
    course_id: string;
  };
  user_details?: {
    email: string;
    display_name?: string;
  };
}

export interface SubmissionCreateRequest {
  problem_slug: string;
  prompt: string;
  code_variations?: CodeVariation[];
  time_spent?: number;
  user_code?: string; // For backward compatibility
}

export interface SubmissionListResponse {
  count: number;
  next?: string;
  previous?: string;
  results: BaseSubmission[];
}

export interface SubmissionStats {
  total_submissions: number;
  unique_users: number;
  average_score: number;
  problems_attempted: number;
  completion_rate: number;
}

// ===== COURSE TYPES =====
export interface Course {
  course_id: string;
  name: string;
  description: string;
  instructor_name?: string;
  problem_sets?: CourseProblemSet[];
  created_at?: string;
  updated_at?: string;
}

export interface CourseEnrollment {
  course: Course;
  enrolled_at: string;
  progress?: CourseProgress;
}

export interface CourseProgress {
  completed_sets: number;
  total_sets: number;
  percentage: number;
  last_activity: string | null;
}

export interface CourseProblemSet {
  id: number;
  name: string;
  description: string;
  slug: string;
  problems_count?: number;
  icon?: string;
  order?: number;
}

