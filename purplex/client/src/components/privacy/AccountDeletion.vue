<template>
  <div class="account-deletion">
    <h3 class="account-deletion__title">{{ t('auth.deletion.title') }}</h3>

    <template v-if="!deletionPending">
      <p class="account-deletion__description">
        {{ t('auth.deletion.description') }}
      </p>

      <div class="account-deletion__warning">
        <strong>{{ t('auth.deletion.warningHeader') }}</strong>
        <ul>
          <li>{{ t('auth.deletion.items.profile') }}</li>
          <li>{{ t('auth.deletion.items.consents') }}</li>
          <li>{{ t('auth.deletion.items.enrollments') }}</li>
          <li>{{ t('auth.deletion.items.hints') }}</li>
          <li>{{ t('auth.deletion.items.aiResults') }}</li>
        </ul>
        <p>
          <em>{{ t('auth.deletion.retentionNote') }}</em>
        </p>
      </div>

      <label class="account-deletion__confirm">
        <input type="checkbox" v-model="confirmed">
        <span>{{ t('auth.deletion.confirmCheckbox') }}</span>
      </label>

      <button
        class="account-deletion__btn account-deletion__btn--danger"
        :disabled="!confirmed || loading"
        @click="requestDeletion"
      >
        {{ loading ? t('common.processing') : t('auth.deletion.requestButton') }}
      </button>
    </template>

    <template v-else>
      <div class="account-deletion__pending">
        <p>
          <strong>{{ t('auth.deletion.scheduledTitle') }}</strong>
          {{ t('auth.deletion.scheduledMessage') }}
          <strong>{{ formatDate(deletionScheduledAt) }}</strong>.
        </p>
        <p>{{ t('auth.deletion.scheduledCancel') }}</p>

        <button
          class="account-deletion__btn account-deletion__btn--cancel"
          :disabled="loading"
          @click="cancelDeletion"
        >
          {{ loading ? t('common.processing') : t('auth.deletion.cancelButton') }}
        </button>
      </div>
    </template>

    <p v-if="error" class="account-deletion__error" role="alert">{{ error }}</p>
    <p v-if="success" class="account-deletion__success" role="status">{{ success }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import privacyService from '../../services/privacyService';

const { t, locale } = useI18n();

const confirmed = ref(false);
const loading = ref(false);
const error = ref('');
const success = ref('');
const deletionPending = ref(false);
const deletionScheduledAt = ref('');

async function requestDeletion() {
    loading.value = true;
    error.value = '';
    success.value = '';

    try {
        const result = await privacyService.requestDeletion();
        if (result.status === 'deletion_scheduled' || result.status === 'already_requested') {
            deletionPending.value = true;
            deletionScheduledAt.value = result.deletion_scheduled_at || '';
            success.value = t('auth.deletion.successScheduled');
        }
    } catch (e: unknown) {
        error.value = t('auth.deletion.errorRequest');
    } finally {
        loading.value = false;
    }
}

async function cancelDeletion() {
    loading.value = true;
    error.value = '';
    success.value = '';

    try {
        await privacyService.cancelDeletion();
        deletionPending.value = false;
        deletionScheduledAt.value = '';
        confirmed.value = false;
        success.value = t('auth.deletion.successCancelled');
    } catch (e: unknown) {
        error.value = t('auth.deletion.errorCancel');
    } finally {
        loading.value = false;
    }
}

function formatDate(isoDate: string): string {
    if (!isoDate) return '';
    return new Date(isoDate).toLocaleDateString(locale.value, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    });
}
</script>

<style scoped>
.account-deletion {
    padding: var(--spacing-xl);
    background: var(--color-bg-panel);
    border-radius: var(--radius-base);
    border: 1px solid var(--color-bg-border);
    box-shadow: var(--shadow-sm);
}

.account-deletion__title {
    margin: 0 0 var(--spacing-sm);
    font-size: var(--font-size-md);
    color: var(--color-text-primary);
}

.account-deletion__description {
    margin: 0 0 var(--spacing-base);
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
}

.account-deletion__warning {
    padding: var(--spacing-base);
    margin-bottom: var(--spacing-base);
    background: var(--color-error-bg);
    border: 1px solid rgba(220, 53, 69, 0.25);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
}

.account-deletion__warning ul {
    margin: var(--spacing-sm) 0;
    padding-left: var(--spacing-xl);
}

.account-deletion__warning li {
    margin-bottom: var(--spacing-xs);
}

.account-deletion__confirm {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-base);
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    cursor: pointer;
}

.account-deletion__btn {
    padding: var(--spacing-sm) var(--spacing-lg);
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-size: var(--font-size-sm);
    font-weight: 600;
    transition: var(--transition-fast);
}

.account-deletion__btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.account-deletion__btn:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.account-deletion__btn--danger {
    background: var(--color-error);
    color: var(--color-text-primary);
}

.account-deletion__btn--danger:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(220, 53, 69, 0.3);
}

.account-deletion__btn--cancel {
    background: linear-gradient(135deg, var(--color-primary-gradient-start), var(--color-primary-gradient-end));
    color: var(--color-text-primary);
}

.account-deletion__btn--cancel:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--shadow-colored);
}

.account-deletion__pending {
    padding: var(--spacing-base);
    background: var(--color-warning-bg);
    border: 1px solid rgba(255, 193, 7, 0.25);
    border-radius: var(--radius-sm);
    margin-bottom: var(--spacing-base);
    color: var(--color-text-secondary);
}

.account-deletion__error {
    margin-top: var(--spacing-sm);
    color: var(--color-error);
    font-size: var(--font-size-sm);
}

.account-deletion__success {
    margin-top: var(--spacing-sm);
    color: var(--color-success);
    font-size: var(--font-size-sm);
}
</style>
