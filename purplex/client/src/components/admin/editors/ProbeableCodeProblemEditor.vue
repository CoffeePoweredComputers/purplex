<template>
  <div class="probeable-code-problem-editor">
    <!-- Basic Information -->
    <BasicInfoSection :editor="editor" />

    <!-- Function Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>{{ $t('admin.editors.probeable.functionConfiguration') }}</h3>
      <p class="section-description">
        {{ $t('admin.editors.probeable.codeConfigDescription') }}
      </p>

      <div class="form-group">
        <label for="function_signature">{{ $t('admin.editors.probeable.functionSignatureLabel') }}</label>
        <input
          id="function_signature"
          :value="editor.form.form.function_signature"
          type="text"
          required
          :placeholder="$t('admin.editors.probeable.functionSignaturePlaceholder')"
          @input="updateField('function_signature', ($event.target as HTMLInputElement).value)"
        >
        <!-- eslint-disable vue/no-v-html -- trusted i18n translation with inline code examples -->
        <p
          class="field-hint"
          v-html="$t('admin.editors.probeable.functionSignatureHint', { example: '<code>def f(x: int, y: str) -&gt; bool:</code>' })"
        />
        <!-- eslint-enable vue/no-v-html -->
      </div>

      <div class="form-group">
        <label for="reference_solution">{{ $t('admin.editors.probeable.referenceSolutionLabel') }}</label>
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
          {{ $t('admin.editors.probeable.oracleCodeHint') }}
        </p>
      </div>
    </div>

    <!-- Probe Settings -->
    <ProbeSettingsSection
      :config="editor.probeableCodeConfig"
      :probe-modes="probeModes"
    />

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

// ===== Validation =====

const isValid = computed(() => {
  const form = editor.value.form.form
  const title = (form.title || '').toString().trim()
  if (!title) {return false}

  // Require description
  const description = (form.description || '').toString().trim()
  if (!description) {return false}

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
</style>
