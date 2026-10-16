<template>
  <div class="test-ladder">
    <!-- One pip per test, in test order: passed / first failure / locked -->
    <div
      class="ladder"
      role="list"
      :aria-label="$t('feedback.tests.ladderLabel')"
    >
      <template
        v-for="n in totalTests"
        :key="n"
      >
        <button
          v-if="n - 1 < passedRows"
          type="button"
          class="pip pass"
          role="listitem"
          :aria-pressed="isOpen(n - 1)"
          :aria-label="$t('feedback.tests.pipPassed', { n })"
          @click="toggle(n - 1)"
        >
          {{ n }}
        </button>
        <span
          v-else-if="n - 1 === failIndex"
          class="pip fail"
          role="listitem"
          aria-current="step"
          :aria-label="$t('feedback.tests.pipFailed', { n })"
        >{{ n }}</span>
        <span
          v-else
          class="pip lock"
          role="listitem"
          :aria-label="$t('feedback.tests.pipLocked', { n })"
          :title="$t('feedback.tests.unlockHint', { n: failIndex + 1 })"
        >{{ n }}</span>
      </template>
    </div>

    <!-- Ledger: passed rows closed by default, the failing row open, then the locked rest -->
    <div class="ledger">
      <template
        v-for="(test, i) in tests"
        :key="i"
      >
        <button
          v-if="isPassingRow(test)"
          type="button"
          class="ledger-row pass"
          :class="isOpen(i) ? 'open' : 'closed'"
          :aria-expanded="isOpen(i)"
          :aria-label="$t('feedback.tests.rowPassed', { n: i + 1, call: test.function_call })"
          @click="toggle(i)"
        >
          <span class="row-num">{{ i + 1 }}</span>
          <span
            class="row-toggle"
            aria-hidden="true"
          >{{ isOpen(i) ? '▾' : '▸' }}</span>
          <span class="row-body">
            <code class="test-call">{{ test.function_call }}</code>
            <span
              class="arrow"
              aria-hidden="true"
            >→</span>
            <code class="result">{{ formatTestValue(test.expected_output) }}</code>
          </span>
          <span
            class="row-status"
            aria-hidden="true"
          >✓</span>
        </button>
        <div
          v-else
          class="ledger-row fail"
        >
          <span class="row-num">{{ i + 1 }}</span>
          <span class="row-toggle" />
          <span class="row-body">
            <code class="test-call">{{ test.function_call }}</code>
            <!-- Two-line diff: "− got <actual>" over "+ expected <expected>" -->
            <span class="diff">
              <span
                class="diff-sign got"
                aria-hidden="true"
              >−</span>
              <span class="diff-label">{{ $t('feedback.tests.gotInline') }}</span>
              <code
                class="actual"
                :class="{ 'is-error': test.error }"
              >{{ test.error || formatTestValue(test.actual_output) }}</code>
              <span
                class="diff-sign want"
                aria-hidden="true"
              >+</span>
              <span class="diff-label">{{ $t('feedback.tests.expectedInline') }}</span>
              <code class="expected">{{ formatTestValue(test.expected_output) }}</code>
            </span>
          </span>
          <span
            class="row-status"
            :aria-label="$t('feedback.tests.pipFailed', { n: i + 1 })"
          >✗</span>
          <button
            type="button"
            class="debug-btn"
            :aria-label="$t('feedback.codeSubmission.debugTestCase', { call: test.function_call })"
            @click="$emit('debug', test)"
          >
            <span aria-hidden="true">🔍</span>
          </button>
        </div>
      </template>
      <div
        v-if="lockedCount > 0"
        class="ledger-row lock"
      >
        <span
          class="row-num"
          aria-hidden="true"
        >🔒</span>
        <span class="row-body">{{ lockedText }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * TestLadder - ordered test results for probeable_code feedback.
 *
 * Rows arrive already truncated to the first failure (backend
 * result_visibility.truncate_to_first_failure): every passing test up to the
 * first failure, then that failure. This renders them as a ladder of pips
 * (one per test, including the locked ones) over a ledger where passed rows
 * are closed one-liners and the failing row is open. Nothing here reveals
 * how the locked tests fared.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { type FeedbackTestRow, formatTestValue, isPassingRow } from './feedbackTests'

interface Props {
  /** Visible rows, in test order */
  tests: FeedbackTestRow[]
  /** Tests hidden after the first failure */
  lockedCount?: number
  /** Total test count; defaults to rows + locked */
  totalCount?: number | null
}

const props = withDefaults(defineProps<Props>(), {
  lockedCount: 0,
  totalCount: null,
})

defineEmits<{
  (e: 'debug', test: FeedbackTestRow): void
}>()

const { t } = useI18n()

const failIndex = computed(() => props.tests.findIndex(test => !isPassingRow(test)))
/** Rows before the first failure (all rows when nothing fails). */
const passedRows = computed(() =>
  failIndex.value < 0 ? props.tests.length : failIndex.value
)
const totalTests = computed(() =>
  props.totalCount ?? props.tests.length + props.lockedCount
)

const lockedText = computed(() =>
  t(props.lockedCount === 1 ? 'feedback.tests.lockedRowOne' : 'feedback.tests.lockedRow', {
    count: props.lockedCount,
    n: failIndex.value + 1,
  })
)

const openRows = ref<Set<number>>(new Set())
watch(() => props.tests, () => { openRows.value = new Set() })

function isOpen(i: number): boolean {
  return openRows.value.has(i)
}

function toggle(i: number): void {
  const next = new Set(openRows.value)
  if (next.has(i)) {next.delete(i)} else {next.add(i)}
  openRows.value = next
}
</script>

<style scoped>
.test-ladder {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  font-family: Monaco, Menlo, 'Ubuntu Mono', monospace;
  font-size: var(--font-size-sm);
}

.ladder {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.pip {
  width: 28px;
  height: 28px;
  padding: 0;
  display: grid;
  place-items: center;
  border-radius: var(--radius-xs);
  border: 1px solid var(--color-bg-input);
  font: inherit;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.pip.pass {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border-color: transparent;
  cursor: pointer;
}

.pip.pass[aria-pressed='true'] {
  outline: 2px solid var(--color-success);
  outline-offset: 1px;
}

.pip.fail {
  background: var(--color-error-bg);
  color: var(--color-error-text);
  border-color: var(--color-error);
  box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 3px var(--color-error);
}

.pip.lock {
  background: var(--color-bg-input);
  color: var(--color-text-muted);
  border-style: dashed;
}

.ledger {
  display: flex;
  flex-direction: column;
}

.ledger-row {
  display: grid;
  grid-template-columns: 2ch 1.2ch minmax(0, 1fr) 2ch auto;
  gap: 0 var(--spacing-sm);
  align-items: start;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-top: 1px solid var(--color-bg-input);
  color: var(--color-text-primary);
  text-align: left;
}

.ledger-row:first-child {
  border-top: 0;
}

/* Passed rows are buttons: strip the native look */
button.ledger-row {
  width: 100%;
  background: none;
  border-left: 0;
  border-right: 0;
  border-bottom: 0;
  font: inherit;
  cursor: pointer;
}

button.ledger-row:hover {
  background: var(--color-bg-section);
}

.row-num {
  color: var(--color-text-muted);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.row-toggle {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.row-body {
  min-width: 0;
  overflow-wrap: anywhere;
}

.arrow {
  color: var(--color-text-muted);
  margin: 0 var(--spacing-xs);
}

.row-status {
  text-align: center;
  font-weight: 700;
}

.ledger-row.pass .row-status {
  color: var(--color-success);
}

.ledger-row.fail .row-status {
  color: var(--color-error);
}

.ledger-row.closed .row-body {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--color-text-muted);
}

.ledger-row.closed .arrow,
.ledger-row.closed .result {
  display: none;
}

.ledger-row.fail {
  background: var(--color-error-overlay);
}

/* Failing row: call on its own line, then a two-line diff beneath it.
   One grid holds both lines so the labels and values align vertically. */
.ledger-row.fail .row-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.diff {
  display: grid;
  grid-template-columns: 1.5ch max-content minmax(0, 1fr);
  column-gap: var(--spacing-xs);
}

.diff-sign {
  font-weight: 700;
}

.diff-label {
  color: var(--color-text-muted);
}

.diff-sign.got,
.actual {
  color: var(--color-error);
}

.diff-sign.want,
.expected {
  color: var(--color-success);
}

.actual.is-error {
  font-style: italic;
}

.ledger-row.lock {
  grid-template-columns: 2ch 1fr;
  background: var(--color-bg-section);
  color: var(--color-text-muted);
  font-family: inherit;
}

.debug-btn {
  background: var(--color-info);
  color: var(--color-text-on-filled);
  border: none;
  padding: var(--spacing-xs);
  border-radius: var(--radius-xs);
  cursor: pointer;
  font-size: var(--font-size-sm);
  min-width: 44px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
}

.debug-btn:hover {
  background: var(--color-info-dark);
}

.pip:focus-visible,
button.ledger-row:focus-visible,
.debug-btn:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

@media (forced-colors: active) {
  .pip.fail {
    outline: 2px solid CanvasText;
  }
}
</style>
