<template>
  <div class="function-call-table-wrapper">
    <table
      v-if="calls && calls.length > 0"
      class="function-call-table"
    >
      <thead>
        <tr>
          <th class="call-column">{{ $t('problems.display.callHeader') }}</th>
          <th class="return-column">{{ $t('problems.display.returnsHeader') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(call, i) in calls" :key="i">
          <td class="call-cell">
            <code>{{ formatCall(call.args) }}</code>
          </td>
          <td class="return-cell">
            <code>{{ formatValue(call.return_value) }}</code>
          </td>
        </tr>
      </tbody>
    </table>
    <div
      v-else
      class="table-empty"
    >
      {{ $t('problems.display.noFunctionCallsConfigured') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FunctionCall } from '@/types'

interface Props {
  functionName: string;
  functionSignature?: string;
  calls: FunctionCall[];
}

const props = withDefaults(defineProps<Props>(), {
  functionSignature: '',
})

function formatValue(val: unknown): string {
  if (val === null || val === undefined) {return 'None'}
  if (typeof val === 'string') {return `'${val}'`}
  if (typeof val === 'boolean') {return val ? 'True' : 'False'}
  if (Array.isArray(val)) {return `[${val.map(formatValue).join(', ')}]`}
  return String(val)
}

function formatCall(args: unknown[]): string {
  const paramNames = parseParamNames(props.functionSignature)
  const formattedArgs = args.map((arg, i) => {
    const name = paramNames[i]
    const val = formatValue(arg)
    return name ? `${name}=${val}` : val
  })
  return `${props.functionName}(${formattedArgs.join(', ')})`
}

function parseParamNames(signature: string): string[] {
  if (!signature) {return []}
  const match = signature.match(/\(([^)]*)\)/)
  if (!match) {return []}
  return match[1]
    .split(',')
    .map(p => p.trim().split(/[:\s=]/)[0].trim())
    .filter(Boolean)
}
</script>

<style scoped>
.function-call-table-wrapper {
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  overflow: hidden;
}

.function-call-table {
  width: 100%;
  border-collapse: collapse;
  font-family: 'Courier New', Courier, monospace;
  font-size: var(--font-size-sm);
}

.function-call-table thead {
  background: var(--color-bg-section);
}

.function-call-table th {
  padding: var(--spacing-sm) var(--spacing-md);
  text-align: left;
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid var(--color-bg-border);
}

.function-call-table td {
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: 1px solid var(--color-bg-border);
  color: var(--color-text-primary);
}

.function-call-table tbody tr:last-child td {
  border-bottom: none;
}

.function-call-table tbody tr:hover {
  background: var(--color-bg-section);
}

.call-cell code {
  color: var(--color-text-primary);
}

.return-cell code {
  color: var(--color-primary-gradient-start);
  font-weight: 600;
}

.call-column {
  width: 65%;
}

.return-column {
  width: 35%;
}

.table-empty {
  color: var(--color-text-muted);
  font-style: italic;
  text-align: center;
  padding: var(--spacing-lg);
  background: var(--color-bg-input);
}
</style>
