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
    padding: 1.5rem;
    background: var(--card-bg, #1e1e2e);
    border-radius: 8px;
    border: 1px solid var(--border-color, #333);
}

.data-export__title {
    margin: 0 0 0.5rem;
    font-size: 1.1rem;
    color: var(--text-primary, #e0e0e0);
}

.data-export__description {
    margin: 0 0 1rem;
    font-size: 0.85rem;
    color: var(--text-secondary, #999);
}

.data-export__btn {
    padding: 0.6rem 1.2rem;
    background: var(--primary-gradient, linear-gradient(135deg, #9b59b6, #6c3483));
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: opacity 0.2s;
}

.data-export__btn:disabled {
    opacity: 0.5;
    cursor: wait;
}

.data-export__error {
    margin-top: 0.5rem;
    color: var(--error-color, #e74c3c);
    font-size: 0.85rem;
}

.data-export__success {
    margin-top: 0.5rem;
    color: var(--success-color, #2ecc71);
    font-size: 0.85rem;
}
</style>
