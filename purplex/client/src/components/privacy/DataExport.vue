<template>
  <div class="data-export">
    <h3 class="data-export__title">{{ t('auth.dataExport.title') }}</h3>
    <p class="data-export__description">
      {{ t('auth.dataExport.description') }}
    </p>

    <button
      class="data-export__btn"
      :disabled="loading"
      @click="exportData"
    >
      {{ loading ? t('auth.dataExport.preparing') : t('auth.dataExport.button') }}
    </button>

    <p v-if="error" class="data-export__error" role="alert">{{ error }}</p>
    <p v-if="success" class="data-export__success" role="status">{{ success }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import privacyService from '../../services/privacyService';

const { t } = useI18n();

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
        success.value = t('auth.dataExport.success');
    } catch (e: unknown) {
        error.value = t('auth.dataExport.error');
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
    color: var(--color-text-on-filled);
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
