<template>
  <div class="mcq-detail">
    <!-- Question -->
    <div class="detail-section">
      <h4 class="section-label">Question</h4>
      <div class="question-box">{{ typeData.question_text }}</div>
    </div>

    <!-- Options -->
    <div class="detail-section">
      <h4 class="section-label">Options</h4>
      <div class="options-list">
        <div
          v-for="option in typeData.options"
          :key="option.id"
          class="option-item"
          :class="{
            'option-selected': option.id === typeData.selected_option_id,
            'option-correct': option.is_correct,
            'option-wrong': option.id === typeData.selected_option_id && !option.is_correct,
          }"
        >
          <span class="option-indicator">
            <span v-if="option.is_correct" class="indicator-icon correct">&#10003;</span>
            <span v-else-if="option.id === typeData.selected_option_id" class="indicator-icon wrong">&#10007;</span>
            <span v-else class="indicator-icon neutral">{{ option.id }}</span>
          </span>
          <div class="option-content">
            <div class="option-text">{{ option.text }}</div>
            <div v-if="option.explanation" class="option-explanation">
              {{ option.explanation }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Result -->
    <div class="detail-section">
      <div class="result-banner" :class="typeData.is_correct ? 'correct' : 'incorrect'">
        {{ typeData.is_correct ? 'Correct Answer' : 'Incorrect Answer' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { McqTypeData } from '@/types';

defineProps<{
  typeData: McqTypeData;
}>();
</script>

<style scoped>
.mcq-detail {
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

.question-box {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary);
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  background: var(--color-bg-panel);
  transition: all 0.2s;
}

.option-item.option-correct {
  border-color: var(--color-success);
  background: var(--color-success-bg);
}

.option-item.option-wrong {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.option-indicator {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 600;
}

.indicator-icon.correct {
  background: var(--color-success);
  color: white;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.indicator-icon.wrong {
  background: var(--color-error);
  color: white;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.indicator-icon.neutral {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-input);
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  text-transform: uppercase;
}

.option-content {
  flex: 1;
}

.option-text {
  font-size: 14px;
  color: var(--color-text-primary);
  line-height: 1.5;
}

.option-explanation {
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
  font-style: italic;
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
