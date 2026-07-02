<template>
  <div class="counterexample-hint">
    <div class="hint-content">
      <span class="hint-label">{{ $t('problems.hints.counterexample.tryInputs') }}</span>
      <div class="hint-params">
        <code
          v-for="(value, key) in input"
          :key="String(key)"
          class="hint-param"
        >
          {{ key }} = {{ formatValue(value) }}
        </code>
      </div>
      <p
        v-if="explanation"
        class="hint-explanation"
      >
        {{ explanation }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  input: Record<string, unknown>
  explanation?: string
}>()

function formatValue(value: unknown): string {
  if (typeof value === 'string') return `"${value}"`
  if (value === null) return 'None'
  if (value === undefined) return 'None'
  if (Array.isArray(value)) return JSON.stringify(value)
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>

<style scoped>
.counterexample-hint {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-md) var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  transition: var(--transition-base);
}

.counterexample-hint:hover {
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-sm);
}

.hint-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.hint-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.hint-params {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.hint-param {
  font-family: var(--font-mono, 'SF Mono', 'Monaco', 'Inconsolata', monospace);
  font-size: var(--font-size-sm);
  background: var(--color-bg-code);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  color: var(--color-text-primary);
}

.hint-explanation {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

@media (max-width: 768px) {
  .counterexample-hint {
    margin: var(--spacing-md);
  }

  .hint-params {
    flex-direction: column;
  }
}
</style>
