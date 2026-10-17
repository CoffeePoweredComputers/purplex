<template>
  <CodeSubmissionFeedback
    :student-code="studentCode"
    :test-results="flatTestResults"
    :submission-history="submissionHistory"
    :is-loading="isLoading"
    :is-navigating="isNavigating"
    :title="effectiveTitle"
    layout="ladder"
    :locked-count="lockedCount"
    :total-count="totalCount"
    :can-debug="!isSpec"
    :code-title="isSpec ? $t('feedback.codeSubmission.generatedCode') : undefined"
    @load-attempt="$emit('load-attempt', $event)"
  >
    <template
      v-if="isSpec"
      #before-submission
    >
      <ExplanationQuote :text="userPrompt" />
    </template>
    <template
      v-if="showAbstraction"
      #after-results
    >
      <AbstractionCard
        :segmentation="segmentation"
        :locked="!versionPassed"
        :reference-code="referenceCode"
        :user-prompt="userPrompt"
      />
    </template>
  </CodeSubmissionFeedback>
</template>

<script setup lang="ts">
/**
 * ProbeableFeedback - Feedback for both probeable activity types.
 *
 * Students discover a function's behavior by probing it, then either write
 * an implementation (probeable_code) or describe it in plain language and
 * have ONE version generated from the description (probeable_spec). Both
 * types grade a single piece of code against the same ordered tests, so both
 * get the same ladder: passes up to the first failure, that failure, and a
 * count of the locked rest (#165).
 *
 * Differences for probeable_spec:
 * - the top panel quotes the student's explanation instead of the code
 * - no debugger button (the student did not write the code)
 * - the Abstraction card follows the ladder when segmentation is enabled
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AbstractionCard from './AbstractionCard.vue'
import CodeSubmissionFeedback from './CodeSubmissionFeedback.vue'
import ExplanationQuote from './ExplanationQuote.vue'
import type { CodeResult, SegmentationData, SubmissionHistoryItem, TestResultDisplay, TestResultEntry } from '../types'

// FeedbackSelector forwards every feedback prop; drop the ones not declared here
defineOptions({ inheritAttrs: false })

const { t } = useI18n()

interface Props {
  /** 'probeable_code' or 'probeable_spec' */
  problemType?: string
  /** The single graded version (student code, or code generated from the explanation) */
  codeResults?: CodeResult[] | string[]
  /** Test execution results (single entry) */
  testResults?: TestResultEntry[] | TestResultDisplay[]
  /** The student's input: code (probeable_code) or explanation (probeable_spec) */
  userPrompt?: string
  /** Segmentation analysis of the explanation (probeable_spec) */
  segmentation?: SegmentationData | null
  /** Whether segmentation is enabled for this problem */
  segmentationEnabled?: boolean
  /** Reference solution code (shown in the segment analysis) */
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
  problemType: 'probeable_code',
  codeResults: () => [],
  testResults: () => [],
  userPrompt: '',
  segmentation: null,
  segmentationEnabled: false,
  referenceCode: '',
  isLoading: false,
  isNavigating: false,
  submissionHistory: () => [],
  title: '',
})

defineEmits<{
  (e: 'load-attempt', attemptId: string): void
}>()

const isSpec = computed(() => props.problemType === 'probeable_spec')

const effectiveTitle = computed(() => props.title || t('feedback.correctnessModal.testResults'))

/** The single graded version's code. */
const studentCode = computed(() => {
  if (props.codeResults.length === 0) {return ''}
  const first = props.codeResults[0]
  // Handle both string[] and CodeResult[] formats
  if (typeof first === 'string') {return first}
  return first.code || ''
})

const entry = computed(() =>
  props.testResults.length > 0 ? (props.testResults[0] as TestResultEntry) : null
)

/**
 * Flatten test results into a simple array.
 * Backend sends nested structure, but we just need flat test cases.
 */
const flatTestResults = computed(() => {
  if (!entry.value) {return []}
  const tests = entry.value.test_results || entry.value.results || []

  return tests.map(test => ({
    function_call: test.function_call,
    expected_output: test.expected_output,
    actual_output: test.actual_output,
    isSuccessful: test.isSuccessful ?? test.pass ?? false,
    error: test.error,
  }))
})

/**
 * Tests hidden after the first failure (rows stop there; see backend
 * result_visibility.truncate_to_first_failure).
 */
const lockedCount = computed(() => entry.value?.lockedCount ?? 0)

/** Total over every test, including locked ones. */
const totalCount = computed(() => entry.value?.totalTests ?? null)

/** The single version passed every test, locked ones included. */
const versionPassed = computed(() => {
  const e = entry.value
  if (!e) {return false}
  if (typeof e.success === 'boolean') {return e.success}
  return e.totalTests !== undefined && e.totalTests > 0 && e.testsPassed === e.totalTests
})

const showAbstraction = computed(() =>
  isSpec.value && props.segmentationEnabled && props.segmentation !== null
)
</script>
