<template>
  <div class="eipl-problem-editor">
    <!-- Basic Information -->
    <BasicInfoSection :editor="editor" />

    <!-- Code Solution -->
    <div class="form-section rounded-lg border-default transition-fast">
      <h3>{{ $t('admin.editors.eipl.codeSolution') }}</h3>

      <div class="form-group">
        <label for="function_signature">{{ $t('admin.editors.eipl.functionSignatureLabel') }}</label>
        <input
          id="function_signature"
          :value="editor.form.form.function_signature"
          type="text"
          required
          :placeholder="$t('admin.editors.eipl.functionSignaturePlaceholder')"
          @input="updateField('function_signature', ($event.target as HTMLInputElement).value)"
        >
      </div>

      <div class="form-group">
        <label for="reference_solution">{{ $t('admin.editors.eipl.referenceSolutionLabel') }}</label>
        <EditorToolbar :editor="editor" />

        <div class="code-editor">
          <Editor
            ref="codeEditor"
            :value="String(editor.form.form.reference_solution || '')"
            :height="'300px'"
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

    <!-- Test Cases -->
    <TestCasesSection
      :editor="editor"
      @test="$emit('test')"
    />

    <!-- Hints Configuration -->
    <div class="form-section rounded-lg border-default transition-fast">
      <h3>{{ $t('admin.editors.eipl.hintsConfiguration') }}</h3>

      <div class="hint-tabs">
        <button
          type="button"
          class="hint-tab-button"
          :class="{ active: editor.hints.activeTab.value === 'variable_fade' }"
          @click="editor.hints.activeTab.value = 'variable_fade'"
        >
          {{ $t('admin.editors.eipl.variableFade') }}
        </button>
        <button
          type="button"
          class="hint-tab-button"
          :class="{ active: editor.hints.activeTab.value === 'subgoal_highlight' }"
          @click="editor.hints.activeTab.value = 'subgoal_highlight'"
        >
          {{ $t('admin.editors.eipl.subgoalHighlighting') }}
        </button>
        <button
          type="button"
          class="hint-tab-button"
          :class="{ active: editor.hints.activeTab.value === 'suggested_trace' }"
          @click="editor.hints.activeTab.value = 'suggested_trace'"
        >
          {{ $t('admin.editors.eipl.suggestedTrace') }}
        </button>
      </div>

      <!-- Variable Fade Configuration -->
      <div
        v-if="editor.hints.activeTab.value === 'variable_fade'"
        class="hint-config-panel"
      >
        <div class="hint-toggle">
          <label class="toggle-label">
            <input
              v-model="editor.hints.hints.variable_fade.is_enabled"
              type="checkbox"
              class="toggle-checkbox"
            >
            <span class="toggle-text">{{ $t('admin.editors.eipl.enableVariableFade') }}</span>
          </label>
          <div
            v-if="editor.hints.hints.variable_fade.is_enabled"
            class="attempts-config"
          >
            <label>{{ $t('admin.editors.eipl.minAttemptsRequired') }}</label>
            <input
              v-model.number="editor.hints.hints.variable_fade.min_attempts"
              type="number"
              min="0"
              max="10"
              class="attempts-input"
            >
          </div>
        </div>

        <div
          v-if="editor.hints.hints.variable_fade.is_enabled"
          class="mappings-section"
        >
          <h4>{{ $t('admin.editors.eipl.variableMappings') }}</h4>
          <div class="mappings-list">
            <div
              v-for="(mapping, index) in editor.hints.hints.variable_fade.content.mappings"
              :key="index"
              class="mapping-item"
            >
              <input
                v-model="mapping.from"
                :placeholder="$t('admin.editors.eipl.originalVariable')"
                class="mapping-input"
              >
              <span class="mapping-arrow">→</span>
              <input
                v-model="mapping.to"
                :placeholder="$t('admin.editors.eipl.replacement')"
                class="mapping-input"
              >
              <button
                type="button"
                class="remove-btn"
                @click="editor.hints.variableFade.removeMapping(index)"
              >
                ×
              </button>
            </div>
          </div>
          <div class="add-mapping">
            <input
              v-model="newVariableMapping.from"
              :placeholder="$t('admin.editors.eipl.originalVariable')"
              class="mapping-input"
              @keyup.enter="addVariableMapping"
            >
            <span class="mapping-arrow">→</span>
            <input
              v-model="newVariableMapping.to"
              :placeholder="$t('admin.editors.eipl.replacement')"
              class="mapping-input"
              @keyup.enter="addVariableMapping"
            >
            <button
              type="button"
              class="btn-secondary"
              :disabled="!newVariableMapping.from || !newVariableMapping.to"
              @click="addVariableMapping"
            >
              {{ $t('admin.editors.eipl.addMapping') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Subgoal Highlighting Configuration -->
      <div
        v-if="editor.hints.activeTab.value === 'subgoal_highlight'"
        class="hint-config-panel"
      >
        <div class="hint-toggle">
          <label class="toggle-label">
            <input
              v-model="editor.hints.hints.subgoal_highlight.is_enabled"
              type="checkbox"
              class="toggle-checkbox"
            >
            <span class="toggle-text">{{ $t('admin.editors.eipl.enableSubgoalHighlighting') }}</span>
          </label>
          <div
            v-if="editor.hints.hints.subgoal_highlight.is_enabled"
            class="attempts-config"
          >
            <label>{{ $t('admin.editors.eipl.minAttemptsRequired') }}</label>
            <input
              v-model.number="editor.hints.hints.subgoal_highlight.min_attempts"
              type="number"
              min="0"
              max="10"
              class="attempts-input"
            >
          </div>
        </div>

        <div
          v-if="editor.hints.hints.subgoal_highlight.is_enabled"
          class="subgoals-section"
        >
          <h4>{{ $t('admin.editors.eipl.subgoals') }}</h4>
          <div class="subgoals-list">
            <div
              v-for="(subgoal, index) in editor.hints.hints.subgoal_highlight.content.subgoals"
              :key="index"
              class="subgoal-item"
            >
              <div class="subgoal-header">
                <input
                  v-model="subgoal.title"
                  :placeholder="$t('admin.editors.eipl.subgoalTitle')"
                  class="subgoal-title-input"
                >
                <button
                  type="button"
                  class="remove-btn"
                  @click="editor.hints.subgoalHighlight.removeSubgoal(index)"
                >
                  ×
                </button>
              </div>
              <div class="subgoal-lines">
                <label>{{ $t('admin.editors.eipl.lines') }}</label>
                <input
                  v-model.number="subgoal.line_start"
                  type="number"
                  min="1"
                  :placeholder="$t('admin.editors.eipl.start')"
                  class="line-input"
                >
                <span>{{ $t('admin.editors.eipl.to') }}</span>
                <input
                  v-model.number="subgoal.line_end"
                  type="number"
                  :min="subgoal.line_start"
                  :placeholder="$t('admin.editors.eipl.end')"
                  class="line-input"
                >
              </div>
              <textarea
                v-model="subgoal.explanation"
                :placeholder="$t('admin.editors.eipl.subgoalExplanation')"
                rows="2"
                class="subgoal-explanation"
              />
            </div>
          </div>
          <div class="add-subgoal">
            <h5>{{ $t('admin.editors.eipl.addNewSubgoal') }}</h5>
            <input
              v-model="newSubgoal.title"
              :placeholder="$t('admin.editors.eipl.subgoalTitle')"
              class="subgoal-title-input"
            >
            <div class="subgoal-lines">
              <label>{{ $t('admin.editors.eipl.lines') }}</label>
              <input
                v-model.number="newSubgoal.line_start"
                type="number"
                min="1"
                :placeholder="$t('admin.editors.eipl.start')"
                class="line-input"
              >
              <span>{{ $t('admin.editors.eipl.to') }}</span>
              <input
                v-model.number="newSubgoal.line_end"
                type="number"
                :min="newSubgoal.line_start"
                :placeholder="$t('admin.editors.eipl.end')"
                class="line-input"
              >
            </div>
            <textarea
              v-model="newSubgoal.explanation"
              :placeholder="$t('admin.editors.eipl.subgoalExplanation')"
              rows="2"
              class="subgoal-explanation"
            />
            <button
              type="button"
              class="btn-secondary"
              :disabled="!newSubgoal.title || !newSubgoal.explanation"
              @click="addSubgoal"
            >
              {{ $t('admin.editors.eipl.addSubgoal') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Suggested Trace Configuration -->
      <div
        v-if="editor.hints.activeTab.value === 'suggested_trace'"
        class="hint-config-panel"
      >
        <div class="hint-toggle">
          <label class="toggle-label">
            <input
              v-model="editor.hints.hints.suggested_trace.is_enabled"
              type="checkbox"
              class="toggle-checkbox"
            >
            <span class="toggle-text">{{ $t('admin.editors.eipl.enableSuggestedTrace') }}</span>
          </label>
          <div
            v-if="editor.hints.hints.suggested_trace.is_enabled"
            class="attempts-config"
          >
            <label>{{ $t('admin.editors.eipl.minAttemptsRequired') }}</label>
            <input
              v-model.number="editor.hints.hints.suggested_trace.min_attempts"
              type="number"
              min="0"
              max="10"
              class="attempts-input"
            >
          </div>
        </div>

        <div
          v-if="editor.hints.hints.suggested_trace.is_enabled"
          class="suggested-trace-section"
        >
          <h4>{{ $t('admin.editors.eipl.configureSuggestedTrace') }}</h4>
          <p class="hint-description">
            {{ $t('admin.editors.eipl.suggestedTraceDescription') }}
          </p>

          <div class="form-group">
            <label class="form-label">
              <span class="label-text">{{ $t('admin.editors.eipl.suggestedFunctionCall') }}</span>
              <span class="label-required">*</span>
            </label>
            <div class="input-with-preview">
              <input
                v-model="editor.hints.hints.suggested_trace.content.suggested_call"
                type="text"
                :placeholder="$t('admin.editors.eipl.suggestedCallPlaceholder')"
                class="form-input suggested-call-input"
              >
              <div
                v-if="editor.hints.functionCallError.value"
                class="input-error"
              >
                {{ editor.hints.functionCallError.value }}
              </div>
            </div>
            <div
              v-if="editor.hints.hints.suggested_trace.content.suggested_call && !editor.hints.functionCallError.value"
              class="trace-preview-section"
            >
              <div class="preview-label">
                {{ $t('admin.editors.eipl.previewLabel') }}
              </div>
              <div class="suggested-trace">
                <div class="trace-content">
                  <span class="trace-label">{{ $t('admin.editors.eipl.tryTracing') }}</span>
                  <code class="trace-function">{{ editor.hints.hints.suggested_trace.content.suggested_call }}</code>
                  <button
                    v-if="editor.form.form.reference_solution"
                    type="button"
                    class="trace-btn"
                    @click="previewInPyTutor"
                  >
                    <span>🔍</span> {{ $t('admin.editors.eipl.trace') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Segmentation Configuration -->
    <SegmentationConfigSection :editor="editor" />

    <!-- Python Tutor Modal -->
    <PyTutorModal
      :is-visible="editor.hints.pyTutorVisible.value"
      :python-tutor-url="editor.hints.pyTutorUrl.value"
      @close="editor.hints.suggestedTrace.closePyTutor"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { ProblemEditorEmits, ProblemEditorProps } from './types'
import Editor from '@/features/editor/Editor.vue'
import PyTutorModal from '@/modals/PyTutorModal.vue'
import BasicInfoSection from './shared/BasicInfoSection.vue'
import TestCasesSection from './shared/TestCasesSection.vue'
import EditorToolbar from './shared/EditorToolbar.vue'
import SegmentationConfigSection from './shared/SegmentationConfigSection.vue'

// Props and emits
const props = defineProps<ProblemEditorProps>()
const emit = defineEmits<ProblemEditorEmits>()

// Alias for editor (convenience)
const editor = computed(() => props.editor)

// Template refs
const codeEditor = ref<any>(null)

// Local form state for adding new items
const newVariableMapping = ref({ from: '', to: '' })
const newSubgoal = ref({ line_start: 1, line_end: 1, title: '', explanation: '' })


// Validate and emit validation state
const isValid = computed(() => {
  const title = (editor.value.form.form.title || '').toString().trim()
  const functionSignature = (editor.value.form.form.function_signature || '').toString().trim()
  const referenceSolution = (editor.value.form.form.reference_solution || '').toString().trim()
  const testCases = editor.value.testCases.testCases.value

  return title.length > 0 &&
    functionSignature.length > 0 &&
    referenceSolution.length > 0 &&
    testCases.length > 0 &&
    !testCases.some(tc => tc.error)
})

watch(isValid, (valid) => {
  emit('validation-change', valid)
}, { immediate: true })

// Methods
function updateField(key: string, value: string) {
  editor.value.form.updateField(key as any, value as any)
}

// Hint management
function addVariableMapping() {
  if (newVariableMapping.value.from && newVariableMapping.value.to) {
    editor.value.hints.variableFade.addMapping(
      newVariableMapping.value.from,
      newVariableMapping.value.to
    )
    newVariableMapping.value = { from: '', to: '' }
  }
}

function addSubgoal() {
  if (newSubgoal.value.title && newSubgoal.value.explanation) {
    editor.value.hints.subgoalHighlight.addSubgoal({
      ...newSubgoal.value,
    })
    newSubgoal.value = { line_start: 1, line_end: 1, title: '', explanation: '' }
  }
}

function previewInPyTutor() {
  editor.value.hints.suggestedTrace.openPyTutor(editor.value.form.form.reference_solution)
}

// Lifecycle
onMounted(() => {
  // Configure ACE editor
  if ((window as any).ace) {
    (window as any).ace.config.set('basePath', 'https://cdn.jsdelivr.net/npm/ace-builds@1.15.0/src-noconflict/')
  }
})

// Expose validate method for parent
defineExpose({
  validate: () => isValid.value,
})
</script>

<style scoped>
/* Common utilities */
.transition-fast {
  transition: var(--transition-fast);
}

.rounded-lg {
  border-radius: var(--radius-lg);
}

.border-default {
  border: 2px solid var(--color-bg-border);
}

/* Form Sections */
.form-section {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-base);
  margin-bottom: var(--spacing-xxl);
}

.form-section h3 {
  margin: 0 0 var(--spacing-xl) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-border);
}

/* Form Groups */
.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
}

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
  transition: var(--transition-base);
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
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

/* Test Cases */
.test-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.left-actions {
  display: flex;
  gap: var(--spacing-sm);
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

.btn-primary {
  padding: var(--spacing-sm) var(--spacing-md);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-base);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.test-cases-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.test-case {
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-md);
}

.test-case.passed {
  border-color: var(--color-success);
  background: rgba(16, 185, 129, 0.1);
}

.test-case.failed {
  border-color: var(--color-error);
  background: rgba(239, 68, 68, 0.1);
}

.test-case.error {
  border-color: var(--color-warning);
  background: rgba(245, 158, 11, 0.1);
}

.test-case-row {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  gap: var(--spacing-md);
  align-items: start;
}

.test-number {
  background: var(--color-primary-gradient-start);
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xs);
  font-weight: bold;
}

.smart-parameters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.smart-param-field {
  flex: 1;
  min-width: 150px;
}

.param-input-container,
.output-input-container {
  position: relative;
}

.param-input {
  width: 100%;
  padding: var(--spacing-sm);
  padding-right: 50px;
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-family: monospace;
}

.param-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

.param-input.param-error {
  border-color: var(--color-error);
}

.param-type-badge {
  position: absolute;
  right: var(--spacing-xs);
  top: 50%;
  transform: translateY(-50%);
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  font-size: 10px;
  font-weight: bold;
  text-transform: uppercase;
}

.type-number {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.type-string {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.type-boolean {
  background: rgba(139, 92, 246, 0.2);
  color: #8b5cf6;
}

.type-list {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.type-tuple {
  background: rgba(6, 182, 212, 0.2);
  color: #06b6d4;
}

.type-dict {
  background: rgba(236, 72, 153, 0.2);
  color: #ec4899;
}

.type-none {
  background: rgba(107, 114, 128, 0.2);
  color: #6b7280;
}

.type-unknown {
  background: rgba(107, 114, 128, 0.2);
  color: #6b7280;
}

.type-error {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.param-label {
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.param-name {
  font-weight: 500;
}

.param-expected-type {
  color: var(--color-text-muted);
}

.no-params-message {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-style: italic;
}

.output-field-container {
  min-width: 150px;
}

.test-case-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
}

.remove-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--color-bg-border);
  background: var(--color-bg-panel);
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.remove-btn:hover {
  background: var(--color-error);
  color: white;
  border-color: var(--color-error);
}

.status-badge {
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: bold;
}

.status-passed {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.status-failed {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.error-msg,
.failure-msg {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: rgba(239, 68, 68, 0.1);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  color: var(--color-error);
}

.test-loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: var(--radius-lg);
}

.loading-spinner-container {
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-bg-border);
  border-top-color: var(--color-primary-gradient-start);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto var(--spacing-sm);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

/* Hints Configuration */
.hint-tabs {
  display: flex;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-lg);
  border-bottom: 2px solid var(--color-bg-border);
  padding-bottom: var(--spacing-sm);
}

.hint-tab-button {
  padding: var(--spacing-sm) var(--spacing-md);
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}

.hint-tab-button:hover {
  color: var(--color-text-primary);
}

.hint-tab-button.active {
  color: var(--color-primary-gradient-start);
  border-bottom-color: var(--color-primary-gradient-start);
}

.hint-config-panel {
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

.hint-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}

.toggle-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.toggle-text {
  font-weight: 500;
  color: var(--color-text-primary);
}

.attempts-config {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.attempts-config label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.attempts-input {
  width: 60px;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  text-align: center;
}

.mappings-section,
.subgoals-section,
.suggested-trace-section {
  margin-top: var(--spacing-lg);
}

.mappings-section h4,
.subgoals-section h4,
.suggested-trace-section h4 {
  margin-bottom: var(--spacing-md);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.mappings-list,
.subgoals-list {
  margin-bottom: var(--spacing-md);
}

.mapping-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.mapping-input {
  flex: 1;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.mapping-arrow {
  color: var(--color-text-muted);
  font-size: var(--font-size-lg);
}

.add-mapping {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-bg-border);
}

.subgoal-item {
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-sm);
}

.subgoal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.subgoal-title-input {
  flex: 1;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.subgoal-lines {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.subgoal-lines label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.line-input {
  width: 60px;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  text-align: center;
}

.subgoal-explanation {
  width: 100%;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  resize: vertical;
}

.add-subgoal {
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-bg-border);
}

.add-subgoal h5 {
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.hint-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-md);
}

.input-with-preview {
  margin-bottom: var(--spacing-md);
}

.suggested-call-input {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-family: monospace;
  font-size: var(--font-size-base);
}

.input-error {
  margin-top: var(--spacing-xs);
  color: var(--color-error);
  font-size: var(--font-size-xs);
}

.trace-preview-section {
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
}

.preview-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-sm);
}

.suggested-trace {
  padding: var(--spacing-md);
  background: rgba(102, 126, 234, 0.1);
  border-radius: var(--radius-base);
  border-left: 4px solid var(--color-primary-gradient-start);
}

.trace-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.trace-label {
  font-weight: 500;
  color: var(--color-text-primary);
}

.trace-function {
  font-family: monospace;
  background: var(--color-bg-input);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  color: var(--color-primary-gradient-start);
}

.trace-btn {
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-primary-gradient-start);
  color: white;
  border: none;
  border-radius: var(--radius-xs);
  cursor: pointer;
  font-size: var(--font-size-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.trace-btn:hover {
  opacity: 0.9;
}

/* Segmentation */
.segmentation-toggle {
  margin-bottom: var(--spacing-lg);
}

.segmentation-config-panel {
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

.segmentation-examples-section h4 {
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-primary);
}

.section-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-lg);
}

.threshold-setting {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
}

.threshold-control {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.threshold-input {
  width: 60px;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  text-align: center;
}

.threshold-help {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  line-height: 1.5;
}

.example-block {
  padding: var(--spacing-lg);
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-lg);
}

.example-block.relational {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.example-block.multi-structural {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.example-block h5 {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-primary);
}

.example-icon {
  font-size: var(--font-size-lg);
}

.example-help {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-md);
}

.segments-editor {
  margin-top: var(--spacing-md);
}

.segments-editor > label {
  display: block;
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.segment-item {
  margin-bottom: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--color-bg-panel);
  border-radius: var(--radius-xs);
}

.segment-row {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.segment-input {
  flex: 1;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.code-lines-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.lines-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.lines-input {
  width: 100px;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.btn-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid var(--color-bg-border);
  background: var(--color-bg-panel);
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  transition: all 0.2s ease;
}

.btn-icon:hover {
  background: var(--color-error);
  color: white;
  border-color: var(--color-error);
}

.btn-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
}

/* Animation */
.error-slide-enter-active,
.error-slide-leave-active {
  transition: all 0.3s ease;
}

.error-slide-enter-from,
.error-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
