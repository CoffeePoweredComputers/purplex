<template>
  <div class="editor-toolbar">
    <div class="toolbar-left">
      <div class="zoom-controls">
        <button
          type="button"
          :disabled="editor.editorSettings.fontSize.value <= 12"
          class="zoom-btn"
          :title="$t('admin.editors.decreaseFontSize')"
          @click="editor.editorSettings.decreaseFontSize"
        >
          <span class="zoom-icon">-</span>
        </button>
        <span class="zoom-display">{{ Math.round((editor.editorSettings.fontSize.value / 14) * 100) }}%</span>
        <button
          type="button"
          :disabled="editor.editorSettings.fontSize.value >= 24"
          class="zoom-btn"
          :title="$t('admin.editors.increaseFontSize')"
          @click="editor.editorSettings.increaseFontSize"
        >
          <span class="zoom-icon">+</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { UseProblemEditorReturn } from '@/composables/admin/useProblemEditor'

interface Props {
  editor: UseProblemEditorReturn
}

const props = defineProps<Props>()

const editor = computed(() => props.editor)
</script>

<style scoped>
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

.zoom-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.zoom-btn:hover:not(:disabled) {
  background: var(--color-primary-gradient-start);
  color: var(--color-text-on-filled);
  border-color: var(--color-primary-gradient-start);
}

.zoom-display {
  min-width: 45px;
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}
</style>
