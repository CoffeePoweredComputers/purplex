<template>
  <div class="refute-problem-editor">
    <!-- Basic Information -->
    <BasicInfoSection :editor="editor" />

    <!-- Claim Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>{{ $t('admin.editors.refute.claimToDisprove') }}</h3>
      <p class="section-description">
        {{ $t('admin.editors.refute.claimDescription') }}
      </p>

      <div class="form-group">
        <label for="claim_text">{{ $t('admin.editors.refute.claimTextLabel') }}</label>
        <textarea
          id="claim_text"
          :value="editor.refuteConfig.claimText.value"
          :placeholder="$t('admin.editors.refute.claimTextPlaceholder')"
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
        <p class="field-hint">
          {{ $t('admin.editors.refute.claimTextHint') }}
        </p>
      </div>

      <div class="form-group">
        <label for="claim_predicate">{{ $t('admin.editors.refute.claimPredicateLabel') }}</label>
        <input
          id="claim_predicate"
          :value="editor.refuteConfig.claimPredicate.value"
          :class="{ 'input-error': editor.refuteConfig.predicateError.value }"
          type="text"
          required
          :placeholder="$t('admin.editors.refute.claimPredicatePlaceholder')"
          @input="editor.refuteConfig.setClaimPredicate(($event.target as HTMLInputElement).value)"
        >
        <div
          v-if="editor.refuteConfig.predicateError.value"
          class="field-error"
        >
          {{ editor.refuteConfig.predicateError.value }}
        </div>
        <p
          v-else
          class="field-hint"
          v-html="$t('admin.editors.refute.predicateHint', { true: '<code>True</code>', result: '<code>result</code>' })"
        />
      </div>

      <div class="predicate-examples">
        <h4>{{ $t('admin.editors.refute.predicateExamples') }}</h4>
        <table class="examples-table">
          <tr>
            <th>{{ $t('admin.editors.refute.claim') }}</th>
            <th>{{ $t('admin.editors.refute.predicate') }}</th>
          </tr>
          <tr>
            <td>{{ $t('admin.editors.refute.exampleClaimAlwaysPositive') }}</td>
            <td><code>{{ $t('admin.editors.refute.examplePredicatePositive') }}</code></td>
          </tr>
          <tr>
            <td>{{ $t('admin.editors.refute.exampleClaimNeverNone') }}</td>
            <td><code>{{ $t('admin.editors.refute.examplePredicateNone') }}</code></td>
          </tr>
          <tr>
            <td>{{ $t('admin.editors.refute.exampleClaimOutputGtInput') }}</td>
            <td><code>{{ $t('admin.editors.refute.examplePredicateGt') }}</code></td>
          </tr>
          <tr>
            <td>{{ $t('admin.editors.refute.exampleClaimReturnsSorted') }}</td>
            <td><code>{{ $t('admin.editors.refute.examplePredicateSorted') }}</code></td>
          </tr>
          <tr>
            <td>{{ $t('admin.editors.refute.exampleClaimSumEqualsLength') }}</td>
            <td><code>{{ $t('admin.editors.refute.examplePredicateSum') }}</code></td>
          </tr>
        </table>
      </div>

      <div class="claim-examples">
        <h4>{{ $t('admin.editors.refute.goodClaimExamples') }}</h4>
        <ul>
          <li><code>{{ $t('admin.editors.refute.exampleGoodClaim1') }}</code></li>
          <li><code>{{ $t('admin.editors.refute.exampleGoodClaim2') }}</code></li>
          <li><code>{{ $t('admin.editors.refute.exampleGoodClaim3') }}</code></li>
          <li><code>{{ $t('admin.editors.refute.exampleGoodClaim4') }}</code></li>
        </ul>
      </div>
    </div>

    <!-- Function Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>{{ $t('admin.editors.refute.functionConfiguration') }}</h3>
      <p class="section-description">
        {{ $t('admin.editors.refute.functionConfigDescription') }}
      </p>

      <div class="form-group">
        <label for="function_signature">{{ $t('admin.editors.refute.functionSignatureLabel') }}</label>
        <input
          id="function_signature"
          :value="editor.form.form.function_signature"
          type="text"
          required
          :placeholder="$t('admin.editors.refute.functionSignaturePlaceholder')"
          @input="updateField('function_signature', ($event.target as HTMLInputElement).value)"
        >
        <p
          class="field-hint"
          v-html="$t('admin.editors.refute.functionSignatureHint', { example: '<code>f(x: int, y: str) -&gt; bool</code>' })"
        />
      </div>

      <div class="form-group">
        <label for="reference_solution">{{ $t('admin.editors.refute.referenceSolutionLabel') }}</label>
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

// Access the editor from props
const editor = computed(() => props.editor)

// Helper to update form fields
function updateField(key: string, value: string) {
  editor.value.form.updateField(key as keyof typeof editor.value.form.form, value)
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
  border-color: var(--color-error) !important;
}

.field-error {
  color: var(--color-error);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

.field-warning {
  color: var(--color-warning);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
  padding: var(--spacing-sm);
  background: var(--color-warning-overlay);
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

/* Predicate Examples */
.predicate-examples {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--color-info-overlay);
  border: 1px solid var(--color-info);
  border-radius: var(--radius-base);
}

.predicate-examples h4 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-sm);
  color: var(--color-primary-gradient-start);
}

.examples-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.examples-table th,
.examples-table td {
  text-align: left;
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: 1px solid var(--color-bg-border);
}

.examples-table th {
  color: var(--color-text-secondary);
  font-weight: 600;
  background: var(--color-bg-hover);
}

.examples-table td {
  color: var(--color-text-muted);
}

.examples-table code {
  background: var(--color-bg-panel);
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  color: var(--color-primary-gradient-start);
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
  color: var(--color-text-primary);
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
</style>
