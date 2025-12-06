<template>
  <Feedback
    :progress="progress"
    :notches="notches"
    :code-results="codeResults"
    :test-results="testResults"
    :comprehension-results="comprehensionResults"
    :user-prompt="userPrompt"
    :segmentation="segmentation"
    :reference-code="referenceCode"
    problem-type="prompt"
    :segmentation-enabled="segmentationEnabled"
    :is-loading="isLoading"
    :is-navigating="isNavigating"
    :submission-history="submissionHistory"
    :title="title"
    @load-attempt="$emit('load-attempt', $event)"
  />
</template>

<script setup lang="ts">
/**
 * PromptFeedback - Feedback component for Prompt (image-based EiPL) activities.
 *
 * Reuses the same feedback display as EiPL since the processing pipeline and
 * result structure are identical. The only difference is the problem_type prop.
 */
import Feedback from '@/components/Feedback.vue'
import type { CodeResult, SegmentationData, SubmissionHistoryItem, TestResultDisplay } from '../types'

interface Props {
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
}

withDefaults(defineProps<Props>(), {
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
})

defineEmits<{
  (e: 'load-attempt', attemptId: string): void
}>()
</script>
