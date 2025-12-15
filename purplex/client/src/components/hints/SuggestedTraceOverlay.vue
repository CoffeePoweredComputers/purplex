<template>
  <div class="suggested-trace">
    <div class="trace-content">
      <span class="trace-label">💡 Try tracing:</span>
      <code class="trace-function">{{ functionCall }}</code>
      <button
        class="trace-btn"
        :disabled="!canTrace"
        @click="openInPyTutor"
      >
        <span>🔍</span> Trace in Python Tutor
      </button>
    </div>
  </div>
</template>

<script lang="ts">
import { computed, defineComponent } from 'vue'
import { PythonTutorService } from '@/services/pythonTutor.service'

export default defineComponent({
  name: 'SuggestedTraceOverlay',
  props: {
    suggestedCall: {
      type: String,
      required: true
    },
    explanation: {
      type: String,
      default: ''
    },
    expectedOutput: {
      type: [String, Number, Boolean, Object, Array],
      default: undefined
    },
    solutionCode: {
      type: String,
      default: ''
    }
  },
  emits: ['open-pytutor', 'close'],
  setup(props, { emit }) {
    const functionCall = computed(() => {
      return props.suggestedCall
    })

    const canTrace = computed(() => {
      return props.solutionCode && functionCall.value
    })

    const openInPyTutor = () => {
      if (!canTrace.value) {return}

      // Generate Python Tutor URL with the solution code and suggested call
      const testCode = `# Suggested trace\nprint(${functionCall.value})`
      const formattedCode = `${props.solutionCode}\n\n${testCode}`
      const pytutorUrl = PythonTutorService.generateEmbedUrl(formattedCode)

      emit('open-pytutor', pytutorUrl)
    }

    return {
      functionCall,
      canTrace,
      openInPyTutor
    }
  }
})
</script>

<style scoped>
.suggested-trace {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-md) var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  transition: var(--transition-base);
}

.suggested-trace:hover {
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-sm);
}

.trace-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.trace-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.trace-function {
  font-family: var(--font-mono, 'SF Mono', 'Monaco', 'Inconsolata', monospace);
  font-size: var(--font-size-sm);
  background: var(--color-bg-code);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  color: var(--color-text-primary);
  flex: 1;
  min-width: 200px;
  overflow-x: auto;
}

.trace-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-base);
  font-size: var(--font-size-sm);
  font-weight: 500;
  white-space: nowrap;
}

.trace-btn:hover:not(:disabled) {
  background: var(--color-primary-gradient-end);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.trace-btn:disabled {
  background: var(--color-bg-disabled);
  color: var(--color-text-muted);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

@media (max-width: 768px) {
  .suggested-trace {
    margin: var(--spacing-md);
  }

  .trace-content {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-sm);
  }

  .trace-function {
    min-width: auto;
  }
}
</style>
