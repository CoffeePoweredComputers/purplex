<template>
  <div class="account-deletion">
    <h3 class="account-deletion__title">Delete Account</h3>

    <template v-if="!deletionPending">
      <p class="account-deletion__description">
        Requesting account deletion will deactivate your account immediately.
        After a 30-day grace period, all your data will be permanently deleted.
        During the grace period, you can cancel the deletion by logging in.
      </p>

      <div class="account-deletion__warning">
        <strong>This action will permanently remove:</strong>
        <ul>
          <li>Your profile and account information</li>
          <li>All consent records</li>
          <li>Course enrollments</li>
          <li>Hint activation history</li>
          <li>AI analysis results</li>
        </ul>
        <p>
          <em>Note: Anonymized submission data may be retained for research purposes
          (scores, code, timestamps) but will no longer be linked to your identity.</em>
        </p>
      </div>

      <label class="account-deletion__confirm">
        <input type="checkbox" v-model="confirmed">
        <span>I understand this action cannot be undone after the grace period.</span>
      </label>

      <button
        class="account-deletion__btn account-deletion__btn--danger"
        :disabled="!confirmed || loading"
        @click="requestDeletion"
      >
        {{ loading ? 'Processing...' : 'Request Account Deletion' }}
      </button>
    </template>

    <template v-else>
      <div class="account-deletion__pending">
        <p>
          <strong>Deletion scheduled.</strong>
          Your account will be permanently deleted on
          <strong>{{ formatDate(deletionScheduledAt) }}</strong>.
        </p>
        <p>You can cancel this request before then.</p>

        <button
          class="account-deletion__btn account-deletion__btn--cancel"
          :disabled="loading"
          @click="cancelDeletion"
        >
          {{ loading ? 'Processing...' : 'Cancel Deletion' }}
        </button>
      </div>
    </template>

    <p v-if="error" class="account-deletion__error" role="alert">{{ error }}</p>
    <p v-if="success" class="account-deletion__success" role="status">{{ success }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import privacyService from '../../services/privacyService';

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
            success.value = 'Account deletion has been scheduled.';
        }
    } catch (e: unknown) {
        error.value = 'Failed to request deletion. Please try again later.';
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
        success.value = 'Deletion cancelled. Your account is active again.';
    } catch (e: unknown) {
        error.value = 'Failed to cancel deletion. Please try again.';
    } finally {
        loading.value = false;
    }
}

function formatDate(isoDate: string): string {
    if (!isoDate) return '';
    return new Date(isoDate).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    });
}
</script>

<style scoped>
.account-deletion {
    padding: 1.5rem;
    background: var(--card-bg, #1e1e2e);
    border-radius: 8px;
    border: 1px solid var(--border-color, #333);
}

.account-deletion__title {
    margin: 0 0 0.5rem;
    font-size: 1.1rem;
    color: var(--text-primary, #e0e0e0);
}

.account-deletion__description {
    margin: 0 0 1rem;
    font-size: 0.85rem;
    color: var(--text-secondary, #999);
}

.account-deletion__warning {
    padding: 1rem;
    margin-bottom: 1rem;
    background: rgba(231, 76, 60, 0.08);
    border: 1px solid rgba(231, 76, 60, 0.25);
    border-radius: 6px;
    font-size: 0.85rem;
    color: var(--text-primary, #e0e0e0);
}

.account-deletion__warning ul {
    margin: 0.5rem 0;
    padding-left: 1.5rem;
}

.account-deletion__warning li {
    margin-bottom: 0.25rem;
}

.account-deletion__confirm {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    margin-bottom: 1rem;
    font-size: 0.85rem;
    color: var(--text-primary, #e0e0e0);
    cursor: pointer;
}

.account-deletion__btn {
    padding: 0.6rem 1.2rem;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: opacity 0.2s;
}

.account-deletion__btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.account-deletion__btn--danger {
    background: var(--error-color, #e74c3c);
    color: white;
}

.account-deletion__btn--cancel {
    background: var(--primary-gradient, linear-gradient(135deg, #9b59b6, #6c3483));
    color: white;
}

.account-deletion__pending {
    padding: 1rem;
    background: rgba(243, 156, 18, 0.08);
    border: 1px solid rgba(243, 156, 18, 0.25);
    border-radius: 6px;
    margin-bottom: 1rem;
}

.account-deletion__error {
    margin-top: 0.5rem;
    color: var(--error-color, #e74c3c);
    font-size: 0.85rem;
}

.account-deletion__success {
    margin-top: 0.5rem;
    color: var(--success-color, #2ecc71);
    font-size: 0.85rem;
}
</style>
