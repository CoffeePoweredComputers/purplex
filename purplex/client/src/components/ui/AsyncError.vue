<template>
  <div
    class="async-error"
    role="alert"
  >
    <p class="error-message">
      Failed to load component
    </p>
    <button
      v-if="retry"
      class="retry-button"
      @click="retry"
    >
      Try Again
    </button>
  </div>
</template>

<script setup lang="ts">
/**
 * AsyncError - Error fallback for async component loading.
 *
 * Vue's defineAsyncComponent passes these props automatically:
 * - error: The error that occurred
 * - retry: Function to retry loading
 * - fail: Function to fail permanently
 */
defineProps<{
  error?: Error
  retry?: () => void
  fail?: () => void
}>()
</script>

<style scoped>
.async-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  min-height: 100px;
  width: 100%;
  height: 100%;
  padding: var(--spacing-lg);
}

.error-message {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin: 0;
}

.retry-button {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-fast);
}

.retry-button:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.retry-button:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.retry-button:focus:not(:focus-visible) {
  outline: none;
}
</style>
