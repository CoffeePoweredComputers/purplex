<template>
  <component
    :is="FeedbackComponent"
    v-if="FeedbackComponent"
    :key="activityType"
    :progress="progress"
    :notches="notches"
    :code-results="codeResults"
    :test-results="testResults"
    :comprehension-results="comprehensionResults"
    :user-prompt="userPrompt"
    :segmentation="segmentation"
    :reference-code="referenceCode"
    :problem-type="activityType"
    :segmentation-enabled="segmentationEnabled"
    :is-loading="isLoading"
    :is-navigating="isNavigating"
    :submission-history="submissionHistory"
    :title="title"
    :mcq-result="mcqResult"
    @load-attempt="$emit('load-attempt', $event)"
    @next-problem="$emit('next-problem')"
  />
  <div
    v-else
    class="activity-feedback-fallback"
  >
    <p>No feedback component available for activity type: {{ activityType }}</p>
  </div>
</template>

<script setup lang="ts">
/**
 * FeedbackSelector - Dynamic activity feedback component loader.
 *
 * Loads the appropriate feedback component based on the activity type.
 * Falls back to a message if no component is registered.
 */
import { computed } from 'vue'
import { getActivityFeedback, isActivityTypeRegistered } from './index'
import type { CodeResult, McqResult, SegmentationData, SubmissionHistoryItem, TestResultDisplay } from './types'

interface Props {
  /** Activity type identifier (e.g., 'eipl') */
  activityType: string
  /** Overall correctness score */
  progress?: number
  /** Number of notches for progress visualization */
  notches?: number
  /** Code variation results */
  codeResults?: CodeResult[]
  /** Test execution results */
  testResults?: TestResultDisplay[]
  /** Comprehension analysis results */
  comprehensionResults?: string
  /** User's original prompt/input */
  userPrompt?: string
  /** Segmentation analysis data */
  segmentation?: SegmentationData | null
  /** Reference solution code */
  referenceCode?: string
  /** Whether segmentation is enabled */
  segmentationEnabled?: boolean
  /** Loading state */
  isLoading?: boolean
  /** Navigation state */
  isNavigating?: boolean
  /** Historical submission data */
  submissionHistory?: SubmissionHistoryItem[]
  /** Title for the feedback section */
  title?: string
  /** MCQ-specific result data */
  mcqResult?: McqResult | null
}

const props = withDefaults(defineProps<Props>(), {
  progress: 0,
  notches: 6,
  codeResults: () => [],
  testResults: () => [],
  comprehensionResults: '',
  userPrompt: '',
  segmentation: null,
  referenceCode: '',
  segmentationEnabled: false,
  isLoading: false,
  isNavigating: false,
  submissionHistory: () => [],
  title: 'Submission & Results',
  mcqResult: null,
})

defineEmits<{
  (e: 'load-attempt', attemptId: string): void
  (e: 'next-problem'): void
}>()

// Get the appropriate feedback component for the activity type
const FeedbackComponent = computed(() => {
  if (!isActivityTypeRegistered(props.activityType)) {
    return null
  }
  return getActivityFeedback(props.activityType)
})
</script>

<style scoped>
.activity-feedback-fallback {
  padding: var(--spacing-lg);
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  color: var(--color-text-muted);
  text-align: center;
}
</style>
