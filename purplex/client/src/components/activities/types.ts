/**
 * Type definitions for the Activity Type Extensibility system.
 *
 * This module defines the interfaces for activity-type-specific components
 * (inputs and feedback displays) that can be dynamically loaded based on
 * the problem's activity type.
 */

import type { Component, DefineComponent } from 'vue'
import type {
  DisplayConfig,
  FeedbackConfig,
  HintConfig,
  HintsHandlerConfig,
  InputConfig,
  McqOption,
  SubmissionHistoryItem,
} from '@/types'

// Re-export config types from central types module
export type {
  DisplayConfig,
  InputConfig,
  FeedbackConfig,
  McqOption,
}

// Alias for backward compatibility
export type HintsConfig = HintsHandlerConfig

// ===== ACTIVITY INPUT TYPES =====

/**
 * Props passed to activity input components.
 * Input components receive the current problem context and emit user input changes.
 */
export interface ActivityInputProps {
  /** The user's current input value */
  modelValue: string
  /** Current problem data including type-specific config */
  problem: ActivityProblem
  /** Currently active hints applied to the problem (optional - not all types use hints) */
  activeHints?: HintConfig[]
  /** Whether the input should be disabled (during submission) */
  disabled?: boolean
  /** Editor theme name */
  theme?: string
  /** Whether a draft has been saved */
  draftSaved?: boolean
}

/**
 * Events emitted by activity input components.
 */
export interface ActivityInputEmits {
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}

// ===== ACTIVITY FEEDBACK TYPES =====

/**
 * Props passed to activity feedback components.
 * Feedback components display submission results in a type-specific way.
 */
export interface ActivityFeedbackProps {
  /** Overall correctness score (0-100 scale typically shown as progress) */
  progress: number
  /** Number of notches for progress visualization */
  notches: number
  /** Code variation results */
  codeResults: CodeResult[]
  /** Test execution results */
  testResults: TestResultDisplay[]
  /** Comprehension analysis results */
  comprehensionResults: string
  /** User's original prompt/input */
  userPrompt: string
  /** Segmentation analysis data (EiPL-specific) */
  segmentation: SegmentationData | null
  /** Reference solution code */
  referenceCode: string
  /** Problem type identifier */
  problemType: string
  /** Whether segmentation is enabled for this problem */
  segmentationEnabled: boolean
  /** Loading state */
  isLoading: boolean
  /** Navigation state */
  isNavigating: boolean
  /** Historical submission data */
  submissionHistory: SubmissionHistoryItem[]
  /** Title for the feedback section */
  title: string
}

/**
 * Events emitted by activity feedback components.
 */
export interface ActivityFeedbackEmits {
  (e: 'load-attempt', attemptId: string): void
}

// ===== SUPPORTING TYPES =====

/**
 * Problem data structure passed to activity components.
 */
export interface ActivityProblem {
  slug: string
  title: string
  description: string
  problem_type: string
  function_name: string
  function_signature: string
  reference_solution: string
  segmentation_enabled?: boolean
  segmentation_threshold?: number
  /** Type-specific display configuration from handler */
  display_config?: DisplayConfig
  /** Type-specific input configuration from handler */
  input_config?: InputConfig
  /** Type-specific hints configuration from handler */
  hints_config?: HintsConfig
  /** Type-specific feedback configuration from handler */
  feedback_config?: FeedbackConfig
  /** Prompt-specific configuration */
  prompt_config?: PromptConfig
  /** Probe configuration for probeable problem types */
  probe_config?: ProbeConfig
}

/**
 * Prompt problem configuration.
 */
export interface PromptConfig {
  image_url?: string
  image_alt_text?: string
}

/**
 * Probe configuration for probeable problem types.
 */
export interface ProbeConfig {
  enabled?: boolean
  mode?: 'explore' | 'cooldown'
  max_probes?: number
  cooldown_attempts?: number
  cooldown_refill?: number
  function_signature?: string
  function_name?: string
  parameters?: ProbeParameter[]
}

// NOTE: DisplayConfig, InputConfig, FeedbackConfig, and McqOption are now
// imported from @/types and re-exported above for backward compatibility.
// HintsConfig is an alias for HintsHandlerConfig from @/types.

/**
 * Code result for a variation.
 */
export interface CodeResult {
  code: string
  variation_number: number
  passed_all_tests: boolean
  tests_passed: number
  total_tests: number
}

/**
 * Test result display data.
 */
export interface TestResultDisplay {
  test_case_id?: number
  passed: boolean
  expected: string
  actual: string
  error_message?: string
  inputs: Record<string, unknown>
}

/**
 * Segmentation analysis data (EiPL-specific).
 */
export interface SegmentationData {
  segments: Segment[]
  segment_count: number
  comprehension_level: 'relational' | 'multi_structural'
  feedback_message?: string
  passed?: boolean
  threshold?: number
  confidence_score?: number
  suggested_improvements?: string[]
  code_mappings?: unknown
}

/**
 * Individual segment from analysis.
 */
export interface Segment {
  id: number
  text: string
  code_lines: number[]
}

/**
 * MCQ submission result data (MCQ-specific).
 */
export interface McqResult {
  is_correct: boolean
  score?: number
  submission_id?: string
  selected_option?: {
    id: string
    text: string
  }
  correct_option?: {
    id: string
    text: string
    explanation?: string
  }
  selected_options?: Array<{ id: string; text: string }>
  correct_options?: Array<{ id: string; text: string; explanation?: string }>
  completion_status?: string
}

// ===== COMPONENT REGISTRY TYPES =====

/**
 * Dynamic component loader function type.
 */
export type ComponentLoader = () => Promise<{ default: Component | DefineComponent }>

/**
 * Activity component definition for the registry.
 */
export interface ActivityComponentDefinition {
  /** Loader for the input component */
  input: ComponentLoader
  /** Loader for the feedback component */
  feedback: ComponentLoader
}

/**
 * Registry mapping activity types to component definitions.
 */
export type ActivityComponentRegistry = Record<string, ActivityComponentDefinition>

// ===== PROBE TYPES =====

/**
 * Probe parameter definition.
 */
export interface ProbeParameter {
  name: string
  type: string
}

/**
 * Probe history entry.
 */
export interface ProbeHistoryEntry {
  input: Record<string, unknown>
  output: unknown
  timestamp?: string
}

/**
 * Probe status from backend.
 */
export interface ProbeStatus {
  mode: 'block' | 'cooldown' | 'explore'
  remaining: number | null
  used: number
  can_probe: boolean
  message: string
  submissions_to_next_refill?: number
}
