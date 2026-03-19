<template>
  <div
    class="feedback-container"
    :class="{ 'is-navigating': isNavigating }"
  >
    <!-- Loading State -->
    <div
      v-if="isLoading && !hasResults"
      class="generating-feedback-panel"
    >
      <div class="generating-content">
        <div class="generating-icon">
          🤖
        </div>
        <div class="generating-message">
          {{ $t('feedback.codeSubmission.runningTests') }}
        </div>
      </div>
    </div>

    <!-- Navigation Skeleton -->
    <div
      v-else-if="isNavigating && !hasResults"
      class="navigation-skeleton-panel"
    >
      <div class="skeleton-header">
        <div class="skeleton-bar skeleton-title" />
        <div class="skeleton-bar skeleton-button" />
      </div>
      <div class="skeleton-content">
        <div class="skeleton-section">
          <div class="skeleton-bar skeleton-label" />
          <div class="skeleton-code-block" />
        </div>
        <div class="skeleton-section">
          <div class="skeleton-bar skeleton-label" />
          <div class="skeleton-test-item" />
          <div class="skeleton-test-item" />
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <template v-else-if="hasResults">
      <!-- Header -->
      <div class="feedback-header">
        <div class="section-label">
          {{ title || $t('feedback.codeSubmission.testResults') }}
        </div>
        <!-- Attempt Selector -->
        <div
          v-if="submissionHistory && submissionHistory.length > 0"
          class="attempt-selector"
        >
          <span class="attempt-header-label">{{ $t('feedback.attempts.label') }}</span>
          <button
            ref="triggerRef"
            class="attempt-dropdown-trigger"
            :class="{ 'is-active': showAttemptDropdown }"
            :aria-label="$t('feedback.attempts.ariaLabel', { current: currentAttemptNumber, total: totalAttempts, score: currentScore })"
            :aria-expanded="showAttemptDropdown"
            :aria-haspopup="true"
            @click="showAttemptDropdown = !showAttemptDropdown"
            @keydown.escape="showAttemptDropdown = false"
          >
            <span class="attempt-text">
              {{ currentAttemptNumber }}/{{ totalAttempts }}
            </span>
            <span
              class="attempt-score-badge"
              :class="scoreClass"
              :aria-label="`Score: ${currentScore} percent`"
            >
              <span aria-hidden="true">{{ getScoreIcon(currentScore) }}</span>
              {{ currentScore }}%
            </span>
            <span
              class="dropdown-arrow"
              aria-hidden="true"
            >{{ showAttemptDropdown ? '▾' : '▾' }}</span>
          </button>

          <!-- Dropdown Panel -->
          <div
            v-show="showAttemptDropdown"
            ref="dropdownRef"
            class="attempt-dropdown-panel"
            role="menu"
            :aria-hidden="!showAttemptDropdown"
          >
            <div class="attempt-list-minimal">
              <button
                v-for="(attempt, index) in submissionHistory"
                :key="attempt.id"
                :ref="index === 0 ? 'firstMenuItemRef' : undefined"
                class="attempt-item-minimal"
                :class="{
                  'is-current': attempt.id === currentSubmissionId,
                  'is-best': attempt.is_best,
                  'is-passing': attempt.score >= 100
                }"
                role="menuitem"
                :tabindex="showAttemptDropdown ? 0 : -1"
                :aria-label="$t('feedback.attempts.attemptAriaLabel', { number: attempt.attempt_number, score: attempt.score, passed: attempt.tests_passed, total: attempt.total_tests }) + (attempt.is_best ? $t('feedback.attempts.bestAttempt') : '')"
                @click="selectAttempt(attempt)"
                @keydown.escape="closeDropdownAndFocusTrigger"
                @keydown.arrow-down.prevent="focusNextItem"
                @keydown.arrow-up.prevent="focusPreviousItem"
                @keydown.home="handleHomeKey"
                @keydown.end="handleEndKey"
              >
                <span
                  class="attempt-indicator"
                  aria-hidden="true"
                />
                <span class="attempt-num">{{ attempt.attempt_number }}</span>
                <span
                  class="attempt-score-minimal"
                  :class="getScoreClass(attempt.score)"
                >{{ attempt.score }}%</span>
                <span class="attempt-tests">{{ attempt.tests_passed }}/{{ attempt.total_tests }}</span>
                <time
                  class="attempt-time"
                  :datetime="attempt.submitted_at"
                >{{ formatTime(attempt.submitted_at) }}</time>
                <span
                  v-if="attempt.is_best"
                  class="best-mark"
                  aria-hidden="true"
                >★</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Code Section -->
      <section class="code-section">
        <div class="code-header">
          <span>{{ $t('feedback.codeSubmission.yourSubmission') }}</span>
        </div>
        <Editor
          :value="studentCode"
          :read-only="true"
          height="250px"
          width="100%"
          lang="python"
          mode="python"
          :show-gutter="true"
        />
      </section>

      <!-- Test Summary Bar -->
      <div class="test-summary-bar">
        <div class="summary-counts">
          <span class="count-item passing">✓ {{ $t('feedback.tests.passing', { count: passingTests.length }) }}</span>
          <span class="count-item failing">✗ {{ $t('feedback.tests.failing', { count: failingTests.length }) }}</span>
        </div>
      </div>

      <!-- Test Results -->
      <section class="test-results">
        <!-- Failing Tests (expanded by default) -->
        <details
          v-if="failingTests.length > 0"
          open
          class="test-group"
        >
          <summary class="test-group-header failing">
            <span class="group-icon">▶</span>
            {{ $t('feedback.tests.failingGroup', { count: failingTests.length }) }}
          </summary>
          <div class="test-list">
            <article
              v-for="(test, i) in failingTests"
              :key="`fail-${i}`"
              class="test-item failing"
            >
              <div class="test-content">
                <code class="test-call">{{ test.function_call }}</code>
                <div class="test-diff">
                  <div>{{ $t('feedback.tests.expected') }} <code class="expected">{{ formatValue(test.expected_output) }}</code></div>
                  <div>
                    {{ $t('feedback.tests.got') }} <code
                      class="actual"
                      :class="{ 'is-error': test.error }"
                    >{{ test.error || formatValue(test.actual_output) }}</code>
                  </div>
                </div>
              </div>
              <button
                class="debug-btn"
                :aria-label="$t('feedback.codeSubmission.debugTestCase', { call: test.function_call })"
                @click="openDebugger(test)"
              >
                <span aria-hidden="true">🔍</span>
              </button>
            </article>
          </div>
        </details>

        <!-- Passing Tests (collapsed by default) -->
        <details
          v-if="passingTests.length > 0"
          class="test-group"
        >
          <summary
            class="test-group-header passing"
            tabindex="0"
            role="button"
            aria-expanded="false"
          >
            <span class="group-icon">▶</span>
            {{ $t('feedback.tests.passingGroup', { count: passingTests.length }) }}
          </summary>
          <div class="test-list">
            <article
              v-for="(test, i) in passingTests"
              :key="`pass-${i}`"
              class="test-item passing"
            >
              <div class="test-content">
                <code class="test-call">{{ test.function_call }} → {{ formatValue(test.expected_output) }}</code>
              </div>
            </article>
          </div>
        </details>
      </section>
    </template>

    <!-- Empty State -->
    <div
      v-else
      class="empty-state"
    >
      <span class="empty-icon">🚀</span>
      <p>{{ $t('feedback.codeSubmission.submitToSeeResults') }}</p>
    </div>

    <!-- PyTutor Modal -->
    <PyTutorModal
      :is-visible="showDebugModal"
      :python-tutor-url="debugUrl"
      @close="showDebugModal = false"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * CodeSubmissionFeedback - Feedback display for code-based activities.
 *
 * A focused component for Debug Fix and Probeable Code activities that
 * shows the student's code submission and test results without the
 * EiPL-specific features (variations, segmentation, comprehension).
 *
 * Design aligned with Feedback.vue for visual consistency.
 *
 * Features:
 * - Read-only code editor showing submitted code
 * - Clear test summary (passing/failing counts)
 * - Failing tests expanded by default
 * - PyTutor integration for debugging
 * - Historical attempt navigation
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Editor from '@/features/editor/Editor.vue'
import PyTutorModal from '@/modals/PyTutorModal.vue'
import { PythonTutorService } from '@/services/pythonTutor.service'
import type { SubmissionHistoryItem } from '@/types'

// Test case structure from backend
interface TestCase {
  function_call: string
  expected_output: unknown
  actual_output: unknown
  isSuccessful: boolean
  error?: string
  pass?: boolean  // Legacy field
}

interface Props {
  /** The student's submitted code */
  studentCode: string
  /** Array of test case results */
  testResults: TestCase[]
  /** Historical submission data */
  submissionHistory?: SubmissionHistoryItem[]
  /** Loading state (running tests) */
  isLoading?: boolean
  /** Navigation state (switching problems) */
  isNavigating?: boolean
  /** Section title */
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  submissionHistory: () => [],
  isLoading: false,
  isNavigating: false,
  title: undefined,
})

const emit = defineEmits<{
  (e: 'load-attempt', attempt: SubmissionHistoryItem): void
}>()

// State
const showAttemptDropdown = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)
const triggerRef = ref<HTMLElement | null>(null)
const firstMenuItemRef = ref<HTMLElement | null>(null)
const showDebugModal = ref(false)
const debugUrl = ref('')

// Current attempt tracking
const currentSubmissionId = ref<string | null>(null)
const currentAttemptNumber = ref(1)
const currentScore = ref(0)

// Computed
const hasResults = computed(() => props.testResults.length > 0 || props.studentCode.length > 0)

const totalAttempts = computed(() => props.submissionHistory.length)

const passingTests = computed(() =>
  props.testResults.filter(t => t.isSuccessful || t.pass)
)

const failingTests = computed(() =>
  props.testResults.filter(t => !t.isSuccessful && !t.pass)
)

const scoreClass = computed(() => getScoreClass(currentScore.value))

// Methods - aligned with Feedback.vue
function getScoreClass(score: number): string {
  if (score >= 100) {return 'score-perfect'}
  if (score >= 80) {return 'score-good'}
  if (score >= 60) {return 'score-partial'}
  return 'score-low'
}

function getScoreIcon(score: number): string {
  if (score >= 100) {return '✓'}
  if (score >= 80) {return '✓'}
  if (score >= 60) {return '~'}
  return '✗'
}

function formatValue(value: unknown): string {
  if (value === null) {return 'None'}
  if (value === undefined) {return 'undefined'}
  if (typeof value === 'string') {return `"${value}"`}
  if (Array.isArray(value)) {return JSON.stringify(value)}
  if (typeof value === 'object') {return JSON.stringify(value)}
  return String(value)
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))

  if (hours < 1) {
    const minutes = Math.floor(diff / (1000 * 60))
    return `${minutes}m ago`
  }
  if (hours < 24) {
    return `${hours}h ago`
  }
  const days = Math.floor(hours / 24)
  if (days < 7) {
    return `${days}d ago`
  }

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
  })
}

function selectAttempt(attempt: SubmissionHistoryItem): void {
  showAttemptDropdown.value = false
  currentSubmissionId.value = attempt.id
  currentAttemptNumber.value = attempt.attempt_number
  currentScore.value = attempt.score
  emit('load-attempt', attempt)
}

function openDebugger(test: TestCase): void {
  const formattedCode = PythonTutorService.formatCodeWithTest(props.studentCode, {
    function_call: test.function_call,
    expected_output: String(test.expected_output),
  })
  debugUrl.value = PythonTutorService.generateEmbedUrl(formattedCode)
  showDebugModal.value = true
}

function handleClickOutside(event: MouseEvent): void {
  if (!showAttemptDropdown.value) {return}

  const dropdown = dropdownRef.value
  const trigger = triggerRef.value

  if (dropdown && trigger &&
      !dropdown.contains(event.target as Node) &&
      !trigger.contains(event.target as Node)) {
    showAttemptDropdown.value = false
  }
}

// Keyboard navigation for dropdown - aligned with Feedback.vue
function closeDropdownAndFocusTrigger(): void {
  showAttemptDropdown.value = false
  nextTick(() => {
    triggerRef.value?.focus()
  })
}

function focusNextItem(event: KeyboardEvent): void {
  const currentElement = event.target as HTMLElement
  const nextElement = currentElement.nextElementSibling as HTMLElement
  if (nextElement && nextElement.classList.contains('attempt-item-minimal')) {
    nextElement.focus()
  }
}

function focusPreviousItem(event: KeyboardEvent): void {
  const currentElement = event.target as HTMLElement
  const previousElement = currentElement.previousElementSibling as HTMLElement
  if (previousElement && previousElement.classList.contains('attempt-item-minimal')) {
    previousElement.focus()
  }
}

function handleHomeKey(event: KeyboardEvent): void {
  event.preventDefault()
  const container = dropdownRef.value
  if (!container) {return}
  const attemptList = container.querySelectorAll('.attempt-item-minimal')
  if (attemptList.length > 0) {
    (attemptList[0] as HTMLElement).focus()
  }
}

function handleEndKey(event: KeyboardEvent): void {
  event.preventDefault()
  const container = dropdownRef.value
  if (!container) {return}
  const attemptList = container.querySelectorAll('.attempt-item-minimal')
  if (attemptList.length > 0) {
    (attemptList[attemptList.length - 1] as HTMLElement).focus()
  }
}

function positionDropdown(): void {
  nextTick(() => {
    const dropdown = dropdownRef.value
    const trigger = triggerRef.value
    if (!dropdown || !trigger) {return}

    const rect = trigger.getBoundingClientRect()
    dropdown.style.top = `${rect.bottom + 4}px`
    dropdown.style.left = `${rect.right - dropdown.offsetWidth}px`
  })
}

// Initialize from submission history
function initFromHistory(): void {
  if (props.submissionHistory.length > 0) {
    const latest = props.submissionHistory[0]
    currentSubmissionId.value = latest.id
    currentAttemptNumber.value = latest.attempt_number
    currentScore.value = latest.score
  }
}

// Watchers
watch(showAttemptDropdown, (newVal) => {
  if (newVal) {
    positionDropdown()
    nextTick(() => {
      firstMenuItemRef.value?.focus()
    })
  }
})

watch(() => props.submissionHistory, () => {
  initFromHistory()
}, { deep: true })

// Lifecycle
onMounted(() => {
  initFromHistory()
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
/* Main Container - Aligned with Feedback.vue */
.feedback-container {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  position: relative;
  /* Removed min-height: 600px to prevent black space overflow */
}

.feedback-container.is-navigating {
  /* Opacity removed - rely on skeleton/progress bar for loading indication */
}

/* Generating Feedback Panel - Aligned with Feedback.vue */
.generating-feedback-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
}

.generating-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  text-align: center;
}

.generating-icon {
  font-size: 3rem;
  animation: robotPulse 2s infinite;
}

.generating-message {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  font-weight: 500;
}

@keyframes robotPulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.05);
  }
}

/* Navigation Skeleton - Aligned with Feedback.vue */
.navigation-skeleton-panel {
  padding: var(--spacing-lg);
  background: var(--color-bg-panel);
  min-height: 300px;
}

.skeleton-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-lg);
}

.skeleton-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.skeleton-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.skeleton-bar {
  height: 20px;
  background: linear-gradient(
    90deg,
    var(--color-overlay-subtle) 0%,
    var(--color-overlay-medium) 50%,
    var(--color-overlay-subtle) 100%
  );
  background-size: 200% 100%;
  border-radius: var(--radius-xs);
  animation: shimmer 2.5s ease-in-out infinite;
}

.skeleton-title {
  width: 40%;
  height: 24px;
}

.skeleton-button {
  width: 100px;
  height: 32px;
}

.skeleton-label {
  width: 30%;
  height: 16px;
}

.skeleton-code-block {
  height: 250px;
  background: linear-gradient(
    90deg,
    var(--color-overlay-subtle) 0%,
    var(--color-overlay-subtle) 50%,
    var(--color-overlay-subtle) 100%
  );
  background-size: 200% 100%;
  border-radius: var(--radius-base);
  animation: shimmer 2.5s ease-in-out infinite;
  border: 1px solid var(--color-bg-border);
}

.skeleton-test-item {
  height: 60px;
  background: linear-gradient(
    90deg,
    var(--color-overlay-subtle) 0%,
    var(--color-overlay-medium) 50%,
    var(--color-overlay-subtle) 100%
  );
  background-size: 200% 100%;
  border-radius: var(--radius-xs);
  animation: shimmer 2.5s ease-in-out infinite;
  border: 1px solid var(--color-bg-border);
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* Header - Aligned with Feedback.vue */
.feedback-header {
  background: var(--color-bg-hover);
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-input);
}

.section-label {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  flex: 1;
  font-family: Inter, system-ui, -apple-system, sans-serif;
}

/* Attempt Selector - Aligned with Feedback.vue */
.attempt-selector {
  position: static;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.attempt-header-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 600;
  padding: 0 var(--spacing-xs);
  font-family: Inter, system-ui, -apple-system, sans-serif;
}

.attempt-dropdown-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 var(--spacing-sm);
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  transition: var(--transition-fast);
  font-weight: 400;
}

.attempt-dropdown-trigger:hover {
  color: var(--color-text-secondary);
  background: transparent;
}

.attempt-dropdown-trigger.is-active {
  color: var(--color-text-primary);
  background: transparent;
}

.attempt-dropdown-trigger:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.attempt-dropdown-trigger:focus:not(:focus-visible) {
  outline: none;
}

.attempt-dropdown-trigger:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.attempt-text {
  font-size: 12px;
  opacity: 0.7;
}

.attempt-score-badge {
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 500;
  font-size: 11px;
}

.attempt-score-badge.score-perfect {
  background: var(--color-success-overlay);
  color: var(--color-success);
}

.attempt-score-badge.score-good {
  background: var(--color-success-overlay);
  color: var(--color-success);
}

.attempt-score-badge.score-partial {
  background: var(--color-warning-overlay);
  color: var(--color-warning);
}

.attempt-score-badge.score-low {
  background: var(--color-error-overlay);
  color: var(--color-error);
}

.dropdown-arrow {
  font-size: 10px;
  opacity: 0.4;
  transition: transform 0.2s;
}

.attempt-dropdown-trigger.is-active .dropdown-arrow {
  transform: rotate(180deg);
}

/* Dropdown Panel - Aligned with Feedback.vue */
.attempt-dropdown-panel {
  position: fixed;
  width: 240px;
  max-height: 200px;
  background: var(--color-bg-panel);
  border: 1px solid var(--color-overlay-subtle);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 99999;
  overflow: hidden;
  transition: opacity 0.15s ease, visibility 0.15s ease;
}

.attempt-dropdown-panel[aria-hidden="true"] {
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
}

.attempt-list-minimal {
  overflow-y: auto;
  max-height: 200px;
  padding: 4px;
}

/* Attempt Items - Aligned with Feedback.vue */
.attempt-item-minimal {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  height: 24px;
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: 11px;
  color: var(--color-text-muted);
  border-radius: 3px;
  position: relative;
  background: transparent;
  border: none;
  font-family: inherit;
  width: 100%;
  text-align: left;
}

.attempt-item-minimal:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.attempt-item-minimal:focus:not(:focus-visible) {
  outline: none;
}

.attempt-item-minimal:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.attempt-item-minimal:hover {
  background: var(--color-overlay-subtle);
  color: var(--color-text-secondary);
}

.attempt-item-minimal.is-current {
  background: var(--color-primary-overlay);
  color: var(--color-text-primary);
}

.attempt-indicator {
  width: 2px;
  height: 12px;
  background: var(--color-bg-border);
  border-radius: 1px;
  position: absolute;
  left: 2px;
}

.attempt-item-minimal.is-passing .attempt-indicator {
  background: var(--color-success);
}

.attempt-item-minimal.is-best .attempt-indicator {
  background: var(--color-warning);
}

.attempt-num {
  min-width: 20px;
  font-weight: 500;
  margin-left: 6px;
}

.attempt-score-minimal {
  min-width: 35px;
  text-align: right;
  font-weight: 500;
}

.attempt-score-minimal.score-perfect {
  color: var(--color-success);
}

.attempt-score-minimal.score-good {
  color: var(--color-success);
}

.attempt-score-minimal.score-partial {
  color: var(--color-warning);
}

.attempt-score-minimal.score-low {
  color: var(--color-error);
}

.attempt-tests {
  font-size: 10px;
  opacity: 0.6;
  min-width: 30px;
}

.attempt-time {
  margin-left: auto;
  font-size: 10px;
  opacity: 0.5;
}

.best-mark {
  color: var(--color-warning);
  font-size: 10px;
  margin-left: 4px;
}

/* Code Section - Aligned with Feedback.vue */
.code-section {
  background: var(--color-bg-panel);
}

.code-header {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-hover);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 600;
  font-family: Inter, system-ui, -apple-system, sans-serif;
}

/* Test Summary Bar - Aligned with Feedback.vue */
.test-summary-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-hover);
  border-top: 1px solid var(--color-bg-input);
  border-bottom: 1px solid var(--color-bg-input);
}

.summary-counts {
  display: flex;
  gap: var(--spacing-lg);
}

.count-item {
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.count-item.passing {
  color: var(--color-success);
}

.count-item.failing {
  color: var(--color-error);
}

/* Test Results - Aligned with Feedback.vue */
.test-results {
  padding: 0;
  background: var(--color-bg-panel);
}

.test-group {
  margin-bottom: var(--spacing-md);
}

.test-group:last-child {
  margin-bottom: 0;
}

.test-group-header {
  cursor: pointer;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  font-weight: 600;
  font-size: var(--font-size-sm);
  list-style: none;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  transition: var(--transition-fast);
}

.test-group-header:hover {
  background: var(--color-bg-input);
}

.test-group-header:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.test-group-header:focus:not(:focus-visible) {
  outline: none;
}

.test-group-header:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.test-group-header.failing {
  border-left: 4px solid var(--color-error);
}

.test-group-header.passing {
  border-left: 4px solid var(--color-success);
}

.group-icon {
  transition: transform 0.2s;
  font-size: var(--font-size-xs);
}

details[open] .group-icon {
  transform: rotate(90deg);
}

details:not([open]) .group-icon {
  transform: rotate(0);
}

.test-list {
  padding: var(--spacing-sm) 0 0 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.test-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  border: 1px solid var(--color-bg-input);
  gap: var(--spacing-md);
}

.test-item.failing {
  border-color: var(--color-error-overlay);
}

.test-item.passing {
  border-color: var(--color-success-overlay);
}

.test-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.test-call {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--font-size-sm);
  background: var(--color-bg-input);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
}

.test-diff {
  font-size: var(--font-size-xs);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.test-diff > div {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
}

.expected {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
}

.actual {
  background: var(--color-error-bg);
  color: var(--color-error-text);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
}

.actual.is-error {
  font-style: italic;
}

.debug-btn {
  background: var(--color-info);
  color: var(--color-text-primary);
  border: none;
  padding: var(--spacing-xs);
  border-radius: var(--radius-xs);
  cursor: pointer;
  font-size: var(--font-size-sm);
  min-width: 44px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
}

.debug-btn:hover {
  background: var(--color-info-dark);
  transform: translateY(-1px);
}

.debug-btn:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.debug-btn:focus:not(:focus-visible) {
  outline: none;
}

.debug-btn:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

/* Empty State - Aligned with Feedback.vue */
.empty-state {
  padding: var(--spacing-xxl);
  text-align: center;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-lg);
}

.empty-icon {
  font-size: 48px;
  opacity: 0.8;
}

.empty-state p {
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  margin: 0;
}

/* Responsive Design - Aligned with Feedback.vue */
@media (max-width: 768px) {
  .test-summary-bar {
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .summary-counts {
    justify-content: center;
  }

  .test-item {
    flex-direction: column;
  }

  .debug-btn {
    width: 100%;
  }
}
</style>
