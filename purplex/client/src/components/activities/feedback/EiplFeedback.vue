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
    problem-type="eipl"
    :segmentation-enabled="segmentationEnabled"
    :is-loading="isLoading"
    :is-navigating="isNavigating"
    :submission-history="submissionHistory"
    :title="effectiveTitle"
    @load-attempt="$emit('load-attempt', $event)"
    @next-problem="$emit('next-problem')"
  />
</template>

<script setup lang="ts">
/**
 * EiplFeedback - Feedback component for EiPL (Explain in Plain Language) activities.
 *
 * This is a thin wrapper around the generic Feedback component that ensures
 * the problem_type is set to 'eipl'. The Feedback component already handles
 * EiPL-specific features like segmentation display.
 *
 * Future enhancements could include EiPL-specific feedback visualizations
 * or comprehension level breakdowns that are unique to this activity type.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Feedback from '@/components/Feedback.vue'
import type { CodeResult, SegmentationData, SubmissionHistoryItem, TestResultDisplay } from '../types'

const { t } = useI18n()

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
  title: '',
})

const effectiveTitle = computed(() => props.title || t('problems.problemSet.submissionResults'))

defineEmits<{
  (e: 'load-attempt', attemptId: string): void
  (e: 'next-problem'): void
}>()
</script>
