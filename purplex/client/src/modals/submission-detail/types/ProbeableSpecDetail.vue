<template>
  <div class="probeable-spec-detail">
    <!-- Function context -->
    <div v-if="typeData.function_signature" class="detail-section">
      <h4 class="section-label">{{ $t('admin.submissions.detail.functionSignature') }}</h4>
      <code class="signature-box">{{ typeData.function_signature }}</code>
    </div>

    <!-- NL prompt (student writes explanation like EiPL) -->
    <div v-if="submission.raw_input" class="detail-section">
      <h4 class="section-label">{{ $t('admin.submissions.detail.studentsExplanation') }}</h4>
      <div class="prompt-box">{{ submission.raw_input }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ProbeableTypeData } from '@/types';

defineProps<{
  typeData: ProbeableTypeData;
  submission: { raw_input?: string };
}>();
</script>

<style scoped>
.probeable-spec-detail {
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
  background: var(--color-bg-section);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  padding: 8px 12px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  color: var(--color-text-primary);
}

.prompt-box {
  background: var(--color-bg-section);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary);
}
</style>
