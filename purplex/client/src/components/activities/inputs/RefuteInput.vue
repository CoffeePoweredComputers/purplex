<template>
  <div class="refute-container">
    <!-- Claim Section -->
    <div class="claim-section">
      <div class="section-header">
        <div class="section-label">
          Claim to Disprove
        </div>
      </div>
      <div class="claim-text">
        {{ claimText }}
      </div>
    </div>

    <!-- Function Reference -->
    <div class="function-section">
      <div class="section-header">
        <div class="section-label">
          Function Signature
        </div>
      </div>
      <div class="function-signature">
        <code>{{ functionSignature }}</code>
      </div>
    </div>

    <!-- Reference Code (if enabled) -->
    <div
      v-if="showReferenceCode"
      class="code-section"
    >
      <div class="section-header">
        <div class="section-label">
          Reference Code
        </div>
      </div>
      <pre class="reference-code"><code>{{ problem.reference_solution }}</code></pre>
    </div>

    <!-- Input Section -->
    <div class="input-section">
      <div class="section-header">
        <div class="section-label">
          {{ inputConfig?.label || 'Enter function arguments as JSON' }}
        </div>
      </div>

      <div class="input-hint">
        Provide input values that will make the claim false.
        <span
          v-if="parameters.length > 0"
          class="param-hint"
        >
          Required parameters: {{ parameters.map(p => p.name).join(', ') }}
        </span>
      </div>

      <div class="json-input-wrapper">
        <textarea
          ref="inputRef"
          :value="modelValue"
          :placeholder="placeholder"
          :disabled="disabled"
          class="json-input"
          rows="3"
          spellcheck="false"
          @input="handleInput"
          @keydown.ctrl.enter="handleSubmit"
          @keydown.meta.enter="handleSubmit"
        />
        <div
          v-if="validationError"
          class="validation-error"
        >
          {{ validationError }}
        </div>
      </div>
    </div>

    <!-- Submit Button -->
    <button
      id="submitButton"
      class="submit-button"
      :disabled="disabled || !isValidJson"
      :aria-busy="disabled"
      :aria-label="getButtonAriaLabel()"
      @click="handleSubmit"
    >
      <span
        v-if="!disabled"
        class="button-text"
      >Find Counterexample</span>
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
        <span class="visually-hidden">Checking input, please wait</span>
      </div>
    </button>
  </div>
</template>

<script setup lang="ts">
/**
 * RefuteInput - Input component for Refute (Counterexample) activities.
 *
 * Allows students to enter JSON arguments to disprove a claim about a function.
 */
import { computed, ref, watch } from 'vue'
import type { ActivityProblem, InputConfig } from '../types'

interface FunctionParam {
  name: string
  type: string
}

interface Props {
  /** Current JSON input (v-model) */
  modelValue: string
  /** Current problem data */
  problem: ActivityProblem
  /** Whether input is disabled (during submission) */
  disabled?: boolean
  /** Editor theme (unused but part of interface) */
  theme?: string
  /** Whether draft has been saved (unused for refute) */
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

const inputRef = ref<HTMLTextAreaElement | null>(null)
const validationError = ref<string>('')

// Get configurations from problem
const inputConfig = computed<InputConfig | undefined>(() => props.problem.input_config)
const displayConfig = computed(() => props.problem.display_config)

// Extract claim and function info from display_config
// These come from the handler's get_problem_config
const claimText = computed<string>(() => {
  // Handler provides claim_text in display_config
  return displayConfig.value?.claim_text ||
         props.problem.description ||
         'No claim specified'
})

const functionSignature = computed<string>(() => {
  // Handler provides function_signature in display_config
  return displayConfig.value?.function_signature ||
         props.problem.function_signature ||
         'f(x)'
})

const showReferenceCode = computed<boolean>(() => {
  return displayConfig.value?.show_reference_code ?? false
})

const placeholder = computed<string>(() => {
  return inputConfig.value?.placeholder || '{"x": 0}'
})

const parameters = computed<FunctionParam[]>(() => {
  return (inputConfig.value?.parameters as FunctionParam[]) || []
})

// Validate JSON input
const isValidJson = computed<boolean>(() => {
  if (!props.modelValue.trim()) {
    return false
  }
  try {
    const parsed = JSON.parse(props.modelValue)
    return typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)
  } catch {
    return false
  }
})

// Watch for input changes and validate
watch(() => props.modelValue, (newValue) => {
  if (!newValue.trim()) {
    validationError.value = ''
    return
  }

  try {
    const parsed = JSON.parse(newValue)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      validationError.value = 'Input must be a JSON object (e.g., {"x": -5})'
    } else {
      // Check for required parameters
      const provided = new Set(Object.keys(parsed))
      const required = new Set(parameters.value.map(p => p.name))
      const missing = [...required].filter(name => !provided.has(name))

      if (missing.length > 0) {
        validationError.value = `Missing parameter(s): ${missing.join(', ')}`
      } else {
        validationError.value = ''
      }
    }
  } catch (e) {
    validationError.value = 'Invalid JSON format'
  }
})

function handleInput(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
}

function handleSubmit() {
  if (!props.disabled && isValidJson.value) {
    emit('submit')
  }
}

function getButtonAriaLabel(): string {
  if (props.disabled) {
    return 'Checking input, please wait'
  }
  if (!isValidJson.value) {
    return 'Please enter valid JSON input before submitting'
  }
  return 'Find Counterexample'
}
</script>

<style scoped>
/* Container */
.refute-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* Section Headers */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-bg-input);
}

.section-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Claim Section */
.claim-section {
  background: var(--color-bg-card);
  border-radius: var(--radius-base);
  overflow: hidden;
  border: 1px solid var(--color-bg-border);
}

.claim-text {
  padding: var(--spacing-md) var(--spacing-lg);
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  font-style: italic;
  background: rgba(234, 102, 102, 0.1);
  border-left: 4px solid var(--color-danger);
}

/* Function Section */
.function-section {
  background: var(--color-bg-card);
  border-radius: var(--radius-base);
  overflow: hidden;
  border: 1px solid var(--color-bg-border);
}

.function-signature {
  padding: var(--spacing-md) var(--spacing-lg);
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  color: var(--color-primary-gradient-start);
  background: var(--color-bg-input);
}

.function-signature code {
  background: transparent;
}

/* Code Section */
.code-section {
  background: var(--color-bg-card);
  border-radius: var(--radius-base);
  overflow: hidden;
  border: 1px solid var(--color-bg-border);
}

.reference-code {
  margin: 0;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-input);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.reference-code code {
  background: transparent;
}

/* Input Section */
.input-section {
  background: var(--color-bg-card);
  border-radius: var(--radius-base);
  overflow: hidden;
  border: 1px solid var(--color-bg-border);
}

.input-hint {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  background: var(--color-bg-input);
}

.param-hint {
  display: block;
  margin-top: var(--spacing-xs);
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
}

.json-input-wrapper {
  padding: var(--spacing-md) var(--spacing-lg);
}

.json-input {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  resize: vertical;
  transition: var(--transition-base);
}

.json-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
}

.json-input:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.json-input::placeholder {
  color: var(--color-text-muted);
}

.validation-error {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(234, 102, 102, 0.1);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  color: var(--color-danger);
}

/* Submit Button */
.submit-button {
  margin: var(--spacing-md);
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
}

.submit-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
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
