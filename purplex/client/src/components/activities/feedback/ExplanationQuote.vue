<template>
  <div
    class="explanation-section"
    role="region"
    aria-labelledby="explanation-heading"
  >
    <div class="section-label">
      <span
        class="label-icon"
        aria-hidden="true"
      >💭</span>
      <h3
        id="explanation-heading"
        class="label-text"
      >
        {{ $t('feedback.yourExplanation') }}
      </h3>
    </div>
    <p class="explanation-text">
      {{ text }}
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * ExplanationQuote - the student's own explanation, quoted back in feedback.
 *
 * Shared by the EiPL/Prompt feedback (Feedback.vue) and the probeable_spec
 * feedback, where it takes the place of the submitted-code panel.
 */
defineProps<{
  /** The student's explanation text */
  text: string
}>()
</script>

<style scoped>
.explanation-section {
  margin: var(--spacing-md) var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--color-bg-section);
  border-radius: var(--radius-base);
  border-left: 3px solid var(--color-primary);
}

.section-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.label-icon {
  font-size: var(--font-size-base);
}

.label-text {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

.explanation-text {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  margin: 0;
  padding: var(--spacing-sm);
  background: var(--color-bg-panel);
  border-radius: var(--radius-xs);
  font-style: italic;
}
</style>
