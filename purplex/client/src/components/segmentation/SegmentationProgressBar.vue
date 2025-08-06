<template>
  <div class="segmentation-progress">
    <div class="progress-header">
      <span class="progress-label">Comprehension Level</span>
      <span class="progress-value" :class="levelClass">
        {{ formatLevel(comprehensionLevel) }}
      </span>
    </div>
    
    <div class="progress-visual">
      <!-- Animated blocks representing segments -->
      <div class="segment-blocks">
        <div 
          v-for="i in maxSegments" 
          :key="i"
          class="segment-block"
          :class="getBlockClass(i)"
          :style="getBlockStyle(i)"
          :title="getBlockTooltip(i)"
        >
          <span v-if="i <= segmentCount" class="block-number">{{ i }}</span>
        </div>
      </div>
      
      <!-- Threshold indicator -->
      <div class="threshold-indicator" :style="{ left: thresholdPosition }">
        <div class="threshold-line"></div>
        <div class="threshold-label">Goal</div>
      </div>
    </div>
    
    <!-- Visual scale -->
    <div class="progress-scale">
      <span class="scale-start">High-level</span>
      <span class="scale-end">Line-by-line</span>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, type PropType, type CSSProperties } from 'vue';

type ComprehensionLevel = 'relational' | 'transitional' | 'multi_structural';

export default defineComponent({
  name: 'SegmentationProgressBar',
  props: {
    segmentCount: {
      type: Number,
      required: true
    },
    comprehensionLevel: {
      type: String as PropType<ComprehensionLevel>,
      required: true,
      validator: (value: string): boolean => ['relational', 'transitional', 'multi_structural'].includes(value)
    },
    threshold: {
      type: Number,
      default: 2
    },
    maxSegments: {
      type: Number,
      default: 8
    }
  },
  computed: {
    levelClass(): string {
      return `level-${this.comprehensionLevel.replace('_', '-')}`;
    },
    thresholdPosition(): string {
      return `${(this.threshold / this.maxSegments) * 100}%`;
    }
  },
  methods: {
    formatLevel(level: ComprehensionLevel): string {
      switch (level) {
        case 'relational':
          return 'Excellent';
        case 'transitional':
          return 'Good';
        case 'multi_structural':
          return 'Needs Work';
        default:
          return 'Unknown';
      }
    },
    getBlockClass(index: number): string[] {
      const classes: string[] = ['segment-block'];
      
      if (index <= this.segmentCount) {
        classes.push('filled');
        classes.push(this.comprehensionLevel.replace('_', '-'));
      }
      
      return classes;
    },
    getBlockStyle(index: number): CSSProperties {
      if (index <= this.segmentCount) {
        // Add staggered animation delay
        return {
          'animationDelay': `${(index - 1) * 0.1}s`
        };
      }
      return {};
    },
    getBlockTooltip(index: number): string {
      if (index <= this.segmentCount) {
        return `Segment ${index}: ${this.segmentCount <= this.threshold ? 'Good' : 'Too detailed'}`;
      }
      return `Segment ${index}: Not used`;
    }
  }
});
</script>

<style scoped>
/* Base variables */
.segmentation-progress {
  --seg-color-good: var(--color-success);
  --seg-color-ok: var(--color-warning);
  --seg-color-poor: var(--color-error);
  
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
  border: 1px solid var(--color-bg-input);
}

/* Header */
.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.progress-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-muted);
}

.progress-value {
  font-size: var(--font-size-sm);
  font-weight: 700;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.progress-value.level-relational {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.progress-value.level-transitional {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.progress-value.level-multi-structural {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}

/* Visual progress */
.progress-visual {
  position: relative;
  margin-bottom: var(--spacing-lg);
}

.segment-blocks {
  display: flex;
  gap: var(--spacing-sm);
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
}

.segment-block {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--font-size-sm);
  transition: var(--transition-base);
  position: relative;
  overflow: hidden;
  opacity: 0.6;
}

.segment-block.filled {
  opacity: 1;
  transform: scale(1.05);
  box-shadow: var(--shadow-md);
  animation: blockFillIn 0.4s ease-out forwards;
}

.segment-block.filled::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, 
    rgba(255, 255, 255, 0.2) 0%, 
    transparent 50%
  );
  animation: shimmer 0.6s ease-out;
}

.block-number {
  color: white;
  font-weight: 700;
  z-index: 1;
}

/* Comprehension level colors */
.segment-block.relational {
  background: var(--seg-color-good);
  border-color: var(--seg-color-good);
}

.segment-block.transitional {
  background: var(--seg-color-ok);
  border-color: var(--seg-color-ok);
}

.segment-block.multi-structural {
  background: var(--seg-color-poor);
  border-color: var(--seg-color-poor);
}

/* Threshold indicator */
.threshold-indicator {
  position: absolute;
  top: -10px;
  transform: translateX(-50%);
  z-index: 2;
}

.threshold-line {
  width: 2px;
  height: 60px;
  background: var(--color-primary-gradient-start);
  margin: 0 auto;
  border-radius: 1px;
  animation: thresholdPulse 2s ease-in-out infinite;
}

.threshold-label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-primary-gradient-start);
  text-align: center;
  margin-top: var(--spacing-xs);
  white-space: nowrap;
}

/* Scale */
.progress-scale {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 500;
}

/* Animations */
@keyframes blockFillIn {
  0% {
    transform: scale(0.8);
    opacity: 0;
  }
  50% {
    transform: scale(1.15);
  }
  100% {
    transform: scale(1.05);
    opacity: 1;
  }
}

@keyframes shimmer {
  from { 
    transform: translateX(-100%); 
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
  to { 
    transform: translateX(100%); 
    opacity: 0;
  }
}

@keyframes thresholdPulse {
  0%, 100% {
    opacity: 0.7;
    transform: scaleY(1);
  }
  50% {
    opacity: 1;
    transform: scaleY(1.1);
  }
}

/* Responsive */
@media (max-width: 768px) {
  .segment-blocks {
    gap: var(--spacing-xs);
  }
  
  .segment-block {
    width: 32px;
    height: 32px;
    font-size: var(--font-size-xs);
  }
  
  .progress-header {
    flex-direction: column;
    gap: var(--spacing-sm);
    text-align: center;
  }
}
</style>