<template>
  <div class="probeable-code-detail">
    <!-- Function context -->
    <div v-if="typeData.function_signature" class="detail-section">
      <h4 class="section-label">Function Signature</h4>
      <code class="signature-box">{{ typeData.function_signature }}</code>
    </div>

    <!-- Submitted code -->
    <div class="detail-section">
      <h4 class="section-label">Submitted Code</h4>
      <Editor
        :value="submission.processed_code || submission.raw_input || '# No code available'"
        :read-only="true"
        height="350px"
        width="100%"
        theme="tomorrow_night"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import Editor from '@/features/editor/Editor.vue';
import type { ProbeableTypeData } from '@/types';

defineProps<{
  typeData: ProbeableTypeData;
  submission: { raw_input?: string; processed_code?: string };
}>();
</script>

<style scoped>
.probeable-code-detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.signature-box {
  display: block;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  padding: 8px 12px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  color: var(--color-text-primary);
}
</style>
