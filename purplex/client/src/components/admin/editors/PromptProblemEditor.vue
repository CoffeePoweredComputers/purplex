<template>
  <div class="prompt-problem-editor">
    <!-- Basic Information -->
    <BasicInfoSection :editor="editor" />

    <!-- Prompt Image Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>Prompt Image</h3>
      <p class="section-description">
        Configure the image that students will see and explain.
      </p>

      <div class="form-group">
        <label for="image_url">Image URL *</label>
        <input
          id="image_url"
          type="url"
          :value="editor.promptConfig.imageUrl.value"
          :class="{ 'input-error': !editor.promptConfig.isValidUrl.value }"
          placeholder="https://example.com/image.png"
          @input="editor.promptConfig.setImageUrl(($event.target as HTMLInputElement).value)"
        >
        <p v-if="!editor.promptConfig.isValidUrl.value" class="field-error">
          Please enter a valid URL
        </p>
      </div>

      <div class="form-group">
        <label for="image_alt">Alt Text</label>
        <input
          id="image_alt"
          type="text"
          :value="editor.promptConfig.altText.value"
          placeholder="Describe the image for accessibility"
          @input="editor.promptConfig.setAltText(($event.target as HTMLInputElement).value)"
        >
        <p class="field-hint">
          Describe the image content for screen readers
        </p>
      </div>

      <!-- Image Preview -->
      <div v-if="editor.promptConfig.hasImage.value && editor.promptConfig.isValidUrl.value" class="image-preview">
        <label>Preview</label>
        <div class="preview-container">
          <img
            :src="editor.promptConfig.imageUrl.value"
            :alt="editor.promptConfig.altText.value || 'Prompt image preview'"
            @error="handleImageError"
            @load="handleImageLoad"
          >
          <div v-if="imageLoadError" class="preview-error">
            Failed to load image. Please check the URL.
          </div>
        </div>
      </div>

      <div v-else-if="!editor.promptConfig.hasImage.value" class="image-placeholder">
        <div class="placeholder-content">
          <span class="placeholder-icon">🖼️</span>
          <p>Enter an image URL above to see a preview</p>
        </div>
      </div>
    </div>

    <!-- Code Solution -->
    <div class="form-section rounded-lg border-default">
      <h3>Code Solution</h3>
      <p class="section-description">
        The reference solution that the image represents.
      </p>

      <div class="form-group">
        <label for="function_signature">Function Signature (with type hints) *</label>
        <input
          id="function_signature"
          :value="editor.form.form.function_signature"
          type="text"
          required
          placeholder="e.g., def calculate_sum(numbers: list[int]) -> int:"
          @input="updateField('function_signature', ($event.target as HTMLInputElement).value)"
        >
      </div>

      <div class="form-group">
        <label for="reference_solution">Reference Solution *</label>
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
import { ref, computed, watch, onMounted } from 'vue'
import type { ProblemEditorProps, ProblemEditorEmits } from './types'
import { log } from '@/utils/logger'
import Editor from '@/features/editor/Editor.vue'
import BasicInfoSection from './shared/BasicInfoSection.vue'
import TestCasesSection from './shared/TestCasesSection.vue'

const props = defineProps<ProblemEditorProps>()
const emit = defineEmits<ProblemEditorEmits>()

// Local state
const imageLoadError = ref(false)

// Access the editor from props
const editor = computed(() => props.editor)

// Helper to update form fields (required for signature → test case parameter flow)
function updateField(key: string, value: string) {
  editor.value.form.updateField(key as any, value as any)
}

// Image handling
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

// Validation
const isValid = computed(() => {
  const form = editor.value.form.form
  const title = (form.title || '').toString().trim()
  if (!title) return false

  // Require valid image URL for prompt type
  if (!editor.value.promptConfig.hasImage.value) return false
  if (!editor.value.promptConfig.isValidUrl.value) return false

  // Require code solution fields
  const signature = (form.function_signature || '').toString().trim()
  if (!signature) return false

  const solution = (form.reference_solution || '').toString().trim()
  if (!solution) return false

  // Require at least one test case
  if (editor.value.testCases.testCases.value.length === 0) return false

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

.input-error {
  border-color: var(--color-error, #e74c3c) !important;
}

.field-error {
  color: var(--color-error, #e74c3c);
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
  background: rgba(231, 76, 60, 0.9);
  color: white;
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
</style>
