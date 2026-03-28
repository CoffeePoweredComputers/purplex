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

      <div class="theme-selector">
        <select
          :value="editor.editorSettings.theme.value"
          class="theme-dropdown"
          @change="editor.editorSettings.setTheme(($event.target as HTMLSelectElement).value)"
        >
          <option value="monokai">
            {{ $t('admin.editors.themes.monokai') }}
          </option>
          <option value="github">
            {{ $t('admin.editors.themes.github') }}
          </option>
          <option value="clouds_midnight">
            {{ $t('admin.editors.themes.cloudsMidnight') }}
          </option>
          <option value="chrome">
            {{ $t('admin.editors.themes.chrome') }}
          </option>
          <option value="solarized_dark">
            {{ $t('admin.editors.themes.solarizedDark') }}
          </option>
          <option value="solarized_light">
            {{ $t('admin.editors.themes.solarizedLight') }}
          </option>
          <option value="dracula">
            {{ $t('admin.editors.themes.dracula') }}
          </option>
          <option value="tomorrow_night">
            {{ $t('admin.editors.themes.tomorrowNight') }}
          </option>
        </select>
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

.theme-dropdown {
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}
</style>
