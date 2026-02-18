<template>
  <div class="data-export">
    <h3 class="data-export__title">Export Your Data</h3>
    <p class="data-export__description">
      Download a copy of all your personal data in JSON format.
      This includes your profile, submissions, progress, and consent history.
    </p>

    <button
      class="data-export__btn"
      :disabled="loading"
      @click="exportData"
    >
      {{ loading ? 'Preparing export...' : 'Download My Data' }}
    </button>

    <p v-if="error" class="data-export__error" role="alert">{{ error }}</p>
    <p v-if="success" class="data-export__success" role="status">{{ success }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import privacyService from '../../services/privacyService';

const loading = ref(false);
const error = ref('');
const success = ref('');

async function exportData() {
    loading.value = true;
    error.value = '';
    success.value = '';

    try {
        const data = await privacyService.exportData();
        const filename = `purplex-data-export-${new Date().toISOString().split('T')[0]}.json`;
        privacyService.downloadAsJson(data, filename);
        success.value = 'Your data has been downloaded.';
    } catch (e: unknown) {
        error.value = 'Failed to export data. Please try again later.';
    } finally {
        loading.value = false;
    }
}
</script>

<style scoped>
.data-export {
    padding: var(--spacing-xl);
    background: var(--color-bg-panel);
    border-radius: var(--radius-base);
    border: 1px solid var(--color-bg-border);
    box-shadow: var(--shadow-sm);
}

.data-export__title {
    margin: 0 0 var(--spacing-sm);
    font-size: var(--font-size-md);
    color: var(--color-text-primary);
}

.data-export__description {
    margin: 0 0 var(--spacing-base);
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
}

.data-export__btn {
    padding: var(--spacing-sm) var(--spacing-lg);
    background: linear-gradient(135deg, var(--color-primary-gradient-start), var(--color-primary-gradient-end));
    color: var(--color-text-primary);
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-weight: 600;
    transition: var(--transition-fast);
}

.data-export__btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--shadow-colored);
}

.data-export__btn:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.data-export__btn:disabled {
    opacity: 0.6;
    cursor: wait;
}

.data-export__error {
    margin-top: var(--spacing-sm);
    color: var(--color-error);
    font-size: var(--font-size-sm);
}

.data-export__success {
    margin-top: var(--spacing-sm);
    color: var(--color-success);
    font-size: var(--font-size-sm);
}
</style>
