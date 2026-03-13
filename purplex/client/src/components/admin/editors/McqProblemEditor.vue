<template>
  <div class="mcq-problem-editor">
    <!-- Basic Information -->
    <BasicInfoSection :editor="editor" />

    <!-- Question & Options -->
    <div class="form-section rounded-lg border-default transition-fast">
      <h3>{{ $t('admin.editors.mcq.questionAndOptions') }}</h3>

      <div class="form-group">
        <label for="question-text">{{ $t('admin.editors.mcq.questionLabel') }}</label>
        <textarea
          id="question-text"
          :value="editor.mcqOptions.questionText.value"
          :placeholder="$t('admin.editors.mcq.questionPlaceholder')"
          rows="3"
          required
          @input="editor.mcqOptions.setQuestionText(($event.target as HTMLTextAreaElement).value)"
        />
      </div>

      <p class="section-description">
        {{ $t('admin.editors.mcq.optionsDescription') }}
      </p>

      <div class="mcq-options-list">
        <div
          v-for="(option, index) in editor.mcqOptions.options.value"
          :key="option.id"
          class="mcq-option-item"
          :class="{ 'is-correct': option.is_correct }"
        >
          <div class="mcq-option-header">
            <span class="option-letter">{{ getOptionLetter(index) }}</span>
            <label class="correct-label">
              <input
                type="radio"
                name="correct_option"
                :checked="option.is_correct"
                @change="editor.mcqOptions.setCorrect(index)"
              >
              <span>{{ $t('admin.editors.mcq.correctAnswer') }}</span>
            </label>
            <button
              type="button"
              class="remove-btn"
              :disabled="editor.mcqOptions.options.value.length <= 2"
              :title="$t('admin.editors.mcq.removeOption')"
              @click="editor.mcqOptions.removeOption(index)"
            >
              ×
            </button>
          </div>
          <div class="mcq-option-fields">
            <input
              v-model="option.text"
              type="text"
              class="option-text-input"
              :placeholder="$t('admin.editors.mcq.optionTextPlaceholder')"
            >
            <input
              v-model="option.explanation"
              type="text"
              class="option-explanation-input"
              :placeholder="$t('admin.editors.mcq.explanationPlaceholder')"
            >
          </div>
        </div>
      </div>

      <button
        type="button"
        class="btn-secondary add-option-btn"
        :disabled="!editor.mcqOptions.canAddMore.value"
        @click="editor.mcqOptions.addOption"
      >
        {{ $t('admin.editors.mcq.addOption') }}
      </button>

      <div
        v-if="!editor.mcqOptions.hasCorrectAnswer.value"
        class="validation-warning"
      >
        {{ $t('admin.editors.mcq.markCorrectAnswer') }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { ProblemEditorEmits, ProblemEditorProps } from './types'
import BasicInfoSection from './shared/BasicInfoSection.vue'

// Props and emits
const props = defineProps<ProblemEditorProps>()
const emit = defineEmits<ProblemEditorEmits>()

// Alias for editor
const editor = computed(() => props.editor)

// Validation
const isValid = computed(() => {
  const title = (editor.value.form.form.title || '').toString().trim()
  const questionText = (editor.value.mcqOptions.questionText.value || '').trim()
  const hasCorrectAnswer = editor.value.mcqOptions.hasCorrectAnswer.value
  const hasValidOptions = editor.value.mcqOptions.options.value.length >= 2 &&
    editor.value.mcqOptions.options.value.every(opt => opt.text.trim().length > 0)

  return title.length > 0 && questionText.length > 0 && hasCorrectAnswer && hasValidOptions
})

watch(isValid, (valid) => {
  emit('validation-change', valid)
}, { immediate: true })

// Methods
function getOptionLetter(index: number): string {
  return String.fromCharCode(65 + index) // A, B, C, D, etc.
}

// Expose validate method
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

.section-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-lg);
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
.form-group textarea,
.form-group select {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-base);
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

/* MCQ Options */
.mcq-options-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.mcq-option-item {
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-md);
  transition: all 0.2s ease;
}

.mcq-option-item.is-correct {
  border-color: var(--color-success);
  background: rgba(16, 185, 129, 0.1);
}

.mcq-option-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.option-letter {
  width: 28px;
  height: 28px;
  background: var(--color-primary-gradient-start);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: var(--font-size-sm);
}

.correct-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.correct-label input[type="radio"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.remove-btn {
  margin-left: auto;
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
  font-size: var(--font-size-lg);
  transition: all 0.2s ease;
}

.remove-btn:hover:not(:disabled) {
  background: var(--color-error);
  color: white;
  border-color: var(--color-error);
}

.remove-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.mcq-option-fields {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.option-text-input,
.option-explanation-input {
  width: 100%;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-base);
}

.option-text-input:focus,
.option-explanation-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

.option-explanation-input {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.option-explanation-input::placeholder {
  font-style: italic;
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

.add-option-btn {
  width: 100%;
}

.validation-warning {
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: var(--radius-base);
  color: var(--color-warning);
  font-size: var(--font-size-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.validation-warning::before {
  content: '⚠';
}
</style>
