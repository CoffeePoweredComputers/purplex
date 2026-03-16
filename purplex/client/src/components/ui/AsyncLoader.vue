<template>
  <div
    class="async-loader"
    role="status"
    aria-live="polite"
  >
    <div
      class="spinner"
      aria-hidden="true"
    />
    <span class="visually-hidden">{{ $t('common.loading') }}</span>
  </div>
</template>

<script setup lang="ts">
// Template uses $t() for i18n — no additional setup needed
</script>

<style scoped>
.async-loader {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100px;
  width: 100%;
  height: 100%;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-bg-input);
  border-top-color: var(--color-primary-gradient-start);
  border-radius: var(--radius-circle);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
