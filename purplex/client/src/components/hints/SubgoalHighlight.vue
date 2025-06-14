<template>
  <div class="subgoal-highlight">
    <div class="hint-header">
      <h3 class="hint-title">Code Structure Breakdown</h3>
      <div class="navigation">
        <button 
          class="nav-button"
          :disabled="currentIndex === 0"
          @click="previousSubgoal"
        >
          ← Previous
        </button>
        <span class="nav-indicator">
          {{ currentIndex + 1 }} / {{ subgoals.length }}
        </span>
        <button 
          class="nav-button"
          :disabled="currentIndex === subgoals.length - 1"
          @click="nextSubgoal"
        >
          Next →
        </button>
      </div>
    </div>

    <div class="current-subgoal">
      <h4 class="subgoal-title">{{ currentSubgoal.title }}</h4>
      <p class="subgoal-explanation">{{ currentSubgoal.explanation }}</p>
    </div>

    <div class="code-container">
      <pre class="code-display"><code v-html="highlightedCode"></code></pre>
    </div>

    <div class="subgoal-list">
      <h4 class="list-title">All Steps:</h4>
      <div class="subgoal-items">
        <div 
          v-for="(subgoal, index) in subgoals"
          :key="subgoal.id"
          class="subgoal-item"
          :class="{ 'active': index === currentIndex }"
          @click="selectSubgoal(index)"
        >
          <span class="subgoal-number">{{ index + 1 }}</span>
          <span class="subgoal-name">{{ subgoal.title }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, PropType } from 'vue'
import type { Subgoal } from '../../types'

export default defineComponent({
  name: 'SubgoalHighlight',
  props: {
    code: {
      type: String,
      required: true
    },
    subgoals: {
      type: Array as PropType<Subgoal[]>,
      required: true
    }
  },
  setup(props) {
    const currentIndex = ref(0)

    const currentSubgoal = computed(() => {
      return props.subgoals[currentIndex.value]
    })

    const highlightedCode = computed(() => {
      const lines = props.code.split('\n')
      const highlighted = lines.map((line, index) => {
        const lineNumber = index + 1
        const isHighlighted = currentSubgoal.value.lineRanges.some(range => 
          lineNumber >= range.start && lineNumber <= range.end
        )
        
        if (isHighlighted) {
          return `<span class="highlighted-line">${escapeHtml(line)}</span>`
        }
        return `<span class="normal-line">${escapeHtml(line)}</span>`
      })
      
      return highlighted.join('\n')
    })

    const escapeHtml = (text: string) => {
      const map: Record<string, string> = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
      }
      return text.replace(/[&<>"'/]/g, (m) => map[m])
    }

    const nextSubgoal = () => {
      if (currentIndex.value < props.subgoals.length - 1) {
        currentIndex.value++
      }
    }

    const previousSubgoal = () => {
      if (currentIndex.value > 0) {
        currentIndex.value--
      }
    }

    const selectSubgoal = (index: number) => {
      currentIndex.value = index
    }

    return {
      currentIndex,
      currentSubgoal,
      highlightedCode,
      nextSubgoal,
      previousSubgoal,
      selectSubgoal
    }
  }
})
</script>

<style scoped>
.subgoal-highlight {
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
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.hint-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.navigation {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.nav-button {
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-base);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-primary);
}

.nav-button:hover:not(:disabled) {
  background: var(--color-bg-hover);
  border-color: var(--color-primary-gradient-start);
}

.nav-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  color: var(--color-text-muted);
}

.nav-indicator {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: 500;
}

.current-subgoal {
  background: var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.subgoal-title {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
}

.subgoal-explanation {
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
  position: relative;
}

.code-display code {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  line-height: 1.6;
}

:deep(.highlighted-line) {
  display: inline-block;
  width: 100%;
  background: rgba(59, 130, 246, 0.15);
  border-left: 3px solid var(--color-primary-gradient-start);
  padding-left: var(--spacing-sm);
  margin-left: -var(--spacing-sm);
  animation: highlightPulse 0.5s ease-out;
}

:deep(.normal-line) {
  display: inline-block;
  width: 100%;
  color: var(--color-text-muted);
  opacity: 0.7;
}

@keyframes highlightPulse {
  0% {
    background: rgba(59, 130, 246, 0.3);
  }
  100% {
    background: rgba(59, 130, 246, 0.15);
  }
}

.subgoal-list {
  background: var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
}

.list-title {
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
}

.subgoal-items {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.subgoal-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-base);
}

.subgoal-item:hover {
  background: var(--color-bg-hover);
}

.subgoal-item.active {
  background: var(--color-primary-gradient-start);
  color: white;
}

.subgoal-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: var(--color-bg-border);
  border-radius: 50%;
  font-size: var(--font-size-sm);
  font-weight: 600;
  flex-shrink: 0;
}

.subgoal-item.active .subgoal-number {
  background: white;
  color: var(--color-primary-gradient-start);
}

.subgoal-name {
  font-size: var(--font-size-sm);
  font-weight: 500;
}

@media (max-width: 768px) {
  .hint-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .navigation {
    width: 100%;
    justify-content: space-between;
  }

  .code-display {
    font-size: var(--font-size-xs);
    padding: var(--spacing-md);
  }
}
</style>