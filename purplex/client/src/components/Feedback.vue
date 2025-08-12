<template>
  <div class="feedback-container">
    <!-- Static Loading Message -->
    <div
      v-if="isLoading && slides.length === 0"
      class="generating-feedback-panel"
    >
      <div class="generating-content">
        <div class="generating-icon">🤖</div>
        <div class="generating-message">Generating feedback...</div>
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

      <!-- Comprehension Banner -->
      <ComprehensionBanner
        v-if="shouldShowSegmentation && segmentation"
        :segmentation="segmentation"
        :reference-code="referenceCode"
        @show-details="showSegmentAnalysisModal = true"
      />

      <!-- Solution Timeline -->
      <nav class="solution-timeline">
        <div 
          v-for="(slide, index) in slides" 
          :key="index"
          class="timeline-node"
          :data-status="getSlideStatus(slide)"
          :data-current="currentSlide === index"
          :title="`Solution ${index + 1}: ${slide.tests.filter(t => t.isSuccessful).length}/${slide.tests.length} tests`"
          @click="goToSlide(index)"
        >
          <span class="node-number">{{ index + 1 }}</span>
          <span class="node-icon">{{ getSlideIcon(slide) }}</span>
        </div>
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
                  <div>Expected: <code class="expected">{{ test.expected_output }}</code></div>
                  <div>Got: <code class="actual">{{ test.actual_output !== null && test.actual_output !== undefined ? test.actual_output : (test.error || 'No output') }}</code></div>
                </div>
              </div>
              <button
                class="debug-btn"
                @click="openPyTutor(test)"
              >
                🔍
              </button>
            </article>
          </div>
        </details>

        <!-- Passing Tests (Collapsed by default) -->
        <details
          v-if="passingTestsForCurrentSlide.length > 0"
          class="test-group"
        >
          <summary class="test-group-header passing">
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
                <code class="test-call">{{ test.function_call }} → {{ test.expected_output }}</code>
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
import SegmentAnalysisModal from './segmentation/SegmentAnalysisModal.vue';
import { PythonTutorService } from '@/services/pythonTutor.service';
import { log } from '@/utils/logger';

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
}

export default defineComponent({
  components: { 
    Editor,
    PyTutorModal,
    ComprehensionBanner,
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
  },
  data(): ComponentData {
    return {
      showModal: false,
      pythonTutorUrl: '',
      currentSlide: 0,
      currentSlideContents: "",
      currentComprehensionResults: [],
      showSegmentAnalysisModal: false,
    };
  },
  computed: {
    isEiPLProblem(): boolean {
      return this.problemType === 'eipl';
    },
    shouldShowSegmentation(): boolean {
      // Show segmentation section if it's an EiPL problem and segmentation is enabled
      return this.isEiPLProblem && this.segmentationEnabled;
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
          let testArray = testResult.test_results || testResult.results || [];
          
          if (Array.isArray(testArray) && testArray.length > 0) {
            // Map backend test format to component format
            // Backend test has 'isSuccessful' field already from CodeExecutionService
            tests = testArray.map(test => ({
              ...test,
              isSuccessful: test.isSuccessful !== undefined ? test.isSuccessful : (test.pass || false),
              function_call: test.function_call || '',
              expected_output: test.expected_output || '',
              actual_output: test.actual_output !== undefined && test.actual_output !== null 
                ? test.actual_output 
                : (test.error ? `Error: ${test.error}` : 'No output'),
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
    slides: {
      handler() {
        this.updateSolutionCode();
      },
      deep: true,
    },
  },
  mounted() {
    this.updateSolutionCode();
  },
  methods: {
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
  font-size: 48px;
  animation: pulse 2s infinite;
}

.generating-message {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  font-weight: 500;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}

/* User Prompt Section */
.user-prompt-section {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-panel);
  border-bottom: 1px solid var(--color-bg-input);
  border-left: 3px solid var(--color-bg-border);
  transition: border-color var(--transition-fast);
}


.submission-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-sm);
}

.submission-icon {
  font-size: var(--font-size-md);
  opacity: 0.8;
}

.submission-label {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-muted);
}

.prompt-content {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  background: var(--color-bg-input);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-xs);
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

/* Header */
.feedback-header {
  background: var(--color-bg-panel);
}

.section-label {
  text-align: center;
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-muted);
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-bg-input);
}

/* Content Grid */
.feedback-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
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
</style>
