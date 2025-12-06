<template>
  <div class="feedback-container" :class="{ 'is-navigating': isNavigating }">
    <!-- Static Loading Message -->
    <div
      v-if="isLoading && slides.length === 0"
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
      v-else-if="isNavigating && slides.length === 0"
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
          <div class="skeleton-bar skeleton-text short" />
        </div>
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

    <!-- Header Section -->
    <div
      v-if="slides.length > 0"
      class="feedback-header"
    >
      <div class="section-label">
        {{ title }}
      </div>
      <!-- Attempt Selector Dropdown -->
      <div
        v-if="submissionHistory && submissionHistory.length > 0"
        class="attempt-selector"
      >
        <span class="attempt-header-label">Previous Submissions:</span>
        <button
          class="attempt-dropdown-trigger"
          :class="{ 'is-active': showAttemptDropdown }"
          :aria-label="`View previous submissions. Current: attempt ${currentAttemptNumber} of ${totalAttempts}, score ${currentAttemptScore}%`"
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
            :class="getScoreClass(currentAttemptScore)"
            :aria-label="`Score: ${currentAttemptScore} percent`"
          >
            <span aria-hidden="true">{{ getScoreIcon(currentAttemptScore) }}</span>
            {{ currentAttemptScore }}%
          </span>
          <span class="dropdown-arrow" aria-hidden="true">{{ showAttemptDropdown ? '▾' : '▾' }}</span>
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
              :ref="index === 0 ? 'firstMenuItem' : undefined"
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
              @keydown.home="handleHomeKey"
              @keydown.end="handleEndKey"
            >
              <span class="attempt-indicator" aria-hidden="true" />
              <span class="attempt-num">{{ attempt.attempt_number }}</span>
              <span
                class="attempt-score-minimal"
                :class="getScoreClass(attempt.score)"
              >{{ attempt.score }}%</span>
              <span class="attempt-tests">{{ attempt.tests_passed }}/{{ attempt.total_tests }}</span>
              <time class="attempt-time" :datetime="attempt.submitted_at">{{ formatTime(attempt.submitted_at) }}</time>
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

    <!-- Main Content -->
    <div
      v-if="slides.length > 0"
      class="feedback-content"
    >
      <!-- User Prompt Section -->
      <div
        v-if="userPrompt"
        class="user-prompt-section"
      >
        <div class="submission-header">
          <span class="submission-icon">💭</span>
          <span class="submission-label">Your response</span>
        </div>
        <div class="prompt-content">
          {{ userPrompt }}
        </div>
      </div>

      <!-- Comprehension Level Section Divider -->
      <div v-if="shouldShowComprehensionSection" class="section-divider">
        <span class="divider-label">
          <span class="divider-icon">🧠</span>
          <span class="divider-title">Comprehension Level</span>
          <span class="divider-separator">•</span>
          <span class="divider-description">Shows how high-level vs. line-by-line your explanation is</span>
        </span>
        <span
          class="info-icon"
          title="Evaluates the abstraction level of your explanation by analyzing how you describe the code's purpose. HIGH-LEVEL (✓): Describes overall goals, algorithm choices, and problem-solving approach without step-by-step details (e.g., 'uses binary search to efficiently find the target'). LINE-BY-LINE (✗): Describes implementation details, variable operations, and control flow step-by-step (e.g., 'sets left to 0, right to length, calculates mid'). This measures understanding depth - can you explain the 'why' and 'what' without the 'how'? Only available after all code variations pass their tests."
          aria-label="Info about comprehension level"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="7" cy="7" r="6.5" stroke="currentColor" />
            <path d="M7 10.5V6.5M7 4.5V4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
          </svg>
        </span>
      </div>

      <!-- Locked Segmentation Banner (when not all variations pass) -->
      <LockedSegmentationBanner
        v-if="showLockedSegmentation"
      />

      <!-- Comprehension Banner (when segmentation data exists) -->
      <ComprehensionBanner
        v-if="shouldShowSegmentation && segmentation && Object.keys(segmentation).length > 0"
        :segmentation="segmentation"
        :reference-code="referenceCode"
        @show-details="showSegmentAnalysisModal = true"
      />

      <!-- Correctness Section Divider -->
      <div class="section-divider">
        <span class="divider-label">
          <span class="divider-icon">🔄</span>
          <span class="divider-title">Correctness</span>
          <span class="divider-separator">•</span>
          <span class="divider-description">Multiple AI interpretations of your description tested against unit tests</span>
        </span>
        <span
          class="info-icon"
          title="Tests the clarity and completeness of your explanation by generating multiple independent code implementations from your description using AI, then running each against the problem's unit tests. Each variation represents a different interpretation of your words - if all variations pass, your explanation was unambiguous and captured all necessary logic. Failing variations reveal gaps, ambiguities, or missing details in how you described the solution. This evaluates whether someone could correctly implement the code from your explanation alone, without seeing the original."
          aria-label="Info about correctness"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="7" cy="7" r="6.5" stroke="currentColor" />
            <path d="M7 10.5V6.5M7 4.5V4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
          </svg>
        </span>
      </div>

      <!-- Solution Timeline -->
      <nav class="solution-timeline" aria-label="Solution variations">
        <button
          v-for="(slide, index) in slides"
          :key="index"
          class="timeline-node"
          :data-status="getSlideStatus(slide)"
          :data-current="currentSlide === index"
          :aria-label="`Solution ${index + 1}: ${slide.tests.filter(t => t.isSuccessful).length} of ${slide.tests.length} tests passing`"
          :aria-current="currentSlide === index ? 'true' : 'false'"
          @click="goToSlide(index)"
        >
          <span class="node-number" aria-hidden="true">{{ index + 1 }}</span>
          <span class="node-icon" aria-hidden="true">{{ getSlideIcon(slide) }}</span>
        </button>
      </nav>

      <!-- Code Editor -->
      <section class="code-section">
        <div class="code-header">
          <span>Solution {{ currentSlide + 1 }} of {{ slides.length }}</span>
        </div>
        <Editor
          :value="currentSlideContents"
          height="300px"
          width="100%"
          :highlight-markers="currentComprehensionResults"
          tab-target-id="promptEditor"
          @update:value="updateSolutionCode"
        />
      </section>

      <!-- Test Summary Bar -->
      <div class="test-summary-bar">
        <div class="summary-counts">
          <span class="count-item passing">✓ {{ passingTestsForCurrentSlide.length }} Passing</span>
          <span class="count-item failing">✗ {{ failingTestsForCurrentSlide.length }} Failing</span>
        </div>
      </div>

      <!-- Test Results -->
      <section class="test-results">
        <!-- Failing Tests (Expanded by default) -->
        <details
          v-if="failingTestsForCurrentSlide.length > 0"
          open
          class="test-group"
        >
          <summary class="test-group-header failing">
            <span class="group-icon">▶</span>
            Failing Tests ({{ failingTestsForCurrentSlide.length }})
          </summary>
          <div class="test-list">
            <article 
              v-for="(test, i) in failingTestsForCurrentSlide" 
              :key="`fail-${i}`" 
              class="test-item failing"
            >
              <div class="test-content">
                <code class="test-call">{{ test.function_call }}</code>
                <div class="test-diff">
                  <div>Expected: <code class="expected">{{ formatTestValue(test.expected_output) }}</code></div>
                  <div>
                    Got: <code
                      class="actual"
                      :class="getValueDisplayClass(test.actual_output)"
                    >{{
                      formatTestValue(test.actual_output) }}</code>
                  </div>
                </div>
              </div>
              <button
                class="debug-btn"
                :aria-label="`Debug test case: ${test.function_call}`"
                @click="openPyTutor(test)"
              >
                <span aria-hidden="true">🔍</span>
              </button>
            </article>
          </div>
        </details>

        <!-- Passing Tests (Collapsed by default) -->
        <details
          v-if="passingTestsForCurrentSlide.length > 0"
          class="test-group"
        >
          <summary
            class="test-group-header passing"
            tabindex="0"
            role="button"
            aria-expanded="false"
          >
            <span class="group-icon">▶</span>
            Passing Tests ({{ passingTestsForCurrentSlide.length }})
          </summary>
          <div class="test-list">
            <article 
              v-for="(test, i) in passingTestsForCurrentSlide" 
              :key="`pass-${i}`" 
              class="test-item passing"
            >
              <div class="test-content">
                <code class="test-call">{{ test.function_call }} → {{ formatTestValue(test.expected_output) }}</code>
              </div>
            </article>
          </div>
        </details>
      </section>
    </div>

    <!-- Empty State - Only show when no data and not loading -->
    <div
      v-else-if="!isLoading"
      class="empty-state"
    >
      <span class="empty-icon">🚀</span>
      <p>Submit a prompt to start getting feedback!</p>
    </div>

    <!-- PyTutor Modal -->
    <PyTutorModal
      :is-visible="showModal"
      :python-tutor-url="pythonTutorUrl"
      @close="showModal = false"
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
import { defineComponent, PropType } from 'vue'
import Editor from '@/features/editor/Editor.vue';
import PyTutorModal from '../modals/PyTutorModal.vue';
import ComprehensionBanner from './segmentation/ComprehensionBanner.vue';
import LockedSegmentationBanner from './segmentation/LockedSegmentationBanner.vue';
import SegmentAnalysisModal from './segmentation/SegmentAnalysisModal.vue';
import { PythonTutorService } from '@/services/pythonTutor.service';
import { log } from '@/utils/logger';
import { formatTestValue, getValueDisplayClass, isMissingValue } from '@/utils/testValueFormatter';

interface TestCase {
  function_call: string;
  expected_output: string;
  actual_output?: string;
  pass: boolean;
  isSuccessful?: boolean;
  error?: string;
}

interface TestResult {
  success?: boolean;
  passed?: number;
  total?: number;
  results?: TestCase[];
}

interface Slide {
  content: string;
  correct: boolean;
  tests: TestCase[];
}

interface ComponentData {
  showModal: boolean;
  pythonTutorUrl: string;
  currentSlide: number;
  currentSlideContents: string;
  currentComprehensionResults: any[];
  showSegmentAnalysisModal: boolean;
  showAttemptDropdown: boolean;
  currentSubmissionId: string | null;
  currentAttemptNumber: number;
  currentAttemptScore: number;
  totalAttempts: number;
  bestAttemptId: string | null;
}

export default defineComponent({
  components: {
    Editor,
    PyTutorModal,
    ComprehensionBanner,
    LockedSegmentationBanner,
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
      default: '',
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
      type: Array as PropType<any[]>,
      default: () => [],
    },
  },
  data(): ComponentData {
    return {
      showModal: false,
      pythonTutorUrl: '',
      currentSlide: 0,
      currentSlideContents: "",
      currentComprehensionResults: [],
      showSegmentAnalysisModal: false,
      showAttemptDropdown: false,
      currentSubmissionId: null,
      currentAttemptNumber: 1,
      currentAttemptScore: 0,
      totalAttempts: 0,
      bestAttemptId: null,
    };
  },
  computed: {
    // Segmentation support is determined by handler config (feedback_config.show_segmentation)
    // passed via the segmentationEnabled prop, so no need for type-specific checks
    shouldShowSegmentation(): boolean {
      return this.segmentationEnabled === true &&
             this.segmentation != null &&
             typeof this.segmentation === 'object' &&
             Object.keys(this.segmentation).length > 0;
    },
    allVariationsPass(): boolean {
      // Check if ALL variations passed ALL test cases
      return this.slides.length > 0 && this.slides.every(slide => slide.correct);
    },
    showLockedSegmentation(): boolean {
      // Show locked banner when:
      // 1. Segmentation is enabled for this problem (via handler config)
      // 2. Not all variations have passed yet
      // 3. We don't have segmentation data yet (because backend gates it on correctness)
      return this.segmentationEnabled === true &&
             !this.allVariationsPass &&
             (this.segmentation == null || Object.keys(this.segmentation).length === 0);
    },
    shouldShowComprehensionSection(): boolean {
      // Show comprehension section divider when problem has segmentation enabled (via handler config)
      return this.segmentationEnabled === true;
    },
    slides(): Slide[] {
      const slideResults = this.codeResults.map((code, index) => {
        const testResult = this.testResults[index];
        
        // Handle different data structures from backend
        let tests = [];
        let correct = false;
        
        if (testResult) {
          // Backend returns either { success, passed, total, test_results: [...] }
          // or { success, passed, total, results: [...] }
          const testArray = testResult.test_results || testResult.results || [];
          
          if (Array.isArray(testArray) && testArray.length > 0) {
            // Map backend test format to component format
            // Backend test has 'isSuccessful' field already from CodeExecutionService
            tests = testArray.map(test => ({
              ...test,
              isSuccessful: test.isSuccessful !== undefined ? test.isSuccessful : (test.pass || false),
              function_call: test.function_call || '',
              expected_output: test.expected_output !== undefined && test.expected_output !== null
                ? test.expected_output  // Preserve original type (don't convert to string)
                : 'None',
              actual_output: test.actual_output !== undefined && test.actual_output !== null
                ? test.actual_output  // Preserve original type (don't convert to string)
                : null,  // Keep null to let template handle it
              error: test.error || null
            }));
            // Variation is correct if all tests passed (using backend field names)
            correct = testResult.testsPassed === testResult.totalTests && testResult.totalTests > 0;
          } 
          // Handle direct array format (legacy or test data)
          else if (Array.isArray(testResult)) {
            // Legacy format - direct array of tests
            tests = testResult.map(test => ({
              ...test,
              isSuccessful: test.isSuccessful || test.pass || false
            }));
            correct = tests.every(test => test.isSuccessful);
          }
        }
        
        return {
          content: code,
          correct: correct,
          tests: tests
        };
      });
      log.debug('SLIDES', { slideResults });
      log.debug('Test Results Raw', { testResults: this.testResults });
      if (this.testResults.length > 0) {
        log.debug('First Test Result Structure', { 
          firstResult: this.testResults[0],
          hasResults: !!this.testResults[0].results,
          hasTestResults: !!this.testResults[0].test_results
        });
      }
      return slideResults;
    },
    overallProgressPercent(): number {
      if (this.slides.length === 0) {return 0;}
      const totalTests = this.slides.reduce((sum, slide) => sum + slide.tests.length, 0);
      const passingTests = this.slides.reduce((sum, slide) => 
        sum + slide.tests.filter(test => test.isSuccessful).length, 0);
      return totalTests > 0 ? (passingTests / totalTests) * 100 : 0;
    },
    passingTests(): number {
      return this.slides.reduce((sum, slide) => 
        sum + slide.tests.filter(test => test.isSuccessful).length, 0);
    },
    totalTests(): number {
      return this.slides.reduce((sum, slide) => sum + slide.tests.length, 0);
    },
    passingTestsForCurrentSlide(): TestCase[] {
      if (this.slides.length === 0 || !this.slides[this.currentSlide]) {return [];}
      return this.slides[this.currentSlide].tests.filter(test => test.isSuccessful);
    },
    failingTestsForCurrentSlide(): TestCase[] {
      if (this.slides.length === 0 || !this.slides[this.currentSlide]) {return [];}
      return this.slides[this.currentSlide].tests.filter(test => !test.isSuccessful);
    },
  },
  watch: {
    showAttemptDropdown(newVal) {
      if (newVal) {
        this.positionDropdown();
        // Focus first menu item when dropdown opens
        this.$nextTick(() => {
          const firstMenuItem = this.$refs.firstMenuItem as HTMLElement | HTMLElement[] | undefined;
          if (firstMenuItem) {
            const element = Array.isArray(firstMenuItem) ? firstMenuItem[0] : firstMenuItem;
            element?.focus();
          }
        });
      }
    },
    slides: {
      handler() {
        this.updateSolutionCode();
      },
      deep: true,
    },
    submissionHistory: {
      handler(newHistory) {
        this.initializeSubmissionHistory();
      },
      deep: true,
      immediate: true
    }
  },
  mounted() {
    this.initializeSubmissionHistory();
    this.updateSolutionCode();

    // Add click outside listener
    document.addEventListener('click', this.handleClickOutside);
  },

  beforeUnmount() {
    // Clean up event listener
    document.removeEventListener('click', this.handleClickOutside);
  },
  methods: {
    // Export utility functions to template
    formatTestValue,
    isMissingValue,
    getValueDisplayClass,

    // Initialize submission history data
    initializeSubmissionHistory(): void {

      if (this.submissionHistory && this.submissionHistory.length > 0) {
        this.totalAttempts = this.submissionHistory.length;
        // Find current attempt (most recent by default)
        const currentAttempt = this.submissionHistory[0];
        if (currentAttempt) {
          this.currentSubmissionId = currentAttempt.id;
          this.currentAttemptNumber = currentAttempt.attempt_number;
          this.currentAttemptScore = currentAttempt.score;
        }
        // Find best attempt
        const bestAttempt = this.submissionHistory.find(a => a.is_best);
        if (bestAttempt) {
          this.bestAttemptId = bestAttempt.id;
        }
      }
    },

    // Core navigation methods
    updateSolutionCode(): void {
      if (this.slides.length === 0) {
        this.currentSlideContents = "";
      } else {
        this.currentSlideContents = this.slides[this.currentSlide].content;
      }
    },
    goToSlide(index: number): void {
      this.currentSlide = index;
      this.updateSolutionCode();
      this.$emit('solution-changed', index);
    },
    
    // Status helpers
    getSlideStatus(slide: Slide): string {
      if (slide.tests.length === 0) {return 'pending';}
      if (slide.correct) {return 'passing';}
      return 'failing';
    },
    getSlideIcon(slide: Slide): string {
      if (slide.tests.length === 0) {return '⏳';}
      if (slide.correct) {return '✓';}
      return '✗';
    },
    
    // Debug functionality
    openPyTutor(testCase: TestCase): void {
      if (!testCase) {return;}
      
      const solutionCode = this.slides[this.currentSlide].content;
      const formattedCode = PythonTutorService.formatCodeWithTest(solutionCode, testCase);
      
      // Generate embed URL using the service
      this.pythonTutorUrl = PythonTutorService.generateEmbedUrl(formattedCode);
      this.showModal = true;
    },

    // Attempt selector methods
    loadAttempt(attempt: any): void {
      this.showAttemptDropdown = false;
      this.currentSubmissionId = attempt.id;
      this.currentAttemptNumber = attempt.attempt_number;
      this.currentAttemptScore = attempt.score;

      // Emit event to parent to load this attempt's data
      this.$emit('load-attempt', attempt);
    },

    positionDropdown(): void {
      this.$nextTick(() => {
        const dropdown = this.$refs.dropdownPanel as HTMLElement;
        if (!dropdown || !this.$el) {return;}

        const trigger = this.$el.querySelector('.attempt-dropdown-trigger') as HTMLElement;
        if (!trigger) {return;}

        const rect = trigger.getBoundingClientRect();
        dropdown.style.top = `${rect.bottom + 4}px`;
        dropdown.style.left = `${rect.right - dropdown.offsetWidth}px`;
      });
    },

    handleClickOutside(event: MouseEvent): void {
      if (!this.showAttemptDropdown || !this.$el) {return;}

      const dropdown = this.$refs.dropdownPanel as HTMLElement;
      const trigger = this.$el.querySelector('.attempt-dropdown-trigger') as HTMLElement;

      // Check if click was outside both dropdown and trigger
      if (dropdown && trigger &&
          !dropdown.contains(event.target as Node) &&
          !trigger.contains(event.target as Node)) {
        this.showAttemptDropdown = false;
      }
    },

    jumpToBestAttempt(): void {
      const bestAttempt = this.submissionHistory.find(a => a.is_best);
      if (bestAttempt) {
        this.loadAttempt(bestAttempt);
      }
    },

    getScoreClass(score: number): string {
      if (score >= 100) {return 'score-perfect';}
      if (score >= 80) {return 'score-good';}
      if (score >= 60) {return 'score-partial';}
      return 'score-low';
    },

    formatTime(timestamp: string): string {
      const date = new Date(timestamp);
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      const hours = Math.floor(diff / (1000 * 60 * 60));

      if (hours < 1) {
        const minutes = Math.floor(diff / (1000 * 60));
        return `${minutes}m ago`;
      }
      if (hours < 24) {
        return `${hours}h ago`;
      }
      const days = Math.floor(hours / 24);
      if (days < 7) {
        return `${days}d ago`;
      }

      // Format as date for older attempts
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
      });
    },

    formatComprehensionLevel(level: string): string {
      if (level === 'high-level') {return '🎯 High';}
      if (level === 'low-level') {return '📚 Low';}
      return level;
    },

    getScoreIcon(score: number): string {
      if (score >= 100) {return '✓';}
      if (score >= 80) {return '✓';}
      if (score >= 60) {return '~';}
      return '✗';
    },

    // Keyboard navigation for dropdown
    closeDropdownAndFocusTrigger(): void {
      this.showAttemptDropdown = false;
      this.$nextTick(() => {
        if (!this.$el) {return;}
        const trigger = this.$el.querySelector('.attempt-dropdown-trigger') as HTMLElement;
        trigger?.focus();
      });
    },

    focusNextItem(event: KeyboardEvent): void {
      const currentElement = event.target as HTMLElement;
      const nextElement = currentElement.nextElementSibling as HTMLElement;
      if (nextElement && nextElement.classList.contains('attempt-item-minimal')) {
        nextElement.focus();
      }
    },

    focusPreviousItem(event: KeyboardEvent): void {
      const currentElement = event.target as HTMLElement;
      const previousElement = currentElement.previousElementSibling as HTMLElement;
      if (previousElement && previousElement.classList.contains('attempt-item-minimal')) {
        previousElement.focus();
      }
    },

    handleHomeKey(event: KeyboardEvent): void {
      event.preventDefault();
      if (!this.$el) {return;}
      const attemptList = this.$el.querySelectorAll('.attempt-item-minimal');
      if (attemptList.length > 0) {
        (attemptList[0] as HTMLElement).focus();
      }
    },

    handleEndKey(event: KeyboardEvent): void {
      event.preventDefault();
      if (!this.$el) {return;}
      const attemptList = this.$el.querySelectorAll('.attempt-item-minimal');
      if (attemptList.length > 0) {
        (attemptList[attemptList.length - 1] as HTMLElement).focus();
      }
    },
  },
});
</script>

<style scoped>
/* Main Container - Simple Grid Layout */
.feedback-container {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  position: relative;
  min-height: 600px; /* Prevent layout shifts during navigation */
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
  font-size: 3rem; /* Large size for emphasis, similar to other empty states */
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

/* User Prompt Section */
.user-prompt-section {
  background: var(--color-bg-panel);
  padding-top: var(--spacing-md);
}

/* Section Dividers - Clean Header Bar Style */
.section-divider {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-bg-hover);
  font-size: var(--font-size-sm);
  font-family: Inter, system-ui, -apple-system, sans-serif;
  gap: var(--spacing-md);
}

.divider-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  flex: 0 1 auto;
}

.divider-icon {
  font-size: var(--font-size-sm);
  opacity: 0.7;
  flex-shrink: 0;
}

.divider-title {
  font-weight: 600;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.divider-separator {
  color: var(--color-text-muted);
  opacity: 0.5;
  flex-shrink: 0;
}

.divider-description {
  font-weight: 400;
  color: var(--color-text-muted);
  opacity: 0.7;
}

.info-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: var(--radius-circle);
  background: rgba(102, 126, 234, 0.15);
  color: var(--color-text-primary);
  cursor: help;
  transition: var(--transition-fast);
  flex-shrink: 0;
  margin-left: auto;
}

.info-icon:hover {
  background: rgba(102, 126, 234, 0.25);
  transform: scale(1.1);
}

.info-icon svg {
  display: block;
  stroke-width: 2;
}


.submission-header {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-bg-hover);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 600;
  font-family: Inter, system-ui, -apple-system, sans-serif;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.submission-icon {
  font-size: var(--font-size-sm);
  opacity: 0.7;
}

.submission-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.prompt-content {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  background: var(--color-bg-input);
  padding: var(--spacing-sm) var(--spacing-md);
  margin: var(--spacing-sm) var(--spacing-lg) var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-xs);
  border-left: 3px solid var(--color-bg-border);
  max-height: 80px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* Subtle scrollbar */
.prompt-content::-webkit-scrollbar {
  width: 3px;
}

.prompt-content::-webkit-scrollbar-track {
  background: transparent;
}

.prompt-content::-webkit-scrollbar-thumb {
  background: var(--color-bg-border);
  border-radius: 3px;
  opacity: 0.5;
}

.prompt-content:hover::-webkit-scrollbar-thumb {
  opacity: 1;
}

/* Header - Seamless Integration */
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

/* Attempt Selector - Ultra-Minimal */
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

.dropdown-arrow {
  font-size: 10px;
  opacity: 0.4;
  transition: transform 0.2s;
}

.attempt-dropdown-trigger.is-active .dropdown-arrow {
  transform: rotate(180deg);
}

/* Dropdown Panel - Ultra-Thin */
.attempt-dropdown-panel {
  position: fixed; /* Fixed positioning to escape overflow:hidden */
  width: 240px;
  max-height: 200px;
  background: var(--color-bg-panel);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 99999; /* Very high z-index */
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

/* Ultra-Thin Attempt Items */
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

/* Content Grid */
.feedback-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  position: relative; /* Create stacking context */
  z-index: 1; /* Below dropdown */
}

/* Solution Timeline */
.solution-timeline {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-sm);
  background: var(--color-bg-panel);
  border-bottom: 1px solid var(--color-bg-input);
  overflow-x: auto;
}

.timeline-node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm);
  min-width: 50px;
  cursor: pointer;
  transition: var(--transition-fast);
  background: transparent;
  border: none;
  font-family: inherit;
}

.timeline-node:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.timeline-node:focus:not(:focus-visible) {
  outline: none;
}

.timeline-node:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}


.node-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-circle);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  font-weight: 700;
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
}

.node-icon {
  font-size: var(--font-size-sm);
  font-weight: 600;
}

/* Timeline States */
.timeline-node[data-current="true"] .node-number {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-text-primary);
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2);
}

.timeline-node[data-status="passing"] .node-number {
  background: var(--color-success-bg);
  border-color: var(--color-success);
  color: var(--color-success-text);
}

.timeline-node[data-status="failing"] .node-number {
  background: var(--color-error-bg);
  border-color: var(--color-error);
  color: var(--color-error-text);
}

.timeline-node:hover .node-number {
  transform: scale(1.1);
}

/* Code Section */
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

/* Test Summary Bar */
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

/* Test Results - Native Collapsible */
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
  border-color: rgba(220, 53, 69, 0.3);
}

.test-item.passing {
  border-color: rgba(76, 175, 80, 0.3);
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
  background: #1976d2;
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
  .header-title {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .solution-timeline {
    padding: var(--spacing-md);
    gap: var(--spacing-md);
  }
  
  .node-number {
    width: 36px;
    height: 36px;
    font-size: var(--font-size-xs);
  }
  
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

/* Comprehension Section - inherits all styling from parent test-results */

.test-group-header.comprehension {
  border-left: 4px solid var(--color-primary);
}

.comprehension-placeholder {
  padding: var(--spacing-sm) 0 0 0;
  text-align: center;
}

.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
}

.placeholder-icon {
  font-size: var(--font-size-xl);
  opacity: 0.6;
}

.placeholder-message {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin: 0;
}

/* Navigation Skeleton Styles - match actual content dimensions to prevent shifts */
.navigation-skeleton-panel {
  padding: var(--spacing-lg);
  background: var(--color-bg-panel);
  min-height: 600px; /* Match feedback-container min-height */
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

/* Skeleton elements with shimmer animation */
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

.skeleton-text.short {
  width: 60%;
}

.skeleton-code-block {
  height: 300px; /* Match actual Editor height */
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.08) 50%,
    rgba(255, 255, 255, 0.03) 100%
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
    rgba(255, 255, 255, 0.05) 0%,
    rgba(255, 255, 255, 0.1) 50%,
    rgba(255, 255, 255, 0.05) 100%
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

/* Slower shimmer animation for subtlety */

/* Navigation transition - removed opacity dimming for smoother UX */
.feedback-container.is-navigating {
  /* Opacity removed - rely on skeleton/progress bar for loading indication */
}
</style>
