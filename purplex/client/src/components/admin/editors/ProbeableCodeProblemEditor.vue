<template>
  <div class="probeable-code-problem-editor">
    <!-- Basic Information -->
    <BasicInfoSection :editor="editor" />

    <!-- Function Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>Function Configuration</h3>
      <p class="section-description">
        Define the function signature and reference solution (oracle code).
        The reference solution is used to evaluate student probe queries.
      </p>

      <div class="form-group">
        <label for="function_signature">Function Signature *</label>
        <input
          id="function_signature"
          :value="editor.form.form.function_signature"
          type="text"
          required
          placeholder="e.g., def mystery_function(x: int, y: str) -> bool:"
          @input="updateField('function_signature', ($event.target as HTMLInputElement).value)"
        >
        <p class="field-hint">
          Include type hints (e.g., <code>def f(x: int, y: str) -> bool:</code>)
        </p>
      </div>

      <div class="form-group">
        <label for="reference_solution">Reference Solution (Oracle Code) *</label>
        <EditorToolbar :editor="editor" />
        <div class="code-editor">
          <Editor
            ref="referenceEditor"
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
        <p class="field-hint">
          This code is hidden from students. It is executed when students probe with inputs.
        </p>
      </div>
    </div>

    <!-- Probe Settings -->
    <ProbeSettingsSection
      :config="editor.probeableCodeConfig"
      :probe-modes="probeModes"
      section-description="Configure how students can query the oracle function to discover its behavior."
      cooldown-attempts-hint="Number of code submissions required before probes are refilled"
    />

    <!-- Test Cases -->
    <TestCasesSection
      :editor="editor"
      @test="$emit('test')"
    />

    <!-- Student Preview -->
    <div class="form-section rounded-lg border-default">
      <h3>Student Preview</h3>
      <p class="section-description">
        This is approximately how the problem will appear to students.
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

        <div class="preview-instructions">
          <div class="instruction-label">
            Your Task:
          </div>
          <div class="instruction-text">
            Discover the behavior of the mystery function by probing it with different inputs.
            Once you understand what it does, write code that produces the same output.
          </div>
        </div>

        <div class="preview-signature-section">
          <div class="signature-label">
            <template v-if="editor.probeableCodeConfig.showFunctionSignature.value">
              Function Signature:
            </template>
            <template v-else>
              Function Parameters:
            </template>
          </div>
          <code class="signature-code">
            <template v-if="editor.probeableCodeConfig.showFunctionSignature.value">
              {{ editor.form.form.function_signature || 'def mystery(x: int, y: str) -> bool:' }}
            </template>
            <template v-else>
              {{ getParameterNamesOnly() }}
            </template>
          </code>
        </div>

        <div class="preview-probe-section">
          <div class="probe-label">
            Oracle Probe:
          </div>
          <div class="probe-info">
            <div class="probe-budget">
              <span class="budget-icon">?</span>
              <span class="budget-text">
                <template v-if="editor.probeableCodeConfig.probeMode.value === 'explore'">
                  Unlimited probes available
                </template>
                <template v-else>
                  {{ editor.probeableCodeConfig.maxProbes.value }} probes remaining
                </template>
              </span>
            </div>
            <div
              v-if="editor.probeableCodeConfig.probeMode.value === 'cooldown'"
              class="cooldown-info"
            >
              <span class="cooldown-text">
                After using all probes, submit {{ editor.probeableCodeConfig.cooldownAttempts.value }} time(s)
                to earn {{ editor.probeableCodeConfig.cooldownRefill.value }} more probes.
              </span>
            </div>
          </div>
          <div class="probe-placeholder">
            Students enter input values here and see the oracle's output...
          </div>
        </div>

        <div class="preview-code-section">
          <div class="code-label">
            Your Implementation:
          </div>
          <div class="code-placeholder">
            Students write their code implementation here...
          </div>
        </div>

        <div class="preview-test-cases">
          <div class="test-cases-label">
            Test Cases ({{ editor.testCases.testCases.value.length }}):
          </div>
          <div
            v-if="editor.testCases.testCases.value.length > 0"
            class="test-cases-preview"
          >
            Your code must pass all {{ editor.testCases.testCases.value.length }} test cases.
            <span class="test-note">(Test inputs are hidden until submission)</span>
          </div>
          <div
            v-else
            class="no-tests-warning"
          >
            No test cases defined. Add at least one test case to validate student code.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { ProblemEditorEmits, ProblemEditorProps } from './types'
import { log } from '@/utils/logger'
import { PROBE_MODES } from '@/composables/admin/useProbeableCodeConfig'
import Editor from '@/features/editor/Editor.vue'
import BasicInfoSection from './shared/BasicInfoSection.vue'
import TestCasesSection from './shared/TestCasesSection.vue'
import EditorToolbar from './shared/EditorToolbar.vue'
import ProbeSettingsSection from './shared/ProbeSettingsSection.vue'

// Props and emits
const props = defineProps<ProblemEditorProps>()
const emit = defineEmits<ProblemEditorEmits>()

// Local state
const referenceEditor = ref<InstanceType<typeof Editor> | null>(null)

// Access the editor from props
const editor = computed(() => props.editor)

// Probe modes for radio buttons
const probeModes = PROBE_MODES

// ===== Helper Functions =====

function updateField(key: string, value: string) {
  editor.value.form.updateField(key as keyof typeof editor.value.form.form, value)
}

function getParameterNamesOnly(): string {
  // Extract just parameter names from signature for hidden-signature mode
  const sig = editor.value.form.form.function_signature || ''
  const match = sig.match(/\(([^)]*)\)/)
  if (!match) {return 'Parameters: (unknown)'}

  const params = match[1]
    .split(',')
    .map(p => p.split(':')[0].trim())
    .filter(p => p)
    .join(', ')

  return `Parameters: (${params})`
}

// ===== Validation =====

const isValid = computed(() => {
  const form = editor.value.form.form
  const title = (form.title || '').toString().trim()
  if (!title) {return false}

  // Require function signature
  const signature = (form.function_signature || '').toString().trim()
  if (!signature) {return false}

  // Require reference solution
  const solution = (form.reference_solution || '').toString().trim()
  if (!solution) {return false}

  // Validate probe config
  const probeValidation = editor.value.probeableCodeConfig.validate()
  if (!probeValidation.valid) {return false}

  // Require at least one test case
  if (editor.value.testCases.testCases.value.length === 0) {return false}

  // No test case errors
  if (editor.value.testCases.testCases.value.some(tc => tc.error)) {return false}

  return true
})

// Emit validation state changes
watch(isValid, (valid) => {
  emit('validation-change', valid)
}, { immediate: true })

// Expose validate method for parent
function validate(): boolean {
  if (!isValid.value) {
    log.warn('ProbeableCode editor validation failed')
    return false
  }
  return true
}

defineExpose({ validate })

onMounted(() => {
  log.info('ProbeableCodeProblemEditor mounted', { isEditing: props.isEditing })

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
.probeable-code-problem-editor {
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

.form-section h4 {
  margin: var(--spacing-lg) 0 var(--spacing-md) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
}

.section-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-lg);
}

.subsection-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-md);
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
.form-group input[type="number"],
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

.form-group input[type="number"] {
  max-width: 120px;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
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

/* Code Editor */
.code-editor {
  border: 2px solid var(--color-bg-border);
  border-top: none;
  border-radius: 0 0 var(--radius-base) var(--radius-base);
  overflow: hidden;
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

.preview-instructions {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background: rgba(59, 130, 246, 0.1);
  border-left: 4px solid #3b82f6;
  border-radius: var(--radius-xs);
}

.instruction-label {
  font-size: var(--font-size-xs);
  color: #3b82f6;
  font-weight: 600;
  margin-bottom: var(--spacing-xs);
  text-transform: uppercase;
}

.instruction-text {
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.preview-signature-section {
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

.preview-probe-section {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background: rgba(168, 85, 247, 0.1);
  border: 1px solid rgba(168, 85, 247, 0.3);
  border-radius: var(--radius-base);
}

.probe-label {
  font-size: var(--font-size-xs);
  color: #a855f7;
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
  text-transform: uppercase;
}

.probe-info {
  margin-bottom: var(--spacing-md);
}

.probe-budget {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.budget-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: #a855f7;
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: var(--font-size-sm);
}

.budget-text {
  color: var(--color-text-primary);
  font-weight: 500;
}

.cooldown-info {
  padding-left: 32px;
}

.cooldown-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-style: italic;
}

.probe-placeholder {
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border: 2px dashed var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-muted);
  font-style: italic;
  font-size: var(--font-size-sm);
}

.preview-code-section {
  margin-bottom: var(--spacing-lg);
}

.code-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-xs);
}

.code-placeholder {
  padding: var(--spacing-lg);
  background: var(--color-bg-panel);
  border: 2px dashed var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-muted);
  font-style: italic;
  font-size: var(--font-size-sm);
  text-align: center;
}

.preview-test-cases {
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border-radius: var(--radius-xs);
}

.test-cases-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-xs);
}

.test-cases-preview {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.test-note {
  color: var(--color-text-muted);
  font-style: italic;
}

.no-tests-warning {
  font-size: var(--font-size-sm);
  color: var(--color-warning);
  font-style: italic;
}
</style>
