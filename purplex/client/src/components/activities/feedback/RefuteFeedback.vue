<template>
  <div class="refute-feedback">
    <div class="feedback-header">
      <h3 class="feedback-title">
        {{ title || $t('feedback.refute.title') }}
      </h3>
    </div>

    <div class="feedback-body">
      <!-- Claim reminder + solved banner -->
      <div
        v-if="claimText"
        class="claim-reminder"
        :class="{ 'claim-reminder--solved': solved }"
      >
        <div class="section-label">
          {{ $t('feedback.refute.theClaim') }}
        </div>
        <div class="claim-text">
          {{ claimText }}
        </div>
        <div
          v-if="solved"
          class="solved-badge"
        >
          {{ $t('feedback.refute.counterexampleFound') }}
        </div>
      </div>

      <!-- Attempts list -->
      <ol
        v-if="attempts.length > 0"
        class="attempts-list"
      >
        <li
          v-for="attempt in attempts"
          :key="attempt.id"
          class="attempt-row"
          :class="{
            'attempt-row--disproves': attempt.status === 'disproves',
            'attempt-row--error': attempt.status === 'error',
          }"
        >
          <span class="attempt-number">{{ attempt.attemptNumber }}</span>
          <span class="attempt-call">{{ attempt.call }}</span>
          <span class="attempt-arrow">→</span>
          <span class="attempt-result">{{ attempt.resultDisplay }}</span>
          <span
            class="attempt-badge"
            :class="`attempt-badge--${attempt.status}`"
          >
            {{ badgeLabel(attempt.status) }}
          </span>
        </li>
      </ol>

      <!-- Empty / loading state -->
      <div
        v-else
        class="no-result"
      >
        <div
          v-if="isLoading"
          class="loading-spinner"
        />
        <p>{{ isLoading ? $t('feedback.refute.checkingInput') : $t('feedback.refute.noAttempts') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * RefuteFeedback - Results panel for Refute (Counterexample) activities.
 *
 * Renders an enumerated list of the student's most recent submissions
 * (up to MAX_ATTEMPTS). Each row shows the input that was tried, what the
 * function returned, and whether that input disproved the claim. Data comes
 * straight from submission history (each item's handler-provided
 * `type_specific` payload) — there is no separate client-side test path.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { RefuteAttemptResult, SubmissionHistoryItem } from '@/types'

const { t } = useI18n()

const MAX_ATTEMPTS = 10

type AttemptStatus = 'disproves' | 'holds' | 'error'

interface Props {
  /** Loading state (a submission is being processed) */
  isLoading?: boolean
  /** Navigation state */
  isNavigating?: boolean
  /** Historical submission data (newest first) */
  submissionHistory?: SubmissionHistoryItem[]
  /** Title for the feedback section */
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  isLoading: false,
  isNavigating: false,
  submissionHistory: () => [],
  title: '',
})

defineEmits<{
  (e: 'load-attempt', attemptId: string): void
}>()

interface DisplayAttempt {
  id: string
  attemptNumber: string
  call: string
  resultDisplay: string
  status: AttemptStatus
}

/** History items that carry a refute result payload, newest first, capped. */
const refuteItems = computed(() =>
  props.submissionHistory
    .filter((item): item is SubmissionHistoryItem & { type_specific: RefuteAttemptResult } =>
      !!item.type_specific && 'claim_disproven' in item.type_specific
    )
    .slice(0, MAX_ATTEMPTS)
)

const claimText = computed(() => refuteItems.value[0]?.type_specific.claim_text ?? '')

const solved = computed(() =>
  refuteItems.value.some(item => item.type_specific.claim_disproven)
)

const attempts = computed<DisplayAttempt[]>(() =>
  refuteItems.value.map(item => {
    const data = item.type_specific
    const funcName = extractFunctionName(data.function_signature)
    let status: AttemptStatus = 'holds'
    if (!data.execution_success) {
      status = 'error'
    } else if (data.claim_disproven) {
      status = 'disproves'
    }
    return {
      id: item.id,
      attemptNumber: `#${item.attempt_number}`,
      call: formatCall(funcName, data.input_args),
      resultDisplay: data.execution_success
        ? formatValue(data.result_value)
        : (data.execution_error || t('feedback.refute.executionError')),
      status,
    }
  })
)

function badgeLabel(status: AttemptStatus): string {
  if (status === 'disproves') {return t('feedback.refute.disproves')}
  if (status === 'error') {return t('feedback.refute.executionFailed')}
  return t('feedback.refute.claimHolds')
}

function extractFunctionName(signature: string): string {
  const match = signature?.match(/(?:def\s+)?(\w+)\s*\(/)
  return match ? match[1] : 'f'
}

function formatCall(funcName: string, args: Record<string, unknown>): string {
  const argStr = Object.entries(args || {})
    .map(([name, value]) => `${name}=${formatValue(value)}`)
    .join(', ')
  return `${funcName}(${argStr})`
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {return 'None'}
  if (typeof value === 'string') {return `"${value}"`}
  if (typeof value === 'boolean') {return value ? 'True' : 'False'}
  if (Array.isArray(value) || typeof value === 'object') {return JSON.stringify(value)}
  return String(value)
}
</script>

<style scoped>
.refute-feedback {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.feedback-header {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-section);
  border-bottom: 1px solid var(--color-bg-input);
}

.feedback-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.feedback-body {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
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
  background: var(--color-error-overlay);
  border-left: 4px solid var(--color-danger);
  border-radius: var(--radius-base);
}

.claim-reminder--solved {
  background: var(--color-success-overlay);
  border-left-color: var(--color-success);
}

.claim-text {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  font-style: italic;
}

.solved-badge {
  /* White (not --color-success) so it clears WCAG AA on the green tint;
     the banner's green tint + border already signals success. */
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text-primary);
}

/* Attempts List */
.attempts-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.attempt-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  font-family: var(--font-family-mono, Monaco, Menlo, 'Ubuntu Mono', monospace);
  font-size: var(--font-size-sm);
}

.attempt-row--disproves {
  background: var(--color-success-overlay);
  border-color: var(--color-success);
}

.attempt-row--error {
  background: var(--color-warning-overlay);
  border-color: var(--color-warning);
}

.attempt-number {
  /* --color-text-secondary (not muted) to clear WCAG AA on tinted rows */
  color: var(--color-text-secondary);
  font-weight: 600;
  flex-shrink: 0;
  min-width: 2.5em;
}

.attempt-call {
  color: var(--color-text-primary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attempt-arrow {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.attempt-result {
  color: var(--color-text-secondary);
  font-weight: 500;
  flex-shrink: 0;
  max-width: 40%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attempt-badge {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 600;
  flex-shrink: 0;
}

.attempt-badge--disproves {
  /* Solid dark pill (not the green overlay) so the green text clears AA
     (6:1) against the already green-tinted row instead of failing at 4.4. */
  background: var(--color-bg-panel);
  color: var(--color-success);
}

.attempt-badge--holds {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
}

.attempt-badge--error {
  background: var(--color-warning-overlay);
  color: var(--color-warning);
}

/* No Result / Loading */
.no-result {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
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
</style>
