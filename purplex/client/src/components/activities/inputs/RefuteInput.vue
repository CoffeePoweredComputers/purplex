<template>
  <div class="refute-input">
    <!-- Claim Banner -->
    <div class="claim-banner">
      <span class="claim-label">{{ $t('problems.refute.disprove') }}</span>
      <span class="claim-text">"{{ claimText }}"</span>
    </div>

    <!-- Function Call Interface -->
    <div class="test-wrapper">
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
            :disabled="testing || disabled"
            :aria-label="`Enter value for ${param.name} (type: ${param.type})`"
            @keydown.enter="!testing && hasValidInputs && testInput()"
          >
        </template>
        <span class="fn-paren">)</span>
        <span class="fn-arrow">→</span>
        <span
          class="fn-result"
          :class="{
            'has-result': lastResult !== null,
            'result-flash': showResultFlash,
            'is-disproven': lastDisproven
          }"
        >
          {{ lastResult !== null ? formatOutput(lastResult) : '?' }}
        </span>
      </div>

      <button
        class="test-btn"
        :disabled="testing || !hasValidInputs"
        @click="testInput"
      >
        <template v-if="testing">
          <span class="spinner" />
          <span>{{ $t('problems.refute.testing') }}</span>
        </template>
        <template v-else>
          <span>{{ $t('problems.refute.test') }}</span>
        </template>
      </button>
    </div>

    <!-- Test Error -->
    <div
      v-if="testError"
      class="test-error"
    >
      {{ testError }}
    </div>

    <!-- Attempt History -->
    <div
      v-if="attempts.length > 0"
      class="attempt-history"
    >
      <div
        v-for="(attempt, idx) in attempts"
        :key="idx"
        class="attempt-row"
        :class="{ 'is-selected': selectedAttempt === idx }"
        @click="selectAttempt(idx)"
      >
        <span class="attempt-call">{{ formatCall(attempt.input) }}</span>
        <span class="attempt-arrow">→</span>
        <span class="attempt-result">{{ formatOutput(attempt.result) }}</span>
        <span
          v-if="attempt.disproven"
          class="badge-success"
        >{{ $t('problems.refute.disproves') }}</span>
        <span
          v-else
          class="badge-muted"
        >{{ $t('problems.refute.claimHolds') }}</span>
      </div>
    </div>

    <!-- Submit Button (only when counterexample found) -->
    <button
      v-if="hasCounterexample"
      class="submit-button"
      :disabled="disabled"
      @click="submitCounterexample"
    >
      <span v-if="!disabled">
        {{ $t('problems.refute.submitCounterexample', { call: formatCall(counterexample!) }) }}
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

    <!-- No counterexample hint -->
    <div
      v-else-if="attempts.length > 0"
      class="hint-message"
    >
      {{ $t('problems.refute.keepTrying') }}
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * RefuteInput - Compact counterexample finder interface.
 *
 * Students test function inputs to find one that disproves the claim.
 * Uses function-call style interface similar to ProbePanel.
 */
import { computed, reactive, ref, watch } from 'vue'
import axios from 'axios'
import type { ActivityProblem } from '../types'
import { log } from '@/utils/logger'

interface FunctionParam {
  name: string
  type: string
}

interface TestAttempt {
  input: Record<string, unknown>
  result: unknown
  disproven: boolean
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
const attempts = ref<TestAttempt[]>([])
const testing = ref(false)
const testError = ref<string | null>(null)
const showResultFlash = ref(false)
const selectedAttempt = ref<number | null>(null)

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

const lastResult = computed(() => {
  if (attempts.value.length === 0) {return null}
  return attempts.value[0].result
})

const lastDisproven = computed(() => {
  if (attempts.value.length === 0) {return false}
  return attempts.value[0].disproven
})

const counterexample = computed<TestAttempt | null>(() => {
  return attempts.value.find(a => a.disproven) || null
})

const hasCounterexample = computed(() => counterexample.value !== null)

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

async function testInput() {
  if (testing.value || !hasValidInputs.value) {return}

  testing.value = true
  testError.value = null

  const inputArgs = buildInputArgs()

  try {
    const response = await axios.post(
      `/api/problems/${props.problem.slug}/test-counterexample/`,
      { input: inputArgs }
    )

    const { success, result, claim_disproven, error } = response.data

    if (!success) {
      testError.value = error || 'Execution failed'
      return
    }

    // Add to history (most recent first)
    attempts.value.unshift({
      input: inputArgs,
      result,
      disproven: claim_disproven
    })

    // Flash effect
    showResultFlash.value = true
    setTimeout(() => { showResultFlash.value = false }, 600)

    log.info('Refute test', { input: inputArgs, result, disproven: claim_disproven })

  } catch (err) {
    // Handle both AxiosError (direct axios) and APIError (service) shapes
    const apiErr = err as { error?: string; response?: { data?: { error?: string } } }
    testError.value = apiErr.error || apiErr.response?.data?.error || 'Test failed'
    log.error('Refute test failed', err)
  } finally {
    testing.value = false
  }
}

function selectAttempt(idx: number) {
  selectedAttempt.value = idx
  const attempt = attempts.value[idx]
  if (attempt.disproven) {
    // Pre-fill for submission
    emit('update:modelValue', JSON.stringify(attempt.input))
  }
}

function submitCounterexample() {
  if (!counterexample.value || props.disabled) {return}

  // Set the model value to the counterexample JSON
  emit('update:modelValue', JSON.stringify(counterexample.value.input))

  // Trigger submit
  emit('submit')
}

function formatCall(input: Record<string, unknown>): string {
  const args = parameters.value.map(p => {
    const val = input[p.name]
    return `${p.name}=${formatOutput(val)}`
  }).join(', ')
  return `${functionName.value}(${args})`
}

function formatOutput(value: unknown): string {
  if (value === null) {return 'None'}
  if (value === undefined) {return '?'}
  if (typeof value === 'string') {return `"${value}"`}
  if (typeof value === 'boolean') {return value ? 'True' : 'False'}
  if (Array.isArray(value)) {return JSON.stringify(value)}
  if (typeof value === 'object') {return JSON.stringify(value)}
  return String(value)
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

/* Test Wrapper */
.test-wrapper {
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  margin: var(--spacing-md) var(--spacing-lg);
  padding: var(--spacing-sm) var(--spacing-md);
  transition: border-color 0.2s ease;
}

.test-wrapper:focus-within {
  border-color: var(--color-primary-gradient-start);
}

.function-call {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  flex-wrap: wrap;
  margin-bottom: var(--spacing-sm);
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
  font-family: var(--font-family-mono);
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

.fn-arrow {
  color: var(--color-text-muted);
  margin: 0 var(--spacing-sm);
}

.fn-result {
  color: var(--color-text-muted);
  font-style: italic;
  min-width: 40px;
  text-align: center;
  transition: all 0.3s ease;
}

.fn-result.has-result {
  color: var(--color-text-primary);
  font-style: normal;
  font-weight: 600;
}

.fn-result.is-disproven {
  color: var(--color-success);
}

.fn-result.result-flash {
  animation: resultFlash 0.6s ease;
}

@keyframes resultFlash {
  0% { transform: scale(1); }
  30% { transform: scale(1.15); }
  100% { transform: scale(1); }
}

/* Test Button */
.test-btn {
  width: 100%;
  padding: var(--spacing-xs) var(--spacing-lg);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-on-filled);
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px var(--color-primary-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.test-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.test-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px var(--color-primary-glow);
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--color-overlay-strong);
  border-top-color: var(--color-text-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Test Error */
.test-error {
  margin: 0 var(--spacing-lg) var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-error-overlay);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-sm);
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

/* Attempt History */
.attempt-history {
  margin: 0 var(--spacing-lg) var(--spacing-md);
  max-height: 200px;
  overflow-y: auto;
}

.attempt-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-xs);
  background: var(--color-bg-hover);
  cursor: pointer;
  transition: background 0.15s ease;
}

.attempt-row:hover {
  background: var(--color-bg-input);
}

.attempt-row.is-selected {
  background: var(--color-bg-input);
  border: 1px solid var(--color-primary-gradient-start);
}

.attempt-call {
  color: var(--color-text-primary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attempt-arrow {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.attempt-result {
  color: var(--color-text-secondary);
  font-weight: 500;
  flex-shrink: 0;
}

.badge-success {
  background: var(--color-success-overlay);
  color: var(--color-success);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 600;
  flex-shrink: 0;
}

.badge-muted {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  flex-shrink: 0;
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
  opacity: 0.7;
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

/* Hint Message */
.hint-message {
  margin: 0 var(--spacing-lg) var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-section);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  text-align: center;
}
</style>
