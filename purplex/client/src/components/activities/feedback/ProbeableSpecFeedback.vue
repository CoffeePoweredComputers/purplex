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
    problem-type="probeable_spec"
    :segmentation-enabled="segmentationEnabled"
    :is-loading="isLoading"
    :is-navigating="isNavigating"
    :submission-history="submissionHistory"
    :title="effectiveTitle"
    @load-attempt="$emit('load-attempt', $event)"
  />
</template>

<script setup lang="ts">
/**
 * ProbeableSpecFeedback - Feedback component for Probeable Spec activities.
 *
 * This is a thin wrapper around the generic Feedback component that ensures
 * the problem_type is set to 'probeable_spec'. The Feedback component handles
 * all the EiPL-like features (segmentation, variations) that Probeable Spec uses.
 *
 * The key difference from EiPL is that students discovered the function behavior
 * through probing rather than seeing the code directly.
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
  /** Reference solution code (usually hidden for Probeable Spec) */
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
  segmentationEnabled: true,  // Probeable Spec has segmentation enabled by default
  isLoading: false,
  isNavigating: false,
  submissionHistory: () => [],
  title: '',
})

const effectiveTitle = computed(() => props.title || t('problems.problemSet.submissionResults'))

defineEmits<{
  (e: 'load-attempt', attemptId: string): void
}>()
</script>
