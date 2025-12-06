<template>
  <div
    v-if="isVisible"
    class="modal-overlay"
    @click="$emit('close')"
  >
    <div
      class="modal-content"
      @click.stop
    >
      <!-- Header -->
      <div class="modal-header">
        <div class="header-info">
          <h2 class="modal-title">
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
            @click="$emit('download', submission)"
          >
            Download
          </button>
          <button
            class="close-btn"
            aria-label="Close"
            @click="$emit('close')"
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
                    <div class="hint-type-name">{{ formatHintType(hint.hint_type) }}</div>
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
</template>

<script>
import Editor from '@/features/editor/Editor.vue';
import { formatTestValue, getValueDisplayClass, isMissingValue } from '@/utils/testValueFormatter';
import { log } from '@/utils/logger';

export default {
  name: 'ViewSubmissionModal',
  components: {
    Editor
  },
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    submission: {
      type: Object,
      default: null
    }
  },
  emits: ['close', 'download'],
  data() {
    return {
      currentVariationIndex: 0
    };
  },
  computed: {
    hasVariations() {
      // For submission history endpoint: check data.variations
      // Consider it has variations if there's at least 1 variation (EiPL submissions)
      if (this.submission?.data?.variations?.length >= 1) {
        return true;
      }

      // For admin endpoint: check code_variations array
      if (this.submission?.code_variations?.length > 1) {
        return true;
      }

      // For progress endpoint: check results/variations arrays
      return this.submission?.results?.length > 1 ||
             (this.submission?.variations?.length > 1) ||
             (this.submission?.total_variations > 1);
    },

    totalVariationsCount() {
      // Submission history endpoint: count data.variations
      if (this.submission?.data?.variations?.length) {
        return this.submission.data.variations.length;
      }

      // Admin endpoint: count code_variations
      if (this.submission?.code_variations?.length) {
        return this.submission.code_variations.length;
      }

      // Progress endpoint: use existing fields
      return this.submission?.total_variations ||
             this.submission?.results?.length ||
             this.submission?.variations?.length ||
             1;
    },

    passingVariationsCount() {
      // Submission history endpoint: count data.variations with all tests passed
      if (this.submission?.data?.variations?.length) {
        return this.submission.data.variations.filter(v =>
          v.passed_all_tests || (v.tests_passed === v.total_tests && v.total_tests > 0)
        ).length;
      }

      // Admin endpoint: count code_variations with perfect scores
      if (this.submission?.code_variations?.length) {
        return this.submission.code_variations.filter(cv =>
          cv.tests_passed === cv.tests_total && cv.tests_total > 0
        ).length;
      }

      // Progress endpoint: use existing fields
      return this.submission?.passing_variations ||
             (this.submission?.results?.filter(r => r.success)?.length) ||
             0;
    },

    currentVariationData() {
      if (!this.hasVariations) {
        // For single submissions, aggregate all test results
        if (this.submission?.test_results) {
          const passed = this.submission.test_results.filter(t => t.passed || t.isSuccessful).length;
          return {
            testsPassed: passed,
            totalTests: this.submission.test_results.length,
            success: passed === this.submission.test_results.length
          };
        }
        return null;
      }

      // Submission history endpoint: get from data.variations
      if (this.submission?.data?.variations?.length) {
        const variation = this.submission.data.variations[this.currentVariationIndex];
        if (variation) {
          return {
            testsPassed: variation.tests_passed,
            totalTests: variation.total_tests,
            success: variation.passed_all_tests || (variation.tests_passed === variation.total_tests && variation.total_tests > 0)
          };
        }
      }

      // Admin endpoint: get from code_variations
      if (this.submission?.code_variations?.length) {
        const variation = this.submission.code_variations[this.currentVariationIndex];
        if (variation) {
          return {
            testsPassed: variation.tests_passed,
            totalTests: variation.tests_total,
            success: variation.tests_passed === variation.tests_total && variation.tests_total > 0
          };
        }
      }

      // Progress endpoint: get from results array
      return this.submission?.results?.[this.currentVariationIndex] || null;
    },

    currentVariationStatusClass() {
      if (!this.currentVariationData) {return '';}
      return this.currentVariationData.success ? 'success' : 'partial';
    },

    currentCodeToDisplay() {
      if (this.hasVariations) {
        // Submission history endpoint: get from data.variations
        if (this.submission?.data?.variations?.length) {
          const variation = this.submission.data.variations[this.currentVariationIndex];
          return variation?.code || '';
        }

        // Admin endpoint: get from code_variations
        if (this.submission?.code_variations?.length) {
          const variation = this.submission.code_variations[this.currentVariationIndex];
          return variation?.code || '';
        }

        // Progress endpoint: get from variations array
        if (this.submission?.variations) {
          return this.submission.variations[this.currentVariationIndex];
        }
      }

      // Check for submission history endpoint data structure
      if (this.submission?.data?.processed_code) {
        return this.submission.data.processed_code;
      }

      return this.submission?.processed_code || this.submission?.raw_input || '';
    },

    currentTestResults() {
      if (!this.hasVariations) {
        // For single submissions, return the test_results directly
        // First check if it's from submission history endpoint
        if (this.submission?.data?.test_results) {
          return this.submission.data.test_results;
        }
        return this.submission?.test_results || [];
      }

      // Submission history endpoint: get test results from variation data
      if (this.submission?.data?.variations?.length) {
        const variation = this.submission.data.variations[this.currentVariationIndex];
        return variation?.test_results || [];
      }

      // Admin endpoint: get per-variation test results
      if (this.submission?.code_variations?.length) {
        const variation = this.submission.code_variations[this.currentVariationIndex];
        return variation?.test_results || [];
      }

      // Progress endpoint: get test results for current variation
      const variationData = this.submission?.results?.[this.currentVariationIndex];
      return variationData?.test_results || variationData?.results || [];
    },

    currentPassingTests() {
      return this.currentTestResults.filter(t => t.passed || t.isSuccessful).length;
    },

    currentFailingTests() {
      return this.currentTestResults.filter(t => !(t.passed || t.isSuccessful)).length;
    },

    currentPassingTestsList() {
      return this.currentTestResults.filter(t => t.passed || t.isSuccessful);
    },

    currentFailingTestsList() {
      return this.currentTestResults.filter(t => !(t.passed || t.isSuccessful));
    },

    hasHintsActivated() {
      return this.submission?.hints_activated?.length > 0;
    },

    hintsActivatedCount() {
      return this.submission?.hints_activated?.length || 0;
    },

  },
  watch: {
    submission(newVal) {
      // Reset variation index when submission changes
      this.currentVariationIndex = 0;
    }
  },
  methods: {
    getScoreClass(score) {
      if (score >= 100) {return 'success';}
      if (score >= 60) {return 'warning';}
      return 'error';
    },

    getStatusClass(status) {
      const s = status?.toLowerCase();
      if (s === 'passed' || s === 'complete') {return 'success';}
      if (s === 'partial') {return 'warning';}
      if (s === 'failed' || s === 'error') {return 'error';}
      return '';
    },

    formatDate(dateString) {
      if (!dateString) {return 'Unknown';}
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    },

    formatComprehension(level) {
      if (!level) {return 'Not evaluated';}
      if (level === 'high_level' || level === 'high-level') {return 'High Level';}
      if (level === 'low_level' || level === 'low-level') {return 'Low Level';}
      return level;
    },

    formatTimeSpent(seconds) {
      if (!seconds) {return 'N/A';}
      const mins = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60);
      return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
    },

    formatValue(value) {
      return formatTestValue(value);
    },

    formatTestValue,
    isMissingValue,
    getValueDisplayClass,

    prevVariation() {
      if (this.currentVariationIndex > 0) {
        this.currentVariationIndex--;
      }
    },

    nextVariation() {
      if (this.currentVariationIndex < this.totalVariationsCount - 1) {
        this.currentVariationIndex++;
      }
    },

    formatTestCall(test) {
      // Format the test description as a function call if possible
      if (test.function_call) {
        return test.function_call;
      }
      if (test.description) {
        // Try to extract function call from description
        const match = test.description.match(/([a-zA-Z_][a-zA-Z0-9_]*\([^)]*\))/);
        if (match) {return match[1];}
        return test.description;
      }
      if (test.inputs !== undefined) {
        return `test(${this.formatValue(test.inputs)})`;
      }
      return `Test Case`;
    },

    async copyCode(code) {
      if (!code) {
        code = this.currentCodeToDisplay;
      }
      if (!code) {return;}

      try {
        await navigator.clipboard.writeText(code);
        // Could show a toast notification here
      } catch (err) {
        log.error('Failed to copy to clipboard', { error: err });
      }
    },

    formatHintType(hintType) {
      const typeMap = {
        'variable_fade': 'Variable Fade',
        'subgoal_highlight': 'Subgoal Highlighting',
        'suggested_trace': 'Suggested Trace'
      };
      return typeMap[hintType] || hintType;
    },

    formatTriggerType(triggerType) {
      const triggerMap = {
        'manual': 'Manually activated',
        'auto_attempts': 'Auto (attempts)',
        'auto_time': 'Auto (time)',
        'instructor': 'Instructor provided'
      };
      return triggerMap[triggerType] || triggerType;
    },

    getHintIcon(hintType) {
      const iconMap = {
        'variable_fade': '🔤',
        'subgoal_highlight': '🎯',
        'suggested_trace': '🔍'
      };
      return iconMap[hintType] || '💡';
    },

    formatHintTime(timestamp) {
      if (!timestamp) {return 'Unknown';}
      return this.formatDate(timestamp);
    }
  }
};
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