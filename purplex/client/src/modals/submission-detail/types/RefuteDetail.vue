<template>
  <div class="refute-detail">
    <!-- Claim -->
    <div class="detail-section">
      <h4 class="section-label">Claim to Disprove</h4>
      <div class="claim-box">{{ typeData.claim_text }}</div>
    </div>

    <!-- Function context -->
    <div v-if="typeData.function_signature" class="detail-section">
      <h4 class="section-label">Function Signature</h4>
      <code class="signature-box">{{ typeData.function_signature }}</code>
    </div>

    <!-- Student's input (counterexample) -->
    <div class="detail-section">
      <h4 class="section-label">Student's Counterexample Input</h4>
      <div class="input-box">
        <code>{{ submission.raw_input }}</code>
      </div>
    </div>

    <!-- Result -->
    <div class="detail-section">
      <div class="result-banner" :class="submission.is_correct ? 'correct' : 'incorrect'">
        {{ submission.is_correct ? 'Valid counterexample found' : 'Counterexample not valid' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RefuteTypeData } from '@/types';

defineProps<{
  typeData: RefuteTypeData;
  submission: { raw_input?: string; is_correct?: boolean };
}>();
</script>

<style scoped>
.refute-detail {
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

.claim-box {
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning);
  border-radius: 4px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary);
  font-style: italic;
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

.input-box {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  padding: 12px;
}

.input-box code {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  color: var(--color-text-primary);
  word-break: break-all;
}

.result-banner {
  padding: 12px 16px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 14px;
  text-align: center;
}

.result-banner.correct {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.result-banner.incorrect {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}
</style>
