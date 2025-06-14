<template>
  <div class="input-suggestion">
    <div class="hint-header">
      <h3 class="hint-title">Suggested Test Cases</h3>
      <p class="hint-subtitle">Try these test cases to better understand the problem</p>
    </div>

    <div class="suggestions-list">
      <div 
        v-for="(suggestion, index) in suggestions"
        :key="index"
        class="suggestion-card"
      >
        <div class="suggestion-header">
          <span class="suggestion-number">Test Case {{ index + 1 }}</span>
          <button 
            v-if="suggestion.pythonTutorUrl"
            class="trace-button"
            @click="openPythonTutor(suggestion.pythonTutorUrl)"
            title="Trace this test case in Python Tutor"
          >
            <span class="trace-icon">🔍</span>
            Trace
          </button>
        </div>

        <div class="suggestion-content">
          <div class="test-inputs">
            <h4 class="content-label">Inputs:</h4>
            <code class="code-block">{{ formatInputs(suggestion.inputs) }}</code>
          </div>

          <div class="test-description">
            <h4 class="content-label">Why this test case:</h4>
            <p class="description-text">{{ suggestion.description }}</p>
          </div>

          <div class="learning-goal">
            <h4 class="content-label">Learning Goal:</h4>
            <p class="goal-text">{{ suggestion.learningGoal }}</p>
          </div>
        </div>

        <div class="suggestion-instructions">
          <p class="instruction-text">
            💡 Try running this test case manually or use the trace button to step through the execution
          </p>
        </div>
      </div>
    </div>

    <div class="general-tips">
      <h4 class="tips-title">How to use these test cases:</h4>
      <ol class="tips-list">
        <li>Copy the inputs and test them with your solution</li>
        <li>Use the trace button to see how the code executes step-by-step</li>
        <li>Compare your output with the expected behavior</li>
        <li>Think about why each test case is important for understanding the problem</li>
      </ol>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue'
import type { TestSuggestion } from '../../types'

export default defineComponent({
  name: 'InputSuggestion',
  props: {
    suggestions: {
      type: Array as PropType<TestSuggestion[]>,
      required: true
    },
    functionName: {
      type: String,
      default: 'function'
    }
  },
  setup(props) {
    const formatInputs = (inputs: any[]) => {
      // Format inputs as a function call
      const formattedArgs = inputs.map(input => {
        if (typeof input === 'string') {
          return `"${input}"`
        } else if (Array.isArray(input)) {
          return `[${input.map(item => 
            typeof item === 'string' ? `"${item}"` : item
          ).join(', ')}]`
        } else if (typeof input === 'object' && input !== null) {
          return JSON.stringify(input)
        }
        return String(input)
      }).join(', ')

      return `${props.functionName}(${formattedArgs})`
    }

    const openPythonTutor = (url: string) => {
      window.open(url, '_blank', 'noopener,noreferrer')
    }

    return {
      formatInputs,
      openPythonTutor
    }
  }
})
</script>

<style scoped>
.input-suggestion {
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-base);
}

.hint-header {
  margin-bottom: var(--spacing-xl);
}

.hint-title {
  margin: 0 0 var(--spacing-xs) 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.hint-subtitle {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
}

.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.suggestion-card {
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
  transition: var(--transition-base);
}

.suggestion-card:hover {
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-sm);
}

.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.suggestion-number {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.trace-button {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-primary-gradient-start);
  color: white;
  border: none;
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-base);
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.trace-button:hover {
  background: var(--color-primary-gradient-end);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.trace-icon {
  font-size: var(--font-size-base);
}

.suggestion-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.content-label {
  margin: 0 0 var(--spacing-xs) 0;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.code-block {
  display: block;
  background: var(--color-bg-code);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-sm);
  padding: var(--spacing-md);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  overflow-x: auto;
}

.description-text,
.goal-text {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  line-height: 1.6;
}

.suggestion-instructions {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-bg-border);
}

.instruction-text {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-style: italic;
}

.general-tips {
  background: var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
}

.tips-title {
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
}

.tips-list {
  margin: 0;
  padding-left: var(--spacing-xl);
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  line-height: 1.8;
}

.tips-list li {
  margin-bottom: var(--spacing-xs);
}

@media (max-width: 768px) {
  .suggestion-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }

  .trace-button {
    width: 100%;
    justify-content: center;
  }

  .code-block {
    font-size: var(--font-size-xs);
  }
}
</style>