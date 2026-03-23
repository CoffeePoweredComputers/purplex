<template>
  <div class="debug-fix-input">
    <div class="section-header">
      <div class="section-label">
        {{ $t('problems.debugFix.sectionLabel') }}
      </div>
    </div>
    <span
      v-if="draftSaved"
      class="draft-indicator"
      role="status"
      aria-live="polite"
    >{{ $t('problems.submission.draftSaved') }}</span>
    <div
      id="codeEditor"
      class="code-editor-wrapper"
      tabindex="-1"
    >
      <Editor
        ref="editorRef"
        v-model:value="inputValue"
        lang="python"
        mode="python"
        height="300px"
        width="100%"
        :show-gutter="true"
        :wrap="false"
        :theme="editorTheme"
      />
    </div>
    <div class="action-row">
      <button
        class="reset-button"
        :disabled="disabled"
        @click="handleReset"
      >
        {{ $t('problems.submission.resetToOriginal') }}
      </button>
      <button
        id="submitButton"
        class="submit-button"
        :disabled="disabled || !isValid"
        :aria-busy="disabled"
        :aria-label="disabled ? $t('problems.submission.testingWait') : (isValid ? $t('problems.submission.testSolution') : $t('problems.submission.codeTooShort'))"
        @click="handleSubmit"
      >
        <span
          v-if="!disabled"
          class="button-text"
        >{{ $t('problems.submission.testSolution') }}</span>
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
          <span class="visually-hidden">{{ $t('problems.submission.testingWait') }}</span>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * DebugFixInput - Input component for Debug Fix activities.
 *
 * Shows buggy code in an editable code editor.
 * Student edits the code to fix bugs and submits for testing.
 */
import { computed, onMounted, ref, watch } from 'vue'
import Editor from '@/features/editor/Editor.vue'
import type { ActivityProblem } from '../types'

interface Props {
  /** User's input code (v-model) */
  modelValue: string
  /** Current problem data */
  problem: ActivityProblem
  /** Whether input is disabled (during submission) */
  disabled?: boolean
  /** Editor theme */
  theme?: string
  /** Whether draft has been saved */
  draftSaved?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  theme: 'dark',
  draftSaved: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}>()

const editorRef = ref<InstanceType<typeof Editor> | null>(null)

// Get initial buggy code from problem config
const buggyCode = computed(() => {
  return props.problem?.input_config?.initial_code || ''
})

// Initialize with buggy code if modelValue is empty
onMounted(() => {
  if (!props.modelValue && buggyCode.value) {
    emit('update:modelValue', buggyCode.value)
  }
})

// Watch for problem changes to reset editor
watch(() => props.problem?.slug, () => {
  if (buggyCode.value && !props.modelValue) {
    emit('update:modelValue', buggyCode.value)
  }
})

// Computed value for v-model binding
const inputValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})

// Validation: check if input meets length requirements
const isValid = computed(() => {
  const minLength = props.problem?.input_config?.min_length ?? 10
  const maxLength = props.problem?.input_config?.max_length ?? 10000
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

function handleReset() {
  if (!props.disabled && buggyCode.value) {
    emit('update:modelValue', buggyCode.value)
  }
}
</script>

<style scoped>
/*
 * Styles for Debug Fix input component
 */

/* Container - positioned ancestor for absolute elements */
.debug-fix-input {
  position: relative;
}

/* Section Header */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-section);
  border-bottom: 1px solid var(--color-bg-input);
  margin-bottom: var(--spacing-sm);
}

.section-label {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-secondary);
}

/* Draft Indicator */
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

/* Code Editor Wrapper */
.code-editor-wrapper {
  padding: 0;
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  margin: var(--spacing-md) var(--spacing-xl);
  margin-bottom: 0;
  border-radius: var(--radius-base);
  overflow: hidden;
  transition: var(--transition-base);
}

.code-editor-wrapper:hover {
  border-color: var(--color-primary-gradient-start);
}

/* Action Row */
.action-row {
  display: flex;
  gap: var(--spacing-md);
  margin: var(--spacing-md) var(--spacing-xl) var(--spacing-sm);
}

/* Reset Button */
.reset-button {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-base);
}

.reset-button:hover:not(:disabled) {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
}

.reset-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Submit Button */
.submit-button {
  flex: 1;
  padding: var(--spacing-md) var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-on-filled);
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
