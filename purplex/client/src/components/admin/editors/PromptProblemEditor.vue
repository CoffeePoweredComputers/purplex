<template>
  <div class="prompt-problem-editor">
    <!-- Basic Information -->
    <BasicInfoSection :editor="editor" />

    <!-- Display Mode Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>{{ $t('admin.editors.prompt.displayMode') }}</h3>
      <p class="section-description">
        {{ $t('admin.editors.prompt.displayModeDescription') }}
      </p>

      <div class="form-group">
        <label for="display_mode">{{ $t('admin.editors.prompt.displayMode') }}</label>
        <select
          id="display_mode"
          :value="editor.promptConfig.displayMode.value"
          @change="editor.promptConfig.setDisplayMode(($event.target as HTMLSelectElement).value as 'image' | 'terminal' | 'function_table')"
        >
          <option value="image">{{ $t('admin.editors.prompt.displayModeImage') }}</option>
          <option value="terminal">{{ $t('admin.editors.prompt.displayModeTerminal') }}</option>
          <option value="function_table">{{ $t('admin.editors.prompt.displayModeFunctionTable') }}</option>
        </select>
      </div>

      <!-- IMAGE MODE -->
      <template v-if="editor.promptConfig.isImageMode.value">
        <div class="form-group">
          <label for="image_url">{{ $t('admin.editors.prompt.imageUrlLabel') }}</label>
          <input
            id="image_url"
            type="url"
            :value="editor.promptConfig.imageUrl.value"
            :class="{ 'input-error': !editor.promptConfig.isValidUrl.value }"
            placeholder="https://example.com/image.png"
            @input="editor.promptConfig.setImageUrl(($event.target as HTMLInputElement).value)"
          >
          <p
            v-if="!editor.promptConfig.isValidUrl.value"
            class="field-error"
          >
            {{ $t('admin.editors.prompt.invalidUrl') }}
          </p>
        </div>

        <div class="form-group">
          <label for="image_alt">{{ $t('admin.editors.prompt.altTextLabel') }}</label>
          <input
            id="image_alt"
            type="text"
            :value="editor.promptConfig.altText.value"
            :placeholder="$t('admin.editors.prompt.altTextPlaceholder')"
            @input="editor.promptConfig.setAltText(($event.target as HTMLInputElement).value)"
          >
          <p class="field-hint">
            {{ $t('admin.editors.prompt.altTextHint') }}
          </p>
        </div>

        <!-- Image Preview -->
        <div
          v-if="editor.promptConfig.hasImage.value && editor.promptConfig.isValidUrl.value"
          class="image-preview"
        >
          <label>{{ $t('admin.editors.prompt.preview') }}</label>
          <div class="preview-container">
            <img
              :src="editor.promptConfig.imageUrl.value"
              :alt="editor.promptConfig.altText.value || $t('admin.editors.prompt.imagePreviewAlt')"
              @error="handleImageError"
              @load="handleImageLoad"
            >
            <div
              v-if="imageLoadError"
              class="preview-error"
            >
              {{ $t('admin.editors.prompt.imageLoadError') }}
            </div>
          </div>
        </div>

        <div
          v-else-if="!editor.promptConfig.hasImage.value"
          class="image-placeholder"
        >
          <div class="placeholder-content">
            <span class="placeholder-icon">&#128444;</span>
            <p>{{ $t('admin.editors.prompt.enterImageUrl') }}</p>
          </div>
        </div>
      </template>

      <!-- TERMINAL MODE -->
      <template v-else-if="editor.promptConfig.isTerminalMode.value">
        <div class="terminal-editor">
          <div
            v-for="(run, ri) in terminalRuns"
            :key="keyFor(run)"
            class="terminal-run-editor"
          >
            <div class="run-header">
              <label>{{ $t('admin.editors.prompt.runLabel') }} {{ ri + 1 }}</label>
              <button
                v-if="terminalRuns.length > 1"
                type="button"
                class="btn-remove-small"
                @click="removeTerminalRun(ri)"
              >
                &times;
              </button>
            </div>
            <div
              v-for="(interaction, ii) in run.interactions"
              :key="keyFor(interaction)"
              class="interaction-row"
            >
              <select
                :value="interaction.type"
                class="interaction-type-select"
                @change="updateInteractionType(ri, ii, ($event.target as HTMLSelectElement).value as 'input' | 'output')"
              >
                <option value="output">{{ $t('admin.editors.prompt.interactionOutput') }}</option>
                <option value="input">{{ $t('admin.editors.prompt.interactionInput') }}</option>
              </select>
              <input
                type="text"
                :value="interaction.text"
                :placeholder="$t('admin.editors.prompt.interactionText')"
                class="interaction-text-input"
                @input="updateInteractionText(ri, ii, ($event.target as HTMLInputElement).value)"
              >
              <button
                v-if="run.interactions.length > 1"
                type="button"
                class="btn-remove-small"
                @click="removeInteraction(ri, ii)"
              >
                &times;
              </button>
            </div>
            <button
              type="button"
              class="btn-add-small"
              @click="addInteraction(ri)"
            >
              {{ $t('admin.editors.prompt.addInteraction') }}
            </button>
          </div>
          <button
            type="button"
            class="btn-add"
            @click="addTerminalRun"
          >
            {{ $t('admin.editors.prompt.addRun') }}
          </button>
        </div>

        <!-- Terminal Preview -->
        <div
          v-if="terminalRuns.length > 0"
          class="terminal-preview"
        >
          <label>{{ $t('admin.editors.prompt.terminalPreview') }}</label>
          <TerminalDisplay :runs="terminalRuns" />
        </div>
      </template>

      <!-- FUNCTION TABLE MODE -->
      <template v-else-if="editor.promptConfig.isFunctionTableMode.value">
        <div class="function-table-editor">
          <div
            v-for="(call, ci) in functionTableCalls"
            :key="keyFor(call)"
            class="call-row"
          >
            <div class="call-field">
              <label v-if="ci === 0">{{ $t('admin.editors.prompt.callArgs') }}</label>
              <input
                type="text"
                :value="formatArgs(call.args)"
                :placeholder="$t('admin.editors.prompt.callArgsPlaceholder')"
                @change="updateCallArgs(ci, ($event.target as HTMLInputElement).value)"
              >
            </div>
            <div class="call-field">
              <label v-if="ci === 0">{{ $t('admin.editors.prompt.callReturnValue') }}</label>
              <input
                type="text"
                :value="formatReturnValue(call.return_value)"
                :placeholder="$t('admin.editors.prompt.callReturnPlaceholder')"
                @change="updateCallReturnValue(ci, ($event.target as HTMLInputElement).value)"
              >
            </div>
            <div class="call-actions">
              <label v-if="ci === 0">&nbsp;</label>
              <button
                v-if="functionTableCalls.length > 1"
                type="button"
                class="btn-remove-small"
                @click="removeCall(ci)"
              >
                &times;
              </button>
            </div>
          </div>
          <button
            type="button"
            class="btn-add"
            @click="addCall"
          >
            {{ $t('admin.editors.prompt.addCall') }}
          </button>
        </div>

        <!-- Function Table Preview -->
        <div
          v-if="functionTableCalls.length > 0"
          class="table-preview"
        >
          <label>{{ $t('admin.editors.prompt.tablePreview') }}</label>
          <FunctionCallTable
            :function-name="String(editor.form.form.function_name || 'f')"
            :function-signature="String(editor.form.form.function_signature || '')"
            :calls="functionTableCalls"
          />
        </div>
      </template>
    </div>

    <!-- Code Solution -->
    <div class="form-section rounded-lg border-default">
      <h3>{{ $t('admin.editors.prompt.codeSolution') }}</h3>
      <p class="section-description">
        {{ $t('admin.editors.prompt.codeSolutionDescription') }}
      </p>

      <div class="form-group">
        <label for="function_signature">{{ $t('admin.editors.prompt.functionSignatureLabel') }}</label>
        <input
          id="function_signature"
          :value="editor.form.form.function_signature"
          type="text"
          required
          :placeholder="$t('admin.editors.prompt.functionSignaturePlaceholder')"
          @input="updateField('function_signature', ($event.target as HTMLInputElement).value)"
        >
      </div>

      <div class="form-group">
        <label for="reference_solution">{{ $t('admin.editors.prompt.referenceSolutionLabel') }}</label>
        <div class="code-editor">
          <Editor
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { ProblemEditorEmits, ProblemEditorProps } from './types'
import type { ProblemFormState } from '@/composables/admin/useProblemForm'
import type { FunctionCall, TerminalInteraction, TerminalRun } from '@/types'
import { log } from '@/utils/logger'
import Editor from '@/features/editor/Editor.vue'
import TerminalDisplay from '@/components/ui/TerminalDisplay.vue'
import FunctionCallTable from '@/components/ui/FunctionCallTable.vue'
import BasicInfoSection from './shared/BasicInfoSection.vue'
import TestCasesSection from './shared/TestCasesSection.vue'

const props = defineProps<ProblemEditorProps>()
const emit = defineEmits<ProblemEditorEmits>()

// Local state
const imageLoadError = ref(false)
let nextKey = 0
const keyMap = new WeakMap<object, number>()
function keyFor(obj: object): number {
  if (!keyMap.has(obj)) { keyMap.set(obj, nextKey++) }
  return keyMap.get(obj)!
}

// Access the editor from props
const editor = computed(() => props.editor)

// Helper to update form fields
function updateField<K extends keyof ProblemFormState>(key: K, value: ProblemFormState[K]) {
  editor.value.form.updateField(key, value)
}

// ===== Terminal mode helpers =====

const terminalRuns = computed<TerminalRun[]>(() => editor.value.promptConfig.terminalRuns.value)

function addTerminalRun() {
  const runs: TerminalRun[] = [...terminalRuns.value, { interactions: [{ type: 'output', text: '' }] }]
  editor.value.promptConfig.setTerminalRuns(runs)
}

function removeTerminalRun(ri: number) {
  const runs = terminalRuns.value.filter((_, i) => i !== ri)
  editor.value.promptConfig.setTerminalRuns(runs)
}

function addInteraction(ri: number) {
  const runs = terminalRuns.value.map((run, i) => {
    if (i !== ri) {return run}
    return { ...run, interactions: [...run.interactions, { type: 'output' as const, text: '' }] }
  })
  editor.value.promptConfig.setTerminalRuns(runs)
}

function removeInteraction(ri: number, ii: number) {
  const runs = terminalRuns.value.map((run, i) => {
    if (i !== ri) {return run}
    return { ...run, interactions: run.interactions.filter((_, j) => j !== ii) }
  })
  editor.value.promptConfig.setTerminalRuns(runs)
}

function updateInteractionType(ri: number, ii: number, type: 'input' | 'output') {
  const runs = terminalRuns.value.map((run, i) => {
    if (i !== ri) {return run}
    return {
      ...run,
      interactions: run.interactions.map((intr: TerminalInteraction, j: number) =>
        j === ii ? { ...intr, type } : intr
      ),
    }
  })
  editor.value.promptConfig.setTerminalRuns(runs)
}

function updateInteractionText(ri: number, ii: number, text: string) {
  const runs = terminalRuns.value.map((run, i) => {
    if (i !== ri) {return run}
    return {
      ...run,
      interactions: run.interactions.map((intr: TerminalInteraction, j: number) =>
        j === ii ? { ...intr, text } : intr
      ),
    }
  })
  editor.value.promptConfig.setTerminalRuns(runs)
}

// ===== Function table mode helpers =====

const functionTableCalls = computed<FunctionCall[]>(() => editor.value.promptConfig.functionCalls.value)

function addCall() {
  const calls = [...functionTableCalls.value, { args: [], return_value: '' }]
  editor.value.promptConfig.setFunctionCalls(calls)
}

function removeCall(ci: number) {
  const calls = functionTableCalls.value.filter((_, i) => i !== ci)
  editor.value.promptConfig.setFunctionCalls(calls)
}

function updateCallArgs(ci: number, raw: string) {
  try {
    const parsed = JSON.parse(`[${raw}]`)
    const calls = functionTableCalls.value.map((call, i) =>
      i === ci ? { ...call, args: parsed } : call
    )
    editor.value.promptConfig.setFunctionCalls(calls)
  } catch {
    // Invalid JSON — ignore until valid
  }
}

function updateCallReturnValue(ci: number, raw: string) {
  try {
    const parsed = JSON.parse(raw)
    const calls = functionTableCalls.value.map((call, i) =>
      i === ci ? { ...call, return_value: parsed } : call
    )
    editor.value.promptConfig.setFunctionCalls(calls)
  } catch {
    // Invalid JSON — ignore until valid
  }
}

function formatArgs(args: unknown[]): string {
  return args.map(a => JSON.stringify(a)).join(', ')
}

function formatReturnValue(val: unknown): string {
  return JSON.stringify(val)
}

// ===== Image handling =====

function handleImageError() {
  imageLoadError.value = true
  log.warn('Failed to load prompt image', { url: editor.value.promptConfig.imageUrl.value })
}

function handleImageLoad() {
  imageLoadError.value = false
}

// Reset image error when URL changes
watch(() => editor.value.promptConfig.imageUrl.value, () => {
  imageLoadError.value = false
})

// ===== Validation =====

const isValid = computed(() => {
  const form = editor.value.form.form
  const title = (form.title || '').toString().trim()
  if (!title) {return false}

  // Require mode-specific data
  if (!editor.value.promptConfig.hasRequiredData.value) {return false}

  // Require code solution fields
  const signature = (form.function_signature || '').toString().trim()
  if (!signature) {return false}

  const solution = (form.reference_solution || '').toString().trim()
  if (!solution) {return false}

  // Require at least one test case
  if (editor.value.testCases.testCases.value.length === 0) {return false}

  return true
})

// Emit validation state changes
watch(isValid, (valid) => {
  emit('validation-change', valid)
}, { immediate: true })

// Expose validate method for parent
function validate(): boolean {
  if (!isValid.value) {
    log.warn('Prompt editor validation failed')
    return false
  }
  return true
}

defineExpose({ validate })

onMounted(() => {
  log.info('PromptProblemEditor mounted', { isEditing: props.isEditing })
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
.prompt-problem-editor {
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
.form-group input[type="url"],
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

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

.input-error {
  border-color: var(--color-error) !important;
}

.field-error {
  color: var(--color-error);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

.field-hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

/* Image Preview */
.image-preview {
  margin-top: var(--spacing-lg);
}

.image-preview label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
}

.preview-container {
  position: relative;
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  overflow: hidden;
  max-height: 400px;
}

.preview-container img {
  display: block;
  max-width: 100%;
  max-height: 400px;
  margin: 0 auto;
  object-fit: contain;
}

.preview-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--color-error);
  color: var(--color-text-on-filled);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
}

/* Image Placeholder */
.image-placeholder {
  background: var(--color-bg-input);
  border: 2px dashed var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-xxl);
}

.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  color: var(--color-text-muted);
}

.placeholder-icon {
  font-size: 48px;
  opacity: 0.5;
}

.placeholder-content p {
  margin: 0;
  font-size: var(--font-size-sm);
}

/* Code Editor */
.code-editor {
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  overflow: hidden;
}

/* Terminal Editor */
.terminal-editor {
  margin-top: var(--spacing-md);
}

.terminal-run-editor {
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.run-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-sm);
}

.run-header label {
  color: var(--color-text-secondary);
  font-weight: 600;
  font-size: var(--font-size-sm);
}

.interaction-row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  margin-bottom: var(--spacing-xs);
}

.interaction-type-select {
  width: 100px;
  flex-shrink: 0;
  padding: var(--spacing-sm);
  background: var(--color-bg-panel);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.interaction-text-input {
  flex: 1;
  padding: var(--spacing-sm);
  background: var(--color-bg-panel);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-family: 'Courier New', Courier, monospace;
}

.interaction-text-input:focus,
.interaction-type-select:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

/* Function Table Editor */
.function-table-editor {
  margin-top: var(--spacing-md);
}

.call-row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: flex-end;
  margin-bottom: var(--spacing-sm);
}

.call-field {
  flex: 1;
}

.call-field label {
  display: block;
  margin-bottom: var(--spacing-xs);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-xs);
}

/* stylelint-disable-next-line no-descending-specificity */
.call-field input {
  width: 100%;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-family: 'Courier New', Courier, monospace;
}

.call-field input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

.call-actions {
  flex-shrink: 0;
}

/* Shared buttons */
.btn-add {
  background: none;
  border: 2px dashed var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-muted);
  padding: var(--spacing-sm) var(--spacing-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  transition: var(--transition-base);
  width: 100%;
  margin-top: var(--spacing-sm);
}

.btn-add-small {
  background: none;
  border: 2px dashed var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: var(--transition-base);
  width: auto;
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-sm);
}

.btn-add:hover,
.btn-add-small:hover {
  border-color: var(--color-primary-gradient-start);
  color: var(--color-primary-gradient-start);
}

.btn-remove-small {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: var(--font-size-lg);
  line-height: 1;
  padding: var(--spacing-xs);
  transition: var(--transition-base);
}

.btn-remove-small:hover {
  color: var(--color-error);
}

/* Preview sections */
.terminal-preview,
.table-preview {
  margin-top: var(--spacing-lg);
}

.terminal-preview > label,
.table-preview > label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
}
</style>
