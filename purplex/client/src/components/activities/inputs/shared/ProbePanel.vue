<template>
  <div class="probe-panel">
    <div class="probe-input-wrapper">
      <div class="probe-row">
        <div class="probe-call">
          <!-- Call line: only the argument list between the parentheses is editable -->
          <!-- Whitespace between these spans contains newlines, so Vue drops it -->
          <div
            class="call-shell"
            :class="{ 'has-error': hasErrors, 'is-disabled': !editable }"
            @click="focusArgs"
          >
            <span class="fn-name">{{ functionName }}</span>
            <span class="fn-paren">(</span>
            <span
              id="probe-args"
              ref="argsRef"
              class="call-args"
              :contenteditable="editable ? EDITABLE_MODE : 'false'"
              role="textbox"
              aria-multiline="false"
              spellcheck="false"
              :data-placeholder="argsPlaceholder"
              :aria-placeholder="argsPlaceholder"
              :aria-label="$t('problems.probe.argsAriaLabel', { name: functionName })"
              :aria-disabled="editable ? undefined : 'true'"
              :aria-invalid="hasErrors ? 'true' : undefined"
              :aria-describedby="hasErrors ? 'probe-field-errors probe-args-help' : 'probe-args-help'"
              @input="onArgsInput"
              @keydown="onArgsKeydown"
              @paste="onArgsPaste"
            />
            <span class="fn-paren">)</span>
          </div>
          <span class="fn-arrow">→</span>
          <span
            class="fn-result"
            :class="{
              'has-result': displayResult !== null,
              'result-flash': showResultFlash,
              'is-cached': isDuplicate
            }"
            :aria-label="isDuplicate ? $t('problems.probe.cachedResultAriaLabel', { result: formatOutput(cachedResult) }) : undefined"
          >
            {{ displayResult !== null ? formatOutput(displayResult) : '?' }}
          </span>
        </div>

        <button
          v-if="uniqueHistory.length > 0"
          class="history-btn"
          :aria-label="$t('problems.probe.historyAriaLabel', { count: uniqueHistory.length })"
          @click="showModal = true"
        >
          {{ $t('problems.probe.history', { count: uniqueHistory.length }) }}
        </button>
      </div>

      <!-- Line-level and per-parameter errors -->
      <ul
        id="probe-field-errors"
        class="probe-field-errors"
        aria-live="polite"
      >
        <li
          v-if="lineError"
          id="probe-err-line"
        >
          {{ lineError }}
        </li>
        <li
          v-for="(message, name) in inputErrors"
          :id="`probe-err-${name}`"
          :key="name"
        >
          {{ name }}: {{ message }}
        </li>
      </ul>

      <!-- Probe Button: exhausted outranks duplicate, so the "· 0 left" badge stays -->
      <button
        class="probe-btn"
        :class="{ 'is-duplicate': isDuplicate && canProbe }"
        :disabled="!canProbe || isExecuting || !hasValidInputs || isDuplicate"
        :aria-busy="isExecuting"
        :aria-disabled="isDuplicate && canProbe"
        :title="buttonTooltip"
        @click="$emit('execute-probe')"
      >
        <template v-if="isExecuting">
          <span class="spinner" />
          <span>{{ $t('problems.probe.probing') }}</span>
        </template>
        <template v-else-if="isDuplicate && canProbe">
          <span
            class="duplicate-icon"
            aria-hidden="true"
          >✓</span>
          <span>{{ $t('problems.probe.alreadyProbed') }}</span>
        </template>
        <template v-else>
          <span>{{ $t('problems.probe.probe') }}</span>
          <span
            v-if="probeCountDisplay"
            class="probe-count-badge"
            :class="probeStatusClass"
          >· {{ probeCountDisplay }}</span>
        </template>
      </button>

      <!-- Keyboard instructions for the call line (visually hidden, via aria-describedby) -->
      <div
        id="probe-args-help"
        class="sr-only"
      >
        {{ $t('problems.probe.argsHelp') }}
      </div>

      <!-- Screen reader announcement (visually hidden) -->
      <div
        class="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {{ srAnnouncement }}
      </div>
    </div>

    <div
      v-if="probeError || probeStatusText"
      :class="probeError ? 'probe-error' : 'probe-status-hint'"
      aria-live="polite"
    >
      {{ probeError || probeStatusText }}
    </div>

    <!-- Full History Modal -->
    <Teleport to="body">
      <div
        v-if="showModal"
        class="modal-overlay"
        @click="showModal = false"
        @keydown.escape="showModal = false"
      >
        <div
          ref="modalContentRef"
          class="modal-content"
          role="dialog"
          aria-modal="true"
          aria-labelledby="history-modal-title"
          @click.stop
        >
          <div class="modal-header">
            <h4 id="history-modal-title">
              {{ $t('problems.probe.probeHistory') }}
            </h4>
            <button
              class="modal-close"
              :aria-label="$t('common.close')"
              @click="showModal = false"
            >
              ✕
            </button>
          </div>
          <div class="modal-body">
            <div
              v-for="(entry, idx) in uniqueHistory"
              :key="idx"
              class="modal-row"
            >
              <span class="modal-index">#{{ uniqueHistory.length - idx }}</span>
              <span class="modal-call">{{ formatFunctionCall(entry.input) }}</span>
              <span class="modal-arrow">→</span>
              <span class="modal-result">{{ formatOutput(entry.output) }}</span>
            </div>
            <div
              v-if="uniqueHistory.length === 0"
              class="empty-state"
            >
              {{ $t('problems.probe.noProbesYet') }}
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ProbeHistoryEntry, ProbeParameter } from '../../types'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { stableStringify } from './probeArgs'

const { t } = useI18n()

interface Props {
  functionName: string
  probeStatusClass: string
  probeCountDisplay: string
  probeStatusText?: string
  probeParams: ProbeParameter[]
  argsLine: string
  lineError: string | null
  canProbe: boolean
  isExecuting: boolean
  hasValidInputs: boolean
  inputErrors: Record<string, string>
  probeHistory: ProbeHistoryEntry[]
  probeError: string | null
  isDuplicate: boolean
  cachedResult: unknown
  formatFunctionCall: (input: Record<string, unknown>) => string
  formatOutput: (output: unknown) => string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'execute-probe'): void
  (e: 'update-args', text: string): void
}>()

/** 'plaintext-only' where supported; older browsers reject it and get plain 'true'. */
function detectEditableMode(): 'plaintext-only' | 'true' {
  try {
    const probe = document.createElement('span')
    probe.contentEditable = 'plaintext-only'
    return probe.contentEditable === 'plaintext-only' ? 'plaintext-only' : 'true'
  } catch {
    return 'true'
  }
}

const EDITABLE_MODE = detectEditableMode()

const argsRef = ref<HTMLElement | null>(null)

const editable = computed(() => props.canProbe && !props.isExecuting)
const hasErrors = computed(() => !!props.lineError || Object.keys(props.inputErrors).length > 0)
// Parameter names are not secret, so they show even when the signature is hidden
// Types show only when the signature is visible: the backend sends '' otherwise
const argsPlaceholder = computed(() =>
  props.probeParams.map(p => (p.type ? `${p.name}: ${p.type}` : p.name)).join(', ')
)

// Keep the DOM in step when the line changes from outside (e.g. reset on a new
// problem); while typing the two already match, so the caret is left alone.
watch(
  () => props.argsLine,
  (line) => {
    const el = argsRef.value
    if (el && (el.textContent ?? '') !== line) {
      el.textContent = line
    }
  },
)

// The line is not editable while a probe runs, which drops focus; give it back
// afterwards so a keyboard user can keep probing with Enter. This watcher runs
// before the DOM update, so focus is still on the line when a probe starts.
let argsFocusedBeforeProbe = false
watch(
  () => props.isExecuting,
  (executing) => {
    if (executing) {
      argsFocusedBeforeProbe = !!argsRef.value && document.activeElement === argsRef.value
      return
    }
    if (!argsFocusedBeforeProbe) {
      return
    }
    argsFocusedBeforeProbe = false
    nextTick(() => {
      const el = argsRef.value
      if (el && editable.value) {
        el.focus()
        placeCaret(el, null)
      }
    })
  },
)

onMounted(() => {
  if (argsRef.value && props.argsLine) {
    argsRef.value.textContent = props.argsLine
  }
})

function emitArgs() {
  const el = argsRef.value
  if (!el) {
    return
  }
  const text = el.textContent ?? ''
  // A browser may leave a stray <br> once emptied; clear it so :empty shows the placeholder
  if (text === '' && el.childNodes.length > 0) {
    el.replaceChildren()
  }
  emit('update-args', text)
}

function onArgsInput() {
  emitArgs()
}

function placeCaret(el: HTMLElement, offset: number | null) {
  const selection = window.getSelection()
  if (!selection) {
    return
  }
  const range = document.createRange()
  const textNode = el.firstChild
  if (offset !== null && textNode?.nodeType === Node.TEXT_NODE) {
    range.setStart(textNode, Math.min(offset, textNode.textContent?.length ?? 0))
    range.collapse(true)
  } else {
    range.selectNodeContents(el)
    range.collapse(false)
  }
  selection.removeAllRanges()
  selection.addRange(range)
}

function focusArgs(event: MouseEvent) {
  const el = argsRef.value
  if (el && editable.value && event.target !== el) {
    el.focus()
    placeCaret(el, null)
  }
}

function onArgsKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    // One logical line: Enter probes, Shift+Enter does nothing
    event.preventDefault()
    if (!event.shiftKey && !props.isExecuting && props.canProbe && props.hasValidInputs && !props.isDuplicate) {
      emit('execute-probe')
    }
    return
  }
}

/** Paste as plain text on one line, for browsers that ignore plaintext-only. */
function onArgsPaste(event: ClipboardEvent) {
  event.preventDefault()
  const text = (event.clipboardData?.getData('text/plain') ?? '').replace(/\r?\n/g, ' ')
  if (!text) {
    return
  }
  // execCommand keeps the native undo stack; it is deprecated but still the only way to
  // do that, so fall back to a Selection edit where it is unsupported
  if (document.execCommand?.('insertText', false, text)) {
    return
  }
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) {
    return
  }
  const range = selection.getRangeAt(0)
  range.deleteContents()
  const node = document.createTextNode(text)
  range.insertNode(node)
  range.setStartAfter(node)
  range.collapse(true)
  selection.removeAllRanges()
  selection.addRange(range)
  argsRef.value?.normalize()
  emitArgs()
}

const showModal = ref(false)
const showResultFlash = ref(false)

// Focus trap for modal accessibility
const { modalContentRef } = useFocusTrap(showModal)

// Unique history entries (dedupe by input)
const uniqueHistory = computed(() => {
  const seen = new Set<string>()
  return props.probeHistory.filter(entry => {
    const key = stableStringify(entry.input)
    if (seen.has(key)) {return false}
    seen.add(key)
    return true
  })
})

// Get the last result to display inline
const lastResult = computed(() => {
  if (props.probeHistory.length === 0) {
    return null
  }
  return props.probeHistory[0].output
})

// Display result: show cached result when duplicate, otherwise last result
const displayResult = computed(() => {
  if (props.isDuplicate) {
    return props.cachedResult
  }
  return lastResult.value
})

// Tooltip for button - changes based on state
const buttonTooltip = computed(() => {
  if (props.isDuplicate && props.canProbe) {
    return t('problems.probe.tooltipDuplicate')
  }
  if (props.probeStatusClass === 'status-explore') {
    return t('problems.probe.tooltipUnlimited')
  }
  if (props.probeStatusClass === 'status-exhausted') {
    return t('problems.probe.tooltipExhausted')
  }
  return t('problems.probe.tooltipDefault')
})

// Screen reader announcement for duplicate state
const srAnnouncement = computed(() => {
  if (props.isDuplicate) {
    return t('problems.probe.srDuplicate', { result: props.formatOutput(props.cachedResult) })
  }
  return ''
})

// Flash animation when new result arrives
watch(() => props.probeHistory.length, () => {
  showResultFlash.value = true
  setTimeout(() => {
    showResultFlash.value = false
  }, 600)
})
</script>

<style scoped>
/* ===========================================
   PROBE PANEL - Container
   =========================================== */
.probe-panel {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
}

/* ===========================================
   PROBE INPUT WRAPPER
   =========================================== */
.probe-input-wrapper {
  background: var(--color-bg-input);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-base);
  margin: var(--spacing-sm) var(--spacing-lg);
  padding: var(--spacing-sm) var(--spacing-md);
  transition: border-color 0.2s ease;
}

.probe-input-wrapper:focus-within {
  border-color: var(--color-focus-ring);
}

/* Row containing probe-call and history button; wraps so a narrow screen
   gives the call line the full width */
.probe-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.probe-call {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  flex-wrap: wrap;

  /* A real basis (not 0) so the history button wraps below on narrow screens */
  flex: 1 1 16rem;
  min-width: 0;
}

/* ===========================================
   HISTORY BUTTON
   =========================================== */
.history-btn {
  flex-shrink: 0;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-btn:hover {
  background: var(--color-bg-input);
  border-color: var(--color-accent);
  color: var(--color-text-primary);
}

.history-btn:focus {
  outline: 2px solid var(--color-focus-ring);
  outline-offset: 2px;
}

.fn-name {
  color: var(--color-info);
  font-weight: 600;
}

.fn-paren {
  color: var(--color-text-muted);
  font-weight: 400;
}

/* Call line: inline flow, so the closing paren trails the last argument character */
.call-shell {
  flex: 1 1 16rem;
  min-width: 0;
  min-height: 32px;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  text-align: left;
  overflow-wrap: anywhere;
  cursor: text;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.call-shell .fn-name,
.call-shell .fn-paren {
  user-select: none;
}

.call-shell:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-accent-overlay);
}

/* Forced-colors mode drops box-shadow and recolours borders: keep a visible focus ring */
@media (forced-colors: active) {
  .call-shell:focus-within {
    outline: 2px solid CanvasText;
    outline-offset: 2px;
  }
}

.call-shell.has-error {
  border-color: var(--color-error);
}

.call-shell.has-error:focus-within {
  box-shadow: 0 0 0 2px var(--color-error-overlay);
}

.call-shell.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.call-args {
  padding: 0 2px;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  outline: none;
}

.call-args:empty::before {
  content: attr(data-placeholder);
  color: var(--color-text-muted);
  pointer-events: none;
}

.fn-arrow {
  color: var(--color-text-muted);
  margin: 0 var(--spacing-sm);
}

.fn-result {
  color: var(--color-text-muted);
  font-style: italic;
  min-width: 24px;
  text-align: center;
  transition: all 0.3s ease;
}

.fn-result.has-result {
  color: var(--color-success);
  font-style: normal;
  font-weight: 600;
}

.fn-result.result-flash {
  animation: resultFlash 0.6s ease;
}

.fn-result.is-cached {
  color: var(--color-warning);
  font-style: normal;
  font-weight: 600;
}

@keyframes resultFlash {
  0% {
    transform: scale(1);
  }

  30% {
    transform: scale(1.15);
  }

  100% {
    transform: scale(1);
  }
}

/* ===========================================
   PROBE BUTTON - Inside input wrapper
   =========================================== */
.probe-btn {
  width: 100%;
  margin-top: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-lg);
  background: var(--gradient-primary);
  color: var(--color-text-on-filled);
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px var(--color-accent-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.probe-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.probe-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px var(--color-accent-glow);
}

.probe-btn:active:not(:disabled) {
  transform: translateY(0);
}

.probe-btn.is-duplicate {
  background: var(--color-bg-hover);
  color: var(--color-warning);
  box-shadow: none;
  opacity: 1;
}

.duplicate-icon {
  font-size: var(--font-size-sm);
}

/* Visually hidden but accessible to screen readers */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--color-overlay-strong);
  border-top-color: var(--color-text-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.probe-count-badge {
  opacity: 0.85;
  font-weight: 500;
}

.probe-count-badge.status-explore {
  color: var(--color-text-primary);
}

.probe-count-badge.status-available {
  color: var(--color-text-primary);
}

.probe-count-badge.status-exhausted {
  color: var(--color-warning);
}

/* ===========================================
   PER-FIELD TYPE ERRORS
   =========================================== */
.probe-field-errors {
  list-style: none;
  margin: 0;
  padding: 0;
  color: var(--color-error);
  font-size: var(--font-size-xs);
  text-align: left;
}

.probe-field-errors:not(:empty) {
  margin-top: var(--spacing-xs);
}

.probe-error,
.probe-status-hint {
  margin: 0 var(--spacing-lg) var(--spacing-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.probe-error {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-error-overlay);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-sm);
  color: var(--color-error);
}

/* ===========================================
   MODAL
   =========================================== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-backdrop-heavy);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 480px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-float);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.modal-header h4 {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
}

.modal-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-hover);
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: var(--font-size-sm);
  transition: all 0.2s ease;
}

.modal-close:hover {
  background: var(--color-error);
  color: var(--color-text-on-filled);
}

.modal-body {
  padding: var(--spacing-md) var(--spacing-lg);
  overflow-y: auto;
  height: 300px;
  max-height: 50vh;
}

.modal-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-xs);
  background: var(--color-bg-hover);
  transition: background 0.15s ease;
}

.modal-row:hover {
  background: var(--color-bg-input);
}

.modal-index {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  min-width: 32px;
  opacity: 0.7;
}

.modal-call {
  color: var(--color-text-primary);
}

.modal-arrow {
  color: var(--color-text-muted);
}

.modal-result {
  color: var(--color-success);
  font-weight: 600;
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}
</style>
