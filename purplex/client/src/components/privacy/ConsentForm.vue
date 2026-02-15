<template>
  <div class="consent-form">
    <h3 class="consent-form__title">Data Processing Consent</h3>
    <p class="consent-form__description">
      Please review and accept the following to continue.
      Items marked with * are required.
    </p>

    <div class="consent-form__items">
      <!-- Required consents -->
      <label class="consent-item consent-item--required">
        <input
          type="checkbox"
          v-model="consents.privacy_policy"
          required
        >
        <span class="consent-item__text">
          I have read and agree to the
          <a href="/privacy" target="_blank" rel="noopener">Privacy Policy</a> *
        </span>
      </label>

      <label class="consent-item consent-item--required">
        <input
          type="checkbox"
          v-model="consents.terms_of_service"
          required
        >
        <span class="consent-item__text">
          I accept the
          <a href="/terms" target="_blank" rel="noopener">Terms of Service</a> *
        </span>
      </label>

      <!-- Optional consents -->
      <div class="consent-form__optional-header">
        <span>Optional data processing (you can change these later in Settings)</span>
      </div>

      <label class="consent-item">
        <input
          type="checkbox"
          v-model="consents.ai_processing"
        >
        <span class="consent-item__text">
          Allow AI analysis of my code submissions
          <small class="consent-item__detail">
            Your code may be sent to OpenAI for comprehension analysis and feedback generation.
          </small>
        </span>
      </label>

      <label class="consent-item">
        <input
          type="checkbox"
          v-model="consents.research_use"
        >
        <span class="consent-item__text">
          Allow anonymized use of my data for research
          <small class="consent-item__detail">
            De-identified submission and progress data may be used for educational research.
          </small>
        </span>
      </label>

      <label class="consent-item">
        <input
          type="checkbox"
          v-model="consents.behavioral_tracking"
        >
        <span class="consent-item__text">
          Allow progress and performance tracking
          <small class="consent-item__detail">
            Track detailed metrics like time spent, hint usage, and completion patterns.
          </small>
        </span>
      </label>
    </div>

    <p v-if="error" class="consent-form__error" role="alert">{{ error }}</p>

    <button
      class="consent-form__submit"
      :disabled="!canSubmit"
      @click="submitConsent"
    >
      Continue
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const emit = defineEmits<{
    (e: 'consent-granted', consents: Record<string, boolean>): void;
}>();

const consents = ref({
    privacy_policy: false,
    terms_of_service: false,
    ai_processing: false,
    research_use: false,
    behavioral_tracking: false,
});

const error = ref('');

const canSubmit = computed(() => {
    return consents.value.privacy_policy && consents.value.terms_of_service;
});

function submitConsent() {
    if (!canSubmit.value) {
        error.value = 'You must accept the Privacy Policy and Terms of Service to continue.';
        return;
    }
    error.value = '';
    emit('consent-granted', { ...consents.value });
}
</script>

<style scoped>
.consent-form {
    max-width: 500px;
    margin: 0 auto;
    padding: 1.5rem;
    background: var(--card-bg, #1e1e2e);
    border-radius: 8px;
    border: 1px solid var(--border-color, #333);
}

.consent-form__title {
    margin: 0 0 0.5rem;
    font-size: 1.2rem;
    color: var(--text-primary, #e0e0e0);
}

.consent-form__description {
    margin: 0 0 1rem;
    font-size: 0.85rem;
    color: var(--text-secondary, #999);
}

.consent-form__items {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.consent-form__optional-header {
    margin-top: 0.5rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--border-color, #333);
    font-size: 0.8rem;
    color: var(--text-secondary, #999);
}

.consent-item {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    cursor: pointer;
    font-size: 0.9rem;
    color: var(--text-primary, #e0e0e0);
}

.consent-item input[type="checkbox"] {
    margin-top: 3px;
    flex-shrink: 0;
}

.consent-item__text {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}

.consent-item__text a {
    color: var(--link-color, #9b59b6);
}

.consent-item__detail {
    font-size: 0.75rem;
    color: var(--text-secondary, #999);
}

.consent-form__error {
    color: var(--error-color, #e74c3c);
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
}

.consent-form__submit {
    width: 100%;
    padding: 0.75rem;
    background: var(--primary-gradient, linear-gradient(135deg, #9b59b6, #6c3483));
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
    transition: opacity 0.2s;
}

.consent-form__submit:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
</style>
