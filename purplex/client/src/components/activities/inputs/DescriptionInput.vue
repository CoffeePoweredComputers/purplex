<template>
  <div class="description-input">
    <div class="section-header">
    <div class="section-label">
      {{ sectionLabel }}
    </div>
  </div>
  <span
    v-if="draftSaved"
    class="draft-indicator"
    role="status"
    aria-live="polite"
  >{{ $t('problems.submission.draftSaved') }}</span>
  <div
    id="promptEditor"
    class="prompt-editor-wrapper"
    tabindex="-1"
  >
    <Editor
      ref="editorRef"
      v-model:value="inputValue"
      lang="text"
      mode="text"
      height="100px"
      width="100%"
      :show-gutter="false"
      :wrap="true"
      :theme="editorTheme"
    />
  </div>
  <button
    id="submitButton"
    class="submit-button"
    :disabled="disabled || !isValid"
    :aria-busy="disabled"
    :aria-label="disabled ? $t('problems.submission.submittingWait') : (isValid ? $t('problems.submission.submitSolution') : $t('problems.submission.minLength'))"
    @click="handleSubmit"
  >
    <span
      v-if="!disabled"
      class="button-text"
    >{{ $t('problems.submission.submitSolution') }}</span>
    <div
      v-if="disabled"
      class="loading-content"
      role="status"
      aria-live="polite"
    >
      <div
        class="bouncing-dots"
        aria-hidden="true"
      >
        <span class="dot" />
        <span class="dot" />
        <span class="dot" />
      </div>
      <span class="visually-hidden">{{ $t('problems.submission.submittingWait') }}</span>
    </div>
  </button>
  </div>
</template>

<script setup lang="ts">
/**
 * DescriptionInput - Shared input component for text-based problem descriptions.
 *
 * Used by EiPL and Prompt activity types. Provides:
 * - Section header with configurable label
 * - Text editor for description input
 * - Submit button with loading state
 * - Draft saved indicator
 */
import { computed, ref } from 'vue'
import Editor from '@/features/editor/Editor.vue'
import type { ActivityProblem } from '../types'

interface Props {
  /** User's input text (v-model) */
  modelValue: string
  /** Current problem data */
  problem: ActivityProblem
  /** Whether input is disabled (during submission) */
  disabled?: boolean
  /** Editor theme */
  theme?: string
  /** Whether draft has been saved */
  draftSaved?: boolean
  /** Section label text */
  sectionLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  theme: 'dark',
  draftSaved: false,
  sectionLabel: 'Describe the code here',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}>()

const editorRef = ref<InstanceType<typeof Editor> | null>(null)

// Computed value for v-model binding
const inputValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})

// Validation: check if input meets length requirements
const isValid = computed(() => {
  const minLength = props.problem?.input_config?.min_length ?? 10
  const maxLength = props.problem?.input_config?.max_length ?? 1000
  const value = props.modelValue?.trim() || ''
  return value.length >= minLength && value.length <= maxLength
})

// Map theme prop to Ace editor theme name
const editorTheme = computed(() => {
  const themeMap: Record<string, string> = {
    dark: 'tomorrow_night',
    light: 'chrome',
    monokai: 'monokai',
    github: 'github',
    'solarized-dark': 'solarized_dark',
    'solarized-light': 'solarized_light',
    dracula: 'dracula',
    'tomorrow-night': 'tomorrow_night',
    'clouds_midnight': 'clouds_midnight',
  }
  return themeMap[props.theme] || props.theme || 'tomorrow_night'
})

function handleSubmit() {
  if (!props.disabled) {
    emit('submit')
  }
}
</script>

<style scoped>
/*
 * Shared styles for description input component
 * Used by EiPL and Prompt activity types
 */

/* Container - positioned ancestor for absolute elements */
.description-input {
  position: relative;
}

/* Section Header */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-bg-input);
  margin-bottom: var(--spacing-sm);
}

.section-label {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-secondary);
}

/* Draft Indicator - positioned absolutely within parent .submission-section */
.draft-indicator {
  position: absolute;
  top: var(--spacing-sm);
  right: var(--spacing-lg);
  color: var(--color-success);
  font-size: var(--font-size-xs);
  font-weight: 600;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Editor Wrapper */
.prompt-editor-wrapper {
  padding: 0;
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  margin: var(--spacing-md) var(--spacing-xl);
  margin-bottom: 0;
  border-radius: var(--radius-base);
  overflow: hidden;
  transition: var(--transition-base);
}

.prompt-editor-wrapper:hover {
  border-color: var(--color-primary-gradient-start);
}

/* Submit Button */
.submit-button {
  margin: var(--spacing-md) var(--spacing-xl) var(--spacing-sm);
  width: calc(100% - calc(var(--spacing-xl) * 2));
  padding: var(--spacing-md) var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
  box-shadow: var(--shadow-colored);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  flex-shrink: 0;
}

.submit-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--color-primary-glow);
}

.submit-button:disabled {
  background: var(--color-bg-disabled);
  cursor: not-allowed;
  opacity: 0.7;
}

/* Loading Animation */
.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
}

.bouncing-dots {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--spacing-sm);
}

.dot {
  width: 10px;
  height: 10px;
  background: var(--color-text-primary);
  border-radius: var(--radius-circle);
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Accessibility */
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
