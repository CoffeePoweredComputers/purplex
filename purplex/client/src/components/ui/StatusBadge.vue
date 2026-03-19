<template>
  <span :class="['status-badge', `status-${variant}`]">
    {{ displayLabel }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { BadgeVariant } from '@/types/datatable';

interface Props {
  /** The value to display (used as label if label not provided) */
  value: string;
  /** Visual variant for the badge */
  variant?: BadgeVariant;
  /** Custom display label (overrides value) */
  label?: string;
  /** Transform text to uppercase */
  uppercase?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  uppercase: true,
});

const displayLabel = computed(() => props.label || props.value);
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 80px;
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  text-align: center;
}

/* Success - green */
.status-success {
  background-color: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

/* Warning - yellow/amber */
.status-warning {
  background-color: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

/* Error - red */
.status-error {
  background-color: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

/* Info - blue */
.status-info {
  background-color: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}

/* Default - neutral/gray */
.status-default {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

/* Admin - gradient purple (matches AdminUsers badge) */
.status-admin {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  box-shadow: 0 2px 8px var(--color-primary-glow);
  border: none;
}

/* Instructor - gradient blue (matches AdminUsers badge) */
.status-instructor {
  background: linear-gradient(135deg, var(--color-info) 0%, var(--color-info-dark) 100%);
  color: var(--color-text-primary);
  box-shadow: 0 2px 8px var(--color-info-overlay);
  border: none;
}
</style>
