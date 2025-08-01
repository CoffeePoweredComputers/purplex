<template>
  <button
    class="segment-analysis-button"
    :class="{ 'has-preview': showPreview }"
    @click="$emit('click')"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <div class="button-content">
      <span class="button-icon">🔍</span>
      <span class="button-text">View Segment Analysis</span>
      <div class="button-badges">
        <span class="badge-count">
          {{ segmentCount }} segment{{ segmentCount !== 1 ? 's' : '' }}
        </span>
        <span class="badge-level" :class="levelBadgeClass">
          {{ formattedLevel }}
        </span>
      </div>
    </div>
    
    <!-- Hover Preview -->
    <div
      v-if="showPreview && isHovered"
      class="preview-tooltip"
      :class="tooltipPosition"
    >
      <div class="preview-header">
        <span class="preview-icon">{{ getFeedbackIcon() }}</span>
        <span class="preview-title">{{ formattedLevel }} Analysis</span>
      </div>
      <div class="preview-content">
        <p class="preview-feedback">{{ feedback }}</p>
        <div class="preview-segments">
          <div 
            v-for="segment in previewSegments" 
            :key="segment.id"
            class="preview-segment"
          >
            <span class="segment-id">{{ segment.id }}</span>
            <span class="segment-text">{{ segment.text }}</span>
          </div>
        </div>
        <div class="preview-hint">
          <small>Click to open detailed analysis</small>
        </div>
      </div>
    </div>
  </button>
</template>

<script>
export default {
  name: 'SegmentAnalysisButton',
  props: {
    segmentCount: {
      type: Number,
      required: true
    },
    comprehensionLevel: {
      type: String,
      required: true
    },
    feedback: {
      type: String,
      default: ''
    },
    segments: {
      type: Array,
      default: () => []
    },
    showPreview: {
      type: Boolean,
      default: true
    },
    tooltipPosition: {
      type: String,
      default: 'top',
      validator: (value) => ['top', 'bottom', 'left', 'right'].includes(value)
    }
  },
  data() {
    return {
      isHovered: false,
      hoverTimeout: null
    };
  },
  computed: {
    levelBadgeClass() {
      return `badge-${this.comprehensionLevel.replace('_', '-')}`;
    },
    
    formattedLevel() {
      switch (this.comprehensionLevel) {
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
    
    previewSegments() {
      // Show first 3 segments for preview
      return this.segments.slice(0, 3);
    }
  },
  methods: {
    handleMouseEnter() {
      if (this.showPreview) {
        // Delay showing preview to avoid accidental triggers
        this.hoverTimeout = setTimeout(() => {
          this.isHovered = true;
        }, 300);
      }
    },
    
    handleMouseLeave() {
      if (this.hoverTimeout) {
        clearTimeout(this.hoverTimeout);
        this.hoverTimeout = null;
      }
      this.isHovered = false;
    },
    
    getFeedbackIcon() {
      switch (this.comprehensionLevel) {
        case 'relational':
          return '🎯';
        case 'transitional':
          return '👍';
        case 'multi_structural':
          return '🔍';
        default:
          return '📝';
      }
    }
  },
  
  beforeUnmount() {
    if (this.hoverTimeout) {
      clearTimeout(this.hoverTimeout);
    }
  }
};
</script>

<style scoped>
.segment-analysis-button {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.segment-analysis-button:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.segment-analysis-button:active {
  transform: translateY(0);
}

.button-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  width: 100%;
}

.button-icon {
  font-size: var(--font-size-base);
  flex-shrink: 0;
}

.button-text {
  font-weight: 600;
  color: var(--color-text-primary);
  flex: 1;
}

.button-badges {
  display: flex;
  gap: var(--spacing-sm);
  flex-shrink: 0;
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

/* Preview Tooltip */
.preview-tooltip {
  position: absolute;
  z-index: 100;
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-lg);
  padding: var(--spacing-md);
  min-width: 300px;
  max-width: 400px;
  animation-duration: 0.2s;
  animation-timing-function: ease-out;
  animation-fill-mode: both;
}

.preview-tooltip.top {
  bottom: calc(100% + var(--spacing-sm));
  left: 50%;
  transform: translateX(-50%);
  animation-name: fadeInTop;
}

.preview-tooltip.bottom {
  top: calc(100% + var(--spacing-sm));
  left: 50%;
  transform: translateX(-50%);
  animation-name: fadeInBottom;
}

.preview-tooltip.left {
  right: calc(100% + var(--spacing-sm));
  top: 50%;
  transform: translateY(-50%);
  animation-name: fadeInLeft;
}

.preview-tooltip.right {
  left: calc(100% + var(--spacing-sm));
  top: 50%;
  transform: translateY(-50%);
  animation-name: fadeInRight;
}

/* Tooltip arrow */
.preview-tooltip::before {
  content: '';
  position: absolute;
  width: 0;
  height: 0;
  border: 6px solid transparent;
}

.preview-tooltip.top::before {
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border-top-color: var(--color-bg-border);
}

.preview-tooltip.bottom::before {
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border-bottom-color: var(--color-bg-border);
}

.preview-tooltip.left::before {
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  border-left-color: var(--color-bg-border);
}

.preview-tooltip.right::before {
  right: 100%;
  top: 50%;
  transform: translateY(-50%);
  border-right-color: var(--color-bg-border);
}

@keyframes fadeInTop {
  from { opacity: 0; transform: translateX(-50%) translateY(10px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

@keyframes fadeInBottom {
  from { opacity: 0; transform: translateX(-50%) translateY(-10px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

@keyframes fadeInLeft {
  from { opacity: 0; transform: translateY(-50%) translateX(10px); }
  to { opacity: 1; transform: translateY(-50%) translateX(0); }
}

@keyframes fadeInRight {
  from { opacity: 0; transform: translateY(-50%) translateX(-10px); }
  to { opacity: 1; transform: translateY(-50%) translateX(0); }
}

.preview-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-bg-border);
}

.preview-icon {
  font-size: var(--font-size-base);
}

.preview-title {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.preview-feedback {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.4;
}

.preview-segments {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.preview-segment {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs);
  background: var(--color-bg-hover);
  border-radius: var(--radius-xs);
}

.segment-id {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  background: var(--color-primary-gradient-start);
  color: white;
  border-radius: var(--radius-circle);
  font-size: var(--font-size-xs);
  font-weight: 700;
  flex-shrink: 0;
}

.segment-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-hint {
  text-align: center;
  padding-top: var(--spacing-xs);
  border-top: 1px solid var(--color-bg-border);
}

.preview-hint small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-style: italic;
}

/* Responsive */
@media (max-width: 768px) {
  .button-content {
    flex-wrap: wrap;
    gap: var(--spacing-xs);
  }
  
  .button-badges {
    order: 1;
    width: 100%;
    justify-content: flex-start;
  }
  
  .button-text {
    font-size: var(--font-size-xs);
  }
  
  .preview-tooltip {
    min-width: 250px;
    max-width: 300px;
  }
  
  /* Disable hover preview on mobile */
  .preview-tooltip {
    display: none;
  }
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
  .segment-analysis-button {
    transition: none;
  }
  
  .preview-tooltip {
    animation: none;
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .segment-analysis-button {
    border-width: 2px;
  }
  
  .preview-tooltip {
    border-width: 2px;
  }
}
</style>