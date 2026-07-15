<template>
  <div class="refute-input">
    <!-- Claim Banner -->
    <div class="claim-banner">
      <span class="claim-label">{{ $t('problems.refute.disprove') }}</span>
      <span class="claim-text">"{{ claimText }}"</span>
    </div>

    <!-- Function Call Interface -->
    <div class="call-wrapper">
      <div class="function-call">
        <span class="fn-name">{{ functionName }}</span>
        <span class="fn-paren">(</span>
        <template
          v-for="(param, i) in parameters"
          :key="param.name"
        >
          <span
            v-if="i > 0"
            class="fn-comma"
          >, </span>
          <span class="param-name">{{ param.name }}</span>
          <span class="param-eq">=</span>
          <input
            :id="`param-${param.name}`"
            v-model="inputs[param.name]"
            type="text"
            class="param-input"
            :placeholder="param.type"
            :disabled="disabled"
            :aria-label="`Enter value for ${param.name} (type: ${param.type})`"
            @keydown.enter="!disabled && hasValidInputs && submit()"
          >
        </template>
        <span class="fn-paren">)</span>
      </div>
    </div>

    <!-- Submit Button -->
    <button
      class="submit-button"
      :disabled="disabled || !hasValidInputs"
      @click="submit"
    >
      <span v-if="!disabled">
        {{ $t('problems.refute.submit') }}
      </span>
      <div
        v-else
        class="loading-content"
      >
        <div class="bouncing-dots">
          <span class="dot" />
          <span class="dot" />
          <span class="dot" />
        </div>
      </div>
    </button>
  </div>
</template>

<script setup lang="ts">
/**
 * RefuteInput - Counterexample submission interface.
 *
 * Students enter function arguments and submit them directly. Each submission
 * is graded server-side and shown in the results list (RefuteFeedback), where
 * the student can see what input was tried, what it returned, and whether it
 * disproved the claim. There is no separate client-side "test" step.
 */
import { computed, reactive, watch } from 'vue'
import type { ActivityProblem } from '../types'

interface FunctionParam {
  name: string
  type: string
}

interface Props {
  modelValue: string
  problem: ActivityProblem
  disabled?: boolean
  theme?: string
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

// State
const inputs = reactive<Record<string, string>>({})

// Get config from problem
const displayConfig = computed(() => props.problem.display_config || {})
const inputConfig = computed(() => props.problem.input_config || {})

const claimText = computed(() =>
  displayConfig.value.claim_text ||
  props.problem.description ||
  'No claim specified'
)

const functionSignature = computed(() =>
  displayConfig.value.function_signature ||
  props.problem.function_signature ||
  'f(x)'
)

const functionName = computed(() =>
  displayConfig.value.function_name ||
  extractFunctionName(functionSignature.value)
)

const parameters = computed<FunctionParam[]>(() => {
  const params = inputConfig.value.parameters as FunctionParam[] | undefined
  if (params && params.length > 0) {return params}
  return parseParameters(functionSignature.value)
})

// Initialize inputs for each parameter
watch(parameters, (params) => {
  params.forEach(p => {
    if (!(p.name in inputs)) {
      inputs[p.name] = ''
    }
  })
}, { immediate: true })

// Computed
const hasValidInputs = computed(() => {
  return parameters.value.every(p => {
    const val = inputs[p.name]?.trim()
    return val && val.length > 0
  })
})

// Methods
function extractFunctionName(signature: string): string {
  const match = signature.match(/(?:def\s+)?(\w+)\s*\(/)
  return match ? match[1] : 'f'
}

function parseParameters(signature: string): FunctionParam[] {
  const match = signature.match(/\(([^)]*)\)/)
  if (!match) {return []}

  const paramsStr = match[1].trim()
  if (!paramsStr) {return []}

  return paramsStr.split(',').map(p => {
    const parts = p.trim().split(':')
    return {
      name: parts[0].trim(),
      type: parts[1]?.trim() || 'Any'
    }
  })
}

function parseInputValue(value: string, type: string): unknown {
  const trimmed = value.trim()

  // Handle common types
  if (type.toLowerCase().includes('int')) {
    const num = parseInt(trimmed, 10)
    return isNaN(num) ? trimmed : num
  }
  if (type.toLowerCase().includes('float')) {
    const num = parseFloat(trimmed)
    return isNaN(num) ? trimmed : num
  }
  if (type.toLowerCase().includes('bool')) {
    if (trimmed.toLowerCase() === 'true') {return true}
    if (trimmed.toLowerCase() === 'false') {return false}
    return trimmed
  }
  if (type.toLowerCase().includes('str')) {
    // Remove quotes if present
    if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
        (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
      return trimmed.slice(1, -1)
    }
    return trimmed
  }
  if (type.toLowerCase().includes('list') || trimmed.startsWith('[')) {
    try {
      return JSON.parse(trimmed)
    } catch {
      return trimmed
    }
  }
  if (type.toLowerCase().includes('dict') || trimmed.startsWith('{')) {
    try {
      return JSON.parse(trimmed)
    } catch {
      return trimmed
    }
  }

  // Try to parse as JSON, fallback to string
  try {
    return JSON.parse(trimmed)
  } catch {
    return trimmed
  }
}

function buildInputArgs(): Record<string, unknown> {
  const args: Record<string, unknown> = {}
  parameters.value.forEach(p => {
    args[p.name] = parseInputValue(inputs[p.name], p.type)
  })
  return args
}

function submit() {
  if (props.disabled || !hasValidInputs.value) {return}

  // Serialize the arguments as JSON — the backend refute handler parses
  // raw_input as a JSON object of function arguments.
  emit('update:modelValue', JSON.stringify(buildInputArgs()))
  emit('submit')
}
</script>

<style scoped>
.refute-input {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* Claim Banner */
.claim-banner {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-error-overlay);
  border-bottom: 2px solid var(--color-error);
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.claim-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-danger);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.claim-text {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  font-style: italic;
}

/* Call Wrapper */
.call-wrapper {
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  margin: var(--spacing-md) var(--spacing-lg);
  padding: var(--spacing-md);
  transition: border-color 0.2s ease;
}

.call-wrapper:focus-within {
  border-color: var(--color-primary-gradient-start);
}

.function-call {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-family: var(--font-family-mono, Monaco, Menlo, 'Ubuntu Mono', monospace);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  flex-wrap: wrap;
}

.fn-name {
  color: var(--color-info);
  font-weight: 600;
}

.fn-paren,
.fn-comma {
  color: var(--color-text-muted);
}

.param-name {
  color: var(--color-text-secondary);
}

.param-eq {
  color: var(--color-text-muted);
  margin: 0 2px;
}

.param-input {
  width: 80px;
  height: 28px;
  padding: 0 var(--spacing-sm);
  background: var(--color-bg-primary);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono, Monaco, Menlo, 'Ubuntu Mono', monospace);
  font-size: var(--font-size-sm);
  text-align: center;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.param-input::placeholder {
  color: var(--color-text-muted);
  opacity: 0.5;
  font-size: var(--font-size-xs);
}

.param-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-overlay);
}

.param-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Submit Button */
.submit-button {
  margin: var(--spacing-md) var(--spacing-lg);
  width: calc(100% - calc(var(--spacing-lg) * 2));
  padding: var(--spacing-md) var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-success) 0%, var(--color-success-dark) 100%);
  color: var(--color-text-on-filled);
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px var(--color-success-overlay);
}

.submit-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.submit-button:hover:not(:disabled) {
  box-shadow: 0 6px 20px var(--color-success-overlay);
}

/* Loading Animation */
.loading-content {
  display: flex;
  align-items: center;
  justify-content: center;
}

.bouncing-dots {
  display: flex;
  gap: var(--spacing-sm);
}

.dot {
  width: 8px;
  height: 8px;
  background: var(--color-text-primary);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

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
</style>
