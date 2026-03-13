<template>
  <div
    class="form-section rounded-lg border-default transition-fast"
    style="position: relative;"
  >
    <h3>{{ $t('admin.editors.testCases') }}</h3>

    <div
      v-if="editor.ui.ui.loading"
      class="test-loading-overlay"
    >
      <div class="loading-spinner-container">
        <div class="spinner" />
        <div class="loading-text">
          {{ $t('admin.editors.runningTests') }}
        </div>
      </div>
    </div>

    <div class="test-actions">
      <div class="left-actions">
        <button
          type="button"
          class="btn-secondary rounded-base transition-fast"
          @click="addTestCase"
        >
          {{ $t('admin.editors.addTest') }}
        </button>
      </div>

      <button
        :disabled="!canTest || editor.ui.ui.loading"
        class="btn-primary rounded-base transition-fast"
        :title="canTestReason || $t('admin.editors.testAllCasesHint')"
        @click="$emit('test')"
      >
        {{ editor.ui.ui.loading ? $t('admin.editors.testing') : $t('admin.editors.testAllCases') }}
      </button>
    </div>

    <div class="test-cases-list">
      <div
        v-for="(testCase, index) in editor.testCases.testCases.value"
        :key="index"
        class="test-case hover-primary transition-fast"
        :class="{
          error: testCase.error,
          passed: editor.testCases.isTestPassed(index, editor.ui.ui.testResults),
          failed: editor.testCases.isTestFailed(index, editor.ui.ui.testResults)
        }"
      >
        <div
          class="test-case-row"
          :style="{ '--param-count': getParameterCount() }"
        >
          <span class="test-number">{{ index + 1 }}</span>

          <div
            v-if="editor.signature.functionParameters.value.length > 0"
            class="smart-parameters"
          >
            <div
              v-for="(param, paramIndex) in editor.signature.functionParameters.value"
              :key="paramIndex"
              class="smart-param-field"
            >
              <div class="param-input-container">
                <input
                  :value="editor.testCases.getParameterDisplayValue(testCase, paramIndex)"
                  :placeholder="editor.testCases.getParameterPlaceholder(param.type)"
                  class="param-input"
                  :class="{ 'param-error': editor.testCases.getParameterValidationError(testCase, paramIndex, editor.signature.functionParameters.value) }"
                  @input="editor.testCases.updateParameterValue(testCase, paramIndex, ($event.target as HTMLInputElement).value)"
                >
                <div
                  class="param-type-badge"
                  :class="editor.testCases.getParameterTypeClass(testCase, paramIndex, editor.signature.functionParameters.value)"
                  :title="editor.testCases.getParameterTypeInfo(testCase, paramIndex, editor.signature.functionParameters.value)"
                >
                  {{ editor.testCases.getParameterDetectedType(testCase, paramIndex) }}
                </div>
              </div>
              <div class="param-label">
                <span class="param-name">{{ param.name }}</span>
                <span class="param-expected-type">: {{ param.type }}</span>
              </div>
            </div>
          </div>

          <div
            v-else
            class="no-params-message"
          >
            {{ $t('admin.editors.noParameters') }}
          </div>

          <div class="output-field-container">
            <div class="output-input-container">
              <input
                :value="editor.testCases.getExpectedDisplay(testCase)"
                :placeholder="editor.testCases.getOutputPlaceholder(getReturnType())"
                class="param-input"
                :class="{ 'param-error': editor.testCases.getOutputValidationError(testCase, getReturnType()) }"
                @input="editor.testCases.updateExpected(testCase, ($event.target as HTMLInputElement).value)"
              >
              <div
                class="param-type-badge"
                :class="editor.testCases.getOutputTypeClass(testCase, getReturnType())"
                :title="editor.testCases.getOutputTypeInfo(testCase, getReturnType())"
              >
                {{ editor.testCases.getOutputDetectedType(testCase) }}
              </div>
            </div>
            <div class="param-label">
              <span class="param-name">{{ $t('admin.editors.output') }}</span>
              <span class="param-expected-type">: {{ getReturnType() }}</span>
            </div>
          </div>

          <div class="test-case-actions">
            <button
              type="button"
              class="remove-btn"
              @click="removeTestCase(index)"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
              >
                <circle
                  cx="8"
                  cy="8"
                  r="7"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                />
                <line
                  x1="5"
                  y1="8"
                  x2="11"
                  y2="8"
                  stroke="currentColor"
                  stroke-width="1.5"
                />
              </svg>
            </button>
            <div
              v-if="editor.ui.ui.testResults"
              class="status-badge"
              :class="editor.testCases.getStatusClass(index, editor.ui.ui.testResults)"
            >
              <div class="status-icon">
                {{ editor.testCases.getStatusText(index, editor.ui.ui.testResults) }}
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="testCase.error"
          class="error-msg"
        >
          {{ testCase.error }}
        </div>

        <div
          v-if="editor.testCases.isTestFailed(index, editor.ui.ui.testResults)"
          class="failure-msg"
        >
          {{ $t('admin.submissions.expected') }} {{ JSON.stringify(editor.ui.ui.testResults?.results[index]?.expected_output) }} |
          {{ $t('admin.submissions.got') }} {{ JSON.stringify(editor.ui.ui.testResults?.results[index]?.actual_output) }}
          <span v-if="editor.ui.ui.testResults?.results[index]?.error">
            | {{ $t('common.error') }}: {{ editor.ui.ui.testResults?.results[index]?.error }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * TestCasesSection - UI component for managing test cases.
 *
 * This component uses the useTestCases composable as the SINGLE SOURCE OF TRUTH
 * for all test case state and operations. It does not manage its own test case state.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { UseProblemEditorReturn } from '@/composables/admin/useProblemEditor'

interface Props {
  editor: UseProblemEditorReturn
}

const props = defineProps<Props>()
const { t } = useI18n()

defineEmits<{
  test: []
}>()

// ===== Computed =====

/**
 * Whether tests can be run - combines form validation with test case validation.
 */
const canTest = computed(() => {
  const functionSignature = (props.editor.form.form.function_signature || '').toString().trim()
  const referenceSolution = (props.editor.form.form.reference_solution || '').toString().trim()

  return !props.editor.ui.ui.loading &&
    functionSignature.length > 0 &&
    referenceSolution.length > 0 &&
    props.editor.testCases.canTest.value
})

/**
 * Reason why tests cannot be run.
 */
const canTestReason = computed(() => {
  const functionSignature = (props.editor.form.form.function_signature || '').toString().trim()
  const referenceSolution = (props.editor.form.form.reference_solution || '').toString().trim()

  if (props.editor.ui.ui.loading) {return t('admin.editors.currentlyLoading')}
  if (!functionSignature) {return t('admin.editors.functionSignatureRequired')}
  if (!referenceSolution) {return t('admin.editors.referenceSolutionRequired')}
  // Delegate to composable for test case-specific reasons
  return props.editor.testCases.canTestReason.value
})

// ===== Helper Functions =====

/**
 * Get parameter count for grid layout.
 */
function getParameterCount(): number {
  return props.editor.signature.functionParameters.value.length || 1
}

/**
 * Get return type from function signature.
 */
function getReturnType(): string {
  return props.editor.signature.returnType.value
}

// ===== Test Case Operations =====

/**
 * Add a new test case with correct number of input fields.
 */
function addTestCase() {
  props.editor.testCases.addTestCase(props.editor.signature.functionParameters.value.length)
}

/**
 * Remove a test case by index.
 */
function removeTestCase(index: number) {
  props.editor.testCases.removeTestCase(index)
}
</script>

<style scoped>
/* Common Utilities */
.transition-fast {
  transition: var(--transition-fast);
}

.rounded-base {
  border-radius: var(--radius-base);
}

.rounded-lg {
  border-radius: var(--radius-lg);
}

.border-default {
  border: 2px solid var(--color-bg-border);
}

.hover-primary:hover {
  border-color: var(--color-primary-gradient-start);
}

/* Form Section */
.form-section {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-base);
}

.form-section h3 {
  margin: 0 0 var(--spacing-xl) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-border);
}

/* Test Actions */
.test-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.left-actions {
  display: flex;
  gap: var(--spacing-md);
}

/* Test Cases List */
.test-cases-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* Test Case Cards */
.test-case {
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  background: var(--color-bg-panel);
  transition: var(--transition-fast);
  overflow: hidden;
}

.test-case.error {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.test-case.passed {
  border-color: var(--color-success);
  background: rgba(16, 185, 129, 0.05);
}

.test-case.failed {
  border-color: var(--color-error);
  background: rgba(239, 68, 68, 0.05);
}

/* Test Case Row */
.test-case-row {
  display: grid;
  grid-template-columns: 40px 1fr 1fr auto;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  align-items: stretch;
}

/* No parameters message */
.no-params-message {
  display: flex;
  align-items: center;
  color: var(--color-text-muted);
  font-style: italic;
  font-size: var(--font-size-sm);
  padding: var(--spacing-sm);
}

/* Smart Parameters Layout */
.smart-parameters {
  display: grid;
  grid-template-columns: repeat(var(--param-count, 1), 1fr);
  gap: var(--spacing-sm);
  align-items: start;
}

.smart-param-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.param-input-container,
.output-input-container {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.param-input {
  flex: 1;
  padding: var(--spacing-md);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
}

.param-input:focus {
  border-color: var(--color-primary-gradient-start);
  outline: none;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.param-input.param-error {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.param-input::placeholder {
  color: var(--color-text-muted);
  font-family: inherit;
}

/* Parameter Labels */
.param-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-xs);
  min-height: 18px;
}

.param-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.param-expected-type {
  color: var(--color-text-muted);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
}

/* Type Badges */
.param-type-badge {
  position: absolute;
  top: -8px;
  right: 8px;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
  z-index: 10;
  pointer-events: none;
  transform: scale(0.9);
  transform-origin: center;
}

.type-number {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #3b82f6;
}

.type-string {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #22c55e;
}

.type-boolean {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #f59e0b;
}

.type-collection {
  background: #ede9fe;
  color: #6b21a8;
  border: 1px solid #8b5cf6;
}

.type-none {
  background: var(--color-bg-muted);
  color: var(--color-text-muted);
  border: 1px solid var(--color-bg-border);
}

.type-any {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.type-invalid {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.type-error {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.type-optional {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #f59e0b;
}

/* Output Field Container */
.output-field-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.test-number {
  font-weight: 600;
  color: var(--color-text-primary);
  text-align: center;
  background: var(--color-bg-hover);
  border-radius: var(--radius-circle);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
}

/* Test Case Actions Container */
.test-case-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
}

/* Status Badge */
.status-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-circle);
  transition: var(--transition-fast);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.status-badge.passed {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.status-badge.failed {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
}

.status-icon {
  font-size: 14px;
  font-weight: bold;
  line-height: 1;
}

/* Remove Button */
.remove-btn {
  background: var(--color-bg-hover);
  border: 1.5px solid var(--color-bg-border);
  color: var(--color-text-muted);
  cursor: pointer;
  border-radius: var(--radius-circle);
  transition: var(--transition-fast);
  width: 32px;
  height: 32px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.remove-btn:hover {
  background: var(--color-error-bg);
  border-color: var(--color-error);
  color: var(--color-error);
  transform: scale(1.05);
}

.remove-btn svg {
  width: 16px;
  height: 16px;
  transition: var(--transition-fast);
}

/* Error and Failure Messages */
.error-msg,
.failure-msg {
  padding: var(--spacing-sm) var(--spacing-md);
  margin: 0 var(--spacing-md) var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-sm);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
}

.error-msg {
  background: var(--color-error-bg);
  color: var(--color-error-text);
  border-left: 3px solid var(--color-error);
}

.failure-msg {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-error-text);
  border-left: 3px solid var(--color-error);
}

/* Loading Overlay */
.test-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: var(--radius-lg);
}

.loading-spinner-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-bg-border);
  border-top-color: var(--color-primary-gradient-start);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  color: white;
  font-size: var(--font-size-sm);
}

/* Buttons */
.btn-primary {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: 2px solid var(--color-primary-gradient-start);
  padding: var(--spacing-md) var(--spacing-lg);
  font-weight: 600;
  font-size: var(--font-size-base);
  cursor: pointer;
  transition: var(--transition-base);
  box-shadow: var(--shadow-colored);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.btn-secondary {
  background: var(--color-bg-panel);
  color: var(--color-text-secondary);
  border: 2px solid var(--color-bg-border);
  padding: var(--spacing-md) var(--spacing-lg);
  font-weight: 600;
  font-size: var(--font-size-base);
  cursor: pointer;
  transition: var(--transition-base);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
}
</style>
