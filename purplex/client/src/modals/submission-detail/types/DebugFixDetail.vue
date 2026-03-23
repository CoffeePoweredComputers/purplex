<template>
  <div class="debugfix-detail">
    <!-- Side-by-side code comparison -->
    <div class="code-comparison">
      <div class="code-panel">
        <div class="panel-header buggy">
          <span class="panel-label">{{ $t('admin.submissions.detail.buggyCodeOriginal') }}</span>
        </div>
        <Editor
          :value="typeData.buggy_code || '# No buggy code available'"
          :read-only="true"
          height="350px"
          width="100%"
          :theme="editorTheme"
        />
      </div>
      <div class="code-panel">
        <div class="panel-header fixed">
          <span class="panel-label">{{ $t('admin.submissions.detail.studentsFix') }}</span>
        </div>
        <Editor
          :value="submission.raw_input || submission.processed_code || '# No code submitted'"
          :read-only="true"
          height="350px"
          width="100%"
          :theme="editorTheme"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Editor from '@/features/editor/Editor.vue';
import type { DebugFixTypeData } from '@/types';
import { useTheme } from '@/composables/useTheme';

const { editorTheme } = useTheme();

defineProps<{
  typeData: DebugFixTypeData;
  submission: { raw_input?: string; processed_code?: string };
}>();
</script>

<style scoped>
.debugfix-detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.code-comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.code-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
}

.panel-header {
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  border-bottom: 1px solid var(--color-bg-input);
}

.panel-header.buggy {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.panel-header.fixed {
  background: var(--color-success-bg);
  color: var(--color-success);
}

@media (max-width: 768px) {
  .code-comparison {
    grid-template-columns: 1fr;
  }
}
</style>
