/**
 * useFeedbackState - Manages atomic feedback state for submission results.
 *
 * This composable groups all feedback-related state into a single reactive object
 * to ensure atomic updates. The feedback cluster (codeResults, testResults,
 * promptCorrectness, comprehensionResults, userPrompt, segmentationData) must
 * always update together to maintain UI consistency.
 *
 * Design rationale:
 * - Single reactive object prevents partial state updates
 * - clear() and set() are the only mutation paths, enforcing atomic updates
 * - Types match what Feedback.vue actually consumes
 */

import { type DeepReadonly, reactive, readonly } from 'vue';
import type { UnifiedSubmissionResult } from '../types';

// ===== FEEDBACK TYPES =====

/**
 * Individual test case result within a variation.
 */
export interface FeedbackTestCase {
  function_call?: string;
  expected_output?: string;
  actual_output?: string;
  pass?: boolean;
  isSuccessful?: boolean;
  error?: string;
  inputs?: unknown;
}

/**
 * Test results for a single code variation.
 * Matches the structure expected by Feedback.vue.
 */
export interface VariationTestResult {
  success?: boolean;
  testsPassed?: number;
  totalTests?: number;
  results?: FeedbackTestCase[];
}

/**
 * MCQ result data for Multiple Choice Question submissions.
 */
export interface McqResultData {
  is_correct: boolean;
  score?: number;
  submission_id?: string;
  selected_option?: {
    id: string;
    text: string;
  };
  correct_option?: {
    id: string;
    text: string;
    explanation?: string;
  };
  selected_options?: Array<{ id: string; text: string }>;
  correct_options?: Array<{ id: string; text: string; explanation?: string }>;
  completion_status?: string;
}

/**
 * Segmentation analysis data from EiPL submissions.
 */
export interface FeedbackSegmentationData {
  segments?: Array<{
    id: number;
    text: string;
    code_lines: number[];
  }>;
  segment_count?: number;
  comprehension_level?: 'relational' | 'multi_structural' | string;
  feedback_message?: string;
  passed?: boolean;
  threshold?: number;
  confidence_score?: number;
  suggested_improvements?: string[];
  code_mappings?: unknown;
}

/**
 * Complete feedback state structure.
 * All properties update atomically via set().
 */
export interface FeedbackState {
  /** Code variations generated from user prompt */
  codeResults: string[];
  /** Test results per variation */
  testResults: VariationTestResult[];
  /** Score/correctness (0-100 typically) */
  promptCorrectness: number;
  /** Comprehension feedback text */
  comprehensionResults: string;
  /** User's original input/prompt */
  userPrompt: string;
  /** Segmentation analysis (EiPL-specific) */
  segmentationData: FeedbackSegmentationData | null;
  /** MCQ result data (MCQ-specific) */
  mcqResult: McqResultData | null;
  /** Unified submission result - contains type-specific data in 'result' field */
  unifiedResult: UnifiedSubmissionResult | null;
}

/**
 * Data to set feedback state. Partial is allowed since
 * set() merges with defaults for any missing fields.
 */
export interface FeedbackSetData {
  codeResults?: string[];
  testResults?: VariationTestResult[];
  promptCorrectness?: number;
  comprehensionResults?: string;
  userPrompt?: string;
  segmentationData?: FeedbackSegmentationData | null;
  mcqResult?: McqResultData | null;
  unifiedResult?: UnifiedSubmissionResult | null;
}

// ===== INITIAL STATE =====

const createInitialState = (): FeedbackState => ({
  codeResults: [],
  testResults: [],
  promptCorrectness: 0,
  comprehensionResults: '',
  userPrompt: '',
  segmentationData: null,
  mcqResult: null,
  unifiedResult: null,
});

// ===== COMPOSABLE =====

export interface UseFeedbackStateReturn {
  /** Readonly feedback state - use set() to update */
  feedback: DeepReadonly<FeedbackState>;
  /** Clear all feedback to initial state */
  clear: () => void;
  /** Atomically set feedback data */
  set: (data: FeedbackSetData) => void;
  /** Check if feedback has any content */
  hasContent: () => boolean;
}

/**
 * Creates a feedback state manager with atomic update semantics.
 *
 * @returns Feedback state and mutation methods
 *
 * @example
 * ```typescript
 * const { feedback, clear, set } = useFeedbackState();
 *
 * // Update all feedback atomically
 * set({
 *   codeResults: variations,
 *   testResults: results,
 *   promptCorrectness: score,
 *   userPrompt: input,
 * });
 *
 * // Clear before new submission
 * clear();
 * ```
 */
export const useFeedbackState = (): UseFeedbackStateReturn => {
  // Single reactive state object for atomic updates
  const state = reactive<FeedbackState>(createInitialState());

  /**
   * Clear all feedback to initial state.
   * Call before starting a new submission.
   */
  const clear = (): void => {
    state.codeResults = [];
    state.testResults = [];
    state.promptCorrectness = 0;
    state.comprehensionResults = '';
    state.userPrompt = '';
    state.segmentationData = null;
    state.mcqResult = null;
    state.unifiedResult = null;
  };

  /**
   * Atomically set feedback data.
   * Missing fields will use current values (for partial updates)
   * or can be explicitly set.
   */
  const set = (data: FeedbackSetData): void => {
    if (data.codeResults !== undefined) {
      state.codeResults = data.codeResults;
    }
    if (data.testResults !== undefined) {
      state.testResults = data.testResults;
    }
    if (data.promptCorrectness !== undefined) {
      state.promptCorrectness = data.promptCorrectness;
    }
    if (data.comprehensionResults !== undefined) {
      state.comprehensionResults = data.comprehensionResults;
    }
    if (data.userPrompt !== undefined) {
      state.userPrompt = data.userPrompt;
    }
    if (data.segmentationData !== undefined) {
      state.segmentationData = data.segmentationData;
    }
    if (data.mcqResult !== undefined) {
      state.mcqResult = data.mcqResult;
    }
    if (data.unifiedResult !== undefined) {
      state.unifiedResult = data.unifiedResult;
    }
  };

  /**
   * Check if feedback has any content to display.
   */
  const hasContent = (): boolean => {
    return (
      state.codeResults.length > 0 ||
      state.testResults.length > 0 ||
      state.promptCorrectness > 0 ||
      state.comprehensionResults !== '' ||
      state.userPrompt !== '' ||
      state.segmentationData !== null ||
      state.mcqResult !== null ||
      state.unifiedResult !== null
    );
  };

  return {
    feedback: readonly(state),
    clear,
    set,
    hasContent,
  };
};
