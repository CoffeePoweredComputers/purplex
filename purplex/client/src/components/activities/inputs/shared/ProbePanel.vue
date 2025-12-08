<template>
  <div class="probe-panel">
    <!-- Probe Input Box with integrated button -->
    <div class="probe-input-wrapper">
      <div class="probe-call">
        <span class="fn-name">{{ functionName }}</span>
        <span class="fn-paren">(</span>
        <template
          v-for="(param, i) in probeParams"
          :key="param.name"
        >
          <span
            v-if="i > 0"
            class="fn-comma"
          >, </span>
          <span class="param-name">{{ param.name }}</span>
          <span class="param-eq">=</span>
          <input
            :id="`probe-${param.name}`"
            :value="probeInputs[param.name]"
            type="text"
            class="param-input"
            :placeholder="param.type"
            :aria-label="`Enter value for ${param.name} (type: ${param.type})`"
            :disabled="!canProbe || isExecuting"
            @input="$emit('update-input', param.name, ($event.target as HTMLInputElement).value)"
            @keydown.enter="!isExecuting && canProbe && hasValidInputs && $emit('execute-probe')"
          >
        </template>
        <span class="fn-paren">)</span>
        <span class="fn-arrow">→</span>
        <span
          class="fn-result"
          :class="{ 'has-result': lastResult !== null, 'result-flash': showResultFlash }"
        >
          {{ lastResult !== null ? formatOutput(lastResult) : '?' }}
        </span>
      </div>

      <!-- Probe Button (inside wrapper) -->
      <button
        class="probe-btn"
        :disabled="!canProbe || isExecuting || !hasValidInputs"
        :aria-busy="isExecuting"
        :title="probeCountTooltip"
        @click="$emit('execute-probe')"
      >
        <template v-if="isExecuting">
          <span class="spinner" />
          <span>Probing</span>
        </template>
        <template v-else>
          <span>Probe</span>
          <span
            v-if="probeCountDisplay"
            class="probe-count-badge"
            :class="probeStatusClass"
          >· {{ probeCountDisplay }}</span>
        </template>
      </button>
    </div>

    <!-- Probe Error -->
    <div
      v-if="probeError"
      class="probe-error"
    >
      {{ probeError }}
    </div>

    <!-- History Section -->
    <div
      v-if="probeHistory.length > 0"
      class="history-section"
    >
      <div class="history-header">
        <span class="history-label">HISTORY</span>
        <button
          v-if="probeHistory.length > 5"
          class="view-all-btn"
          @click="showModal = true"
        >
          View all ({{ probeHistory.length }})
        </button>
      </div>
      <div
        class="history-list"
        aria-live="polite"
      >
        <div
          v-for="(entry, idx) in recentHistory"
          :key="idx"
          class="history-item"
        >
          <span class="history-index">#{{ probeHistory.length - idx }}</span>
          <span class="history-call">{{ formatFunctionCall(entry.input) }}</span>
          <span class="history-arrow">→</span>
          <span class="history-result">{{ formatOutput(entry.output) }}</span>
        </div>
      </div>
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
          class="modal-content"
          role="dialog"
          aria-modal="true"
          aria-labelledby="history-modal-title"
          @click.stop
        >
          <div class="modal-header">
            <h4 id="history-modal-title">
              Probe History
            </h4>
            <button
              class="modal-close"
              aria-label="Close"
              @click="showModal = false"
            >
              ✕
            </button>
          </div>
          <div class="modal-body">
            <div
              v-for="(entry, idx) in probeHistory"
              :key="idx"
              class="modal-row"
            >
              <span class="modal-index">#{{ probeHistory.length - idx }}</span>
              <span class="modal-call">{{ formatFunctionCall(entry.input) }}</span>
              <span class="modal-arrow">→</span>
              <span class="modal-result">{{ formatOutput(entry.output) }}</span>
            </div>
            <div
              v-if="probeHistory.length === 0"
              class="empty-state"
            >
              No probes yet. Enter values and click Probe to discover function behavior.
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ProbeHistoryEntry, ProbeParameter } from '../../types'

interface Props {
  functionName: string
  probeStatusClass: string
  probeCountDisplay: string
  probeParams: ProbeParameter[]
  probeInputs: Record<string, string>
  canProbe: boolean
  isExecuting: boolean
  hasValidInputs: boolean
  probeHistory: ProbeHistoryEntry[]
  probeError: string | null
  formatFunctionCall: (input: Record<string, unknown>) => string
  formatOutput: (output: unknown) => string
}

const props = defineProps<Props>()

defineEmits<{
  (e: 'execute-probe'): void
  (e: 'update-input', paramName: string, value: string): void
}>()

const showModal = ref(false)
const showResultFlash = ref(false)

// Show only 5 most recent history entries
const recentHistory = computed(() => {
  return props.probeHistory.slice(0, 5)
})

// Get the last result to display inline
const lastResult = computed(() => {
  if (props.probeHistory.length === 0) {
    return null
  }
  return props.probeHistory[0].output
})

// Tooltip text for probe count
const probeCountTooltip = computed(() => {
  if (props.probeStatusClass === 'status-explore') {
    return 'Unlimited probes available'
  }
  if (props.probeStatusClass === 'status-exhausted') {
    return 'No probes remaining'
  }
  return 'Probes remaining'
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
  /* No extra styling - inherits from parent */
}

/* ===========================================
   PROBE INPUT WRAPPER - Matches code editor wrapper
   =========================================== */
.probe-input-wrapper {
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  margin: var(--spacing-md) var(--spacing-xl);
  padding: var(--spacing-md) var(--spacing-lg);
  transition: border-color 0.2s ease;
}

.probe-input-wrapper:focus-within {
  border-color: var(--color-primary-gradient-start);
}

.probe-call {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  flex-wrap: wrap;
}

.fn-name {
  color: var(--color-info);
  font-weight: 600;
}

.fn-paren,
.fn-comma {
  color: var(--color-text-muted);
}

.param-name {
  color: var(--color-text-secondary);
}

.param-eq {
  color: var(--color-text-muted);
  margin: 0 2px;
}

.param-input {
  width: 72px;
  height: 28px;
  padding: 0 var(--spacing-sm);
  background: var(--color-bg-primary);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  text-align: center;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.param-input::placeholder {
  color: var(--color-text-muted);
  opacity: 0.5;
  font-size: var(--font-size-xs);
}

.param-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.param-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.probe-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.probe-btn:active:not(:disabled) {
  transform: translateY(0);
}

.probe-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
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
  color: rgba(255, 255, 255, 0.9);
}

.probe-count-badge.status-available {
  color: rgba(255, 255, 255, 0.9);
}

.probe-count-badge.status-exhausted {
  color: var(--color-warning);
}

/* ===========================================
   ERROR MESSAGE
   =========================================== */
.probe-error {
  margin: 0 var(--spacing-xl) var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-sm);
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

/* ===========================================
   HISTORY SECTION
   =========================================== */
.history-section {
  margin: var(--spacing-lg) var(--spacing-xl) 0;
  padding: var(--spacing-md);
  background: var(--color-bg-primary);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.history-label {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  letter-spacing: 0.08em;
}

.view-all-btn {
  font-size: var(--font-size-xs);
  color: var(--color-info);
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  transition: background 0.2s ease;
}

.view-all-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-primary);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) 0;
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
}

.history-index {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  min-width: 28px;
  opacity: 0.6;
}

.history-call {
  color: var(--color-text-primary);
}

.history-arrow {
  color: var(--color-text-muted);
}

.history-result {
  color: var(--color-success);
  font-weight: 600;
}

/* ===========================================
   MODAL
   =========================================== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 480px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-border);
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
  color: white;
}

.modal-body {
  padding: var(--spacing-md) var(--spacing-lg);
  overflow-y: auto;
  flex: 1;
}

.modal-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
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
