// Re-export datatable types
export * from './datatable';

// ===== CORE DOMAIN TYPES =====

export type DifficultyLevel = 'easy' | 'beginner' | 'intermediate' | 'advanced';
// NOTE: Problem types are extensible via the activity type system.
// See docs/architecture/ACTIVITY_TYPE_EXTENSIBILITY.md
export type ProblemType = 'eipl' | 'mcq' | 'prompt' | string;

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

// ===== PROBLEM SET TYPES =====
export interface ProblemSetProblem {
  readonly slug: string;
  readonly title: string;
  readonly problem_type: ProblemType;
  readonly difficulty: DifficultyLevel;
  readonly order: number;
}

export interface ProblemSet {
  readonly slug: string;
  title: string;
  description?: string;
  icon?: string;
  is_public?: boolean;
  readonly problems_count?: number;
  readonly problems?: ProblemSetProblem[];
  readonly problems_detail?: ProblemSetProblem[];
  readonly created_by?: number;
  readonly created_by_name?: string;
  readonly created_at?: string;
  readonly updated_at?: string;
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
  error?: string | null;
}

// ===== HANDLER CONFIG TYPES =====
// These are returned by ActivityHandler.get_problem_config() on the backend

export interface DisplayConfig {
  show_reference_code?: boolean;
  code_read_only?: boolean;
  show_function_signature?: boolean;
  /** Label for the input section header (e.g., "Describe the code here") */
  section_label?: string;
  /** Prompt-specific: show an image instead of code */
  show_image?: boolean;
  /** Prompt-specific: URL of the image to display */
  image_url?: string;
  /** Prompt-specific: alt text for the image */
  image_alt_text?: string;
  /** Refute-specific: show the claim to disprove */
  show_claim?: boolean;
  /** Refute-specific: the claim text */
  claim_text?: string;
  /** Refute-specific: function signature */
  function_signature?: string;
  /** Refute-specific: function name */
  function_name?: string;
}

export interface InputConfig {
  type?: 'textarea' | 'code' | 'radio' | 'checkbox' | 'json';
  label?: string;
  placeholder?: string;
  min_length?: number;
  max_length?: number;
  options?: Array<{ id: string; text: string }>;
  /** Refute-specific: function parameters for JSON input */
  parameters?: Array<{ name: string; type: string }>;
}

export interface HintsHandlerConfig {
  available?: string[];
  enabled?: boolean;
}

export interface FeedbackConfig {
  show_variations?: boolean;
  show_segmentation?: boolean;
  show_test_results?: boolean;
  show_correct_answer?: boolean;
}

export interface SegmentationExample {
  prompt: string;
  segments: string[];
  code_lines: number[][];
}

export interface SegmentationConfig {
  enabled?: boolean;
  // Note: threshold is stored in segmentation_threshold DB field, not in this JSON config
  examples?: {
    relational?: SegmentationExample;
    multi_structural?: SegmentationExample;
  };
}

// ===== MCQ TYPES =====
export interface McqOption {
  id: string;
  text: string;
  is_correct?: boolean;
  explanation?: string;
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
  // Handler-provided configuration (from get_problem_config)
  display_config?: DisplayConfig;
  input_config?: InputConfig;
  hints_config?: HintsHandlerConfig;
  feedback_config?: FeedbackConfig;
  // Segmentation settings (model fields)
  segmentation_enabled?: boolean;
  segmentation_config?: SegmentationConfig;
  // Prompt config (model field for prompt type)
  prompt_config?: { image_url?: string; image_alt_text?: string };
}

// MCQ-specific problem interface (polymorphic McqProblem)
export interface McqProblem extends Omit<BaseProblem, 'function_name' | 'function_signature' | 'reference_solution'> {
  problem_type: 'mcq';
  question_text: string;
  grading_mode: 'deterministic' | 'llm' | 'manual';
  options: McqOption[];
  allow_multiple: boolean;
  shuffle_options: boolean;
}

export interface ProblemDetailed extends BaseProblem {
  categories: ProblemCategory[];
  category_ids: number[];
  test_cases: TestCaseDisplay[];
  test_cases_count: number;
  visible_test_cases_count: number;
  readonly created_by?: number;
  readonly created_by_name?: string;
  // MCQ-specific fields (present when problem_type is 'mcq')
  question_text?: string;
  options?: McqOption[];
  grading_mode?: 'deterministic' | 'llm' | 'manual';
  allow_multiple?: boolean;
  shuffle_options?: boolean;
  // Prompt-specific fields (present when problem_type is 'prompt')
  image_url?: string;
  image_alt_text?: string;
}

export interface ProblemCreateRequest {
  title: string;
  description?: string;
  difficulty: DifficultyLevel;
  problem_type: ProblemType;
  category_ids: number[];
  function_name?: string;
  function_signature?: string;
  reference_solution?: string;
  hints?: string;
  memory_limit?: number;
  tags: string[];
  is_active: boolean;
  test_cases?: TestCaseInput[];
  // Type-specific fields
  segmentation_config?: SegmentationConfig | null;
  requires_highlevel_comprehension?: boolean;
  prompt_config?: { image_url?: string; image_alt_text?: string };
}

// MCQ-specific create request
export interface McqProblemCreateRequest {
  title: string;
  difficulty: DifficultyLevel;
  problem_type: 'mcq';
  category_ids?: number[];
  tags?: string[];
  is_active?: boolean;
  // MCQ-specific fields
  question_text: string;
  grading_mode?: 'deterministic' | 'llm' | 'manual';
  options: McqOption[];
  allow_multiple?: boolean;
  shuffle_options?: boolean;
}

export interface ProblemUpdateRequest extends Partial<ProblemCreateRequest> {
  readonly slug: string;
}

// ===== API RESPONSE TYPES =====
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
  isSuccessful: boolean;  // Clear boolean property name - was "pass"
  test_number: number;
  inputs: unknown[];
  expected_output: unknown;
  actual_output?: unknown;
  error?: string;
  execution_time?: number;
  description?: string;
  function_call: string;  // Always provided by backend
}

export interface TestExecutionResult {
  success: boolean;
  testsPassed: number;  // Clear count property name - was "passed"
  totalTests: number;   // Clear count property name - was "total"
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

// ===== NOTIFICATION TYPES =====
export type NotificationType = 'success' | 'error' | 'warning' | 'info';

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
  title?: string;
  comment?: string;
  explanation?: string;
  id?: string;
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

// Type aliases for compatibility
export type VariableMapping = VariableFadeMapping;
export type VariableFadeHintData = VariableFadeHint;
export type SubgoalHighlightData = SubgoalHighlightHint;
export type Subgoal = SubgoalHighlight;
export type LineRange = { start: number; end: number };
export type SuggestedTraceData = SuggestedTraceHint;

export interface HintUpdateRequest {
  hints: HintConfig[];
}

export interface HintRequest {
  problemSlug: string;
  hintType: HintType;
  courseId?: string;
  problemSetSlug?: string;
}

export interface HintResponse {
  success: boolean;
  data?: unknown;
  error?: string;
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
  isSuccessful: boolean;  // Clear boolean property name - was "pass"
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
  status: 'incomplete' | 'partial' | 'complete';
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

// ===== TYPE-SPECIFIC DATA (from get_submission_details type_data) =====

export interface McqTypeData {
  question_text: string;
  options: McqOption[];
  selected_option_id: string | null;
  selected_option_ids?: string[];
  correct_option: McqOption | null;
  correct_options?: McqOption[];
  is_correct: boolean;
}

export interface RefuteTypeData {
  claim_text: string;
  function_signature: string;
  function_name: string;
}

export interface DebugFixTypeData {
  buggy_code: string;
}

export interface PromptTypeData {
  image_url: string;
  image_alt_text: string;
}

export interface ProbeableTypeData {
  function_signature: string;
}

export type SubmissionTypeData =
  | McqTypeData
  | RefuteTypeData
  | DebugFixTypeData
  | PromptTypeData
  | ProbeableTypeData
  | Record<string, never>;

export interface SubmissionDetailed extends BaseSubmission {
  submission_type?: string;
  type_data?: SubmissionTypeData;
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

export interface SubmissionStats {
  total_submissions: number;
  unique_users: number;
  average_score: number;
  problems_attempted: number;
  completion_rate: number;
}

// ===== UNIFIED SSE SUBMISSION RESULT =====
// Common envelope for all activity types from SSE completion events

/**
 * EiPL-specific result data from handler.serialize_result()
 */
export interface EiplResultData {
  variations: Array<{
    code: string;
    score: number;
    tests_passed: number;
    tests_total: number;
    is_selected: boolean;
  }>;
  test_results: Array<{
    success: boolean;
    testsPassed: number;
    totalTests: number;
    test_results: Array<{
      isSuccessful: boolean;
      function_call: string;
      expected_output: string;
      actual_output: string;
      error: string;
    }>;
    results?: unknown[];
  }>;
  segmentation: {
    segment_count: number;
    comprehension_level: string;
    passed: boolean;
    threshold: number;
    // Full data for SegmentAnalysisModal
    segments: Array<{ id: number; text: string; code_lines: number[] }>;
    code_mappings: unknown;
    feedback_message: string;
    confidence_score: number;
    suggested_improvements: string[];
  } | null;
}

/**
 * MCQ-specific result data from handler.serialize_result()
 */
export interface McqResultData {
  selected_option: { id: string; text: string };
  correct_option: { id: string; text: string; explanation?: string };
  selected_options?: Array<{ id: string; text: string }>;
  correct_options?: Array<{ id: string; text: string; explanation?: string }>;
  is_correct: boolean;
  score?: number;
}

/**
 * Unified submission result envelope from SSE completion events.
 * All activity types share this structure - type-specific data is in `result`.
 */
export interface UnifiedSubmissionResult {
  // Common metadata (all types)
  submission_id: string;
  problem_type: ProblemType;
  score: number;
  is_correct: boolean;
  completion_status: string;
  problem_slug: string;
  user_input: string;

  // Type-specific payload from handler.serialize_result()
  result: EiplResultData | McqResultData;

  // Legacy fields (for backward compatibility during migration)
  variations?: string[];
  test_results?: unknown[];
  segmentation?: unknown;
  selected_option?: { id: string; text: string };
  correct_option?: { id: string; text: string; explanation?: string };
}

// ===== SUBMISSION HISTORY TYPES =====
export interface SubmissionHistoryItem {
  id: string;
  attempt_number: number;
  submitted_at: string;
  score: number;
  passed_all_tests: boolean;
  completion_status: 'incomplete' | 'partial' | 'complete';
  execution_status: string;
  submission_type: 'eipl' | 'mcq' | 'prompt';
  tests_passed: number;
  total_tests: number;
  execution_time_ms: number | null;
  is_best: boolean;
  variations_count: number;
  comprehension_level: string | null;
  segmentation?: {
    segment_count: number;
    comprehension_level: string;
    confidence_score: number;
    feedback_message: string;
    suggested_improvements: string[];
    segments: unknown;
    code_mappings: unknown;
  };
  data: {
    raw_input: string;
    processed_code: string;
    variations: Array<{
      code: string;
      variation_number: number;
      passed_all_tests: boolean;
      tests_passed: number;
      total_tests: number;
      test_results: Array<{
        test_case_id: number;
        passed: boolean;
        expected: string;
        actual: string;
        error_message: string;
        inputs: string;
      }>;
    }>;
    test_results: Array<{
      test_case_id: number;
      passed: boolean;
      expected: string;
      actual: string;
      error_message: string;
      inputs: string;
    }>;
  };
}

export interface SubmissionHistoryResponse {
  problem_slug: string;
  total_attempts: number;
  best_score: number;
  best_attempt_id: string;
  current_progress: {
    status: ProgressStatus;
    best_score: number;
    attempts: number;
    is_completed: boolean;
  } | null;
  submissions: SubmissionHistoryItem[];
}

// ===== COURSE TYPES =====
export type CourseInstructorRole = 'primary' | 'ta';

export interface CourseInstructorMember {
  user_id: number;
  username: string;
  full_name: string;
  email: string;
  role: CourseInstructorRole;
  added_at: string;
}

export interface Course {
  id: number;
  course_id: string;
  name: string;
  description: string;
  instructor_name: string;
  is_active: boolean;
  enrollment_open: boolean;
  problem_sets_count: number;
  enrolled_students_count: number;
  enrollment_code?: string;
  problem_sets?: CourseProblemSet[];
  instructors?: CourseInstructorMember[];
  my_role?: CourseInstructorRole;
  created_at: string;
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

export type DeadlineType = 'none' | 'soft' | 'hard';

/**
 * Deadline information for a problem set in a specific course context.
 * Returned from progress API when course_id is provided.
 */
export interface Deadline {
  due_date: string;
  deadline_type: DeadlineType;
  is_past_due: boolean;
  is_locked: boolean;
}

export interface CourseProblemSet {
  id: number;
  problem_set: {
    slug: string;
    title: string;
    description?: string;
    problems_count: number;
  };
  order?: number;
  is_required?: boolean;
  due_date?: string | null;
  deadline_type?: DeadlineType;
}

/**
 * Represents a student enrolled in a course with their progress.
 * Used in admin/instructor course student management pages.
 */
export interface CourseStudent {
  id: number; // enrollment ID
  user: {
    id: number;
    email: string;
    username: string;
    first_name?: string;
    last_name?: string;
    full_name?: string;
  };
  enrolled_at: string;
  is_active: boolean;
  progress: {
    completion_percentage: number;
    completed_problem_sets: number;
    total_problem_sets: number;
  };
}

/**
 * Represents an instructor for course assignment.
 * Used in admin course creation/editing.
 */
export interface Instructor {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  full_name: string;
}
