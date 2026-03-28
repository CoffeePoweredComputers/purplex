<template>
  <div class="language-switcher">
    <label
      class="switcher-label"
      for="language-select"
    >
      {{ $t('auth.account.language') }}
    </label>
    <p class="switcher-description">
      {{ $t('auth.account.languageDescription') }}
    </p>
    <div class="select-wrapper">
      <select
        id="language-select"
        v-model="selectedLanguage"
        class="language-select"
        :disabled="isUpdating"
        @change="handleLanguageChange"
      >
        <option
          v-for="lang in languages"
          :key="lang.code"
          :value="lang.code"
        >
          {{ lang.native }} ({{ lang.name }})
        </option>
      </select>
      <span
        v-if="isUpdating"
        class="loading-indicator"
      >...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useStore } from 'vuex';
import axios from 'axios';
import { SUPPORTED_LANGUAGES } from '../i18n/brand';
import { setLocale, type SupportedLocale } from '../i18n';
import { log } from '../utils/logger';

const { locale } = useI18n();
const store = useStore();

const languages = SUPPORTED_LANGUAGES;
const selectedLanguage = ref(locale.value);
const isUpdating = ref(false);

const isLoggedIn = computed(() => store.getters['auth/isLoggedIn']);

// Sync with locale changes from elsewhere
watch(locale, (newLocale) => {
  selectedLanguage.value = newLocale;
});

async function handleLanguageChange() {
  const newLanguage = selectedLanguage.value as SupportedLocale;

  // Immediately update the UI locale
  await setLocale(newLanguage);

  // If user is logged in, persist to backend
  if (isLoggedIn.value) {
    isUpdating.value = true;
    try {
      await axios.patch('/api/user/me/language/', {
        language_preference: newLanguage
      });

      // Update store with new language preference
      const currentUser = store.state.auth.user;
      if (currentUser) {
        store.commit('auth/updateUserData', {
          ...currentUser,
          languagePreference: newLanguage
        });
      }

      log.info('Language preference updated', { language: newLanguage });
    } catch (error) {
      log.error('Failed to update language preference', error);
      // Still keep the local change - it's stored in localStorage by setLocale
    } finally {
      isUpdating.value = false;
    }
  }
}
</script>

<style scoped>
.language-switcher {
  margin-top: var(--spacing-lg);
}

.switcher-label {
  display: block;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.switcher-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--spacing-md) 0;
}

.select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.language-select {
  width: 100%;
  max-width: 300px;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-base);
  font-family: inherit;
  color: var(--color-text-primary);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-fast);
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23999' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
}

.language-select:hover {
  border-color: var(--color-primary-gradient-start);
}

.language-select:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 2px var(--color-primary-overlay);
}

.language-select:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.language-select option {
  background: var(--color-bg-dark);
  color: var(--color-text-primary);
  padding: var(--spacing-sm);
}

.loading-indicator {
  color: var(--color-text-muted);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@media (width <= 480px) {
  .language-select {
    max-width: 100%;
  }
}
</style>
