<template>
  <div class="prompt-detail">
    <!-- Image display -->
    <div v-if="typeData.image_url" class="detail-section">
      <h4 class="section-label">{{ $t('admin.submissions.detail.problemImage') }}</h4>
      <div class="image-container">
        <img
          :src="typeData.image_url"
          :alt="typeData.image_alt_text || $t('admin.submissions.detail.problemImageAlt')"
          class="problem-image"
          loading="lazy"
        >
      </div>
    </div>

    <!-- NL prompt -->
    <div v-if="submission.raw_input" class="detail-section">
      <h4 class="section-label">{{ $t('admin.submissions.detail.studentsExplanation') }}</h4>
      <div class="prompt-box">{{ submission.raw_input }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PromptTypeData } from '@/types';

defineProps<{
  typeData: PromptTypeData;
  submission: { raw_input?: string };
}>();
</script>

<style scoped>
.prompt-detail {
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

.image-container {
  background: var(--color-bg-section);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  padding: 12px;
  text-align: center;
}

.problem-image {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  border-radius: 4px;
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
