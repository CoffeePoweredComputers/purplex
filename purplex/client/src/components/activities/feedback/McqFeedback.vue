<template>
  <div class="mcq-feedback">
    <div class="feedback-header">
      <h3 class="feedback-title">
        {{ title || $t('feedback.mcq.title') }}
      </h3>
    </div>

    <div
      v-if="isLoading"
      class="loading-state"
    >
      <div class="loading-spinner" />
      <span>{{ $t('feedback.mcq.checking') }}</span>
    </div>

    <div
      v-else-if="hasResult"
      class="result-container"
    >
      <!-- Result Banner -->
      <div
        class="result-banner"
        :class="bannerClass"
      >
        <div class="result-icon">
          {{ isCorrect ? '✓' : isPartial ? '~' : '✗' }}
        </div>
        <div class="result-text">
          <span class="result-label">{{ isCorrect ? $t('feedback.mcq.correct') : isPartial ? $t('feedback.mcq.partiallyCorrect') : $t('feedback.mcq.incorrect') }}</span>
          <span class="result-score">{{ $t('feedback.mcq.score', { score }) }}</span>
        </div>
      </div>

      <!-- Answer Details -->
      <div class="answer-details">
        <div class="answer-section">
          <div class="answer-label">
            {{ $t('feedback.mcq.yourAnswer') }}
          </div>
          <div
            class="answer-value"
            :class="isCorrect ? 'answer-value--correct' : isPartial ? 'answer-value--partial' : 'answer-value--incorrect'"
          >
            {{ selectedAnswer }}
          </div>
        </div>

        <div
          v-if="!isCorrect"
          class="answer-section"
        >
          <div class="answer-label">
            {{ $t('feedback.mcq.correctAnswer') }}
          </div>
          <div class="answer-value answer-value--correct">
            {{ correctAnswer }}
          </div>
        </div>

        <div
          v-if="explanation"
          class="explanation-section"
        >
          <div class="answer-label">
            {{ $t('feedback.mcq.explanation') }}
          </div>
          <div class="explanation-text">
            {{ explanation }}
          </div>
        </div>
      </div>
    </div>

    <div
      v-else
      class="no-result"
    >
      <p>{{ $t('feedback.mcq.noResult') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * McqFeedback - Feedback component for Multiple Choice Question activities.
 *
 * Displays correct/incorrect status, the selected answer,
 * and the correct answer if wrong.
 */
import { computed } from 'vue'
import type { SubmissionHistoryItem } from '../types'

interface McqResult {
  is_correct: boolean
  score?: number
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
}

interface Props {
  /** Overall correctness score */
  progress?: number
  /** MCQ-specific result data */
  mcqResult?: McqResult | null
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
  mcqResult: null,
  isLoading: false,
  isNavigating: false,
  submissionHistory: () => [],
  title: '',
})

defineEmits<{
  (e: 'load-attempt', attemptId: string): void
}>()

const hasResult = computed(() => props.mcqResult !== null)
const isCorrect = computed(() => props.mcqResult?.is_correct ?? false)
const score = computed(() => {
  if (props.mcqResult?.score !== undefined) return props.mcqResult.score
  return isCorrect.value ? 100 : 0
})
const isPartial = computed(() => !isCorrect.value && score.value > 0)
const selectedAnswer = computed(() => {
  const plural = props.mcqResult?.selected_options
  if (plural && plural.length > 1) {
    return plural.map(o => o.text).join(', ')
  }
  return props.mcqResult?.selected_option?.text ?? 'Unknown'
})
const correctAnswer = computed(() => {
  const plural = props.mcqResult?.correct_options
  if (plural && plural.length > 1) {
    return plural.map(o => o.text).join(', ')
  }
  return props.mcqResult?.correct_option?.text ?? 'Unknown'
})
const explanation = computed(() => {
  const plural = props.mcqResult?.correct_options
  if (plural && plural.length > 0) {
    const explanations = plural.map(o => o.explanation).filter(Boolean)
    if (explanations.length > 0) return explanations.join('; ')
  }
  return props.mcqResult?.correct_option?.explanation ?? ''
})
const bannerClass = computed(() => {
  if (isCorrect.value) return 'result-banner--correct'
  if (isPartial.value) return 'result-banner--partial'
  return 'result-banner--incorrect'
})
</script>

<style scoped>
.mcq-feedback {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.feedback-header {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-bg-input);
}

.feedback-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  gap: var(--spacing-md);
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-bg-border);
  border-top-color: var(--color-primary-gradient-start);
  border-radius: var(--radius-circle);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Result Container */
.result-container {
  padding: var(--spacing-lg);
}

/* Result Banner */
.result-banner {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-lg);
}

.result-banner--correct {
  background: var(--color-success-overlay);
  border: 1px solid var(--color-success);
}

.result-banner--incorrect {
  background: var(--color-error-overlay);
  border: 1px solid var(--color-error);
}

.result-banner--partial {
  background: var(--color-warning-overlay);
  border: 1px solid var(--color-warning);
}

.result-banner--partial .result-icon {
  background: var(--color-warning);
  color: var(--color-text-primary);
}

.result-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-circle);
  font-size: 24px;
  font-weight: 700;
}

.result-banner--correct .result-icon {
  background: var(--color-success);
  color: var(--color-text-primary);
}

.result-banner--incorrect .result-icon {
  background: var(--color-error);
  color: var(--color-text-primary);
}

.result-text {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.result-label {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text-primary);
}

.result-score {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* Answer Details */
.answer-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.answer-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.answer-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.answer-value {
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  border-left: 4px solid var(--color-bg-border);
}

.answer-value--correct {
  border-left-color: var(--color-success);
}

.answer-value--incorrect {
  border-left-color: var(--color-error);
}

.answer-value--partial {
  border-left-color: var(--color-warning);
}

/* Explanation */
.explanation-section {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-bg-border);
}

.explanation-text {
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* No Result */
.no-result {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-secondary);
}
</style>
