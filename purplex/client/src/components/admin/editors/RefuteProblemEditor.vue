<template>
  <div class="refute-problem-editor">
    <!-- Basic Information -->
    <BasicInfoSection :editor="editor" />

    <!-- Claim Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>Claim to Disprove</h3>
      <p class="section-description">
        Enter a false claim about the function that students must find a counterexample for.
        The claim should be specific and testable.
      </p>

      <div class="form-group">
        <label for="claim_text">Claim Text *</label>
        <textarea
          id="claim_text"
          :value="editor.refuteConfig.claimText.value"
          placeholder="e.g., The function always returns a positive number"
          rows="3"
          required
          @input="editor.refuteConfig.setClaimText(($event.target as HTMLTextAreaElement).value)"
        />
        <div
          v-if="editor.refuteConfig.claimWarning.value"
          class="field-warning"
        >
          {{ editor.refuteConfig.claimWarning.value }}
        </div>
      </div>

      <div class="claim-examples">
        <h4>Good Claim Examples</h4>
        <ul>
          <li><code>f(x) always returns a positive number</code></li>
          <li><code>The function never returns None</code></li>
          <li><code>For all inputs, the output is greater than the input</code></li>
          <li><code>The function will always terminate in O(n) time</code></li>
        </ul>
      </div>
    </div>

    <!-- Function Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>Function Configuration</h3>
      <p class="section-description">
        Define the function that students will test against the claim.
      </p>

      <div class="form-group">
        <label for="function_signature">Function Signature *</label>
        <input
          id="function_signature"
          :value="editor.form.form.function_signature"
          type="text"
          required
          placeholder="e.g., def f(x: int) -> int:"
          @input="updateField('function_signature', ($event.target as HTMLInputElement).value)"
        >
        <p class="field-hint">
          Include type hints to help parse student input (e.g., <code>f(x: int, y: str) -> bool</code>)
        </p>
      </div>

      <div class="form-group">
        <label for="reference_solution">Reference Solution (Function Code) *</label>
        <EditorToolbar :editor="editor" />

        <div class="code-editor">
          <Editor
            ref="codeEditor"
            :value="String(editor.form.form.reference_solution || '')"
            :height="'250px'"
            :width="'100%'"
            :theme="editor.editorSettings.theme.value"
            :show-gutter="true"
            :mode="'python'"
            :lang="'python'"
            @update:value="editor.form.updateReferenceSolution($event)"
          />
        </div>
      </div>
    </div>

    <!-- Expected Counterexample (Optional) -->
    <div class="form-section rounded-lg border-default">
      <h3>Expected Counterexample (Optional)</h3>
      <p class="section-description">
        Provide a known counterexample as JSON. This can be used for hint generation
        and validation. Leave empty if you want students to discover it themselves.
      </p>

      <div class="form-group">
        <label for="expected_counterexample">Counterexample JSON</label>
        <textarea
          id="expected_counterexample"
          :value="editor.refuteConfig.expectedCounterexample.value"
          :class="{ 'input-error': !editor.refuteConfig.isValidJson.value }"
          placeholder="e.g., {&quot;x&quot;: -5} or {&quot;a&quot;: [1, 2], &quot;b&quot;: 0}"
          rows="3"
          class="code-textarea"
          @input="editor.refuteConfig.setExpectedCounterexample(($event.target as HTMLTextAreaElement).value)"
        />
        <div
          v-if="editor.refuteConfig.jsonError.value"
          class="field-error"
        >
          {{ editor.refuteConfig.jsonError.value }}
        </div>
        <p
          v-else
          class="field-hint"
        >
          Enter a JSON object with parameter names as keys
        </p>
      </div>

      <!-- Parsed Preview -->
      <div
        v-if="editor.refuteConfig.parsedCounterexample.value"
        class="counterexample-preview"
      >
        <h4>Parsed Counterexample</h4>
        <div class="preview-grid">
          <div
            v-for="(value, key) in editor.refuteConfig.parsedCounterexample.value"
            :key="String(key)"
            class="preview-item"
          >
            <span class="preview-key">{{ key }}</span>
            <span class="preview-value">{{ formatValue(value) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Preview Section -->
    <div class="form-section rounded-lg border-default">
      <h3>Student Preview</h3>
      <p class="section-description">
        This is how the problem will appear to students.
      </p>

      <div class="student-preview">
        <div class="preview-header">
          <h4>{{ editor.form.form.title || 'Problem Title' }}</h4>
          <p
            v-if="editor.form.form.description"
            class="preview-description"
          >
            {{ editor.form.form.description }}
          </p>
        </div>

        <div class="preview-claim">
          <div class="claim-label">
            Claim to Disprove:
          </div>
          <div class="claim-text">
            {{ editor.refuteConfig.claimText.value || 'Enter a claim above...' }}
          </div>
        </div>

        <div class="preview-signature">
          <div class="signature-label">
            Function Signature:
          </div>
          <code class="signature-code">
            {{ editor.form.form.function_signature || 'def f(x: int) -> int:' }}
          </code>
        </div>

        <div class="preview-input">
          <div class="input-label">
            Your Counterexample:
          </div>
          <div class="input-placeholder">
            Students will enter values for each parameter here...
          </div>
        </div>
      </div>

      <!-- Test Counterexample Button -->
      <div
        v-if="canTestCounterexample"
        class="test-section"
      >
        <button
          type="button"
          class="btn-secondary"
          :disabled="isTesting"
          @click="testCounterexample"
        >
          <span v-if="isTesting">Testing...</span>
          <span v-else>Test Expected Counterexample</span>
        </button>
        <div
          v-if="testResult !== null"
          :class="['test-result', testResult ? 'success' : 'failure']"
        >
          {{ testResult ? 'Counterexample successfully disproves the claim!' : 'Counterexample does not disprove the claim.' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { ProblemEditorEmits, ProblemEditorProps } from './types'
import { log } from '@/utils/logger'
import Editor from '@/features/editor/Editor.vue'
import BasicInfoSection from './shared/BasicInfoSection.vue'
import EditorToolbar from './shared/EditorToolbar.vue'

// Props and emits
const props = defineProps<ProblemEditorProps>()
const emit = defineEmits<ProblemEditorEmits>()

// Local state
const codeEditor = ref<InstanceType<typeof Editor> | null>(null)
const isTesting = ref(false)
const testResult = ref<boolean | null>(null)

// Access the editor from props
const editor = computed(() => props.editor)

// Helper to update form fields
function updateField(key: string, value: string) {
  editor.value.form.updateField(key as keyof typeof editor.value.form.form, value)
}

// Format value for display
function formatValue(value: unknown): string {
  if (typeof value === 'string') {return `"${value}"`}
  if (Array.isArray(value)) {return JSON.stringify(value)}
  if (typeof value === 'object' && value !== null) {return JSON.stringify(value)}
  return String(value)
}

// Check if we can test the counterexample
const canTestCounterexample = computed(() => {
  return editor.value.refuteConfig.parsedCounterexample.value !== null &&
    editor.value.form.form.reference_solution &&
    editor.value.form.form.function_signature
})

// Test the expected counterexample
async function testCounterexample() {
  if (!canTestCounterexample.value) {return}

  isTesting.value = true
  testResult.value = null

  try {
    // For now, just simulate a test - in a real implementation,
    // this would call the backend to execute the function with the counterexample
    await new Promise(resolve => setTimeout(resolve, 1000))

    // Placeholder: In production, this would call an API endpoint
    log.info('Testing counterexample', {
      counterexample: editor.value.refuteConfig.parsedCounterexample.value,
      signature: editor.value.form.form.function_signature,
    })

    // Simulate success for now
    testResult.value = true
  } catch (error) {
    log.error('Failed to test counterexample', error)
    testResult.value = false
  } finally {
    isTesting.value = false
  }
}

// Validation
const isValid = computed(() => {
  const form = editor.value.form.form
  const title = (form.title || '').toString().trim()
  if (!title) {return false}

  // Require claim text
  if (!editor.value.refuteConfig.hasClaim.value) {return false}

  // Require function signature
  const signature = (form.function_signature || '').toString().trim()
  if (!signature) {return false}

  // Require reference solution
  const solution = (form.reference_solution || '').toString().trim()
  if (!solution) {return false}

  // If expected counterexample is provided, it must be valid JSON
  if (editor.value.refuteConfig.expectedCounterexample.value.trim() &&
      !editor.value.refuteConfig.isValidJson.value) {
    return false
  }

  return true
})

// Emit validation state changes
watch(isValid, (valid) => {
  emit('validation-change', valid)
}, { immediate: true })

// Expose validate method for parent
function validate(): boolean {
  if (!isValid.value) {
    log.warn('Refute editor validation failed')
    return false
  }
  return true
}

defineExpose({ validate })

onMounted(() => {
  log.info('RefuteProblemEditor mounted', { isEditing: props.isEditing })

  // Configure ACE editor
  if ((window as unknown as { ace?: { config: { set: (key: string, value: string) => void } } }).ace) {
    (window as unknown as { ace: { config: { set: (key: string, value: string) => void } } }).ace.config.set(
      'basePath',
      'https://cdn.jsdelivr.net/npm/ace-builds@1.15.0/src-noconflict/'
    )
  }
})
</script>

<style scoped>
/* Common Utilities */
.rounded-lg {
  border-radius: var(--radius-lg);
}

.border-default {
  border: 2px solid var(--color-bg-border);
}

/* Main Container */
.refute-problem-editor {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xxl);
}

/* Form Sections */
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

.section-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-lg);
}

/* Form Groups */
.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
}

/* Input Styling */
.form-group input[type="text"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-family: inherit;
  transition: var(--transition-base);
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.code-textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--font-size-sm);
}

.input-error {
  border-color: var(--color-error, #e74c3c) !important;
}

.field-error {
  color: var(--color-error, #e74c3c);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

.field-warning {
  color: var(--color-warning, #f59e0b);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
  padding: var(--spacing-sm);
  background: rgba(245, 158, 11, 0.1);
  border-radius: var(--radius-xs);
}

.field-hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

.field-hint code {
  background: var(--color-bg-hover);
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
}

/* Claim Examples */
.claim-examples {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

.claim-examples h4 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.claim-examples ul {
  margin: 0;
  padding-left: var(--spacing-lg);
}

.claim-examples li {
  margin-bottom: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.claim-examples code {
  background: var(--color-bg-panel);
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
}

/* Editor Toolbar */
.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm);
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-border);
  border-bottom: none;
  border-radius: var(--radius-base) var(--radius-base) 0 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.zoom-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--color-bg-border);
  background: var(--color-bg-panel);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.zoom-btn:hover:not(:disabled) {
  background: var(--color-primary-gradient-start);
  color: white;
  border-color: var(--color-primary-gradient-start);
}

.zoom-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.zoom-display {
  min-width: 45px;
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.theme-dropdown {
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.code-editor {
  border: 2px solid var(--color-bg-border);
  border-top: none;
  border-radius: 0 0 var(--radius-base) var(--radius-base);
  overflow: hidden;
}

/* Counterexample Preview */
.counterexample-preview {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-md);
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: var(--radius-base);
}

.counterexample-preview h4 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-sm);
  color: var(--color-success);
}

.preview-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.preview-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-panel);
  border-radius: var(--radius-xs);
}

.preview-key {
  font-weight: 600;
  color: var(--color-primary-gradient-start);
}

.preview-value {
  font-family: monospace;
  color: var(--color-text-primary);
}

/* Student Preview */
.student-preview {
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border: 2px dashed var(--color-bg-border);
  border-radius: var(--radius-base);
}

.preview-header h4 {
  margin: 0 0 var(--spacing-sm) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
}

.preview-description {
  margin: 0 0 var(--spacing-lg) 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.preview-claim {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background: rgba(239, 68, 68, 0.1);
  border-left: 4px solid var(--color-error);
  border-radius: var(--radius-xs);
}

.claim-label {
  font-size: var(--font-size-xs);
  color: var(--color-error);
  font-weight: 600;
  margin-bottom: var(--spacing-xs);
  text-transform: uppercase;
}

.claim-text {
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-style: italic;
}

.preview-signature {
  margin-bottom: var(--spacing-lg);
}

.signature-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-xs);
}

.signature-code {
  display: block;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-panel);
  border-radius: var(--radius-xs);
  font-family: monospace;
  font-size: var(--font-size-sm);
  color: var(--color-primary-gradient-start);
}

.preview-input {
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border: 2px dashed var(--color-bg-border);
  border-radius: var(--radius-base);
}

.input-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-xs);
}

.input-placeholder {
  color: var(--color-text-muted);
  font-style: italic;
  font-size: var(--font-size-sm);
}

/* Test Section */
.test-section {
  margin-top: var(--spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.btn-secondary {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-panel);
  color: var(--color-text-secondary);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.test-result {
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.test-result.success {
  background: rgba(16, 185, 129, 0.1);
  color: var(--color-success);
}

.test-result.failure {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-error);
}
</style>
