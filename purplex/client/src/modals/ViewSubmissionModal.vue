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
              {{ $t('admin.submissions.title') }}
            </h2>
            <div class="header-meta">
              <span class="meta-item">{{ submission?.user || $t('admin.submissions.unknownUser') }}</span>
              <span class="meta-separator">•</span>
              <span class="meta-item">{{ submission?.problem?.title || submission?.problem || $t('admin.submissions.unknownProblem') }}</span>
              <span v-if="submissionTypeLabel" class="meta-separator">•</span>
              <span v-if="submissionTypeLabel" class="meta-item type-badge">{{ submissionTypeLabel }}</span>
              <span class="meta-separator">•</span>
              <span class="meta-item">{{ formatDate(submission?.submitted_at) }}</span>
            </div>
          </div>
          <div class="header-actions">
            <button
              v-if="expandRoute"
              class="expand-btn"
              :title="$t('admin.submissions.openFullPage')"
              @click="expandToFullPage"
            >
              {{ $t('admin.submissions.expand') }}
            </button>
            <button
              class="download-btn"
              :disabled="!submission"
              :title="$t('admin.submissions.downloadData')"
              @click="downloadSubmission"
            >
              {{ $t('admin.submissions.download') }}
            </button>
            <button
              class="close-btn"
              :aria-label="$t('common.close')"
              @click="closeModal"
            >
              ✕
            </button>
          </div>
        </div>

        <!-- Key Metrics Bar -->
        <div class="metrics-bar">
          <div class="metric">
            <span class="metric-label">{{ $t('admin.submissions.score') }}</span>
            <span
              class="metric-value"
              :class="getScoreClass(submission?.score)"
            >
              {{ submission?.score || 0 }}%
            </span>
          </div>
          <div class="metric">
            <span class="metric-label">{{ $t('admin.submissions.status') }}</span>
            <span
              class="metric-value"
              :class="getStatusClass(submission?.completion_status || submission?.status)"
            >
              {{ submission?.completion_status || submission?.status || $t('admin.submissions.unknown') }}
            </span>
          </div>
          <div
            v-if="hasVariations"
            class="metric"
          >
            <span class="metric-label">{{ $t('admin.submissions.variations') }}</span>
            <span class="metric-value">
              {{ $t('admin.submissions.variationsPassed', { passing: passingVariationsCount, total: totalVariationsCount }) }}
            </span>
          </div>
          <div
            v-if="currentVariationData"
            class="metric"
          >
            <span class="metric-label">{{ $t('admin.submissions.currentVariation') }}</span>
            <span class="metric-value">
              {{ $t('admin.submissions.testsPassed', { passed: currentVariationData.testsPassed, total: currentVariationData.totalTests }) }}
            </span>
          </div>
          <div
            v-if="submission?.execution_time_ms"
            class="metric"
          >
            <span class="metric-label">{{ $t('admin.submissions.time') }}</span>
            <span class="metric-value">{{ $t('common.units.ms', { value: submission.execution_time_ms }) }}</span>
          </div>
        </div>

        <!-- Main Content Area -->
        <div class="modal-body">
          <!-- Type-specific content (MCQ options, Refute claim, DebugFix side-by-side, etc.) -->
          <SubmissionDetailContent
            v-if="submission"
            :submission="(submission as Record<string, unknown>)"
          >
          <!-- Natural Language Prompt (EiPL/Prompt types) - full-width above grid -->
          <div
            v-if="submission?.raw_input"
            class="prompt-section"
          >
            <span class="section-title">{{ $t('admin.submissions.naturalLanguagePrompt') }}</span>
            <div class="prompt-box">
              {{ submission.raw_input }}
            </div>
          </div>

          <!-- Main Grid: code+tests group | segmentation -->
          <div
            class="main-grid"
            :class="{ 'has-segmentation': submission?.segmentation?.segments?.length }"
          >
            <!-- Left group: Code + Tests -->
            <div class="code-tests-group">
              <!-- Variation nav (scoped to code+tests) -->
              <div
                v-if="hasVariations"
                class="variation-nav"
              >
                <div class="nav-info">
                  <span class="variation-label">{{ $t('admin.submissions.variationOf', { current: currentVariationIndex + 1, total: totalVariationsCount }) }}</span>
                  <div
                    class="variation-status"
                    :class="currentVariationStatusClass"
                  >
                    {{ currentVariationData?.success ? $t('admin.submissions.allTestsPassed') : $t('admin.submissions.testsPassedOf', { passed: currentVariationData?.testsPassed || 0, total: currentVariationData?.totalTests || 0 }) }}
                  </div>
                </div>
                <div class="nav-controls">
                  <button
                    class="nav-btn"
                    :disabled="currentVariationIndex === 0"
                    :title="$t('admin.submissions.previousVariation')"
                    @click="prevVariation"
                  >
                    {{ $t('admin.submissions.previousArrow') }}
                  </button>
                  <button
                    class="nav-btn"
                    :disabled="currentVariationIndex >= totalVariationsCount - 1"
                    :title="$t('admin.submissions.nextVariation')"
                    @click="nextVariation"
                  >
                    {{ $t('admin.submissions.nextArrow') }}
                  </button>
                </div>
              </div>

              <div class="code-tests-columns">
                <!-- Code -->
                <div class="code-column">
                  <div class="code-section">
                    <div class="section-header">
                      <span class="section-title">
                        {{ hasVariations ? $t('admin.submissions.generatedCodeVariation', { index: currentVariationIndex + 1 }) : (submission?.raw_input ? $t('admin.submissions.generatedCode') : $t('admin.submissions.submittedCode')) }}
                      </span>
                      <button
                        class="copy-btn"
                        @click="copyCode(currentCodeToDisplay)"
                      >
                        {{ $t('admin.submissions.copy') }}
                      </button>
                    </div>
                    <Editor
                      :value="currentCodeToDisplay || '# No code available'"
                      :read-only="true"
                      :min-lines="3"
                      :max-lines="30"
                      width="100%"
                      theme="tomorrow_night"
                    />
                  </div>
                </div>

                <!-- Tests -->
                <div class="tests-panel">
                  <div class="section-header">
                    <span class="section-title">
                      {{ $t('admin.submissions.testResults', { passing: currentPassingTests, total: currentTestResults.length }) }}
                    </span>
                  </div>

                  <div
                    v-if="!currentTestResults || currentTestResults.length === 0"
                    class="empty-state"
                  >
                    {{ hasVariations ? $t('admin.submissions.noTestResultsVariation') : $t('admin.submissions.noTestResults') }}
                  </div>
                  <div
                    v-else
                    class="test-results"
                  >
                    <!-- Test Summary Bar -->
                    <div class="test-summary-bar">
                      <div class="summary-counts">
                        <span class="count-item passing">✓ {{ currentPassingTests }} {{ $t('admin.submissions.passing') }}</span>
                        <span class="count-item failing">✗ {{ currentFailingTests }} {{ $t('admin.submissions.failing') }}</span>
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
                        {{ $t('admin.submissions.failingTests', { count: currentFailingTests }) }}
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
                              <div>{{ $t('admin.submissions.expected') }} <code class="expected">{{ formatValue(test.expected_output || test.expected) }}</code></div>
                              <div>
                                {{ $t('admin.submissions.got') }} <code
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
                        {{ $t('admin.submissions.passingTests', { count: currentPassingTests }) }}
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

                  <!-- Hints (compact, inside tests panel) -->
                  <div
                    v-if="hasHintsActivated"
                    class="hints-compact"
                  >
                    <div class="section-header">
                      <span class="section-title">{{ $t('admin.submissions.hintsUsed', { count: hintsActivatedCount }) }}</span>
                    </div>
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
                </div>
              </div>
            </div>

            <!-- Right: Segmentation (only for EiPL) -->
            <div
              v-if="submission?.segmentation?.segments?.length"
              class="segmentation-panel"
            >
              <div class="section-header">
                <span class="section-title">
                  {{ $t('admin.submissions.segmentation') }}
                  <span class="segment-count-highlight">{{ submission.segmentation.segment_count || submission.segmentation.segments.length }}</span>
                </span>
              </div>
              <div class="segments-list">
                <div
                  v-for="(segment, idx) in submission.segmentation.segments"
                  :key="segment.id"
                  class="segment-item"
                  :style="{
                    borderLeftColor: getSegmentColor(idx),
                    backgroundColor: getSegmentColor(idx) + '10'
                  }"
                >
                  <span
                    class="segment-number"
                    :style="{ backgroundColor: getSegmentColor(idx) }"
                  >{{ idx + 1 }}</span>
                  <span class="segment-body">
                    <span class="segment-text">{{ segment.text }}</span>
                    <span v-if="segment.code_lines?.length" class="segment-lines">
                      {{ $t('admin.submissions.lines', { lines: formatCodeLines(segment.code_lines) }) }}
                    </span>
                  </span>
                </div>
              </div>
            </div>
          </div>
          </SubmissionDetailContent>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Editor from '@/features/editor/Editor.vue'
import SubmissionDetailContent from '@/modals/submission-detail/SubmissionDetailContent.vue'
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

interface SegmentData {
  id: number
  text: string
  code_lines: number[]
}

interface Segmentation {
  segments?: SegmentData[]
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

const { t } = useI18n()

// Focus trap composable
const { modalContentRef } = useFocusTrap(toRef(() => props.isVisible))

// Router for expand-to-full-page link
const router = useRouter()

const expandRoute = computed(() => {
  if (!props.submission) return null
  const subId = props.submission.submission_id || props.submission.id
  const courseData = (props.submission as Record<string, unknown>).course as { id?: string } | undefined
  if (courseData?.id) {
    return { name: 'InstructorSubmissionDetail', params: { courseId: courseData.id, submissionId: subId } }
  }
  return { name: 'AdminSubmissionDetail', params: { submissionId: subId } }
})

function expandToFullPage(): void {
  if (expandRoute.value) {
    closeModal()
    router.push(expandRoute.value)
  }
}

const submissionTypeLabel = computed(() => {
  const typeMap: Record<string, string> = {
    eipl: 'EiPL',
    mcq: 'MCQ',
    prompt: 'Prompt',
    refute: 'Refute',
    debug_fix: 'Debug Fix',
    probeable_code: 'Probeable Code',
    probeable_spec: 'Probeable Spec',
  }
  const st = (props.submission as Record<string, unknown> | null)?.submission_type as string | undefined
  return st ? (typeMap[st] || st) : ''
})

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
    return t('admin.submissions.unknown')
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
    return t('admin.submissions.notEvaluated')
  }
  if (level === 'high_level' || level === 'high-level') {
    return t('admin.submissions.highLevel')
  }
  if (level === 'low_level' || level === 'low-level') {
    return t('admin.submissions.lowLevel')
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
  return t('admin.submissions.testCase')
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
    'variable_fade': t('admin.submissions.hintTypes.variableFade'),
    'subgoal_highlight': t('admin.submissions.hintTypes.subgoalHighlight'),
    'suggested_trace': t('admin.submissions.hintTypes.suggestedTrace'),
  }
  return typeMap[hintType] || hintType
}

function formatTriggerType(triggerType: string): string {
  const triggerMap: Record<string, string> = {
    'manual': t('admin.submissions.triggerTypes.manual'),
    'auto_attempts': t('admin.submissions.triggerTypes.autoAttempts'),
    'auto_time': t('admin.submissions.triggerTypes.autoTime'),
    'instructor': t('admin.submissions.triggerTypes.instructor'),
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
    return t('admin.submissions.unknown')
  }
  return formatDate(timestamp)
}

// Segment display helpers
const SEGMENT_COLORS = ['#9f7aea', '#4299e1', '#4fd1c5', '#68d391', '#f6ad55', '#fc8181']

function getSegmentColor(index: number): string {
  return SEGMENT_COLORS[index % SEGMENT_COLORS.length]
}

function formatCodeLines(lines: number[]): string {
  if (!lines.length) return ''
  const sorted = [...lines].sort((a, b) => a - b)
  const ranges: string[] = []
  let start = sorted[0]
  let end = start
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] === end + 1) {
      end = sorted[i]
    } else {
      ranges.push(start === end ? `${start}` : `${start}-${end}`)
      start = sorted[i]
      end = start
    }
  }
  ranges.push(start === end ? `${start}` : `${start}-${end}`)
  return ranges.join(', ')
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
  background: var(--color-backdrop);
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
  box-shadow: var(--shadow-modal);
  max-width: 1400px;
  width: 95vw;
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

.expand-btn {
  padding: 6px 12px;
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.expand-btn:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-primary-gradient-start);
}

.type-badge {
  display: inline-block;
  padding: 1px 6px;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.download-btn {
  padding: 6px 12px;
  background: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
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

/* Modal Body */
.modal-body {
  flex: 1;
  overflow-y: auto;
  background: var(--color-bg-panel);
  padding: 20px;
}

/* Main Grid Layout */
.main-grid {
  display: grid;
  grid-template-columns: 1fr;
  align-items: start;
  gap: 20px;
}

.main-grid.has-segmentation {
  grid-template-columns: 2fr 1fr;
}

.code-tests-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.code-tests-group .variation-nav {
  border-bottom: none;
  padding: 8px 12px;
  border-radius: var(--radius-base);
}

.code-tests-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.tests-panel {
  background: var(--color-bg-main);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
}

.segmentation-panel {
  background: var(--color-bg-main);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
}

.hints-compact {
  border-top: 1px solid var(--color-bg-input);
  margin-top: 16px;
  padding-top: 16px;
}

.test-count {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-weight: normal;
}


/* Prompt Section (full-width above grid) */
.prompt-section {
  margin-bottom: 20px;
}

.prompt-section > .section-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-text-muted);
  margin-bottom: 8px;
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
  border-color: var(--color-error-overlay);
  background: var(--color-error-bg);
}

.test-item.passing {
  border-color: var(--color-success-overlay);
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

/* (analysis-section-static removed — content is now in the 3-col grid) */

.segments-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.segment-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 4px;
  border-left: 3px solid;
  font-size: 13px;
  color: var(--color-text-primary);
}

.segment-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: 600;
}

.segment-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.segment-lines {
  font-size: 11px;
  font-family: monospace;
  color: var(--color-text-muted);
}

.segment-count-highlight {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 8px;
  background: linear-gradient(135deg, #9f7aea 0%, var(--color-primary-gradient-start) 100%);
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: 700;
  border-radius: 6px;
  box-shadow: 0 2px 8px var(--color-segment-shadow);
  animation: pulse-glow 2s ease-in-out infinite;
  margin: 0 2px;
}

@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 2px 8px var(--color-segment-shadow);
  }
  50% {
    box-shadow: var(--shadow-segment-hover);
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
  box-shadow: 0 2px 8px var(--color-primary-overlay);
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

  .modal-body {
    padding: 16px;
  }

  .main-grid,
  .main-grid.has-segmentation {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .code-tests-columns {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .tests-panel,
  .segmentation-panel {
    background: transparent;
    border-radius: 0;
    border: none;
    border-top: 1px solid var(--color-bg-input);
    padding: 16px 0 0 0;
  }

  .prompt-section {
    margin-bottom: 16px;
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
