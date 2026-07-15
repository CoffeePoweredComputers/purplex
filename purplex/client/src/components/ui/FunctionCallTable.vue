<template>
  <div class="function-call-table-wrapper">
    <table
      v-if="calls && calls.length > 0"
      class="function-call-table"
    >
      <thead>
        <tr>
          <th class="call-column">
            {{ $t('problems.display.callHeader') }}
          </th>
          <th class="return-column">
            {{ $t('problems.display.returnsHeader') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(call, i) in calls"
          :key="i"
        >
          <td class="call-cell">
            <code>
              <span
                v-for="(seg, segIdx) in callSegments(call.args)"
                :key="segIdx"
                :class="seg.cls"
              >{{ seg.text }}</span>
            </code>
          </td>
          <td class="return-cell">
            <span class="return-chip">{{ formatValue(call.return_value) }}</span>
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
import { computed } from 'vue'
import type { FunctionCall } from '@/types'

interface Props {
  functionName: string;
  functionSignature?: string;
  calls: FunctionCall[];
}

const props = withDefaults(defineProps<Props>(), {
  functionSignature: '',
})

const paramNames = computed(() => parseParamNames(props.functionSignature))

interface CallSegment {
  text: string;
  cls: string;
}

/**
 * Break a call into styled segments (function name, punctuation, param
 * names, values) so the template can syntax-color each part.
 */
function callSegments(args: unknown[]): CallSegment[] {
  const segments: CallSegment[] = [
    { text: props.functionName, cls: 'call-fn' },
    { text: '(', cls: 'call-punc' },
  ]
  args.forEach((arg, i) => {
    if (i > 0) {segments.push({ text: ', ', cls: 'call-punc' })}
    const name = paramNames.value[i]
    if (name) {segments.push({ text: `${name}=`, cls: 'call-param' })}
    segments.push({ text: formatValue(arg), cls: 'call-value' })
  })
  segments.push({ text: ')', cls: 'call-punc' })
  return segments
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) {return 'None'}
  if (typeof val === 'string') {return `'${val}'`}
  if (typeof val === 'boolean') {return val ? 'True' : 'False'}
  if (Array.isArray(val)) {return `[${val.map(formatValue).join(', ')}]`}
  return String(val)
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
  background: var(--color-bg-table);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  overflow: hidden;
}

.function-call-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-base);
}

/* Header row: section surface with a 2px primary-gradient rule along the
   bottom edge (painted as a clipped row background, not a border, so the
   gradient runs continuously across both columns). */
.function-call-table thead tr {
  background-color: var(--color-bg-section);
  background-image: linear-gradient(
    90deg,
    var(--color-primary-gradient-start),
    var(--color-primary-gradient-end)
  );
  background-size: 100% 2px;
  background-position: bottom;
  background-repeat: no-repeat;
}

.function-call-table th {
  padding: var(--spacing-md) var(--spacing-lg);
  text-align: left;
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.function-call-table td {
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-border);
  color: var(--color-text-primary);
  text-align: left;
  font-family: var(--font-family-mono, Monaco, Menlo, 'Ubuntu Mono', monospace);
}

.function-call-table tbody tr:last-child td {
  border-bottom: none;
}

.function-call-table tbody tr {
  transition: var(--transition-fast);
}

.function-call-table tbody tr:hover {
  background: var(--color-primary-overlay);
}

.function-call-table tbody tr:hover td:first-child {
  box-shadow: inset 2px 0 0 var(--color-primary-gradient-start);
}

.call-cell code {
  color: var(--color-text-primary);
}

.call-fn {
  color: var(--color-syntax-builtin);
  font-weight: 600;
}

.call-punc {
  color: var(--color-text-muted);
}

.call-param {
  color: var(--color-text-muted);
}

.call-value {
  color: var(--color-text-primary);
}

.return-column,
.return-cell {
  text-align: right;
}

.return-chip {
  display: inline-block;
  min-width: 44px;
  padding: 3px 14px;
  border-radius: var(--radius-round);
  background: var(--color-bg-section);
  border: 1px solid var(--color-success-overlay);
  color: var(--color-success);
  font-weight: 700;
  text-align: center;
  font-variant-numeric: tabular-nums;
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
}
</style>
