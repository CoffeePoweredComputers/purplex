<template>
  <div
    class="terminal-display"
    role="log"
    :aria-label="ariaLabel || $t('problems.display.terminalAriaLabel')"
  >
    <template v-for="(run, ri) in runs" :key="ri">
      <div
        v-if="runs.length > 1"
        class="run-divider"
      >
        <span class="run-label">{{ run.label || $t('problems.display.runNumber', { n: ri + 1 }) }}</span>
      </div>
      <div class="terminal-run">
        <div
          v-for="(line, li) in run.interactions"
          :key="`${ri}-${li}`"
          class="terminal-line"
          :class="{
            'terminal-input': line.type === 'input',
            'terminal-output': line.type === 'output',
          }"
        >
          <span
            v-if="line.type === 'input'"
            class="input-marker"
          >&gt;</span>
          <span class="line-text">{{ line.text }}</span>
        </div>
      </div>
    </template>
    <div
      v-if="!runs || runs.length === 0"
      class="terminal-empty"
    >
      {{ $t('problems.display.noTerminalConfigured') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TerminalRun } from '@/types'

interface Props {
  runs: TerminalRun[];
  ariaLabel?: string;
}

withDefaults(defineProps<Props>(), {
  ariaLabel: 'Terminal interaction display',
})
</script>

<style scoped>
.terminal-display {
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-md);
  font-family: 'Courier New', Courier, monospace;
  font-size: var(--font-size-sm);
  line-height: 1.6;
  overflow-x: auto;
}

.run-divider {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin: var(--spacing-md) 0 var(--spacing-sm);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.run-divider:first-child {
  margin-top: 0;
}

.run-divider::before,
.run-divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid var(--color-bg-border);
}

.run-label {
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.terminal-run {
  display: flex;
  flex-direction: column;
}

.terminal-line {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-xs);
  padding: 1px 0;
  white-space: pre-wrap;
  overflow-wrap: break-word;
}

.terminal-output {
  color: var(--color-text-secondary);
}

.terminal-input {
  color: var(--color-primary-gradient-start);
}

.input-marker {
  color: var(--color-primary-gradient-start);
  font-weight: 700;
  user-select: none;
  flex-shrink: 0;
}

.line-text {
  flex: 1;
}

.terminal-empty {
  color: var(--color-text-muted);
  font-style: italic;
  text-align: center;
  padding: var(--spacing-lg);
}
</style>
