<template>
  <div class="debug-fix-problem-editor">
    <!-- Basic Information -->
    <BasicInfoSection :editor="editor" />

    <!-- Function Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>Function Configuration</h3>
      <p class="section-description">
        Define the function signature and reference solution (correct code).
      </p>

      <div class="form-group">
        <label for="function_signature">Function Signature *</label>
        <input
          id="function_signature"
          :value="editor.form.form.function_signature"
          type="text"
          required
          placeholder="e.g., def calculate_average(numbers: list) -> float:"
          @input="updateField('function_signature', ($event.target as HTMLInputElement).value)"
        >
        <p class="field-hint">
          Include type hints (e.g., <code>def f(x: int, y: str) -> bool:</code>)
        </p>
      </div>

      <div class="form-group">
        <label for="reference_solution">Reference Solution (Correct Code) *</label>
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
      </div>
    </div>

    <!-- Buggy Code Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>Buggy Code</h3>
      <p class="section-description">
        Enter the code with intentional bugs. This is what students will see and need to fix.
      </p>

      <!-- Side-by-side view toggle -->
      <div class="view-toggle">
        <button
          type="button"
          :class="['toggle-btn', { active: viewMode === 'single' }]"
          @click="viewMode = 'single'"
        >
          Single View
        </button>
        <button
          type="button"
          :class="['toggle-btn', { active: viewMode === 'side-by-side' }]"
          @click="viewMode = 'side-by-side'"
        >
          Side-by-Side Comparison
        </button>
      </div>

      <!-- Single view mode -->
      <div
        v-if="viewMode === 'single'"
        class="form-group"
      >
        <label for="buggy_code">Buggy Code *</label>
        <EditorToolbar :editor="editor" />
        <div class="code-editor">
          <Editor
            ref="buggyEditor"
            :value="editor.debugFixConfig.buggyCode.value"
            :height="'300px'"
            :width="'100%'"
            :theme="editor.editorSettings.theme.value"
            :show-gutter="true"
            :mode="'python'"
            :lang="'python'"
            @update:value="editor.debugFixConfig.setBuggyCode($event)"
          />
        </div>
      </div>

      <!-- Side-by-side comparison mode -->
      <div
        v-else
        class="side-by-side-container"
      >
        <div class="code-panel">
          <div class="panel-header buggy-header">
            <span class="panel-title">Buggy Code (Student Sees)</span>
            <span class="panel-badge buggy-badge">Has Bugs</span>
          </div>
          <div class="code-editor">
            <Editor
              ref="buggyEditorSbs"
              :value="editor.debugFixConfig.buggyCode.value"
              :height="'300px'"
              :width="'100%'"
              :theme="editor.editorSettings.theme.value"
              :show-gutter="true"
              :mode="'python'"
              :lang="'python'"
              @update:value="editor.debugFixConfig.setBuggyCode($event)"
            />
          </div>
        </div>

        <div class="code-panel">
          <div class="panel-header reference-header">
            <span class="panel-title">Reference Solution</span>
            <span class="panel-badge reference-badge">Correct</span>
          </div>
          <div class="code-editor readonly-editor">
            <Editor
              :value="String(editor.form.form.reference_solution || '')"
              :height="'300px'"
              :width="'100%'"
              :theme="editor.editorSettings.theme.value"
              :show-gutter="true"
              :mode="'python'"
              :lang="'python'"
              :read-only="true"
            />
          </div>
        </div>
      </div>

      <!-- Validation warnings -->
      <div
        v-if="!codesDifferComputed && editor.debugFixConfig.hasBuggyCode.value"
        class="validation-warning"
      >
        <span class="warning-icon">!</span>
        Buggy code is identical to reference solution. Students need code with actual bugs to fix.
      </div>

      <div
        v-if="!editor.debugFixConfig.hasBuggyCode.value && editor.form.form.reference_solution"
        class="action-hint"
      >
        <button
          type="button"
          class="btn-secondary btn-sm"
          @click="copyReferenceAsBuggy"
        >
          Copy Reference as Starting Point
        </button>
        <span class="hint-text">
          Start with the correct code and introduce bugs
        </span>
      </div>
    </div>

    <!-- Bug Hints -->
    <div class="form-section rounded-lg border-default collapsible-section">
      <div
        class="section-header"
        @click="hintsExpanded = !hintsExpanded"
      >
        <h3>
          Bug Hints
          <span class="hint-count">
            ({{ editor.debugFixConfig.bugHints.value.length }})
          </span>
        </h3>
        <button
          type="button"
          class="expand-btn"
        >
          {{ hintsExpanded ? '-' : '+' }}
        </button>
      </div>

      <div
        v-show="hintsExpanded"
        class="section-content"
      >
        <p class="section-description">
          Add progressive hints that help students find bugs.
          Level 1 = vague hint, Level 2 = more specific, Level 3 = very specific.
        </p>

        <!-- Existing hints -->
        <div
          v-if="editor.debugFixConfig.bugHints.value.length > 0"
          class="hints-list"
        >
          <div
            v-for="(hint, index) in editor.debugFixConfig.bugHints.value"
            :key="index"
            class="hint-item"
            :class="`level-${hint.level}`"
          >
            <div class="hint-header">
              <div class="hint-level-selector">
                <label>Level:</label>
                <select
                  :value="hint.level"
                  class="level-select"
                  @change="updateHintLevel(index, parseInt(($event.target as HTMLSelectElement).value) as 1 | 2 | 3)"
                >
                  <option :value="1">
                    1 - Vague
                  </option>
                  <option :value="2">
                    2 - Moderate
                  </option>
                  <option :value="3">
                    3 - Specific
                  </option>
                </select>
              </div>
              <button
                type="button"
                class="remove-btn"
                title="Remove hint"
                @click="editor.debugFixConfig.removeHint(index)"
              >
                x
              </button>
            </div>
            <textarea
              :value="hint.text"
              rows="2"
              placeholder="Enter hint text..."
              class="hint-text-input"
              @input="updateHintText(index, ($event.target as HTMLTextAreaElement).value)"
            />
          </div>
        </div>

        <div
          v-else
          class="no-hints-message"
        >
          No hints added yet. Hints help struggling students find bugs.
        </div>

        <!-- Add new hint -->
        <div class="add-hint-form">
          <h4>Add New Hint</h4>
          <div class="new-hint-row">
            <div class="level-field">
              <label>Level:</label>
              <select
                v-model.number="editor.debugFixConfig.newHint.value.level"
                class="level-select"
              >
                <option :value="1">
                  1 - Vague
                </option>
                <option :value="2">
                  2 - Moderate
                </option>
                <option :value="3">
                  3 - Specific
                </option>
              </select>
            </div>
            <div class="text-field">
              <textarea
                v-model="editor.debugFixConfig.newHint.value.text"
                rows="2"
                placeholder="e.g., Check the loop condition on line 5"
                class="hint-text-input"
                @keydown.enter.ctrl="addNewHint"
              />
            </div>
            <button
              type="button"
              class="btn-secondary"
              :disabled="!editor.debugFixConfig.newHint.value.text.trim()"
              @click="addNewHint"
            >
              Add Hint
            </button>
          </div>
          <p class="level-guide">
            <strong>Level 1:</strong> "There's an off-by-one error somewhere"<br>
            <strong>Level 2:</strong> "Check the loop bounds"<br>
            <strong>Level 3:</strong> "Line 5: the loop should use &lt; instead of &lt;="
          </p>
        </div>

        <button
          v-if="editor.debugFixConfig.bugHints.value.length > 1"
          type="button"
          class="btn-secondary btn-sm sort-btn"
          @click="editor.debugFixConfig.sortHintsByLevel"
        >
          Sort Hints by Level
        </button>
      </div>
    </div>

    <!-- Behavior Settings -->
    <div class="form-section rounded-lg border-default">
      <h3>Behavior Settings</h3>

      <div class="toggle-setting">
        <label class="toggle-label">
          <input
            :checked="editor.debugFixConfig.allowCompleteRewrite.value"
            type="checkbox"
            class="toggle-checkbox"
            @change="editor.debugFixConfig.setAllowCompleteRewrite(($event.target as HTMLInputElement).checked)"
          >
          <span class="toggle-text">Allow Complete Rewrite</span>
        </label>
        <p class="setting-description">
          <span v-if="editor.debugFixConfig.allowCompleteRewrite.value">
            Students can rewrite the entire function from scratch.
          </span>
          <span v-else>
            Students should make minimal, targeted fixes to the buggy code.
            This is recommended for teaching debugging skills.
          </span>
        </p>
      </div>
    </div>

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
            The following code has bugs. Fix the code so that it passes all test cases.
            <span v-if="!editor.debugFixConfig.allowCompleteRewrite.value">
              Make minimal, targeted fixes rather than rewriting from scratch.
            </span>
          </div>
        </div>

        <div class="preview-code-section">
          <div class="code-label">
            Buggy Code to Fix:
          </div>
          <pre class="preview-code">{{ editor.debugFixConfig.buggyCode.value || '# Buggy code will appear here' }}</pre>
        </div>

        <div
          v-if="editor.debugFixConfig.bugHints.value.length > 0"
          class="preview-hints"
        >
          <div class="hints-label">
            Available Hints ({{ editor.debugFixConfig.bugHints.value.length }}):
          </div>
          <div class="hint-preview-list">
            <div
              v-for="(hint, index) in sortedHints"
              :key="index"
              class="hint-preview-item"
            >
              <span class="hint-level-badge">Level {{ hint.level }}</span>
              <span class="hint-preview-text">{{ truncateHint(hint.text) }}</span>
            </div>
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
            Your code must pass all {{ editor.testCases.testCases.value.length }} test cases to be marked correct.
          </div>
          <div
            v-else
            class="no-tests-warning"
          >
            No test cases defined. Add at least one test case.
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
import Editor from '@/features/editor/Editor.vue'
import BasicInfoSection from './shared/BasicInfoSection.vue'
import TestCasesSection from './shared/TestCasesSection.vue'
import EditorToolbar from './shared/EditorToolbar.vue'

// Props and emits
const props = defineProps<ProblemEditorProps>()
const emit = defineEmits<ProblemEditorEmits>()

// Local state
const referenceEditor = ref<InstanceType<typeof Editor> | null>(null)
const buggyEditor = ref<InstanceType<typeof Editor> | null>(null)
const buggyEditorSbs = ref<InstanceType<typeof Editor> | null>(null)
const viewMode = ref<'single' | 'side-by-side'>('single')
const hintsExpanded = ref(true)

// Access the editor from props
const editor = computed(() => props.editor)

// ===== Computed =====

const codesDifferComputed = computed(() => {
  return editor.value.debugFixConfig.codesDiffer(
    editor.value.form.form.reference_solution || ''
  )
})

const sortedHints = computed(() => {
  return [...editor.value.debugFixConfig.bugHints.value].sort((a, b) => a.level - b.level)
})

// ===== Helper Functions =====

function updateField(key: string, value: string) {
  editor.value.form.updateField(key as keyof typeof editor.value.form.form, value)
}

function copyReferenceAsBuggy() {
  const reference = editor.value.form.form.reference_solution || ''
  editor.value.debugFixConfig.setBuggyCode(reference)
}

function updateHintLevel(index: number, level: 1 | 2 | 3) {
  editor.value.debugFixConfig.updateHint(index, { level })
}

function updateHintText(index: number, text: string) {
  editor.value.debugFixConfig.updateHint(index, { text })
}

function addNewHint() {
  const hint = editor.value.debugFixConfig.newHint.value
  if (!hint.text.trim()) {return}

  editor.value.debugFixConfig.addHint({
    level: hint.level,
    text: hint.text,
  })

  // Reset the new hint form
  editor.value.debugFixConfig.newHint.value = { level: 1, text: '' }
}

function truncateHint(text: string, maxLength: number = 60): string {
  if (text.length <= maxLength) {return text}
  return text.substring(0, maxLength) + '...'
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

  // Require buggy code
  if (!editor.value.debugFixConfig.hasBuggyCode.value) {return false}

  // Buggy code must differ from reference
  if (!codesDifferComputed.value) {return false}

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
    log.warn('DebugFix editor validation failed')
    return false
  }
  return true
}

defineExpose({ validate })

onMounted(() => {
  log.info('DebugFixProblemEditor mounted', { isEditing: props.isEditing })

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
.debug-fix-problem-editor {
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

.readonly-editor {
  opacity: 0.8;
}

/* View Toggle */
.view-toggle {
  display: flex;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-xs);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  width: fit-content;
}

.toggle-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  background: transparent;
  border: none;
  border-radius: var(--radius-xs);
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: 500;
  transition: var(--transition-fast);
}

.toggle-btn:hover {
  color: var(--color-text-primary);
}

.toggle-btn.active {
  background: var(--color-bg-panel);
  color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-base);
}

/* Side-by-side container */
.side-by-side-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-lg);
}

.code-panel {
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-base) var(--radius-base) 0 0;
  border: 2px solid var(--color-bg-border);
  border-bottom: none;
}

.buggy-header {
  background: rgba(239, 68, 68, 0.1);
}

.reference-header {
  background: rgba(16, 185, 129, 0.1);
}

.panel-title {
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.panel-badge {
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.buggy-badge {
  background: var(--color-error);
  color: white;
}

.reference-badge {
  background: var(--color-success);
  color: white;
}

/* Validation Warning */
.validation-warning {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: var(--radius-base);
  color: var(--color-warning);
  font-size: var(--font-size-sm);
}

.warning-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: var(--color-warning);
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: var(--font-size-xs);
}

/* Action Hint */
.action-hint {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

.hint-text {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

/* Collapsible Section */
.collapsible-section .section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  margin: calc(-1 * var(--spacing-xl));
  margin-bottom: 0;
  padding: var(--spacing-xl);
  padding-bottom: var(--spacing-base);
}

.collapsible-section .section-header h3 {
  margin: 0;
  padding: 0;
  border: none;
}

.hint-count {
  font-weight: normal;
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
}

.expand-btn {
  width: 28px;
  height: 28px;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-secondary);
  font-size: var(--font-size-lg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
}

.expand-btn:hover {
  background: var(--color-primary-gradient-start);
  color: white;
  border-color: var(--color-primary-gradient-start);
}

.section-content {
  padding-top: var(--spacing-lg);
  border-top: 2px solid var(--color-bg-border);
  margin-top: var(--spacing-lg);
}

/* Hints List */
.hints-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.hint-item {
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  border-left: 4px solid var(--color-bg-border);
}

.hint-item.level-1 {
  border-left-color: #10b981;
}

.hint-item.level-2 {
  border-left-color: #f59e0b;
}

.hint-item.level-3 {
  border-left-color: #ef4444;
}

.hint-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.hint-level-selector {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.hint-level-selector label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.level-select {
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.hint-text-input {
  width: 100%;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  resize: vertical;
}

.hint-text-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

.no-hints-message {
  padding: var(--spacing-lg);
  text-align: center;
  color: var(--color-text-muted);
  font-style: italic;
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-lg);
}

/* Add Hint Form */
.add-hint-form {
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  border: 2px dashed var(--color-bg-border);
}

.add-hint-form h4 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.new-hint-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: var(--spacing-md);
  align-items: start;
}

.level-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.level-field label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.text-field {
  flex: 1;
}

.level-guide {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-bg-border);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  line-height: 1.6;
}

.sort-btn {
  margin-top: var(--spacing-md);
}

/* Toggle Setting */
.toggle-setting {
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  margin-bottom: var(--spacing-sm);
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

.setting-description {
  margin: 0;
  padding-left: 26px;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
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

.preview-code-section {
  margin-bottom: var(--spacing-lg);
}

.code-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-xs);
}

.preview-code {
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border-radius: var(--radius-xs);
  font-family: monospace;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  white-space: pre-wrap;
  overflow-x: auto;
  margin: 0;
}

.preview-hints {
  margin-bottom: var(--spacing-lg);
}

.hints-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-sm);
}

.hint-preview-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.hint-preview-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-panel);
  border-radius: var(--radius-xs);
}

.hint-level-badge {
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: 600;
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
}

.hint-preview-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
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

.no-tests-warning {
  font-size: var(--font-size-sm);
  color: var(--color-warning);
  font-style: italic;
}

/* Buttons */
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

.btn-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.remove-btn {
  width: 24px;
  height: 24px;
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
}

.remove-btn:hover {
  background: var(--color-error);
  color: white;
  border-color: var(--color-error);
}
</style>
