<template>
  <div class="segmentation-wrapper" v-if="segmentation && segmentation.segments">
    <!-- Comprehension Analysis Results -->
    <details class="test-group" open>
      <summary class="test-group-header comprehension">
        <span class="group-icon">▶</span>
        Comprehension Analysis
      </summary>
      <div class="segmentation-content">

    <!-- Progress Bar -->
    <SegmentationProgressBar 
      :segment-count="segmentation.segment_count"
      :comprehension-level="segmentation.comprehension_level"
      :threshold="threshold"
      :max-segments="8"
    />
    
    <!-- Feedback Message -->
    <div class="segmentation-feedback" :class="feedbackClass">
      <div class="feedback-content">
        <span class="feedback-icon">{{ getFeedbackIcon() }}</span>
        <div class="feedback-text">
          <p class="feedback-message">{{ segmentation.feedback }}</p>
          <p class="feedback-explanation">{{ getExplanation() }}</p>
        </div>
      </div>
    </div>
    
    <!-- Segment Mapping (Collapsible) -->
    <details 
      class="segment-details"
      :open="isExpanded"
      @toggle="onToggle"
    >
      <summary class="segment-summary">
        <span class="detail-icon" :class="{ expanded: isExpanded }">▶</span>
        <span class="detail-text">View Segment Analysis</span>
        <div class="segment-badges">
          <span class="badge-count">
            {{ segmentation.segment_count }} segment{{ segmentation.segment_count !== 1 ? 's' : '' }}
          </span>
          <span class="badge-level" :class="levelBadgeClass">
            {{ formatLevel(segmentation.comprehension_level) }}
          </span>
        </div>
      </summary>
      
      <div class="segment-detail-content">
        <SegmentMapping 
          :segments="segmentation.segments"
          :reference-code="referenceCode"
        />
      </div>
    </details>

      </div>
    </details>
  </div>
</template>

<script>
import SegmentationProgressBar from './SegmentationProgressBar.vue';
import SegmentMapping from './SegmentMapping.vue';

export default {
  name: 'SegmentationSection',
  components: {
    SegmentationProgressBar,
    SegmentMapping
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
  },
  data() {
    return {
      isExpanded: false
    };
  },
  computed: {
    feedbackClass() {
      return `feedback-${this.segmentation.comprehension_level.replace('_', '-')}`;
    },
    
    levelBadgeClass() {
      return `badge-${this.segmentation.comprehension_level.replace('_', '-')}`;
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
    
    getExplanation() {
      const count = this.segmentation.segment_count;
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return `You focused on the overall purpose (${count} segment${count !== 1 ? 's' : ''}). This shows strong conceptual understanding.`;
        case 'transitional':
          return `You identified key steps (${count} segments). Good balance between detail and big picture.`;
        case 'multi_structural':
          return `You provided line-by-line detail (${count} segments). Try focusing on the main goal instead.`;
        default:
          return '';
      }
    },
    
    
    onToggle(event) {
      this.isExpanded = event.target.open;
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

/* Feedback - simplified styling */
.segmentation-feedback {
  padding: var(--spacing-sm) var(--spacing-md);
  margin: 0;
  border-radius: var(--radius-xs);
}

.feedback-content {
  display: flex;
  gap: var(--spacing-sm);
  align-items: flex-start;
}

.feedback-icon {
  font-size: var(--font-size-base);
  flex-shrink: 0;
}

.feedback-text {
  flex: 1;
}

.feedback-message {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
  line-height: 1.5;
}

.feedback-explanation {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

/* Feedback level colors - simplified */
.feedback-relational {
  background: var(--color-success-bg);
  border-left: 3px solid var(--color-success);
}

.feedback-transitional {
  background: var(--color-warning-bg);
  border-left: 3px solid var(--color-warning);
}

.feedback-multi-structural {
  background: var(--color-error-bg);
  border-left: 3px solid var(--color-error);
}

/* Segment Details - inner collapsible */
.segment-details {
  margin: var(--spacing-sm) 0 0 0;
}

.segment-summary {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  cursor: pointer;
  list-style: none;
  font-size: var(--font-size-sm);
  background: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  transition: var(--transition-fast);
}

.segment-summary:hover {
  background: var(--color-bg-input);
}

.detail-icon {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  transition: transform var(--transition-fast);
}

.detail-icon.expanded {
  transform: rotate(90deg);
}

.detail-text {
  font-weight: 600;
  color: var(--color-text-primary);
  flex: 1;
}

.segment-badges {
  display: flex;
  gap: var(--spacing-sm);
}

.badge-count,
.badge-level {
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.badge-count {
  background: var(--color-bg-input);
  color: var(--color-text-muted);
}

.badge-level.badge-relational {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.badge-level.badge-transitional {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.badge-level.badge-multi-structural {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}

.segment-detail-content {
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  margin-top: var(--spacing-sm);
}


/* Removed animations for consistency */

/* Responsive */
@media (max-width: 768px) {
  .section-header {
    padding: var(--spacing-md);
  }
  
  .header-content {
    gap: var(--spacing-sm);
  }
  
  .section-title {
    font-size: var(--font-size-base);
  }
  
  .segmentation-feedback {
    padding: var(--spacing-md);
  }
  
  .feedback-content {
    gap: var(--spacing-sm);
  }
  
  .mapping-toggle {
    padding: var(--spacing-md);
    gap: var(--spacing-sm);
  }
  
  .toggle-badges {
    flex-direction: column;
    gap: var(--spacing-xs);
  }
  
  .mapping-content {
    padding: var(--spacing-md);
  }
  
}
</style>