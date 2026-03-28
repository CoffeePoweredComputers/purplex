<template>
  <div class="consent-form">
    <h3 class="consent-form__title">
      {{ t('auth.consent.title') }}
    </h3>
    <p class="consent-form__description">
      {{ t('auth.consent.description') }}
    </p>

    <div class="consent-form__items">
      <!-- Required consents -->
      <label class="consent-item consent-item--required">
        <input
          v-model="consents.privacy_policy"
          type="checkbox"
          required
        >
        <span class="consent-item__text">
          {{ t('auth.consent.privacyPolicy') }}
          <a
            href="/privacy"
            target="_blank"
            rel="noopener"
          >{{ t('auth.consent.privacyPolicyLink') }}</a> *
        </span>
      </label>

      <label class="consent-item consent-item--required">
        <input
          v-model="consents.terms_of_service"
          type="checkbox"
          required
        >
        <span class="consent-item__text">
          {{ t('auth.consent.termsOfService') }}
          <a
            href="/terms"
            target="_blank"
            rel="noopener"
          >{{ t('auth.consent.termsOfServiceLink') }}</a> *
        </span>
      </label>

      <!-- Optional consents -->
      <div class="consent-form__optional-header">
        <span>{{ t('auth.consent.optionalHeader') }}</span>
      </div>

      <label class="consent-item">
        <input
          v-model="consents.ai_processing"
          type="checkbox"
        >
        <span class="consent-item__text">
          {{ t('auth.consent.aiProcessing') }}
          <small class="consent-item__detail">
            {{ t('auth.consent.aiProcessingDetail') }}
          </small>
        </span>
      </label>

      <label class="consent-item">
        <input
          v-model="consents.research_use"
          type="checkbox"
        >
        <span class="consent-item__text">
          {{ t('auth.consent.researchUse') }}
          <small class="consent-item__detail">
            {{ t('auth.consent.researchUseDetail') }}
          </small>
        </span>
      </label>

      <label class="consent-item">
        <input
          v-model="consents.behavioral_tracking"
          type="checkbox"
        >
        <span class="consent-item__text">
          {{ t('auth.consent.behavioralTracking') }}
          <small class="consent-item__detail">
            {{ t('auth.consent.behavioralTrackingDetail') }}
          </small>
        </span>
      </label>
    </div>

    <p
      v-if="error"
      class="consent-form__error"
      role="alert"
    >
      {{ error }}
    </p>

    <button
      class="consent-form__submit"
      :disabled="!canSubmit"
      @click="submitConsent"
    >
      {{ t('common.continue') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

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
        error.value = t('auth.consent.consentRequired');
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
    padding: var(--spacing-xl);
    background: var(--color-bg-panel);
    border-radius: var(--radius-base);
    border: 1px solid var(--color-bg-border);
    box-shadow: var(--shadow-base);
}

.consent-form__title {
    margin: 0 0 var(--spacing-sm);
    font-size: var(--font-size-md);
    color: var(--color-text-primary);
}

.consent-form__description {
    margin: 0 0 var(--spacing-base);
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
}

.consent-form__items {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-base);
}

.consent-form__optional-header {
    margin-top: var(--spacing-sm);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--color-bg-border);
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
}

.consent-item {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    cursor: pointer;
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
}

.consent-item input[type="checkbox"] {
    margin-top: 3px;
    flex-shrink: 0;
    accent-color: var(--color-primary-gradient-start);
}

.consent-item__text {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.consent-item__text a {
    color: var(--color-primary-gradient-start);
}

.consent-item__text a:hover {
    color: var(--color-primary-gradient-end);
}

.consent-item__detail {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
}

.consent-form__error {
    color: var(--color-error);
    font-size: var(--font-size-sm);
    margin-bottom: var(--spacing-sm);
}

.consent-form__submit {
    width: 100%;
    padding: var(--spacing-md);
    background: linear-gradient(135deg, var(--color-primary-gradient-start), var(--color-primary-gradient-end));
    color: var(--color-text-on-filled);
    border: none;
    border-radius: var(--radius-sm);
    font-size: var(--font-size-base);
    font-weight: 600;
    cursor: pointer;
    transition: var(--transition-fast);
}

.consent-form__submit:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.consent-form__submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.consent-form__submit:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--shadow-colored);
}
</style>
