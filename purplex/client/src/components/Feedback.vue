<template>
  <div
    class="feedback-container"
    :class="{ 'is-navigating': isNavigating }"
  >
    <!-- Static Loading Message -->
    <div
      v-if="isLoading && variants.length === 0"
      class="generating-feedback-panel"
    >
      <div class="generating-content">
        <div class="generating-icon">
          🤖
        </div>
        <div class="generating-message">
          Generating feedback...
        </div>
      </div>
    </div>

    <!-- Navigation Skeleton - Shows during problem switching -->
    <div
      v-else-if="isNavigating && variants.length === 0"
      class="navigation-skeleton-panel"
    >
      <div class="skeleton-header">
        <div class="skeleton-bar skeleton-title" />
        <div class="skeleton-bar skeleton-button" />
      </div>
      <div class="skeleton-content">
        <div class="skeleton-section">
          <div class="skeleton-bar skeleton-label" />
          <div class="skeleton-bar skeleton-text" />
        </div>
        <div class="skeleton-section">
          <div class="skeleton-bar skeleton-card" />
          <div class="skeleton-bar skeleton-card" />
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <template v-else-if="variants.length > 0">
      <!-- Header Section -->
      <div class="feedback-header">
        <span class="header-title">{{ title }}</span>
        <!-- Attempt Selector Dropdown -->
        <div
          v-if="submissionHistory && submissionHistory.length > 0"
          class="attempt-selector"
        >
          <span class="attempt-header-label">Attempt:</span>
          <button
            class="attempt-dropdown-trigger"
            :class="{ 'is-active': showAttemptDropdown }"
            :aria-label="`View previous submissions. Current: attempt ${currentAttemptNumber} of ${totalAttempts}, score ${currentAttemptScore}%`"
            :aria-expanded="showAttemptDropdown"
            :aria-haspopup="true"
            @click="showAttemptDropdown = !showAttemptDropdown"
            @keydown.escape="showAttemptDropdown = false"
          >
            <span class="attempt-text">{{ currentAttemptNumber }}/{{ totalAttempts }}</span>
            <span
              class="attempt-score-badge"
              :class="[getScoreClass(currentAttemptScore), { 'is-partial': currentAttemptStatus === 'partial' }]"
            >
              {{ currentAttemptScore }}%
              <span v-if="currentAttemptStatus === 'partial'" class="partial-indicator" title="Tests passed but abstraction needs work">⚠</span>
            </span>
            <span class="dropdown-arrow" aria-hidden="true">▾</span>
          </button>

          <!-- Dropdown Panel -->
          <div
            v-show="showAttemptDropdown"
            ref="dropdownPanel"
            class="attempt-dropdown-panel"
            role="menu"
            :aria-hidden="!showAttemptDropdown"
          >
            <div class="attempt-list-minimal">
              <button
                v-for="(attempt, index) in submissionHistory"
                :key="attempt.id"
                class="attempt-item-minimal"
                :class="{
                  'is-current': attempt.id === currentSubmissionId,
                  'is-best': attempt.is_best,
                  'is-passing': attempt.score >= 100
                }"
                role="menuitem"
                :tabindex="showAttemptDropdown ? 0 : -1"
                :aria-label="`Attempt ${attempt.attempt_number}: ${attempt.score}%, ${attempt.tests_passed} of ${attempt.total_tests} tests passed${attempt.is_best ? ', best attempt' : ''}`"
                @click="loadAttempt(attempt)"
                @keydown.escape="closeDropdownAndFocusTrigger"
                @keydown.arrow-down.prevent="focusNextItem"
                @keydown.arrow-up.prevent="focusPreviousItem"
              >
                <span class="attempt-indicator" aria-hidden="true" />
                <span class="attempt-num">{{ attempt.attempt_number }}</span>
                <span
                  class="attempt-score-minimal"
                  :class="getScoreClass(attempt.score)"
                >{{ attempt.score }}%</span>
                <span class="attempt-tests">{{ attempt.tests_passed }}/{{ attempt.total_tests }}</span>
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

      <!-- User Explanation Section -->
      <div
        v-if="userPrompt"
        class="explanation-section"
        role="region"
        aria-labelledby="explanation-heading"
      >
        <div class="section-label">
          <span class="label-icon" aria-hidden="true">💭</span>
          <h3 id="explanation-heading" class="label-text">Your Explanation</h3>
        </div>
        <p class="explanation-text">{{ userPrompt }}</p>
      </div>

      <!-- Correctness Metric Card -->
      <button
        class="metric-card"
        :class="[correctnessClass, { 'expanded': showCorrectnessModal }]"
        @click="openCorrectnessModal"
        @keydown.enter="openCorrectnessModal"
        @keydown.space.prevent="openCorrectnessModal"
        :aria-expanded="showCorrectnessModal"
        aria-haspopup="dialog"
      >
        <div class="card-content">
          <div class="card-label" id="correctness-label">CORRECTNESS</div>

          <div
            class="progress-bar-container"
            role="progressbar"
            :aria-valuenow="correctnessFill"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="`Correctness: ${passingVariants} of ${totalVariants} versions passing`"
          >
            <div
              class="progress-bar-fill"
              :style="{ width: correctnessFill + '%' }"
              :class="correctnessBarClass"
            ></div>
          </div>

          <div class="card-status">
            <span class="status-icon" aria-hidden="true">{{ correctnessStatus.icon }}</span>
            <span class="status-label">{{ correctnessStatus.label }}</span>
            <span class="status-metric">{{ passingVariants }}/{{ totalVariants }} pass</span>
          </div>
          <div class="card-description">{{ correctnessStatus.description }}</div>
        </div>
        <div class="card-action" :class="correctnessClass" title="View analysis">
          <span class="action-icon">→</span>
        </div>
      </button>

      <!-- Abstraction Metric Card -->
      <button
        class="metric-card"
        :class="[abstractionClass, { 'expanded': showSegmentAnalysisModal && !isAbstractionLocked }]"
        @click="handleAbstractionClick"
        @keydown.enter="handleAbstractionClick"
        @keydown.space.prevent="handleAbstractionClick"
        :aria-expanded="showSegmentAnalysisModal"
        :aria-disabled="isAbstractionLocked"
        :aria-haspopup="isAbstractionLocked ? undefined : 'dialog'"
      >
        <div class="card-content">
          <div class="card-label" id="abstraction-label">ABSTRACTION</div>

          <div
            class="progress-bar-container"
            role="progressbar"
            :aria-valuenow="abstractionFill"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="isAbstractionLocked ? 'Abstraction: locked' : `Abstraction: ${segmentCount} segments`"
          >
            <div
              class="progress-bar-fill"
              :style="{ width: abstractionFill + '%' }"
              :class="abstractionBarClass"
            ></div>
          </div>

          <div class="card-status">
            <span class="status-icon" aria-hidden="true">{{ abstractionStatus.icon }}</span>
            <span class="status-label">{{ abstractionStatus.label }}</span>
            <span v-if="!isAbstractionLocked" class="status-metric">
              {{ segmentCount }} segments
              <span v-if="segmentCount > segmentThreshold" class="metric-hint">(want {{ segmentThreshold }})</span>
            </span>
          </div>
          <div class="card-description">{{ abstractionStatus.description }}</div>
        </div>
        <div v-if="!isAbstractionLocked" class="card-action" :class="abstractionClass" title="View analysis">
          <span class="action-icon">→</span>
        </div>
      </button>

      <!-- Next Step Banner -->
      <div
        v-if="nextStepAction"
        class="next-step-banner"
        :class="nextStepUrgency"
        role="alert"
      >
        <span class="banner-icon" aria-hidden="true">{{ nextStepUrgency === 'urgency-success' ? '🎉' : '💡' }}</span>
        <span class="banner-text">{{ nextStepBannerText }}</span>
        <button class="banner-button" @click="handleNextStepAction">
          {{ nextStepAction }}
        </button>
      </div>

      <!-- Live region for announcements -->
      <div
        class="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {{ announcement }}
      </div>
    </template>

    <!-- Empty State - Only show when no data and not loading -->
    <div
      v-else-if="!isLoading"
      class="empty-state"
    >
      <span class="empty-icon">🚀</span>
      <p>Submit a prompt to start getting feedback!</p>
    </div>

    <!-- Correctness Modal -->
    <CorrectnessModal
      :is-visible="showCorrectnessModal"
      :variants="variants"
      :selected-version="selectedVariant"
      @close="showCorrectnessModal = false"
      @update:selected-version="selectedVariant = $event"
      @debug="handleDebug"
    />

    <!-- PyTutor Modal -->
    <PyTutorModal
      :is-visible="showPyTutorModal"
      :python-tutor-url="pythonTutorUrl"
      @close="showPyTutorModal = false"
    />

    <!-- Segment Analysis Modal -->
    <SegmentAnalysisModal
      v-if="segmentation"
      :is-visible="showSegmentAnalysisModal"
      :segmentation="segmentation"
      :reference-code="referenceCode"
      :user-prompt="userPrompt"
      @close="showSegmentAnalysisModal = false"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType, nextTick } from 'vue'
import CorrectnessModal from '../modals/CorrectnessModal.vue'
import PyTutorModal from '../modals/PyTutorModal.vue'
import SegmentAnalysisModal from './segmentation/SegmentAnalysisModal.vue'
import { PythonTutorService } from '@/services/pythonTutor.service'
import { formatTestValue } from '@/utils/testValueFormatter'

interface TestCase {
  function_call: string
  expected_output: string
  actual_output?: string
  pass?: boolean
  isSuccessful?: boolean
  error?: string
}

interface TestResult {
  success?: boolean
  testsPassed?: number
  totalTests?: number
  results?: TestCase[]
  test_results?: TestCase[]
}

interface Variant {
  code: string
  passing: boolean
  testsPassed: number
  testsTotal: number
  tests: Array<{
    call: string
    expected: string
    actual?: string
    passed: boolean
  }>
}

interface SubmissionHistoryItem {
  id: string
  attempt_number: number
  score: number
  tests_passed: number
  total_tests: number
  is_best: boolean
  submitted_at: string
  completion_status?: string
}

interface ComponentData {
  showCorrectnessModal: boolean
  showSegmentAnalysisModal: boolean
  showPyTutorModal: boolean
  pythonTutorUrl: string
  selectedVariant: number
  showAttemptDropdown: boolean
  currentSubmissionId: string | null
  currentAttemptNumber: number
  currentAttemptScore: number
  currentAttemptStatus: string
  totalAttempts: number
  announcement: string
}

export default defineComponent({
  components: {
    CorrectnessModal,
    PyTutorModal,
    SegmentAnalysisModal
  },
  props: {
    progress: {
      type: Number as PropType<number>,
      default: 0,
    },
    notches: {
      type: Number as PropType<number>,
      default: 10,
    },
    title: {
      type: String as PropType<string>,
      default: 'Feedback',
    },
    feedback: {
      type: String as PropType<string>,
      default: '',
    },
    codeResults: {
      type: Array as PropType<string[]>,
      default: () => [],
    },
    testResults: {
      type: Array as PropType<TestResult[]>,
      default: () => [],
    },
    solutionCode: {
      type: String as PropType<string>,
      default: '',
    },
    comprehensionResults: {
      type: String as PropType<string>,
      default: '',
    },
    userPrompt: {
      type: String as PropType<string>,
      default: '',
    },
    segmentation: {
      type: Object as PropType<any>,
      default: null,
    },
    referenceCode: {
      type: String as PropType<string>,
      default: '',
    },
    problemType: {
      type: String as PropType<string>,
      default: '',
    },
    segmentationEnabled: {
      type: Boolean as PropType<boolean>,
      default: false,
    },
    isLoading: {
      type: Boolean as PropType<boolean>,
      default: false,
    },
    isNavigating: {
      type: Boolean as PropType<boolean>,
      default: false,
    },
    submissionHistory: {
      type: Array as PropType<SubmissionHistoryItem[]>,
      default: () => [],
    },
  },
  emits: ['load-attempt', 'solution-changed', 'next-problem'],
  data(): ComponentData {
    return {
      showCorrectnessModal: false,
      showSegmentAnalysisModal: false,
      showPyTutorModal: false,
      pythonTutorUrl: '',
      selectedVariant: 0,
      showAttemptDropdown: false,
      currentSubmissionId: null,
      currentAttemptNumber: 1,
      currentAttemptScore: 0,
      currentAttemptStatus: 'incomplete',
      totalAttempts: 0,
      announcement: '',
    }
  },
  computed: {
    // Transform codeResults + testResults into variants structure
    variants(): Variant[] {
      return this.codeResults.map((code, index) => {
        const testResult = this.testResults[index]
        let tests: Array<{ call: string; expected: string; actual?: string; passed: boolean }> = []
        let testsPassed = 0
        let testsTotal = 0

        if (testResult) {
          const testArray = testResult.test_results || testResult.results || []
          testsTotal = testResult.totalTests ?? testArray.length
          testsPassed = testResult.testsPassed ?? testArray.filter(t => t.isSuccessful ?? t.pass).length

          tests = testArray.map(t => ({
            call: t.function_call || '',
            expected: formatTestValue(t.expected_output),
            actual: t.actual_output !== undefined ? formatTestValue(t.actual_output) : undefined,
            passed: t.isSuccessful ?? t.pass ?? false
          }))
        }

        return {
          code,
          passing: testsPassed === testsTotal && testsTotal > 0,
          testsPassed,
          testsTotal,
          tests
        }
      })
    },

    totalVariants(): number {
      return this.variants.length
    },

    passingVariants(): number {
      return this.variants.filter(v => v.passing).length
    },

    allVariationsPass(): boolean {
      return this.totalVariants > 0 && this.passingVariants === this.totalVariants
    },

    correctnessFill(): number {
      if (this.totalVariants === 0) return 0
      return (this.passingVariants / this.totalVariants) * 100
    },

    segmentCount(): number {
      return this.segmentation?.segment_count ?? 0
    },

    segmentThreshold(): number {
      return this.segmentation?.threshold ?? 2
    },

    isAbstractionLocked(): boolean {
      // Lock abstraction when not all variants pass OR segmentation is disabled
      return !this.allVariationsPass || !this.segmentationEnabled
    },

    abstractionFill(): number {
      if (this.isAbstractionLocked) return 0
      if (this.segmentCount <= this.segmentThreshold) return 100
      return Math.max(0, 100 - (this.segmentCount - this.segmentThreshold) * 20)
    },

    correctnessStatus(): { icon: string; label: string; description: string } {
      if (this.passingVariants === 0) {
        return { icon: '✗', label: 'Not yet working', description: 'None of the versions passed the tests' }
      }
      if (this.passingVariants < this.totalVariants) {
        return { icon: '~', label: 'Works, but ambiguous', description: 'One version interpreted it differently' }
      }
      return { icon: '✓', label: 'Clear', description: 'All versions produced working code' }
    },

    abstractionStatus(): { icon: string; label: string; description: string } {
      if (this.isAbstractionLocked) {
        return { icon: '🔒', label: 'Locked', description: 'Unlocks when all versions pass' }
      }
      if (this.segmentCount <= this.segmentThreshold) {
        return { icon: '✓', label: 'High-level', description: 'Focused on purpose, not implementation' }
      }
      return { icon: '✗', label: 'Too detailed', description: 'Describe the goal, not the steps' }
    },

    correctnessClass(): string {
      if (this.passingVariants === 0) return 'status-error'
      if (this.passingVariants < this.totalVariants) return 'status-warning'
      return 'status-success'
    },

    abstractionClass(): string {
      if (this.isAbstractionLocked) return 'status-locked'
      if (this.segmentCount <= this.segmentThreshold) return 'status-success'
      return 'status-error'
    },

    correctnessBarClass(): string {
      if (this.passingVariants === 0) return 'bar-error'
      if (this.passingVariants < this.totalVariants) return 'bar-warning'
      return 'bar-success'
    },

    abstractionBarClass(): string {
      if (this.isAbstractionLocked) return 'bar-locked'
      if (this.segmentCount <= this.segmentThreshold) return 'bar-success'
      return 'bar-error'
    },

    nextStepAction(): string | null {
      if (this.passingVariants === 0) {
        return 'View Analysis'
      }
      if (this.passingVariants < this.totalVariants) {
        return 'See What Failed'
      }
      if (!this.isAbstractionLocked && this.segmentCount > this.segmentThreshold) {
        return 'Review Abstraction'
      }
      // Fully successful
      if (this.allVariationsPass && !this.isAbstractionLocked && this.segmentCount <= this.segmentThreshold) {
        return 'Next Problem'
      }
      // All correct but abstraction not enabled/available
      if (this.allVariationsPass) {
        return 'Next Problem'
      }
      return null
    },

    nextStepBannerText(): string {
      if (this.passingVariants === 0) {
        return 'Your explanation didn\'t produce working code yet. Let\'s look at what the code tried to do and where it went wrong.'
      }
      if (this.passingVariants < this.totalVariants) {
        return 'Your explanation could be read in different ways. One interpretation worked, but another didn\'t. Try being more specific.'
      }
      if (!this.isAbstractionLocked && this.segmentCount > this.segmentThreshold) {
        return 'Your explanation focuses on individual steps. Try describing what the code accomplishes overall instead of how it works line-by-line.'
      }
      // Fully successful
      if (this.allVariationsPass) {
        return 'Problem complete! Your explanation is clear and correct.'
      }
      return ''
    },

    nextStepUrgency(): string {
      if (this.passingVariants === 0) return 'urgency-high'
      if (this.passingVariants < this.totalVariants) return 'urgency-medium'
      if (!this.isAbstractionLocked && this.segmentCount > this.segmentThreshold) return 'urgency-low'
      // Fully successful
      return 'urgency-success'
    }
  },
  watch: {
    showAttemptDropdown(newVal) {
      if (newVal) {
        this.positionDropdown()
        nextTick(() => {
          const firstItem = this.$el?.querySelector('.attempt-item-minimal') as HTMLElement
          firstItem?.focus()
        })
      }
    },
    submissionHistory: {
      handler() {
        this.initializeSubmissionHistory()
      },
      deep: true,
      immediate: true
    }
  },
  mounted() {
    this.initializeSubmissionHistory()
    document.addEventListener('click', this.handleClickOutside)
  },
  beforeUnmount() {
    document.removeEventListener('click', this.handleClickOutside)
  },
  methods: {
    announce(message: string) {
      this.announcement = ''
      nextTick(() => {
        this.announcement = message
      })
    },

    // Submission history methods
    initializeSubmissionHistory(): void {
      if (this.submissionHistory && this.submissionHistory.length > 0) {
        this.totalAttempts = this.submissionHistory.length
        const currentAttempt = this.submissionHistory[0]
        if (currentAttempt) {
          this.currentSubmissionId = currentAttempt.id
          this.currentAttemptNumber = currentAttempt.attempt_number
          this.currentAttemptScore = currentAttempt.score
          this.currentAttemptStatus = currentAttempt.completion_status || 'incomplete'
        }
      }
    },

    loadAttempt(attempt: SubmissionHistoryItem): void {
      this.showAttemptDropdown = false
      this.currentSubmissionId = attempt.id
      this.currentAttemptNumber = attempt.attempt_number
      this.currentAttemptScore = attempt.score
      this.currentAttemptStatus = attempt.completion_status || 'incomplete'
      this.$emit('load-attempt', attempt)
    },

    positionDropdown(): void {
      nextTick(() => {
        const dropdown = this.$refs.dropdownPanel as HTMLElement
        if (!dropdown || !this.$el) return

        const trigger = this.$el.querySelector('.attempt-dropdown-trigger') as HTMLElement
        if (!trigger) return

        const rect = trigger.getBoundingClientRect()
        dropdown.style.top = `${rect.bottom + 4}px`
        dropdown.style.left = `${rect.right - dropdown.offsetWidth}px`
      })
    },

    handleClickOutside(event: MouseEvent): void {
      if (!this.showAttemptDropdown || !this.$el) return

      const dropdown = this.$refs.dropdownPanel as HTMLElement
      const trigger = this.$el.querySelector('.attempt-dropdown-trigger') as HTMLElement

      if (dropdown && trigger &&
          !dropdown.contains(event.target as Node) &&
          !trigger.contains(event.target as Node)) {
        this.showAttemptDropdown = false
      }
    },

    closeDropdownAndFocusTrigger(): void {
      this.showAttemptDropdown = false
      nextTick(() => {
        const trigger = this.$el?.querySelector('.attempt-dropdown-trigger') as HTMLElement
        trigger?.focus()
      })
    },

    focusNextItem(event: KeyboardEvent): void {
      const currentElement = event.target as HTMLElement
      const nextElement = currentElement.nextElementSibling as HTMLElement
      if (nextElement && nextElement.classList.contains('attempt-item-minimal')) {
        nextElement.focus()
      }
    },

    focusPreviousItem(event: KeyboardEvent): void {
      const currentElement = event.target as HTMLElement
      const previousElement = currentElement.previousElementSibling as HTMLElement
      if (previousElement && previousElement.classList.contains('attempt-item-minimal')) {
        previousElement.focus()
      }
    },

    getScoreClass(score: number): string {
      if (score >= 100) return 'score-perfect'
      if (score >= 80) return 'score-good'
      if (score >= 60) return 'score-partial'
      return 'score-low'
    },

    // Modal handlers
    openCorrectnessModal(): void {
      this.showCorrectnessModal = true
      this.announce('Correctness Analysis dialog opened')
    },

    handleAbstractionClick(): void {
      if (this.isAbstractionLocked) {
        this.announce('Abstraction is locked. Complete all correctness tests first.')
        return
      }
      this.showSegmentAnalysisModal = true
      this.announce('Abstraction Details dialog opened')
    },

    handleNextStepAction(): void {
      if (this.passingVariants < this.totalVariants) {
        // Open correctness modal for issues
        this.openCorrectnessModal()
      } else if (!this.isAbstractionLocked && this.segmentCount > this.segmentThreshold) {
        // Open abstraction modal
        this.showSegmentAnalysisModal = true
      } else {
        // Navigate to next problem
        this.$emit('next-problem')
      }
    },

    handleDebug(variant: Variant): void {
      // Find first failing test to debug
      const failingTest = variant.tests.find(t => !t.passed)
      if (!failingTest) return

      const testCase = {
        function_call: failingTest.call,
        expected_output: failingTest.expected,
        actual_output: failingTest.actual
      }

      const formattedCode = PythonTutorService.formatCodeWithTest(variant.code, testCase)
      this.pythonTutorUrl = PythonTutorService.generateEmbedUrl(formattedCode)
      this.showPyTutorModal = true
    }
  }
})
</script>

<style scoped>
/* Screen reader only utility */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Main Container */
.feedback-container {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  position: relative;
  min-height: 400px;
}

/* Generating Feedback Panel */
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

/* Navigation Skeleton */
.navigation-skeleton-panel {
  padding: var(--spacing-lg);
  background: var(--color-bg-panel);
  min-height: 400px;
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
    rgba(255, 255, 255, 0.05) 0%,
    rgba(255, 255, 255, 0.1) 50%,
    rgba(255, 255, 255, 0.05) 100%
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

.skeleton-text {
  width: 90%;
  height: 16px;
}

.skeleton-card {
  height: 80px;
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* Header */
.feedback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-bg-input);
}

.header-title {
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
  margin: 0;
}

/* Attempt Selector */
.attempt-selector {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.attempt-header-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 600;
  padding: 0 var(--spacing-xs);
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
  font-family: inherit;
}

.attempt-dropdown-trigger:hover {
  color: var(--color-text-secondary);
}

.attempt-dropdown-trigger.is-active {
  color: var(--color-text-primary);
}

.attempt-dropdown-trigger:focus {
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
  background: rgba(76, 175, 80, 0.15);
  color: var(--color-success);
}

.attempt-score-badge.score-good {
  background: rgba(76, 175, 80, 0.1);
  color: rgb(76, 175, 80);
}

.attempt-score-badge.score-partial {
  background: rgba(255, 193, 7, 0.1);
  color: rgb(255, 193, 7);
}

.attempt-score-badge.score-low {
  background: rgba(220, 53, 69, 0.1);
  color: var(--color-error);
}

.attempt-score-badge.is-partial {
  background: rgba(255, 152, 0, 0.15);
  border: 1px solid rgba(255, 152, 0, 0.5);
}

.partial-indicator {
  margin-left: 2px;
  font-size: 10px;
}

.dropdown-arrow {
  font-size: 10px;
  opacity: 0.4;
  transition: transform 0.2s;
}

.attempt-dropdown-trigger.is-active .dropdown-arrow {
  transform: rotate(180deg);
}

/* Dropdown Panel */
.attempt-dropdown-panel {
  position: fixed;
  width: 240px;
  max-height: 200px;
  background: var(--color-bg-panel);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 99999;
  overflow: hidden;
}

.attempt-list-minimal {
  overflow-y: auto;
  max-height: 200px;
  padding: 4px;
}

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

.attempt-item-minimal:hover {
  background: rgba(255, 255, 255, 0.03);
  color: var(--color-text-secondary);
}

.attempt-item-minimal.is-current {
  background: rgba(102, 126, 234, 0.08);
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
  color: rgb(76, 175, 80);
}

.attempt-score-minimal.score-partial {
  color: rgb(255, 193, 7);
}

.attempt-score-minimal.score-low {
  color: var(--color-error);
}

.attempt-tests {
  flex: 1;
  text-align: right;
  opacity: 0.6;
}

.best-mark {
  color: var(--color-warning);
  font-size: 10px;
}

/* Explanation Section */
.explanation-section {
  margin: var(--spacing-md) var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  border-left: 3px solid var(--color-primary);
}

.section-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.label-icon {
  font-size: var(--font-size-base);
}

.label-text {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

.explanation-text {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  margin: 0;
  padding: var(--spacing-sm);
  background: var(--color-bg-dark);
  border-radius: var(--radius-xs);
  font-style: italic;
}

/* Metric Cards */
.metric-card {
  display: flex;
  align-items: stretch;
  width: calc(100% - calc(var(--spacing-lg) * 2));
  margin: var(--spacing-md) var(--spacing-lg);
  padding: 0;
  background: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: var(--transition-fast);
  border: none;
  border-left: 4px solid transparent;
  text-align: left;
  font-family: inherit;
  overflow: hidden;
}

.card-content {
  flex: 1;
  padding: var(--spacing-sm) var(--spacing-md);
  min-width: 0;
}

.metric-card:hover {
  background: var(--color-bg-input);
}

.metric-card:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.metric-card.status-error {
  border-left-color: var(--color-error);
}

.metric-card.status-warning {
  border-left-color: var(--color-warning);
}

.metric-card.status-success {
  border-left-color: var(--color-success);
}

.metric-card.status-locked {
  border-left-color: var(--color-bg-disabled);
  opacity: 0.6;
  cursor: not-allowed;
}

.metric-card.status-locked:hover {
  background: var(--color-bg-hover);
}

.card-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  letter-spacing: 0.5px;
  margin-bottom: var(--spacing-md);
}

/* Progress Bar */
.progress-bar-container {
  height: 8px;
  background: var(--color-bg-dark);
  border-radius: var(--radius-xs);
  overflow: hidden;
  margin-bottom: var(--spacing-md);
}

.progress-bar-fill {
  height: 100%;
  border-radius: var(--radius-xs);
  transition: width 0.4s ease;
}

.progress-bar-fill.bar-error {
  background: linear-gradient(90deg, var(--color-error), #c82333);
}

.progress-bar-fill.bar-warning {
  background: linear-gradient(90deg, var(--color-warning), #e0a800);
}

.progress-bar-fill.bar-success {
  background: linear-gradient(90deg, var(--color-success), #218838);
}

.progress-bar-fill.bar-locked {
  background: var(--color-bg-border);
}

/* Card Status */
.card-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.status-icon {
  font-size: var(--font-size-base);
}

.status-label {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.status-metric {
  margin-left: auto;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.metric-hint {
  color: var(--color-text-muted);
  opacity: 0.7;
}

.card-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

/* Action Column */
.card-action {
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  align-self: stretch;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.2s ease;
  flex-shrink: 0;
  margin: 0;
}

.card-action.status-success {
  background: rgba(76, 175, 80, 0.08);
  border-left-color: rgba(76, 175, 80, 0.3);
}

.card-action.status-warning {
  background: rgba(255, 193, 7, 0.08);
  border-left-color: rgba(255, 193, 7, 0.3);
}

.card-action.status-error {
  background: rgba(220, 53, 69, 0.08);
  border-left-color: rgba(220, 53, 69, 0.3);
}

.action-icon {
  font-size: 18px;
  font-weight: 600;
  transition: transform 0.2s ease;
}

.card-action.status-success .action-icon {
  color: var(--color-success);
}

.card-action.status-warning .action-icon {
  color: var(--color-warning);
}

.card-action.status-error .action-icon {
  color: var(--color-error);
}

/* Hover effects */
.metric-card:hover .card-action.status-success {
  background: rgba(76, 175, 80, 0.2);
}

.metric-card:hover .card-action.status-warning {
  background: rgba(255, 193, 7, 0.2);
}

.metric-card:hover .card-action.status-error {
  background: rgba(220, 53, 69, 0.2);
}

.metric-card:hover .card-action .action-icon {
  transform: translateX(3px);
}

/* Next Step Banner */
.next-step-banner {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin: var(--spacing-md) var(--spacing-lg);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  border-width: 2px;
  border-style: solid;
}

.next-step-banner.urgency-high {
  background: rgba(220, 53, 69, 0.15);
  border-color: rgba(220, 53, 69, 0.5);
  font-size: var(--font-size-sm);
}

.next-step-banner.urgency-medium {
  background: rgba(255, 193, 7, 0.15);
  border-color: rgba(255, 193, 7, 0.5);
  font-size: var(--font-size-sm);
}

.next-step-banner.urgency-low {
  background: rgba(33, 150, 243, 0.15);
  border-color: rgba(33, 150, 243, 0.5);
  font-size: var(--font-size-sm);
}

.next-step-banner.urgency-success {
  background: rgba(76, 175, 80, 0.15);
  border-color: rgba(76, 175, 80, 0.5);
}

.banner-icon {
  font-size: var(--font-size-lg);
  flex-shrink: 0;
}

.banner-text {
  flex: 1;
  color: var(--color-text-primary);
  line-height: 1.4;
  font-weight: 500;
}

.banner-button {
  flex-shrink: 0;
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
  border-radius: var(--radius-xs);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-fast);
  font-family: inherit;
}

.urgency-high .banner-button {
  background: var(--color-error);
  color: white;
}

.urgency-high .banner-button:hover {
  background: #c82333;
}

.urgency-medium .banner-button {
  background: var(--color-warning);
  color: #1a1a1a;
}

.urgency-medium .banner-button:hover {
  background: #e0a800;
}

.urgency-low .banner-button {
  background: var(--color-info);
  color: white;
}

.urgency-low .banner-button:hover {
  background: #1976d2;
}

.urgency-success .banner-button {
  background: var(--color-success);
  color: white;
}

.urgency-success .banner-button:hover {
  background: #43a047;
}

.banner-button:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

/* Empty State */
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

/* Responsive Design */
@media (max-width: 768px) {
  .feedback-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }

  .attempt-selector {
    width: 100%;
    justify-content: space-between;
  }

  .next-step-banner {
    flex-direction: column;
    text-align: center;
  }

  .banner-button {
    width: 100%;
  }
}

/* Navigation transition */
.feedback-container.is-navigating {
  /* Opacity removed - rely on skeleton for loading indication */
}
</style>
