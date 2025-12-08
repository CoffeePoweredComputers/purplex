<template>
  <CodeSubmissionFeedback
    :student-code="studentCode"
    :test-results="flatTestResults"
    :submission-history="submissionHistory"
    :is-loading="isLoading"
    :is-navigating="isNavigating"
    :title="title"
    @load-attempt="$emit('load-attempt', $event)"
  />
</template>

<script setup lang="ts">
/**
 * ProbeableCodeFeedback - Feedback component for Probeable Code activities.
 *
 * Thin wrapper around CodeSubmissionFeedback that transforms the
 * backend data format into the flat structure expected by the component.
 *
 * Probeable Code students discover function behavior by probing, then
 * write their own implementation. The feedback shows:
 * - Their submitted implementation code
 * - Test results showing which tests pass/fail
 *
 * Note: Unlike EiPL/ProbeableSpec, there's no segmentation or AI variations
 * because the student writes actual code, not a natural language description.
 */
import { computed } from 'vue'
import CodeSubmissionFeedback from './CodeSubmissionFeedback.vue'
import type { CodeResult, SubmissionHistoryItem, TestResultDisplay } from '../types'

interface TestResultFromBackend {
  success?: boolean
  testsPassed?: number
  totalTests?: number
  test_results?: Array<{
    isSuccessful?: boolean
    pass?: boolean
    function_call: string
    expected_output: unknown
    actual_output: unknown
    error?: string
  }>
  results?: Array<{
    isSuccessful?: boolean
    pass?: boolean
    function_call: string
    expected_output: unknown
    actual_output: unknown
    error?: string
  }>
}

interface Props {
  /** Overall correctness score */
  progress?: number
  /** Number of notches for progress visualization */
  notches?: number
  /** Code variation results (single entry for probeable code) */
  codeResults?: CodeResult[] | string[]
  /** Test execution results */
  testResults?: TestResultFromBackend[] | TestResultDisplay[]
  /** User's implementation code */
  userPrompt?: string
  /** Reference solution code (usually hidden) */
  referenceCode?: string
  /** Loading state */
  isLoading?: boolean
  /** Navigation state */
  isNavigating?: boolean
  /** Historical submission data */
  submissionHistory?: SubmissionHistoryItem[]
  /** Title for the feedback section */
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  progress: 0,
  notches: 6,
  codeResults: () => [],
  testResults: () => [],
  userPrompt: '',
  referenceCode: '',
  isLoading: false,
  isNavigating: false,
  submissionHistory: () => [],
  title: 'Test Results',
})

defineEmits<{
  (e: 'load-attempt', attemptId: string): void
}>()

/**
 * Extract the student's code from codeResults.
 * For probeable code, there's only one "variation" - the student's code.
 */
const studentCode = computed(() => {
  if (props.codeResults.length === 0) {return ''}
  const first = props.codeResults[0]
  // Handle both string[] and CodeResult[] formats
  if (typeof first === 'string') {return first}
  return first.code || ''
})

/**
 * Flatten test results into a simple array.
 * Backend sends nested structure, but we just need flat test cases.
 */
const flatTestResults = computed(() => {
  if (props.testResults.length === 0) {return []}

  const first = props.testResults[0] as TestResultFromBackend
  // Extract test_results or results array
  const tests = first.test_results || first.results || []

  return tests.map(t => ({
    function_call: t.function_call,
    expected_output: t.expected_output,
    actual_output: t.actual_output,
    isSuccessful: t.isSuccessful ?? t.pass ?? false,
    error: t.error,
  }))
})
</script>
