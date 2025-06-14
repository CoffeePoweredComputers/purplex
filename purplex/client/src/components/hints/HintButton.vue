<template>
  <button 
    class="hint-button"
    :class="{ 'disabled': !canRequestHint }"
    :disabled="!canRequestHint"
    @click="handleHintRequest"
    :title="buttonTooltip"
  >
    <span class="hint-icon">💡</span>
    <span class="hint-text">{{ buttonText }}</span>
  </button>
</template>

<script lang="ts">
import { computed, defineComponent } from 'vue'

export default defineComponent({
  name: 'HintButton',
  props: {
    problemSlug: {
      type: String,
      required: true
    },
    problemSetSlug: {
      type: String,
      required: true
    },
    courseId: {
      type: String,
      required: true
    },
    attempts: {
      type: Number,
      required: true
    },
    requiredAttempts: {
      type: Number,
      default: 3
    }
  },
  emits: ['hint-requested'],
  setup(props, { emit }) {
    const canRequestHint = computed(() => {
      return props.attempts >= props.requiredAttempts
    })

    const remainingAttempts = computed(() => {
      return Math.max(0, props.requiredAttempts - props.attempts)
    })

    const buttonText = computed(() => {
      if (canRequestHint.value) {
        return 'Get Hint'
      }
      return `Need ${remainingAttempts.value} more attempt${remainingAttempts.value === 1 ? '' : 's'}`
    })

    const buttonTooltip = computed(() => {
      if (canRequestHint.value) {
        return 'Click to request a hint'
      }
      return `You need to make ${remainingAttempts.value} more attempt${remainingAttempts.value === 1 ? '' : 's'} before hints are available`
    })

    const handleHintRequest = () => {
      if (canRequestHint.value) {
        emit('hint-requested', {
          problemSlug: props.problemSlug,
          problemSetSlug: props.problemSetSlug,
          courseId: props.courseId,
          attempts: props.attempts
        })
      }
    }

    return {
      canRequestHint,
      remainingAttempts,
      buttonText,
      buttonTooltip,
      handleHintRequest
    }
  }
})
</script>

<style scoped>
.hint-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-primary-gradient-start);
  color: white;
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-base);
  box-shadow: var(--shadow-base);
}

.hint-button:hover:not(.disabled) {
  background: var(--color-primary-gradient-end);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.hint-button:active:not(.disabled) {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}

.hint-button.disabled {
  background: var(--color-bg-input);
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.7;
}

.hint-icon {
  font-size: var(--font-size-lg);
}

.hint-text {
  white-space: nowrap;
}

@media (max-width: 768px) {
  .hint-button {
    padding: var(--spacing-xs) var(--spacing-md);
    font-size: var(--font-size-sm);
  }
  
  .hint-icon {
    font-size: var(--font-size-base);
  }
}
</style>