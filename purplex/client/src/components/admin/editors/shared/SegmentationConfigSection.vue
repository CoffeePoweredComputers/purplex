<template>
  <div class="form-section rounded-lg border-default">
    <h3>{{ title || $t('admin.editors.segmentation.title') }}</h3>

    <div class="segmentation-toggle">
      <label class="toggle-label">
        <input
          :checked="editor.segmentation.isEnabled.value"
          type="checkbox"
          class="toggle-checkbox"
          @change="editor.segmentation.setEnabled(($event.target as HTMLInputElement).checked)"
        >
        <span class="toggle-text">{{ $t('admin.editors.segmentation.enableToggle') }}</span>
      </label>
      <p class="hint-description">
        {{ $t('admin.editors.segmentation.enableHint') }}
      </p>
    </div>

    <div
      v-if="editor.segmentation.isEnabled.value"
      class="segmentation-config-panel"
    >
      <div class="segmentation-examples-section">
        <h4>{{ $t('admin.editors.segmentation.trainingExamples') }}</h4>
        <p class="section-description">
          {{ $t('admin.editors.segmentation.trainingDescription') }}
        </p>

        <div class="threshold-setting">
          <label class="form-label">{{ $t('admin.editors.segmentation.comprehensionThreshold') }}</label>
          <div class="threshold-control">
            <input
              :value="editor.segmentation.threshold.value"
              type="number"
              min="1"
              max="5"
              class="threshold-input"
              @input="editor.segmentation.setThreshold(parseInt(($event.target as HTMLInputElement).value) || 3)"
            >
            <span class="threshold-help">
              <template v-if="useUnicodeSymbols">≤</template><template v-else>&lt;=</template> {{ editor.segmentation.threshold.value }} {{ $t('admin.editors.segmentation.segmentsEquals') }} {{ $t('admin.editors.segmentation.goodRelational') }}<br>
              > {{ editor.segmentation.threshold.value }} {{ $t('admin.editors.segmentation.segmentsEquals') }} {{ $t('admin.editors.segmentation.needsWorkMulti') }}
            </span>
          </div>
        </div>

        <!-- Relational Example -->
        <div class="example-block relational">
          <h5>
            <span class="example-icon">{{ relationalIcon }}</span>
            {{ $t('admin.editors.segmentation.goodExample') }}
          </h5>
          <p class="example-help">
            {{ $t('admin.editors.segmentation.goodExampleHelp') }}
          </p>

          <div class="form-group">
            <label>{{ $t('admin.editors.segmentation.studentDescription') }}</label>
            <textarea
              :value="editor.segmentation.config.examples.relational.prompt"
              :placeholder="$t('admin.editors.segmentation.relationalPromptPlaceholder')"
              rows="3"
              @input="editor.segmentation.setRelationalPrompt(($event.target as HTMLTextAreaElement).value)"
            />
          </div>

          <div class="segments-editor">
            <label>{{ $t('admin.editors.segmentation.expectedSegments', { count: editor.segmentation.relationalSegments.value.length }) }}</label>
            <div
              v-for="(segText, idx) in editor.segmentation.relationalSegments.value"
              :key="`rel-${idx}`"
              class="segment-item"
            >
              <div class="segment-row">
                <input
                  :value="segText"
                  :placeholder="$t('admin.editors.segmentation.segmentPlaceholder')"
                  class="segment-input"
                  @input="editor.segmentation.updateRelationalSegmentText(idx, ($event.target as HTMLInputElement).value)"
                >
                <button
                  type="button"
                  class="btn-icon"
                  @click="editor.segmentation.removeRelationalSegment(idx)"
                >
                  ×
                </button>
              </div>
              <div class="code-lines-row">
                <label class="lines-label">{{ $t('admin.editors.segmentation.codeLines') }}</label>
                <input
                  :value="editor.segmentation.formatLineRange(editor.segmentation.relationalCodeLines.value[idx] || [])"
                  :placeholder="$t('admin.editors.segmentation.codeLinesPlaceholder')"
                  class="lines-input"
                  @input="editor.segmentation.updateRelationalSegmentCodeLines(idx, editor.segmentation.parseLineRange(($event.target as HTMLInputElement).value))"
                >
              </div>
            </div>
            <button
              type="button"
              class="btn-secondary btn-sm"
              @click="editor.segmentation.addRelationalSegment"
            >
              {{ $t('admin.editors.segmentation.addSegment') }}
            </button>
          </div>
        </div>

        <!-- Multi-structural Example -->
        <div class="example-block multi-structural">
          <h5>
            <span class="example-icon">{{ multiStructuralIcon }}</span>
            {{ $t('admin.editors.segmentation.needsWorkExample') }}
          </h5>
          <p class="example-help">
            {{ $t('admin.editors.segmentation.needsWorkExampleHelp') }}
          </p>

          <div class="form-group">
            <label>{{ $t('admin.editors.segmentation.studentDescription') }}</label>
            <textarea
              :value="editor.segmentation.config.examples.multi_structural.prompt"
              :placeholder="$t('admin.editors.segmentation.multiStructuralPromptPlaceholder')"
              rows="3"
              @input="editor.segmentation.setMultiStructuralPrompt(($event.target as HTMLTextAreaElement).value)"
            />
          </div>

          <div class="segments-editor">
            <label>{{ $t('admin.editors.segmentation.expectedSegments', { count: editor.segmentation.multiStructuralSegments.value.length }) }}</label>
            <div
              v-for="(segText, idx) in editor.segmentation.multiStructuralSegments.value"
              :key="`multi-${idx}`"
              class="segment-item"
            >
              <div class="segment-row">
                <input
                  :value="segText"
                  :placeholder="$t('admin.editors.segmentation.segmentPlaceholder')"
                  class="segment-input"
                  @input="editor.segmentation.updateMultiStructuralSegmentText(idx, ($event.target as HTMLInputElement).value)"
                >
                <button
                  type="button"
                  class="btn-icon"
                  @click="editor.segmentation.removeMultiStructuralSegment(idx)"
                >
                  ×
                </button>
              </div>
              <div class="code-lines-row">
                <label class="lines-label">{{ $t('admin.editors.segmentation.codeLines') }}</label>
                <input
                  :value="editor.segmentation.formatLineRange(editor.segmentation.multiStructuralCodeLines.value[idx] || [])"
                  :placeholder="$t('admin.editors.segmentation.codeLinesPlaceholder')"
                  class="lines-input"
                  @input="editor.segmentation.updateMultiStructuralSegmentCodeLines(idx, editor.segmentation.parseLineRange(($event.target as HTMLInputElement).value))"
                >
              </div>
            </div>
            <button
              type="button"
              class="btn-secondary btn-sm"
              @click="editor.segmentation.addMultiStructuralSegment"
            >
              {{ $t('admin.editors.segmentation.addSegment') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import type { UseProblemEditorReturn } from '@/composables/admin/useProblemEditor';

const { t } = useI18n();

interface Props {
  /** Editor composable with segmentation config */
  editor: UseProblemEditorReturn;
  /** Section title (optional) */
  title?: string;
  /** Icon for relational (good) example - default matches EiplProblemEditor */
  relationalIcon?: string;
  /** Icon for multi-structural (needs work) example - default matches EiplProblemEditor */
  multiStructuralIcon?: string;
  /** Whether to use Unicode ≤ or HTML &lt;= for threshold display */
  useUnicodeSymbols?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  title: undefined,
  relationalIcon: '✅',
  multiStructuralIcon: '❌',
  useUnicodeSymbols: true,
});
</script>

<style scoped>
/* Common Utilities */
.rounded-lg {
  border-radius: var(--radius-lg);
}

.border-default {
  border: 2px solid var(--color-bg-border);
}

/* Form Section */
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
  resize: vertical;
}

.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

/* Segmentation Toggle */
.segmentation-toggle {
  margin-bottom: var(--spacing-lg);
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

.hint-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-sm);
  padding-left: 26px;
}

/* Segmentation Config Panel */
.segmentation-config-panel {
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

.segmentation-examples-section h4 {
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-primary);
}

/* Threshold Setting */
.threshold-setting {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
}

.form-label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
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

/* Example Blocks */
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
  font-weight: bold;
}

.example-help {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-md);
}

/* Segments Editor */
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

.btn-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
}
</style>
