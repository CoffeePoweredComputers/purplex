<template>
  <!-- Question Text -->
  <div
    v-if="questionText"
    class="question-text"
  >
    {{ questionText }}
  </div>

  <div class="section-header">
    <div class="section-label">
      {{ problem?.display_config?.section_label || inputConfig?.label || $t('problems.mcq.sectionLabel') }}
    </div>
  </div>

  <div class="mcq-options-container">
    <div
      v-for="option in options"
      :key="option.id"
      class="mcq-option"
      :class="{
        'mcq-option--selected': isCheckboxMode ? selectedIds.has(option.id) : modelValue === option.id,
        'mcq-option--disabled': disabled
      }"
      @click="selectOption(option.id)"
    >
      <input
        :id="`option-${option.id}`"
        :type="isCheckboxMode ? 'checkbox' : 'radio'"
        :name="`mcq-${problem.slug}`"
        :value="option.id"
        :checked="isCheckboxMode ? selectedIds.has(option.id) : modelValue === option.id"
        :disabled="disabled"
        class="mcq-radio"
        @change.stop
      >
      <label
        :for="`option-${option.id}`"
        class="mcq-label"
      >
        <span class="option-marker">{{ getOptionMarker(option.id) }}</span>
        <span class="option-text">{{ option.text }}</span>
      </label>
    </div>
  </div>

  <button
    id="submitButton"
    class="submit-button"
    :disabled="disabled || (isCheckboxMode ? selectedIds.size === 0 : !modelValue)"
    :aria-busy="disabled"
    :aria-label="getButtonAriaLabel()"
    @click="handleSubmit"
  >
    <span
      v-if="!disabled"
      class="button-text"
    >{{ $t('problems.mcq.submitAnswer') }}</span>
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
      <span class="visually-hidden">{{ $t('problems.mcq.checkingWait') }}</span>
    </div>
  </button>
</template>

<script setup lang="ts">
/**
 * McqInput - Input component for Multiple Choice Question activities.
 *
 * Renders radio buttons (single-select) or checkboxes (multi-select) for MCQ problems.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ActivityProblem, InputConfig } from '../types'

interface McqOption {
  id: string
  text: string
}

interface Props {
  /** Selected option ID (v-model) — plain string for radio, JSON array for checkbox */
  modelValue: string
  /** Current problem data */
  problem: ActivityProblem
  /** Whether input is disabled (during submission) */
  disabled?: boolean
  /** Editor theme (unused for MCQ but part of interface) */
  theme?: string
  /** Whether draft has been saved (unused for MCQ) */
  draftSaved?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  theme: 'dark',
  draftSaved: false,
})

const { t } = useI18n()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}>()

// Get input config from problem
const inputConfig = computed<InputConfig | undefined>(() => props.problem.input_config)

// Detect checkbox mode from input config
const isCheckboxMode = computed(() => inputConfig.value?.type === 'checkbox')

// Internal set for checkbox mode
const selectedIds = ref<Set<string>>(new Set())

// Sync selectedIds from modelValue when in checkbox mode
watch(() => props.modelValue, (val) => {
  if (!isCheckboxMode.value) {return}
  if (!val) {
    selectedIds.value = new Set()
    return
  }
  try {
    const parsed = JSON.parse(val)
    if (Array.isArray(parsed)) {
      selectedIds.value = new Set(parsed)
      return
    }
  } catch { /* not JSON */ }
  selectedIds.value = val ? new Set([val]) : new Set()
}, { immediate: true })

// Reset selection state when navigating to a different problem
watch(() => props.problem.slug, () => {
  selectedIds.value = new Set()
})

// Get question text from problem (MCQ-specific field)
const questionText = computed<string>(() => {
  // Try question_text field first (MCQ problems), fallback to description
  return (props.problem as Record<string, unknown>).question_text as string || ''
})

// Get options from input config
const options = computed<McqOption[]>(() => {
  return inputConfig.value?.options || []
})

// Get option marker (A, B, C, etc.)
function getOptionMarker(optionId: string): string {
  const index = options.value.findIndex(opt => opt.id === optionId)
  return String.fromCharCode(65 + index) // A, B, C, D...
}

function selectOption(optionId: string) {
  if (props.disabled) {return}

  if (isCheckboxMode.value) {
    const next = new Set(selectedIds.value)
    if (next.has(optionId)) {
      next.delete(optionId)
    } else {
      next.add(optionId)
    }
    selectedIds.value = next
    emit('update:modelValue', JSON.stringify([...next]))
  } else {
    emit('update:modelValue', optionId)
  }
}

function handleSubmit() {
  if (props.disabled) {return}
  if (isCheckboxMode.value) {
    if (selectedIds.value.size > 0) {emit('submit')}
  } else {
    if (props.modelValue) {emit('submit')}
  }
}

function getButtonAriaLabel(): string {
  if (props.disabled) {
    return t('problems.mcq.checkingWait')
  }
  const hasSelection = isCheckboxMode.value ? selectedIds.value.size > 0 : !!props.modelValue
  if (!hasSelection) {
    return t('problems.mcq.selectFirst')
  }
  return t('problems.mcq.submitAnswer')
}
</script>

<style scoped>
/* Question Text */
.question-text {
  padding: var(--spacing-lg) var(--spacing-xl);
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  line-height: 1.6;
  border-bottom: 1px solid var(--color-bg-border);
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

/* MCQ Options Container */
.mcq-options-container {
  padding: var(--spacing-md) var(--spacing-xl);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* MCQ Option */
.mcq-option {
  display: flex;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-base);
}

.mcq-option:hover:not(.mcq-option--disabled) {
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-hover);
}

.mcq-option--selected {
  border-color: var(--color-primary-gradient-start);
  background: var(--color-primary-overlay);
}

.mcq-option--disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* Radio Input */
.mcq-radio {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

/* Label */
.mcq-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  cursor: pointer;
  width: 100%;
}

.mcq-option--disabled .mcq-label {
  cursor: not-allowed;
}

/* Option Marker (A, B, C, D) */
.option-marker {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--color-bg-hover);
  border-radius: var(--radius-circle);
  font-weight: 700;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  flex-shrink: 0;
  transition: var(--transition-base);
}

.mcq-option--selected .option-marker {
  background: var(--color-primary-gradient-start);
  color: var(--color-text-on-filled);
}

/* Option Text */
.option-text {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  line-height: 1.5;
}

/* Submit Button */
.submit-button {
  margin: var(--spacing-md) var(--spacing-xl) var(--spacing-sm);
  width: calc(100% - calc(var(--spacing-xl) * 2));
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
