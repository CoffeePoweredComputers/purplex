<template>
  <div class="segmentation-section" v-if="segmentation && segmentation.segments">
    <!-- Section Header -->
    <div class="section-header">
      <div class="header-content">
        <span class="section-icon">🧠</span>
        <div class="header-text">
          <h3 class="section-title">Comprehension Analysis</h3>
          <p class="section-subtitle">How you understood the code</p>
        </div>
      </div>
    </div>

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
      class="segment-mapping-container"
      :open="isExpanded"
      @toggle="onToggle"
    >
      <summary class="mapping-toggle">
        <span class="toggle-icon" :class="{ expanded: isExpanded }">▶</span>
        <span class="toggle-text">View Segment Analysis</span>
        <div class="toggle-badges">
          <span class="segment-badge">
            {{ segmentation.segment_count }} segment{{ segmentation.segment_count !== 1 ? 's' : '' }}
          </span>
          <span class="level-badge" :class="levelBadgeClass">
            {{ formatLevel(segmentation.comprehension_level) }}
          </span>
        </div>
      </summary>
      
      <div class="mapping-content">
        <SegmentMapping 
          :segments="segmentation.segments"
          :reference-code="referenceCode"
        />
      </div>
    </details>

    <!-- Educational Tips -->
    <div class="educational-tips" v-if="showTips">
      <div class="tips-header">
        <span class="tips-icon">💡</span>
        <span class="tips-title">Tips for Better Comprehension</span>
      </div>
      <div class="tips-content">
        <ul class="tips-list">
          <li v-for="tip in getTips()" :key="tip" class="tip-item">
            {{ tip }}
          </li>
        </ul>
      </div>
    </div>
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
    showTips: {
      type: Boolean,
      default: true
    }
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
    
    getTips() {
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return [
            'Great job! You understand the high-level purpose',
            'This approach shows strong problem-solving skills',
            'Keep focusing on the "why" rather than the "how"'
          ];
        case 'transitional':
          return [
            'Good understanding! You identified the main steps',
            'Try to be even more concise in your explanations',
            'Focus on the overall goal and 2-3 key operations'
          ];
        case 'multi_structural':
          return [
            'You have good attention to detail',
            'Try to step back and see the bigger picture',
            'Ask yourself: "What is this code trying to accomplish?"',
            'Aim for 1-2 high-level descriptions instead of line-by-line'
          ];
        default:
          return [];
      }
    },
    
    onToggle(event) {
      this.isExpanded = event.target.open;
    }
  }
};
</script>

<style scoped>
.segmentation-section {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  margin: var(--spacing-md) 0;
  overflow: hidden;
  border: 1px solid var(--color-bg-border);
  animation: slideInUp 0.4s ease-out;
}

/* Section Header */
.section-header {
  background: var(--color-bg-hover);
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-input);
}

.header-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.section-icon {
  font-size: var(--font-size-xl);
}

.header-text {
  flex: 1;
}

.section-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
}

.section-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0;
}

/* Feedback */
.segmentation-feedback {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-input);
}

.feedback-content {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-start;
}

.feedback-icon {
  font-size: var(--font-size-lg);
  flex-shrink: 0;
  margin-top: var(--spacing-xs);
}

.feedback-text {
  flex: 1;
}

.feedback-message {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
  line-height: 1.5;
}

.feedback-explanation {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

/* Feedback level colors */
.feedback-relational {
  background: linear-gradient(135deg, 
    rgba(76, 175, 80, 0.1) 0%, 
    rgba(76, 175, 80, 0.05) 100%
  );
  border-left: 4px solid var(--color-success);
}

.feedback-transitional {
  background: linear-gradient(135deg, 
    rgba(255, 193, 7, 0.1) 0%, 
    rgba(255, 193, 7, 0.05) 100%
  );
  border-left: 4px solid var(--color-warning);
}

.feedback-multi-structural {
  background: linear-gradient(135deg, 
    rgba(220, 53, 69, 0.1) 0%, 
    rgba(220, 53, 69, 0.05) 100%
  );
  border-left: 4px solid var(--color-error);
}

/* Collapsible Mapping */
.segment-mapping-container {
  background: var(--color-bg-panel);
}

.mapping-toggle {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  cursor: pointer;
  list-style: none;
  transition: var(--transition-fast);
  border-bottom: 1px solid var(--color-bg-input);
  user-select: none;
}

.mapping-toggle:hover {
  background: var(--color-bg-hover);
}

.toggle-icon {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  transition: transform var(--transition-fast);
}

.toggle-icon.expanded {
  transform: rotate(90deg);
}

.toggle-text {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
  flex: 1;
}

.toggle-badges {
  display: flex;
  gap: var(--spacing-sm);
}

.segment-badge,
.level-badge {
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.segment-badge {
  background: var(--color-bg-input);
  color: var(--color-text-muted);
}

.level-badge.badge-relational {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.level-badge.badge-transitional {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.level-badge.badge-multi-structural {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}

.mapping-content {
  padding: var(--spacing-lg);
  background: var(--color-bg-dark);
}

/* Educational Tips */
.educational-tips {
  background: var(--color-bg-hover);
  padding: var(--spacing-lg);
  border-top: 1px solid var(--color-bg-input);
}

.tips-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.tips-icon {
  font-size: var(--font-size-base);
}

.tips-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.tips-content {
  margin-left: calc(var(--font-size-base) + var(--spacing-sm));
}

.tips-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.tip-item {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--spacing-sm);
  position: relative;
  padding-left: var(--spacing-lg);
}

.tip-item::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--color-primary-gradient-start);
  font-weight: 700;
}

.tip-item:last-child {
  margin-bottom: 0;
}

/* Animations */
@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

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
  
  .educational-tips {
    padding: var(--spacing-md);
  }
}
</style>