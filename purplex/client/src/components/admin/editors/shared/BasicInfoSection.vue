<template>
  <div class="form-section rounded-lg border-default">
    <h3>Basic Information</h3>

    <div class="form-group">
      <label for="title">Title *</label>
      <input
        id="title"
        :value="editor.form.form.title"
        type="text"
        required
        placeholder="Enter problem title"
        @input="updateField('title', ($event.target as HTMLInputElement).value)"
      >
    </div>

    <div class="form-group">
      <label for="description">Description *</label>
      <textarea
        id="description"
        :value="editor.form.form.description || ''"
        placeholder="Enter problem description"
        rows="3"
        required
        @input="updateField('description', ($event.target as HTMLTextAreaElement).value)"
      />
    </div>

    <div class="form-group">
      <label for="tags">Tags</label>
      <div class="tags-container">
        <div class="tags-list">
          <span
            v-for="(tag, index) in parsedTags"
            :key="index"
            class="tag"
          >
            {{ tag }}
            <button
              type="button"
              class="tag-remove"
              @click="removeTag(index)"
            >
              &times;
            </button>
          </span>
        </div>
        <input
          v-model="newTag"
          type="text"
          placeholder="Add tag and press Enter"
          class="tag-input"
          @keydown.enter.prevent="addTag"
        >
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { UseProblemEditorReturn } from '@/composables/admin/useProblemEditor'

interface Props {
  editor: UseProblemEditorReturn
}

const props = defineProps<Props>()

const newTag = ref('')

const parsedTags = computed(() => {
  const tags = props.editor.form.form.tags
  if (!tags) {return []}
  if (Array.isArray(tags)) {return tags}
  return []
})

function updateField(field: string, value: string) {
  props.editor.form.updateField(field, value)
}

function addTag() {
  const tag = newTag.value.trim()
  if (!tag) {return}

  const currentTags = [...parsedTags.value]
  if (!currentTags.includes(tag)) {
    currentTags.push(tag)
    props.editor.form.updateField('tags', currentTags)
  }
  newTag.value = ''
}

function removeTag(index: number) {
  const currentTags = [...parsedTags.value]
  currentTags.splice(index, 1)
  props.editor.form.updateField('tags', currentTags)
}
</script>

<style scoped>
.rounded-lg {
  border-radius: var(--radius-lg);
}

.border-default {
  border: 2px solid var(--color-bg-border);
}

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

.form-group input[type="text"],
.form-group textarea {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-fast);
}

.form-group input[type="text"]:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.form-group input::placeholder,
.form-group textarea::placeholder {
  color: var(--color-text-muted);
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

/* Tags */
.tags-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.tag-remove {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  font-size: var(--font-size-base);
  line-height: 1;
  transition: var(--transition-fast);
}

.tag-remove:hover {
  color: var(--color-error);
}

.tag-input {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-fast);
}

.tag-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.tag-input::placeholder {
  color: var(--color-text-muted);
}
</style>
