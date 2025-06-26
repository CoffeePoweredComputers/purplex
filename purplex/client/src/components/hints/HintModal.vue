<template>
  <div v-if="visible" class="modal-overlay" @click="handleOverlayClick">
    <div class="modal-container" @click.stop>
      <div class="modal-header">
        <h2 class="modal-title">Select Hint Type</h2>
        <button class="close-button" @click="closeModal" aria-label="Close">
          ×
        </button>
      </div>
      
      <div class="modal-body">
        <div class="hint-options">
          <div 
            v-for="hintType in availableHints" 
            :key="hintType.type"
            class="hint-option"
            @click="selectHint(hintType.type)"
          >
            <div class="hint-option-icon">{{ hintType.icon }}</div>
            <div class="hint-option-content">
              <h3 class="hint-option-title">{{ hintType.title }}</h3>
              <p class="hint-option-description">{{ hintType.description }}</p>
            </div>
            <div class="hint-option-arrow">→</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue'
import type { HintType } from '../../types'

interface HintOption {
  type: HintType
  title: string
  description: string
  icon: string
}

export default defineComponent({
  name: 'HintModal',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    availableHintTypes: {
      type: Array as PropType<HintType[]>,
      default: () => ['variable_fade', 'subgoal_highlight', 'suggested_trace']
    }
  },
  emits: ['close', 'hint-selected'],
  setup(props, { emit }) {
    const hintOptions: HintOption[] = [
      {
        type: 'variable_fade',
        title: 'Variable Name Hints',
        description: 'Toggle between original and meaningful variable names to better understand the code',
        icon: '🏷️'
      },
      {
        type: 'subgoal_highlight',
        title: 'Code Structure Hints',
        description: 'See the code broken down into logical steps with explanations',
        icon: '🎯'
      },
      {
        type: 'suggested_trace',
        title: 'Suggested Trace',
        description: 'Get a suggested function call to trace through Python Tutor',
        icon: '🔍'
      }
    ]

    const availableHints = hintOptions.filter(hint => 
      props.availableHintTypes.includes(hint.type)
    )

    const closeModal = () => {
      emit('close')
    }

    const handleOverlayClick = () => {
      closeModal()
    }

    const selectHint = (hintType: HintType) => {
      emit('hint-selected', hintType)
      closeModal()
    }

    return {
      availableHints,
      closeModal,
      handleOverlayClick,
      selectHint
    }
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-container {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-border);
}

.modal-title {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
}

.close-button {
  background: none;
  border: none;
  font-size: 32px;
  line-height: 1;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-base);
  transition: var(--transition-base);
}

.close-button:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.modal-body {
  padding: var(--spacing-xl);
  overflow-y: auto;
  max-height: calc(80vh - 100px);
}

.hint-options {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.hint-option {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--color-bg-input);
  border: 2px solid transparent;
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-base);
}

.hint-option:hover {
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-hover);
  transform: translateX(4px);
}

.hint-option-icon {
  font-size: 36px;
  flex-shrink: 0;
}

.hint-option-content {
  flex: 1;
}

.hint-option-title {
  margin: 0 0 var(--spacing-xs) 0;
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
}

.hint-option-description {
  margin: 0;
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  line-height: 1.5;
}

.hint-option-arrow {
  font-size: var(--font-size-lg);
  color: var(--color-text-muted);
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .modal-container {
    width: 95%;
    margin: var(--spacing-md);
  }

  .hint-option {
    padding: var(--spacing-md);
  }

  .hint-option-icon {
    font-size: 28px;
  }

  .hint-option-title {
    font-size: var(--font-size-base);
  }

  .hint-option-description {
    font-size: var(--font-size-sm);
  }
}
</style>