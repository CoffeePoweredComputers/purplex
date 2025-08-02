<template>
  <div class="segmentation-wrapper" v-if="segmentation && segmentation.segments">
    <!-- Comprehension Analysis Results -->
    <details class="test-group" open>
      <summary class="test-group-header comprehension">
        <span class="group-icon">▶</span>
        Comprehension Analysis
        <span v-if="segmentation.passed !== undefined" class="status-indicator" :class="segmentation.passed ? 'passed' : 'failed'">
          {{ segmentation.passed ? '✓ Passed' : '✗ Failed' }}
        </span>
      </summary>
      <div class="segmentation-content">

    <!-- Progress Bar -->
    <SegmentationProgressBar 
      :segment-count="segmentation.segment_count"
      :comprehension-level="segmentation.comprehension_level"
      :threshold="threshold"
      :max-segments="8"
    />
    
    <!-- Feedback Card with Integrated Action -->
    <div class="feedback-card" :class="feedbackCardClass">
      <div class="feedback-inner">
        <div class="feedback-main">
          <div class="feedback-header">
            <span class="feedback-icon">{{ getFeedbackIcon() }}</span>
            <span class="feedback-title">
              {{ formatLevel(segmentation.comprehension_level) }} understanding!
            </span>
          </div>
          <p class="feedback-explanation">{{ getExplanation() }}</p>
        </div>
        <button 
          class="analysis-action"
          @click="showSegmentAnalysisModal"
          :aria-label="`View detailed analysis of your understanding`"
        >
          <span class="action-text">View Details</span>
          <span class="action-icon">🔍</span>
        </button>
      </div>
    </div>
    
    <!-- Segment Analysis Modal -->
    <SegmentAnalysisModal
      :is-visible="isModalVisible"
      :segmentation="segmentation"
      :reference-code="referenceCode"
      :user-prompt="userPrompt"
      @close="hideSegmentAnalysisModal"
    />

      </div>
    </details>
  </div>
</template>

<script>
import SegmentationProgressBar from './SegmentationProgressBar.vue';
import SegmentAnalysisModal from './SegmentAnalysisModal.vue';

export default {
  name: 'SegmentationSection',
  components: {
    SegmentationProgressBar,
    SegmentAnalysisModal
  },
  props: {
    segmentation: {
      type: Object,
      required: true,
      validator: (value) => {
        return value && 
               typeof value.segment_count === 'number' &&
               typeof value.comprehension_level === 'string' &&
               Array.isArray(value.segments);
      }
    },
    referenceCode: {
      type: String,
      required: true
    },
    threshold: {
      type: Number,
      default: 2
    },
    userPrompt: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      isModalVisible: false
    };
  },
  computed: {
    feedbackCardClass() {
      return `card-${this.segmentation.comprehension_level.replace('_', '-')}`;
    }
  },
  methods: {
    getFeedbackIcon() {
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return '🎯';
        case 'transitional':
          return '👍';
        case 'multi_structural':
          return '🔍';
        default:
          return '📝';
      }
    },
    
    getExplanation() {
      const passedText = this.segmentation.passed !== undefined ? 
        (this.segmentation.passed ? '' : ' To pass, describe the overall purpose in fewer segments.') : '';
      
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return `You focused on the overall purpose with ${this.segmentation.segment_count} segment${this.segmentation.segment_count > 1 ? 's' : ''}. This shows strong conceptual understanding.${passedText}`;
        case 'transitional':
          return `You identified key steps. Good balance between detail and big picture.${passedText}`;
        case 'multi_structural':
          return `You provided ${this.segmentation.segment_count} detailed segments. Try focusing on the main goal instead.${passedText}`;
        default:
          return '';
      }
    },
    
    formatLevel(level) {
      switch (level) {
        case 'relational':
          return 'Excellent';
        case 'transitional':
          return 'Good';
        case 'multi_structural':
          return 'Detailed';
        default:
          return 'Unknown';
      }
    },
    
    
    showSegmentAnalysisModal() {
      this.isModalVisible = true;
    },
    
    hideSegmentAnalysisModal() {
      this.isModalVisible = false;
    }
  }
};
</script>

<style scoped>
/* Wrapper removes extra styling */
.segmentation-wrapper {
  /* No extra styling - inherits from parent */
}

/* Main collapsible group styling */
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

.test-group-header.comprehension {
  border-left: 4px solid var(--color-primary);
}

.status-indicator {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.status-indicator.passed {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.status-indicator.failed {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.group-icon {
  transition: transform 0.2s;
  font-size: var(--font-size-xs);
}

details[open] .group-icon {
  transform: rotate(90deg);
}

.segmentation-content {
  padding: var(--spacing-sm) 0 0 0;
}

/* Removed section header styles - using test-group-header instead */

/* Feedback Card - Hybrid Design */
.feedback-card {
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  padding: var(--spacing-xs);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.1);
}

.feedback-inner {
  display: flex;
  align-items: stretch;
  gap: var(--spacing-xs);
  background: var(--color-bg-panel);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.feedback-main {
  flex: 1;
  padding: var(--spacing-md) var(--spacing-lg);
}

.feedback-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.feedback-icon {
  font-size: var(--font-size-lg);
  flex-shrink: 0;
}

.feedback-title {
  font-size: var(--font-size-base);
  font-weight: 700;
  color: var(--color-text-primary);
}


.feedback-explanation {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

.analysis-action {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  padding: 0 var(--spacing-xl);
  background: var(--color-bg-hover);
  border: none;
  border-left: 1px solid var(--color-bg-border);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-fast);
  min-width: 120px;
}

.analysis-action:hover {
  background: var(--color-primary);
  color: var(--color-text-primary);
}

.analysis-action:active {
  transform: scale(0.98);
}

.action-text {
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.action-icon {
  font-size: var(--font-size-lg);
}

/* Comprehension level card variants - subtle color accents */
.feedback-card.card-relational .feedback-inner {
  border-left: 3px solid var(--color-success);
}

.feedback-card.card-transitional .feedback-inner {
  border-left: 3px solid var(--color-warning);
}

.feedback-card.card-multi-structural .feedback-inner {
  border-left: 3px solid var(--color-error);
}

/* Modal trigger styling handled by SegmentAnalysisButton component */


/* Removed animations for consistency */

/* Responsive */
@media (max-width: 768px) {
  .feedback-card {
    padding: var(--spacing-xs);
  }
  
  .feedback-inner {
    flex-direction: column;
    gap: 0;
  }
  
  .feedback-main {
    padding: var(--spacing-md);
  }
  
  .analysis-action {
    min-width: auto;
    width: 100%;
    flex-direction: row;
    padding: var(--spacing-md);
    border-left: none;
    border-top: 1px solid var(--color-bg-border);
  }
  
  .action-icon {
    font-size: var(--font-size-base);
  }
}
</style>