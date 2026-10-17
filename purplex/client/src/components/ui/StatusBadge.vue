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
  label: undefined,
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
  border: 1px solid var(--color-border);
}

/* Admin and Instructor - solid role colours */
.status-admin {
  background: var(--color-admin);
  color: var(--color-text-on-filled);
  border: 1px solid var(--color-admin);
}

.status-instructor {
  background: var(--color-bg-panel);
  color: var(--color-instructor);
  border: 1px solid var(--color-instructor);
}

/* Category - outline in a categorical ramp slot (labels, not status). The
   ramp only clears 3:1, so the slot colours the border and the text stays
   neutral. */
.status-category-1,
.status-category-2,
.status-category-3,
.status-category-4,
.status-category-5,
.status-category-6 {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid;
}

.status-category-1 { border-color: var(--color-category-1); }
.status-category-2 { border-color: var(--color-category-2); }
.status-category-3 { border-color: var(--color-category-3); }
.status-category-4 { border-color: var(--color-category-4); }
.status-category-5 { border-color: var(--color-category-5); }
.status-category-6 { border-color: var(--color-category-6); }
</style>
