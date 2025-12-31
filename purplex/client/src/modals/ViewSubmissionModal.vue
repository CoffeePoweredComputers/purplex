<template>
  <Teleport to="body">
    <div
      v-if="isVisible"
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="submission-modal-title"
      @click.self="closeModal"
    >
      <div
        ref="modalContentRef"
        class="modal-content"
        @keydown.esc="closeModal"
      >
        <!-- Header -->
        <div class="modal-header">
          <div class="header-info">
            <h2
              id="submission-modal-title"
              class="modal-title"
            >
              Submission Details
            </h2>
            <div class="header-meta">
              <span class="meta-item">{{ submission?.user || 'Unknown User' }}</span>
              <span class="meta-separator">•</span>
              <span class="meta-item">{{ submission?.problem?.title || submission?.problem || 'Unknown Problem' }}</span>
              <span class="meta-separator">•</span>
              <span class="meta-item">ID: {{ submission?.submission_id || submission?.id || 'N/A' }}</span>
              <span class="meta-separator">•</span>
              <span class="meta-item">{{ formatDate(submission?.submitted_at) }}</span>
            </div>
          </div>
          <div class="header-actions">
            <button
              class="download-btn"
              :disabled="!submission"
              title="Download Data"
              @click="downloadSubmission"
            >
              Download
            </button>
            <button
              class="close-btn"
              aria-label="Close"
              @click="closeModal"
            >
              ✕
            </button>
          </div>
        </div>

        <!-- Key Metrics Bar -->
        <div class="metrics-bar">
          <div class="metric">
            <span class="metric-label">Score:</span>
            <span
              class="metric-value"
              :class="getScoreClass(submission?.score)"
            >
              {{ submission?.score || 0 }}%
            </span>
          </div>
          <div class="metric">
            <span class="metric-label">Status:</span>
            <span
              class="metric-value"
              :class="getStatusClass(submission?.completion_status || submission?.status)"
            >
              {{ submission?.completion_status || submission?.status || 'Unknown' }}
            </span>
          </div>
          <div
            v-if="hasVariations"
            class="metric"
          >
            <span class="metric-label">Variations:</span>
            <span class="metric-value">
              {{ passingVariationsCount }}/{{ totalVariationsCount }} passed all tests
            </span>
          </div>
          <div
            v-if="currentVariationData"
            class="metric"
          >
            <span class="metric-label">Current Variation:</span>
            <span class="metric-value">
              {{ currentVariationData.testsPassed }}/{{ currentVariationData.totalTests }} tests passed
            </span>
          </div>
          <div
            v-if="submission?.execution_time_ms"
            class="metric"
          >
            <span class="metric-label">Time:</span>
            <span class="metric-value">{{ submission.execution_time_ms }}ms</span>
          </div>
        </div>

        <!-- Variation Navigation (only show for EiPL submissions) -->
        <div
          v-if="hasVariations"
          class="variation-nav"
        >
          <div class="nav-info">
            <span class="variation-label">Variation {{ currentVariationIndex + 1 }} of {{ totalVariationsCount }}</span>
            <div
              class="variation-status"
              :class="currentVariationStatusClass"
            >
              {{ currentVariationData?.success ? 'All tests passed' : `${currentVariationData?.testsPassed || 0}/${currentVariationData?.totalTests || 0} tests passed` }}
            </div>
          </div>
          <div class="nav-controls">
            <button
              class="nav-btn"
              :disabled="currentVariationIndex === 0"
              title="Previous variation"
              @click="prevVariation"
            >
              ← Previous
            </button>
            <button
              class="nav-btn"
              :disabled="currentVariationIndex >= totalVariationsCount - 1"
              title="Next variation"
              @click="nextVariation"
            >
              Next →
            </button>
          </div>
        </div>

        <!-- Main Content Area -->
        <div class="main-content">
          <!-- Two Column Layout -->
          <div class="two-column-layout">
            <!-- Left Column: Code -->
            <div class="code-column">
              <!-- Natural Language Prompt (EiPL/Prompt types) - show if raw_input exists -->
              <div
                v-if="submission?.raw_input"
                class="code-section"
              >
                <div class="section-header">
                  <span class="section-title">Natural Language Prompt</span>
                </div>
                <div class="prompt-box">
                  {{ submission.raw_input }}
                </div>
              </div>

              <!-- Code -->
              <div class="code-section">
                <div class="section-header">
                  <span class="section-title">
                    {{ hasVariations ? `Generated Code - Variation ${currentVariationIndex + 1}` : (submission?.raw_input ? 'Generated Code' : 'Submitted Code') }}
                  </span>
                  <button
                    class="copy-btn"
                    @click="copyCode(currentCodeToDisplay)"
                  >
                    Copy
                  </button>
                </div>
                <Editor
                  :value="currentCodeToDisplay || '# No code available'"
                  :read-only="true"
                  height="400px"
                  width="100%"
                  theme="tomorrow_night"
                />
              </div>
            </div>

            <!-- Right Column: Tests -->
            <div class="tests-column">
              <div class="section-header">
                <span class="section-title">
                  Test Results
                  <span
                    v-if="currentTestResults.length > 0"
                    class="test-count"
                  >
                    ({{ currentPassingTests }}/{{ currentTestResults.length }} passing)
                  </span>
                </span>
              </div>

              <div
                v-if="!currentTestResults || currentTestResults.length === 0"
                class="empty-state"
              >
                No test results available{{ hasVariations ? ' for current variation' : '' }}
              </div>
              <div
                v-else
                class="test-results"
              >
                <!-- Test Summary Bar -->
                <div class="test-summary-bar">
                  <div class="summary-counts">
                    <span class="count-item passing">✓ {{ currentPassingTests }} Passing</span>
                    <span class="count-item failing">✗ {{ currentFailingTests }} Failing</span>
                  </div>
                </div>

                <!-- Failing Tests (Expanded by default) -->
                <details
                  v-if="currentFailingTests > 0"
                  open
                  class="test-group"
                >
                  <summary class="test-group-header failing">
                    <span class="group-icon">▶</span>
                    Failing Tests ({{ currentFailingTests }})
                  </summary>
                  <div class="test-list">
                    <article
                      v-for="(test, i) in currentFailingTestsList"
                      :key="`fail-${i}`"
                      class="test-item failing"
                    >
                      <div class="test-content">
                        <code class="test-call">{{ formatTestCall(test) }}</code>
                        <div class="test-diff">
                          <div>Expected: <code class="expected">{{ formatValue(test.expected_output || test.expected) }}</code></div>
                          <div>
                            Got: <code
                              class="actual"
                              :class="getValueDisplayClass(test.actual_output || test.actual)"
                            >{{ formatTestValue(test.actual_output || test.actual) }}</code>
                          </div>
                        </div>
                      </div>
                    </article>
                  </div>
                </details>

                <!-- Passing Tests (Collapsed by default) -->
                <details
                  v-if="currentPassingTests > 0"
                  class="test-group"
                >
                  <summary class="test-group-header passing">
                    <span class="group-icon">▶</span>
                    Passing Tests ({{ currentPassingTests }})
                  </summary>
                  <div class="test-list">
                    <article
                      v-for="(test, i) in currentPassingTestsList"
                      :key="`pass-${i}`"
                      class="test-item passing"
                    >
                      <div class="test-content">
                        <code class="test-call">{{ formatTestCall(test) }} → {{ formatValue(test.expected_output || test.expected) }}</code>
                      </div>
                    </article>
                  </div>
                </details>
              </div>
            </div>
          </div>

          <!-- Analysis Section - Always Visible Below -->
          <div
            v-if="submission?.segmentation || hasHintsActivated"
            class="analysis-section-static"
          >
            <div class="section-header">
              <h3 class="section-title">
                Analysis & Hints
              </h3>
            </div>

            <div class="analysis-content">
              <!-- Hints Activated Section -->
              <div
                v-if="hasHintsActivated"
                class="analysis-section hints-section"
              >
                <h4 class="section-title">
                  Hints Used ({{ hintsActivatedCount }})
                </h4>
                <div class="hints-list">
                  <div
                    v-for="(hint, idx) in submission.hints_activated"
                    :key="idx"
                    class="hint-item"
                  >
                    <span class="hint-icon">{{ getHintIcon(hint.hint_type) }}</span>
                    <div class="hint-details">
                      <div class="hint-type-name">
                        {{ formatHintType(hint.hint_type) }}
                      </div>
                      <div class="hint-meta">
                        <span class="hint-trigger">{{ formatTriggerType(hint.trigger_type) }}</span>
                        <span class="hint-time">{{ formatHintTime(hint.activated_at) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div
                v-if="submission.segmentation.confidence_score"
                class="info-item"
              >
                <span class="info-label">Confidence:</span>
                <span class="info-value">{{ Math.round(submission.segmentation.confidence_score * 100) }}%</span>
              </div>

              <div
                v-if="submission.segmentation.feedback_message"
                class="analysis-section"
              >
                <h4 class="section-title">
                  Feedback
                </h4>
                <p class="feedback-text">
                  {{ submission.segmentation.feedback_message }}
                </p>
              </div>

              <div
                v-if="submission.segmentation.suggested_improvements?.length"
                class="analysis-section"
              >
                <h4 class="section-title">
                  Suggested Improvements
                </h4>
                <ul class="improvements-list">
                  <li
                    v-for="(improvement, idx) in submission.segmentation.suggested_improvements"
                    :key="idx"
                  >
                    {{ improvement }}
                  </li>
                </ul>
              </div>

              <div
                v-if="submission.segmentation.segments?.length"
                class="analysis-section"
              >
                <h4 class="section-title">
                  Code Segments (<span class="segment-count-highlight">{{ submission.segmentation.segment_count || submission.segmentation.segments.length }}</span>)
                </h4>
                <div class="segments-list">
                  <div
                    v-for="(segment, idx) in submission.segmentation.segments"
                    :key="idx"
                    class="segment-item"
                  >
                    {{ segment }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue'
import Editor from '@/features/editor/Editor.vue'
import { formatTestValue, getValueDisplayClass } from '@/utils/testValueFormatter'
import { log } from '@/utils/logger'
import { useFocusTrap } from '@/composables/useFocusTrap'

interface TestResult {
  passed?: boolean
  isSuccessful?: boolean
  function_call?: string
  description?: string
  inputs?: unknown
  expected_output?: unknown
  expected?: unknown
  actual_output?: unknown
  actual?: unknown
}

interface Variation {
  code?: string
  passed_all_tests?: boolean
  tests_passed?: number
  total_tests?: number
  tests_total?: number
  test_results?: TestResult[]
}

interface HintActivated {
  hint_type: string
  trigger_type: string
  activated_at?: string
}

interface Segmentation {
  confidence_score?: number
  feedback_message?: string
  suggested_improvements?: string[]
  segments?: string[]
  segment_count?: number
}

interface Submission {
  id?: string
  submission_id?: string
  user?: string
  problem?: { title?: string } | string
  submitted_at?: string
  score?: number
  completion_status?: string
  status?: string
  execution_time_ms?: number
  raw_input?: string
  processed_code?: string
  test_results?: TestResult[]
  hints_activated?: HintActivated[]
  segmentation?: Segmentation
  data?: {
    variations?: Variation[]
    test_results?: TestResult[]
    processed_code?: string
  }
  code_variations?: Variation[]
  results?: Array<{ success?: boolean; test_results?: TestResult[]; results?: TestResult[] }>
  variations?: string[]
  total_variations?: number
  passing_variations?: number
}

const props = defineProps<{
  isVisible: boolean
  submission: Submission | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'download', submission: Submission | null): void
}>()

// Focus trap composable
const { modalContentRef } = useFocusTrap(toRef(() => props.isVisible))

// State
const currentVariationIndex = ref(0)

// Computed
const hasVariations = computed(() => {
  if (props.submission?.data?.variations?.length && props.submission.data.variations.length >= 1) {
    return true
  }
  if (props.submission?.code_variations?.length && props.submission.code_variations.length > 1) {
    return true
  }
  return (props.submission?.results?.length ?? 0) > 1 ||
         (props.submission?.variations?.length ?? 0) > 1 ||
         (props.submission?.total_variations ?? 0) > 1
})

const totalVariationsCount = computed(() => {
  if (props.submission?.data?.variations?.length) {
    return props.submission.data.variations.length
  }
  if (props.submission?.code_variations?.length) {
    return props.submission.code_variations.length
  }
  return props.submission?.total_variations ||
         props.submission?.results?.length ||
         props.submission?.variations?.length ||
         1
})

const passingVariationsCount = computed(() => {
  if (props.submission?.data?.variations?.length) {
    return props.submission.data.variations.filter(v =>
      v.passed_all_tests || (v.tests_passed === v.total_tests && (v.total_tests ?? 0) > 0)
    ).length
  }
  if (props.submission?.code_variations?.length) {
    return props.submission.code_variations.filter(cv =>
      cv.tests_passed === cv.tests_total && (cv.tests_total ?? 0) > 0
    ).length
  }
  return props.submission?.passing_variations ||
         (props.submission?.results?.filter(r => r.success)?.length) ||
         0
})

const currentVariationData = computed(() => {
  if (!hasVariations.value) {
    if (props.submission?.test_results) {
      const passed = props.submission.test_results.filter(t => t.passed || t.isSuccessful).length
      return {
        testsPassed: passed,
        totalTests: props.submission.test_results.length,
        success: passed === props.submission.test_results.length
      }
    }
    return null
  }

  if (props.submission?.data?.variations?.length) {
    const variation = props.submission.data.variations[currentVariationIndex.value]
    if (variation) {
      return {
        testsPassed: variation.tests_passed,
        totalTests: variation.total_tests,
        success: variation.passed_all_tests || (variation.tests_passed === variation.total_tests && (variation.total_tests ?? 0) > 0)
      }
    }
  }

  if (props.submission?.code_variations?.length) {
    const variation = props.submission.code_variations[currentVariationIndex.value]
    if (variation) {
      return {
        testsPassed: variation.tests_passed,
        totalTests: variation.tests_total,
        success: variation.tests_passed === variation.tests_total && (variation.tests_total ?? 0) > 0
      }
    }
  }

  return props.submission?.results?.[currentVariationIndex.value] || null
})

const currentVariationStatusClass = computed(() => {
  if (!currentVariationData.value) {
    return ''
  }
  return currentVariationData.value.success ? 'success' : 'partial'
})

const currentCodeToDisplay = computed(() => {
  if (hasVariations.value) {
    if (props.submission?.data?.variations?.length) {
      const variation = props.submission.data.variations[currentVariationIndex.value]
      return variation?.code || ''
    }
    if (props.submission?.code_variations?.length) {
      const variation = props.submission.code_variations[currentVariationIndex.value]
      return variation?.code || ''
    }
    if (props.submission?.variations) {
      return props.submission.variations[currentVariationIndex.value]
    }
  }
  if (props.submission?.data?.processed_code) {
    return props.submission.data.processed_code
  }
  return props.submission?.processed_code || props.submission?.raw_input || ''
})

const currentTestResults = computed(() => {
  if (!hasVariations.value) {
    if (props.submission?.data?.test_results) {
      return props.submission.data.test_results
    }
    return props.submission?.test_results || []
  }

  if (props.submission?.data?.variations?.length) {
    const variation = props.submission.data.variations[currentVariationIndex.value]
    return variation?.test_results || []
  }
  if (props.submission?.code_variations?.length) {
    const variation = props.submission.code_variations[currentVariationIndex.value]
    return variation?.test_results || []
  }
  const variationData = props.submission?.results?.[currentVariationIndex.value]
  return variationData?.test_results || variationData?.results || []
})

const currentPassingTests = computed(() =>
  currentTestResults.value.filter(t => t.passed || t.isSuccessful).length
)

const currentFailingTests = computed(() =>
  currentTestResults.value.filter(t => !(t.passed || t.isSuccessful)).length
)

const currentPassingTestsList = computed(() =>
  currentTestResults.value.filter(t => t.passed || t.isSuccessful)
)

const currentFailingTestsList = computed(() =>
  currentTestResults.value.filter(t => !(t.passed || t.isSuccessful))
)

const hasHintsActivated = computed(() =>
  (props.submission?.hints_activated?.length ?? 0) > 0
)

const hintsActivatedCount = computed(() =>
  props.submission?.hints_activated?.length || 0
)

// Methods
function closeModal(): void {
  emit('close')
}

function downloadSubmission(): void {
  emit('download', props.submission)
}

function getScoreClass(score: number | undefined): string {
  if (!score) {
    return 'error'
  }
  if (score >= 100) {
    return 'success'
  }
  if (score >= 60) {
    return 'warning'
  }
  return 'error'
}

function getStatusClass(status: string | undefined): string {
  const s = status?.toLowerCase()
  if (s === 'passed' || s === 'complete') {
    return 'success'
  }
  if (s === 'partial') {
    return 'warning'
  }
  if (s === 'failed' || s === 'error') {
    return 'error'
  }
  return ''
}

function formatDate(dateString: string | undefined): string {
  if (!dateString) {
    return 'Unknown'
  }
  const date = new Date(dateString)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function _formatComprehension(level: string | undefined): string {
  if (!level) {
    return 'Not evaluated'
  }
  if (level === 'high_level' || level === 'high-level') {
    return 'High Level'
  }
  if (level === 'low_level' || level === 'low-level') {
    return 'Low Level'
  }
  return level
}

function _formatTimeSpent(seconds: number | undefined): string {
  if (!seconds) {
    return 'N/A'
  }
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
}

function formatValue(value: unknown): string {
  return formatTestValue(value)
}

function prevVariation(): void {
  if (currentVariationIndex.value > 0) {
    currentVariationIndex.value--
  }
}

function nextVariation(): void {
  if (currentVariationIndex.value < totalVariationsCount.value - 1) {
    currentVariationIndex.value++
  }
}

function formatTestCall(test: TestResult): string {
  if (test.function_call) {
    return test.function_call
  }
  if (test.description) {
    const match = test.description.match(/([a-zA-Z_][a-zA-Z0-9_]*\([^)]*\))/)
    if (match) {
      return match[1]
    }
    return test.description
  }
  if (test.inputs !== undefined) {
    return `test(${formatValue(test.inputs)})`
  }
  return 'Test Case'
}

async function copyCode(code?: string): Promise<void> {
  const codeToCopy = code || currentCodeToDisplay.value
  if (!codeToCopy) {
    return
  }

  try {
    await navigator.clipboard.writeText(codeToCopy)
  } catch (err) {
    log.error('Failed to copy to clipboard', { error: err })
  }
}

function formatHintType(hintType: string): string {
  const typeMap: Record<string, string> = {
    'variable_fade': 'Variable Fade',
    'subgoal_highlight': 'Subgoal Highlighting',
    'suggested_trace': 'Suggested Trace'
  }
  return typeMap[hintType] || hintType
}

function formatTriggerType(triggerType: string): string {
  const triggerMap: Record<string, string> = {
    'manual': 'Manually activated',
    'auto_attempts': 'Auto (attempts)',
    'auto_time': 'Auto (time)',
    'instructor': 'Instructor provided'
  }
  return triggerMap[triggerType] || triggerType
}

function getHintIcon(hintType: string): string {
  const iconMap: Record<string, string> = {
    'variable_fade': '🔤',
    'subgoal_highlight': '🎯',
    'suggested_trace': '🔍'
  }
  return iconMap[hintType] || '💡'
}

function formatHintTime(timestamp: string | undefined): string {
  if (!timestamp) {
    return 'Unknown'
  }
  return formatDate(timestamp)
}

// Watchers
watch(() => props.submission, () => {
  currentVariationIndex.value = 0
})
</script>

<style scoped>
/* Base Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: var(--color-bg-panel);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  max-width: 800px;
  width: 90vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  padding: 20px;
  border-bottom: 1px solid var(--color-bg-input);
}

.header-info {
  flex: 1;
}

.modal-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.header-meta {
  margin-top: 4px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.meta-separator {
  margin: 0 8px;
  opacity: 0.5;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.download-btn {
  padding: 6px 12px;
  background: var(--color-primary-gradient-start);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.download-btn:hover:not(:disabled) {
  background: var(--color-primary-gradient-end);
}

.download-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Metrics Bar */
.metrics-bar {
  display: flex;
  gap: 24px;
  padding: 16px 20px;
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-bg-input);
  flex-wrap: wrap;
}

.metric {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.metric-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.metric-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.metric-value.success { color: var(--color-success); }
.metric-value.warning { color: var(--color-warning); }
.metric-value.error { color: var(--color-error); }

/* Variation Navigation */
.variation-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-bg-input);
}

.nav-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.variation-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.variation-status {
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 12px;
}

.variation-status.success {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.variation-status.partial {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.nav-controls {
  display: flex;
  gap: 8px;
}

.nav-btn {
  padding: 6px 12px;
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-text-primary);
}

.nav-btn:hover:not(:disabled) {
  background: var(--color-bg-input);
  border-color: var(--color-bg-border);
}

.nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Main Content */
.main-content {
  flex: 1;
  overflow-y: auto;
  background: var(--color-bg-panel);
  padding: 20px;
}

/* Two Column Layout */
.two-column-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.code-column,
.tests-column {
  min-height: 400px;
}

.tests-column {
  border-left: 1px solid var(--color-bg-input);
  padding-left: 20px;
}

.test-count {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-weight: normal;
}


/* Code Section */
.code-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.copy-btn {
  padding: 4px 12px;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-text-primary);
}

.copy-btn:hover {
  background: var(--color-bg-input);
}

.prompt-box {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-text-primary);
  margin-bottom: 16px;
}

/* Test Results Section */
.test-results {
  padding: 0;
  background: var(--color-bg-panel);
}

/* Test Summary Bar */
.test-summary-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-bg-input);
  margin-bottom: var(--spacing-md);
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

/* Collapsible Test Groups */
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

/* Test List */
.test-list {
  padding: var(--spacing-sm) 0 0 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* Individual Test Items */
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
  border-color: rgba(220, 53, 69, 0.3);
  background: var(--color-error-bg);
}

.test-item.passing {
  border-color: rgba(76, 175, 80, 0.3);
  background: var(--color-success-bg);
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

/* Static Analysis Section */
.analysis-section-static {
  border-top: 2px solid var(--color-bg-input);
  margin-top: 24px;
  padding-top: 24px;
}

.analysis-section-static .section-header {
  margin-bottom: 16px;
}

.analysis-section-static .section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.analysis-section {
  border-top: 1px solid var(--color-bg-input);
  padding-top: 16px;
}

.analysis-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.info-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;
}

.info-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
  flex-shrink: 0;
}

.info-value {
  font-size: 14px;
  color: var(--color-text-primary);
  word-break: break-all;
}

.feedback-text {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary);
  margin: 0;
}

.improvements-list {
  margin: 0;
  padding-left: 20px;
  list-style: disc;
}

.improvements-list li {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.segments-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.segment-item {
  background: var(--color-bg-hover);
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
  color: var(--color-text-primary);
}

.segment-count-highlight {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 8px;
  background: linear-gradient(135deg, #9f7aea 0%, #667eea 100%);
  color: white;
  font-size: 16px;
  font-weight: 700;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(159, 122, 234, 0.3);
  animation: pulse-glow 2s ease-in-out infinite;
  margin: 0 2px;
}

@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 2px 8px rgba(159, 122, 234, 0.3);
  }
  50% {
    box-shadow: 0 4px 16px rgba(159, 122, 234, 0.5);
  }
}

/* Hints Section */
.hints-section {
  background: var(--color-bg-hover);
  border-radius: 6px;
  padding: 16px;
}

.hints-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.hint-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  transition: all 0.2s;
}

.hint-item:hover {
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
}

.hint-icon {
  font-size: 20px;
  line-height: 1;
  flex-shrink: 0;
}

.hint-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hint-type-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.hint-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.hint-trigger {
  font-style: italic;
}

.hint-time {
  opacity: 0.8;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .modal-content {
    width: 100vw;
    max-width: 100vw;
    height: 100vh;
    max-height: 100vh;
    border-radius: 0;
  }

  .metrics-bar {
    gap: 16px;
  }

  .variation-nav {
    flex-direction: column;
    gap: 12px;
    text-align: center;
  }

  .nav-controls {
    width: 100%;
    justify-content: center;
  }

  .test-summary-bar {
    flex-direction: column;
    gap: 8px;
    text-align: center;
  }

  .main-content {
    padding: 16px;
  }

  .two-column-layout {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .tests-column {
    border-left: none;
    border-top: 1px solid var(--color-bg-input);
    padding-left: 0;
    padding-top: 16px;
  }

  .header-actions {
    flex-direction: column;
    gap: 8px;
  }

  .header-meta {
    font-size: 12px;
  }

  .meta-item {
    display: block;
    margin-bottom: 2px;
  }

  .meta-separator {
    display: none;
  }
}
</style>
