<template>
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div
        v-if="visible"
        class="dialog-overlay"
        @click.self="onDecline"
      >
        <div
          class="dialog"
          role="alertdialog"
          :aria-label="$t('auth.privacy.aiConsentPrompt.title')"
        >
          <h3>{{ $t('auth.privacy.aiConsentPrompt.title') }}</h3>
          <p>{{ $t('auth.privacy.aiConsentPrompt.body') }}</p>
          <p
            v-if="errorMessage"
            class="error"
            role="alert"
          >
            {{ errorMessage }}
          </p>
          <div class="dialog-actions">
            <button
              class="btn btn-secondary"
              :disabled="loading"
              @click="onDecline"
            >
              {{ $t('auth.privacy.aiConsentPrompt.decline') }}
            </button>
            <button
              class="btn btn-primary"
              :disabled="loading"
              @click="onGrant"
            >
              {{ loading ? $t('auth.privacy.aiConsentPrompt.granting') : $t('auth.privacy.aiConsentPrompt.grant') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useStore } from 'vuex';
import privacyService from '../../services/privacyService';
import { log } from '../../utils/logger';

const store = useStore();
const { t } = useI18n();

const visible = computed<boolean>(() => store.state.consentPrompt.visible);
const purpose = computed<string | null>(() => store.state.consentPrompt.purpose);

const loading = ref(false);
const errorMessage = ref<string | null>(null);

async function onGrant() {
  if (purpose.value !== 'ai_processing') {
    // Future purposes will need their own grant calls — fail loudly if we're
    // asked to handle one we don't understand instead of silently accepting.
    log.error('AIConsentModal: unsupported purpose', purpose.value);
    errorMessage.value = t('auth.privacy.aiConsentPrompt.error');
    return;
  }

  loading.value = true;
  errorMessage.value = null;
  try {
    await privacyService.grantConsent('ai_processing', { consent_method: 'in_app' });
    store.dispatch('consentPrompt/resolveDecision', true);
  } catch (err) {
    log.error('AIConsentModal: grantConsent failed', err);
    errorMessage.value = t('auth.privacy.aiConsentPrompt.error');
  } finally {
    loading.value = false;
  }
}

function onDecline() {
  if (loading.value) return;
  errorMessage.value = null;
  store.dispatch('consentPrompt/resolveDecision', false);
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  max-width: 480px;
  width: 90%;
  box-shadow: var(--shadow-lg);
}

.dialog h3 {
  margin: 0 0 var(--spacing-lg) 0;
  color: var(--color-text-primary);
}

.dialog p {
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-lg);
  line-height: 1.5;
}

.dialog p.error {
  color: var(--color-error);
}

.dialog-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  margin-top: var(--spacing-lg);
}

.btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: var(--transition-base);
}

.btn-secondary {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.btn-primary {
  background: var(--color-primary);
  color: var(--color-text-on-filled);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
