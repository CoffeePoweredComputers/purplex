<template>
  <div class="variable-fade-hint">
    <div class="hint-header">
      <h3 class="hint-title">Variable Name Toggle</h3>
      <button 
        class="toggle-button"
        :class="{ 'active': showMeaningful }"
        @click="toggleVariables"
      >
        <span class="toggle-icon">{{ showMeaningful ? '👁️' : '👁️‍🗨️' }}</span>
        <span class="toggle-text">{{ toggleText }}</span>
      </button>
    </div>
    
    <div class="hint-description">
      <p>{{ description }}</p>
    </div>

    <div class="code-container">
      <pre class="code-display"><code>{{ displayedCode }}</code></pre>
    </div>

    <div class="mappings-legend" v-if="showMeaningful">
      <h4 class="legend-title">Variable Mappings:</h4>
      <div class="mapping-list">
        <div v-for="mapping in mappings" :key="mapping.from" class="mapping-item">
          <code class="mapping-from">{{ mapping.from }}</code>
          <span class="mapping-arrow">→</span>
          <code class="mapping-to">{{ mapping.to }}</code>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, PropType } from 'vue'
import type { VariableMapping } from '../../types'

export default defineComponent({
  name: 'VariableFadeHint',
  props: {
    code: {
      type: String,
      required: true
    },
    mappings: {
      type: Array as PropType<VariableMapping[]>,
      required: true
    }
  },
  setup(props) {
    const showMeaningful = ref(false)

    const toggleText = computed(() => {
      return showMeaningful.value ? 'Show Original Names' : 'Show Meaningful Names'
    })

    const description = computed(() => {
      return showMeaningful.value 
        ? 'Variable names have been replaced with more meaningful names to help you understand the code better.'
        : 'Click the button above to see the code with more descriptive variable names.'
    })

    const displayedCode = computed(() => {
      if (!showMeaningful.value) {
        return props.code
      }

      let modifiedCode = props.code
      
      // Sort mappings by length (longest first) to avoid partial replacements
      const sortedMappings = [...props.mappings].sort((a, b) => 
        b.from.length - a.from.length
      )

      // Replace each variable with its meaningful name
      sortedMappings.forEach(mapping => {
        // Use word boundaries to avoid partial replacements
        const regex = new RegExp(`\\b${escapeRegExp(mapping.from)}\\b`, 'g')
        modifiedCode = modifiedCode.replace(regex, mapping.to)
      })

      return modifiedCode
    })

    const toggleVariables = () => {
      showMeaningful.value = !showMeaningful.value
    }

    // Helper function to escape special regex characters
    const escapeRegExp = (string: string) => {
      return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    }

    return {
      showMeaningful,
      toggleText,
      description,
      displayedCode,
      toggleVariables
    }
  }
})
</script>

<style scoped>
.variable-fade-hint {
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-base);
}

.hint-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.hint-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.toggle-button {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-base);
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--color-text-primary);
}

.toggle-button:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-primary-gradient-start);
}

.toggle-button.active {
  background: var(--color-primary-gradient-start);
  color: white;
  border-color: var(--color-primary-gradient-start);
}

.toggle-icon {
  font-size: var(--font-size-lg);
}

.hint-description {
  margin-bottom: var(--spacing-lg);
}

.hint-description p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  line-height: 1.6;
}

.code-container {
  margin-bottom: var(--spacing-lg);
}

.code-display {
  background: var(--color-bg-code);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
  overflow-x: auto;
  margin: 0;
}

.code-display code {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  white-space: pre;
}

.mappings-legend {
  background: var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.legend-title {
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
}

.mapping-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.mapping-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.mapping-from,
.mapping-to {
  background: var(--color-bg-code);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.mapping-arrow {
  color: var(--color-text-muted);
  font-weight: 500;
}

@media (max-width: 768px) {
  .hint-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .toggle-button {
    width: 100%;
    justify-content: center;
  }

  .code-display {
    font-size: var(--font-size-xs);
    padding: var(--spacing-md);
  }
}
</style>