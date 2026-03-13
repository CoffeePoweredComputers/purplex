<template>
  <div class="refute-feedback">
    <div class="feedback-header">
      <h3 class="feedback-title">
        {{ title || $t('feedback.refute.title') }}
      </h3>
    </div>

    <div
      v-if="isLoading"
      class="loading-state"
    >
      <div class="loading-spinner" />
      <span>{{ $t('feedback.refute.checkingInput') }}</span>
    </div>

    <div
      v-else-if="hasResult"
      class="result-container"
    >
      <!-- Result Banner -->
      <div
        class="result-banner"
        :class="isCounterexampleFound ? 'result-banner--success' : 'result-banner--failure'"
      >
        <div class="result-icon">
          {{ isCounterexampleFound ? '!' : '?' }}
        </div>
        <div class="result-text">
          <span class="result-label">
            {{ isCounterexampleFound ? $t('feedback.refute.counterexampleFound') : $t('feedback.refute.notCounterexample') }}
          </span>
          <span class="result-score">{{ $t('feedback.refute.score', { score }) }}</span>
        </div>
      </div>

      <!-- Claim Reminder -->
      <div class="claim-reminder">
        <div class="section-label">
          {{ $t('feedback.refute.theClaim') }}
        </div>
        <div class="claim-text">
          {{ claimText }}
        </div>
      </div>

      <!-- Input Details -->
      <div class="details-section">
        <div class="section-label">
          {{ $t('feedback.refute.yourInput') }}
        </div>
        <div class="input-display">
          <code>{{ formattedInput }}</code>
        </div>
      </div>

      <!-- Execution Result -->
      <div
        v-if="executionSuccess"
        class="details-section"
      >
        <div class="section-label">
          {{ $t('feedback.refute.functionOutput') }}
        </div>
        <div
          class="output-display"
          :class="isCounterexampleFound ? 'output-display--disproves' : 'output-display--supports'"
        >
          <code>{{ formattedResult }}</code>
          <span class="output-interpretation">
            {{ resultInterpretation }}
          </span>
        </div>
      </div>

      <!-- Execution Error -->
      <div
        v-else-if="executionError"
        class="details-section"
      >
        <div class="section-label">
          {{ $t('feedback.refute.executionError') }}
        </div>
        <div class="error-display">
          {{ executionError }}
        </div>
      </div>

      <!-- Explanation -->
      <div
        v-if="isCounterexampleFound"
        class="success-explanation"
      >
        <div class="section-label">
          {{ $t('feedback.refute.whyThisWorks') }}
        </div>
        <div class="explanation-text">
          {{ $t('feedback.refute.disprovesClaimExplanation', { result: formattedResult, claim: claimText }) }}
        </div>
      </div>

      <div
        v-else-if="executionSuccess"
        class="failure-explanation"
      >
        <div class="section-label">
          {{ $t('feedback.refute.whyThisDoesntWork') }}
        </div>
        <div class="explanation-text">
          {{ $t('feedback.refute.supportsClaimExplanation', { result: formattedResult, claim: claimText }) }}
        </div>
      </div>
    </div>

    <div
      v-else
      class="no-result"
    >
      <p>{{ $t('feedback.refute.enterAndSubmit') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * RefuteFeedback - Feedback component for Refute (Counterexample) activities.
 *
 * Displays whether the student found a valid counterexample,
 * the function's output, and explanation of the result.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { SubmissionHistoryItem } from '../types'

const { t } = useI18n()

interface RefuteResult {
  claim_disproven: boolean
  input_args: Record<string, unknown>
  result_value: unknown
  execution_success: boolean
  execution_error?: string
  claim_text?: string
  function_signature?: string
  score?: number
}

interface Props {
  /** Overall correctness score */
  progress?: number
  /** Refute-specific result data */
  refuteResult?: RefuteResult | null
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
  refuteResult: null,
  isLoading: false,
  isNavigating: false,
  submissionHistory: () => [],
  title: '',
})

defineEmits<{
  (e: 'load-attempt', attemptId: string): void
}>()

const hasResult = computed(() => props.refuteResult !== null)
const isCounterexampleFound = computed(() => props.refuteResult?.claim_disproven ?? false)
const executionSuccess = computed(() => props.refuteResult?.execution_success ?? false)
const executionError = computed(() => props.refuteResult?.execution_error ?? '')
const score = computed(() => props.refuteResult?.score ?? (isCounterexampleFound.value ? 100 : 0))
const claimText = computed(() => props.refuteResult?.claim_text ?? t('feedback.refute.noClaimSpecified'))

const formattedInput = computed(() => {
  const args = props.refuteResult?.input_args
  if (!args) {return '{}'}
  return JSON.stringify(args, null, 2)
})

const formattedResult = computed(() => {
  const result = props.refuteResult?.result_value
  if (result === undefined || result === null) {return 'null'}
  if (typeof result === 'string') {return `"${result}"`}
  if (typeof result === 'object') {return JSON.stringify(result)}
  return String(result)
})

const resultInterpretation = computed(() => {
  if (isCounterexampleFound.value) {
    return t('feedback.refute.disprovesClaim')
  }
  return t('feedback.refute.supportsClaim')
})
</script>

<style scoped>
.refute-feedback {
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
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

/* Result Banner */
.result-banner {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-radius: var(--radius-base);
}

.result-banner--success {
  background: rgba(72, 187, 120, 0.15);
  border: 1px solid var(--color-success);
}

.result-banner--failure {
  background: rgba(237, 137, 54, 0.15);
  border: 1px solid var(--color-warning);
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

.result-banner--success .result-icon {
  background: var(--color-success);
  color: white;
}

.result-banner--failure .result-icon {
  background: var(--color-warning);
  color: white;
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

/* Section Label */
.section-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--spacing-sm);
}

/* Claim Reminder */
.claim-reminder {
  padding: var(--spacing-md);
  background: rgba(234, 102, 102, 0.1);
  border-left: 4px solid var(--color-danger);
  border-radius: var(--radius-base);
}

.claim-text {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  font-style: italic;
}

/* Details Section */
.details-section {
  display: flex;
  flex-direction: column;
}

.input-display {
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border-radius: var(--radius-base);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  overflow-x: auto;
  white-space: pre;
}

.input-display code {
  background: transparent;
}

.output-display {
  padding: var(--spacing-md);
  border-radius: var(--radius-base);
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
}

.output-display--disproves {
  background: rgba(72, 187, 120, 0.1);
  border: 1px solid var(--color-success);
}

.output-display--supports {
  background: rgba(237, 137, 54, 0.1);
  border: 1px solid var(--color-warning);
}

.output-display code {
  background: transparent;
  color: var(--color-text-primary);
  font-weight: 600;
}

.output-interpretation {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-family: var(--font-sans);
}

.error-display {
  padding: var(--spacing-md);
  background: rgba(245, 101, 101, 0.1);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-base);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-error);
}

/* Explanations */
.success-explanation,
.failure-explanation {
  padding: var(--spacing-md);
  border-radius: var(--radius-base);
}

.success-explanation {
  background: var(--color-bg-hover);
  border-left: 4px solid var(--color-success);
}

.failure-explanation {
  background: var(--color-bg-hover);
  border-left: 4px solid var(--color-warning);
}

.explanation-text {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.explanation-text code {
  background: var(--color-bg-input);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  color: var(--color-primary-gradient-start);
}

/* No Result */
.no-result {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-secondary);
}
</style>
