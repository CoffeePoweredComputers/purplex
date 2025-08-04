<template>
  <div 
    v-if="segmentation"
    class="comprehension-banner"
    :class="bannerClass"
  >
    <div class="banner-content">
      <div class="banner-main">
        <div class="progress-section">
          <div class="segments-container">
            <span 
              v-for="(segment, index) in 8" 
              :key="index"
              class="segment"
              :class="{
                'filled': index < filledSegments,
                'threshold': index === 1
              }"
            >
              {{ index < filledSegments ? '■' : '□' }}
            </span>
          </div>
        </div>
        <div class="banner-message">
          <span class="level-text">{{ getLevelText() }}</span>
          <span class="separator">•</span>
          <span class="description-text">{{ getShortDescription() }}</span>
        </div>
      </div>
      <button 
        class="analyze-button"
        @click="$emit('show-details')"
        aria-label="View detailed analysis"
        title="View details"
      >
        <span class="button-icon">›</span>
      </button>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue';

// Define the segmentation type based on existing types
interface Segmentation {
  segment_count: number;
  comprehension_level: 'relational' | 'transitional' | 'multi_structural';
  segments?: Array<{
    id: number;
    text: string;
    code_lines: number[];
  }>;
  passed?: boolean;
}

export default defineComponent({
  name: 'ComprehensionBanner',
  props: {
    segmentation: {
      type: Object as PropType<Segmentation>,
      required: true,
      validator: (value: Segmentation): boolean => {
        return value && 
               typeof value.segment_count === 'number' &&
               typeof value.comprehension_level === 'string';
      }
    }
  },
  emits: ['show-details'],
  computed: {
    bannerClass(): string {
      return `banner-${this.segmentation.comprehension_level.replace('_', '-')}`;
    },
    
    filledSegments(): number {
      // Map comprehension levels to number of filled segments
      const segmentCount = this.segmentation.segment_count || 0;
      
      // Use actual segment count, but also consider comprehension level
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return Math.min(segmentCount, 8); // Usually 1-2 segments
        case 'transitional':
          return Math.min(segmentCount, 8); // Usually 3-5 segments
        case 'multi_structural':
          return Math.min(segmentCount, 8); // Usually 6-8 segments
        default:
          return Math.min(segmentCount, 8);
      }
    }
  },
  methods: {
    getLevelText(): string {
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return 'Excellent';
        case 'transitional':
          return 'Good';
        case 'multi_structural':
          return 'Detailed';
        default:
          return 'Analyzed';
      }
    },
    
    getShortDescription(): string {
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return 'High-level focus';
        case 'transitional':
          return 'Key steps identified';
        case 'multi_structural':
          return 'Detail-oriented';
        default:
          return 'View analysis';
      }
    }
  }
});
</script>

<style scoped>
.comprehension-banner {
  margin: var(--spacing-sm) 0;
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: var(--transition-fast);
}

.comprehension-banner:hover {
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.15);
}

.banner-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-md);
  gap: var(--spacing-md);
}

.banner-main {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}


.progress-section {
  flex-shrink: 0;
}

.segments-container {
  display: flex;
  align-items: center;
  gap: 3px;
}

.segment {
  font-size: 12px;
  line-height: 1;
  color: var(--color-text-muted);
  transition: color 0.3s ease;
  position: relative;
  animation: fadeInSegment 0.3s ease-out;
  animation-fill-mode: both;
}

.segment:nth-child(1) { animation-delay: 0.05s; }
.segment:nth-child(2) { animation-delay: 0.1s; }
.segment:nth-child(3) { animation-delay: 0.15s; }
.segment:nth-child(4) { animation-delay: 0.2s; }
.segment:nth-child(5) { animation-delay: 0.25s; }
.segment:nth-child(6) { animation-delay: 0.3s; }
.segment:nth-child(7) { animation-delay: 0.35s; }
.segment:nth-child(8) { animation-delay: 0.4s; }

@keyframes fadeInSegment {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.segment.filled {
  color: var(--color-primary);
}

/* Threshold marker */
.segment.threshold::after {
  content: '';
  position: absolute;
  right: -5px;
  top: 50%;
  transform: translateY(-50%);
  width: 1px;
  height: 12px;
  background: var(--color-text-muted);
  opacity: 0.5;
}

/* Level-specific segment colors */
.banner-relational .segment.filled {
  color: var(--color-success);
}

.banner-transitional .segment.filled {
  color: var(--color-warning);
}

.banner-multi-structural .segment.filled {
  color: var(--color-error);
}

.banner-message {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
}

.level-text {
  font-weight: 600;
  color: var(--color-text-primary);
}

.separator {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.description-text {
  color: var(--color-text-secondary);
}

.analyze-button {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: var(--transition-fast);
}

.analyze-button:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.button-icon {
  font-size: var(--font-size-lg);
  line-height: 1;
  font-weight: 300;
}

/* Subtle level indicators */
.banner-relational {
  border-left: 3px solid var(--color-success);
}

.banner-transitional {
  border-left: 3px solid var(--color-warning);
}

.banner-multi-structural {
  border-left: 3px solid var(--color-error);
}

/* Responsive */
@media (max-width: 768px) {
  .banner-content {
    flex-direction: column;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
  }
  
  .banner-main {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .segments-container {
    gap: 2px;
  }
  
  .segment {
    font-size: 10px;
  }
  
  .banner-message {
    width: 100%;
    order: 2;
    flex-direction: column;
    gap: var(--spacing-xs);
  }
  
  .analyze-button {
    width: 28px;
    height: 28px;
  }
}

/* Animation on mount */
@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.comprehension-banner {
  animation: slideDown 0.3s ease-out;
}
</style>