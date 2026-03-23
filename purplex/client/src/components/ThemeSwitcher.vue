<template>
  <div class="theme-switcher">
    <label class="switcher-label">
      {{ $t('auth.account.theme') }}
    </label>
    <p class="switcher-description">
      {{ $t('auth.account.themeDescription') }}
    </p>
    <div
      class="theme-options"
      role="radiogroup"
      :aria-label="$t('auth.account.theme')"
    >
      <button
        v-for="option in options"
        :key="option.value"
        type="button"
        role="radio"
        :aria-checked="theme === option.value"
        :aria-label="option.label"
        class="theme-option"
        :class="{ active: theme === option.value }"
        @click="setTheme(option.value)"
      >
        {{ option.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { type ThemePreference, useTheme } from '@/composables/useTheme';

const { t } = useI18n();
const { theme, setTheme } = useTheme();

const options = computed<{ value: ThemePreference; label: string }[]>(() => [
  { value: 'light', label: t('auth.account.themeLight') },
  { value: 'auto', label: t('auth.account.themeAuto') },
  { value: 'dark', label: t('auth.account.themeDark') },
]);
</script>

<style scoped>
.theme-switcher {
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

.theme-options {
  display: flex;
  gap: 0;
  background: var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: 3px;
  max-width: 300px;
}

.theme-option {
  flex: 1;
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
  border-radius: calc(var(--radius-base) - 2px);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-fast);
}

.theme-option:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.theme-option:hover:not(.active) {
  color: var(--color-text-secondary);
}

.theme-option.active {
  background: var(--color-bg-panel);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-sm), 0 0 0 1px var(--color-bg-border);
}

@media (width <= 480px) {
  .theme-options {
    max-width: 100%;
  }
}
</style>
