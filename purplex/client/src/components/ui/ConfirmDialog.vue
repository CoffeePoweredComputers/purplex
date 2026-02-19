<template>
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div v-if="visible" class="dialog-overlay" @click.self="$emit('cancel')">
        <div class="dialog" role="alertdialog" :aria-label="title">
          <h3>{{ title }}</h3>
          <p>{{ message }}</p>
          <div class="dialog-actions">
            <button class="btn btn-secondary" @click="$emit('cancel')">
              Cancel
            </button>
            <button
              :class="['btn', confirmVariant === 'warning' ? 'btn-warning' : 'btn-danger']"
              :disabled="loading"
              @click="$emit('confirm')"
            >
              {{ loading ? 'Please wait...' : confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
interface Props {
  visible: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  confirmVariant?: 'danger' | 'warning';
  loading?: boolean;
}

withDefaults(defineProps<Props>(), {
  confirmLabel: 'Confirm',
  confirmVariant: 'danger',
  loading: false,
});

defineEmits<{
  confirm: [];
  cancel: [];
}>();
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  max-width: 400px;
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

.btn-danger {
  background: var(--color-error);
  color: var(--color-text-primary);
}

.btn-warning {
  background: var(--color-warning);
  color: var(--color-text-primary);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Transition */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
