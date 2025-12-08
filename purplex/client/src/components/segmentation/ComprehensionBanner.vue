<template>
  <div 
    v-if="segmentation"
    class="comprehension-banner"
    :class="bannerClass"
  >
    <div class="banner-content">
      <div class="banner-main">
        <div class="progress-section">
          <span
            class="feedback-icon"
            :class="iconClass"
          >
            {{ getIcon() }}
          </span>
        </div>
        <div class="banner-message">
          <span class="level-text">{{ getLevelText() }}</span>
          <span class="separator">•</span>
          <span class="description-text">{{ getShortDescription() }}</span>
        </div>
      </div>
      <button
        class="analyze-button"
        :class="{ 'pulse-glow': shouldGlow }"
        aria-label="View detailed analysis"
        title="View details"
        @click="$emit('show-details')"
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
  comprehension_level: 'relational' | 'multi_structural';
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
    },
    referenceCode: {
      type: String,
      default: ''
    }
  },
  emits: ['show-details'],
  computed: {
    bannerClass(): string {
      return `banner-${this.segmentation.comprehension_level.replace('_', '-')}`;
    },

    iconClass(): string {
      return this.segmentation.comprehension_level === 'relational' ? 'icon-success' : 'icon-warning';
    },

    shouldGlow(): boolean {
      return this.segmentation.comprehension_level === 'multi_structural';
    }
  },
  methods: {
    getIcon(): string {
      return this.segmentation.comprehension_level === 'relational' ? '✓' : '✗';
    },

    getLevelText(): string {
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return 'Great!';
        case 'multi_structural':
          return 'Too detailed';
        default:
          return 'Analyzed';
      }
    },

    getShortDescription(): string {
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return 'High-level understanding';
        case 'multi_structural':
          return 'Review suggested improvements';
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
  min-height: 36px; /* Ensure consistent height */
}

.banner-main {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-md); /* Increased from sm to md */
}


.progress-section {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.feedback-icon {
  font-size: 24px;
  font-weight: bold;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-circle);
  transition: var(--transition-fast);
}

.icon-success {
  color: var(--color-success);
  background: var(--color-success-bg);
}

.icon-warning {
  color: var(--color-error);
  background: var(--color-error-bg);
}

.banner-message {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
  line-height: 1.2;
  padding: 0 var(--spacing-xs); /* Add horizontal padding for breathing room */
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
  width: 36px;
  height: 36px;
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
  margin-left: var(--spacing-sm);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.analyze-button:hover {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
  transform: translateX(3px) scale(1.05);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

/* Enhanced styling for multi-structural (low-level) */
.banner-multi-structural .analyze-button {
  background: rgba(220, 53, 69, 0.1);
  border-color: var(--color-error);
  color: var(--color-error);
}

.banner-multi-structural .analyze-button:hover {
  background: var(--color-error);
  border-color: var(--color-error);
  color: white;
}

.button-icon {
  font-size: var(--font-size-lg);
  line-height: 1;
  font-weight: 700;
  transform: rotate(0deg);
  transition: transform 0.2s ease;
}

.analyze-button:hover .button-icon {
  transform: rotate(90deg);
}

/* Subtle level indicators */
.banner-relational {
  border-left: 3px solid var(--color-success);
}

.banner-multi-structural {
  border-left: 3px solid var(--color-error);
}

/* Pulse glow animation for attention */
.analyze-button.pulse-glow {
  animation: pulseGlow 2s infinite;
}

@keyframes pulseGlow {
  0% {
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(220, 53, 69, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0);
  }
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

  .feedback-icon {
    font-size: 20px;
    width: 28px;
    height: 28px;
  }

  .banner-message {
    width: 100%;
    order: 2;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .analyze-button {
    width: 32px;
    height: 32px;
  }
}

</style>