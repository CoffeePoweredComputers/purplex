<template>
  <Teleport to="body">
    <transition name="modal-fade">
      <div
        v-if="isVisible"
        class="modal-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="correctness-modal-title"
        aria-describedby="correctness-modal-description"
        @click.self="closeModal"
      >
        <div
          ref="modalContentRef"
          class="modal-content correctness-modal"
          :style="modalStyle"
          @keydown.esc="closeModal"
        >
          <div class="modal-header">
            <div class="header-content">
              <h3
                id="correctness-modal-title"
                class="modal-title"
              >
                {{ $t('feedback.correctnessModal.title') }}
              </h3>
              <div class="header-badges">
                <span
                  class="badge-level"
                  :class="headerBadgeClass"
                >
                  {{ $t('feedback.correctnessModal.versionPass', { passing: passingVariants, total: totalVariants }) }}
                </span>
              </div>
            </div>
            <div class="modal-actions">
              <div class="size-controls-group" aria-hidden="true">
                <span class="size-label">{{ $t('feedback.correctnessModal.sizeLabel') }}</span>
                <div class="size-controls">
                  <button
                    v-for="size in sizePresets"
                    :key="size.name"
                    :class="['size-btn', { active: currentSize === size.name }]"
                    :title="`${size.label} view`"
                    tabindex="-1"
                    @click="setModalSize(size.name)"
                  >
                    {{ size.icon }}
                  </button>
                </div>
              </div>
              <button
                class="close-button"
                :title="$t('feedback.correctnessModal.closeEsc')"
                :aria-label="$t('feedback.correctnessModal.closeModal')"
                @click="closeModal"
              >
                &times;
              </button>
            </div>
          </div>

          <!-- Summary Section -->
          <div
            class="analysis-summary"
            :class="summaryClass"
          >
            <div
              class="summary-icon"
              aria-hidden="true"
            >
              {{ summaryIcon }}
            </div>
            <div class="summary-content">
              <p
                id="correctness-modal-description"
                class="summary-headline"
              >
                {{ summaryHeadline }}
              </p>
              <p class="summary-explanation">
                {{ summaryExplanation }}
              </p>
            </div>
          </div>

          <div class="modal-body">
            <!-- Version Selector Pills -->
            <div class="version-selector">
              <span id="version-selector-label" class="selector-label">{{ $t('feedback.correctnessModal.viewVersion') }}</span>
              <div
                class="version-pills"
                role="tablist"
                :aria-label="$t('feedback.correctnessModal.codeVersions')"
              >
                <button
                  v-for="(v, i) in variants"
                  :id="`version-tab-${i}`"
                  :key="i"
                  role="tab"
                  :aria-selected="localSelectedVersion === i"
                  :aria-controls="`version-panel-${i}`"
                  class="version-pill"
                  :class="{
                    active: localSelectedVersion === i,
                    passing: v.passing,
                    failing: !v.passing
                  }"
                  :tabindex="localSelectedVersion === i ? 0 : -1"
                  @click="selectVersion(i)"
                  @keydown.left="selectPreviousVersion"
                  @keydown.right="selectNextVersion"
                  @keydown.home="selectVersion(0)"
                  @keydown.end="selectVersion(variants.length - 1)"
                >
                  <span
                    class="pill-icon"
                    aria-hidden="true"
                  >{{ v.passing ? '✓' : '✗' }}</span>
                  <span class="pill-label">{{ i + 1 }}</span>
                  <span class="sr-only">{{ v.passing ? $t('feedback.correctnessModal.passing') : $t('feedback.correctnessModal.failing') }}</span>
                </button>
              </div>
            </div>

            <!-- Version Panel -->
            <div
              v-for="(v, i) in variants"
              v-show="localSelectedVersion === i"
              :id="`version-panel-${i}`"
              :key="`panel-${i}`"
              role="tabpanel"
              :aria-labelledby="`version-tab-${i}`"
              class="version-panel"
            >
              <!-- Two-column layout: Code + Tests -->
              <div class="version-details">
                <div class="details-code">
                  <div class="section-header">
                    <h4 class="section-title">{{ $t('feedback.correctnessModal.generatedCode') }}</h4>
                    <span
                      class="section-meta"
                      :class="{ passing: v.passing, failing: !v.passing }"
                    >
                      {{ v.passing ? $t('feedback.correctnessModal.allTestsPass') : $t('feedback.correctnessModal.failingCount', { count: v.testsTotal - v.testsPassed }) }}
                    </span>
                  </div>
                  <div class="code-wrapper">
                    <div class="code-block" inert>
                      <Editor
                        :value="v.code"
                        :read-only="true"
                        height="100%"
                        width="100%"
                        theme="tomorrow_night"
                        :show-gutter="true"
                      />
                    </div>
                    <pre
                      class="code-accessible"
                      tabindex="0"
                      role="group"
                      :aria-label="`Generated code for version ${i + 1}, read-only`"
                      v-text="v.code"
                    ></pre>
                  </div>
                </div>

                <div class="details-tests">
                  <div class="section-header">
                    <h4 class="section-title">{{ $t('feedback.correctnessModal.testResults') }}</h4>
                    <span class="section-meta">{{ v.testsPassed }}/{{ v.testsTotal }}</span>
                  </div>
                  <ul class="tests-list">
                    <li
                      v-for="(test, ti) in v.tests"
                      :key="`test-${ti}`"
                      tabindex="0"
                      class="test-item"
                      :class="{ passing: test.passed, failing: !test.passed }"
                      :aria-label="testAriaLabel(test)"
                    >
                      <div class="test-call-row">
                        <span
                          class="test-status"
                          :class="test.passed ? 'status-pass' : 'status-fail'"
                          aria-hidden="true"
                        >{{ test.passed ? '✓' : '✗' }}</span>
                        <code class="test-call">{{ test.call }}</code>
                      </div>
                      <div class="test-values-row">
                        <span class="test-value">
                          <span class="value-label">{{ $t('feedback.correctnessModal.expected') }}</span>
                          <code class="value-content">{{ test.expected }}</code>
                        </span>
                        <span class="test-value">
                          <span class="value-label">{{ $t('feedback.correctnessModal.got') }}</span>
                          <code
                            class="value-content"
                            :class="{ mismatch: !test.passed, 'is-error': test.error }"
                          >{{ test.error || (test.actual ?? test.expected) }}</code>
                        </span>
                      </div>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
          <!-- Live region for version switch announcements -->
          <div
            class="sr-only"
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            {{ versionAnnouncement }}
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, toRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Editor from '@/features/editor/Editor.vue'
import { useFocusTrap } from '@/composables/useFocusTrap'

type SizePreset = 'small' | 'medium' | 'large' | 'fullscreen'

interface Test {
  call: string
  expected: string
  actual?: string
  error?: string
  passed: boolean
}

interface Variant {
  code: string
  passing: boolean
  testsPassed: number
  testsTotal: number
  tests: Test[]
}

interface SizePresetConfig {
  name: SizePreset
  label: string
  icon: string
  width: string
  height: string
}

const props = defineProps<{
  isVisible: boolean
  variants: Variant[]
  selectedVersion?: number
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'update:selectedVersion', value: number): void
  (e: 'debug', variant: Variant): void
}>()

const { t } = useI18n()

// Focus trap composable
const { modalContentRef } = useFocusTrap(toRef(() => props.isVisible))

// State
const localSelectedVersion = ref(props.selectedVersion ?? 0)
const currentSize = ref<SizePreset>('medium')
const versionAnnouncement = ref('')

const sizePresets = computed<SizePresetConfig[]>(() => [
  { name: 'small', label: t('feedback.correctnessModal.sizePresets.small'), icon: '◻', width: '800px', height: 'auto' },
  { name: 'medium', label: t('feedback.correctnessModal.sizePresets.medium'), icon: '◼', width: '1000px', height: 'auto' },
  { name: 'large', label: t('feedback.correctnessModal.sizePresets.large'), icon: '⬛', width: '1200px', height: 'auto' },
  { name: 'fullscreen', label: t('feedback.correctnessModal.sizePresets.fullscreen'), icon: '⛶', width: '100%', height: '100vh' }
])

// Computed
const modalStyle = computed(() => {
  const preset = sizePresets.value.find(s => s.name === currentSize.value)
  if (!preset) {
    return {}
  }
  return {
    '--modal-width': preset.width,
    '--modal-height': preset.height,
    '--modal-max-width': preset.name === 'fullscreen' ? '100%' : preset.width,
    '--modal-max-height': preset.name === 'fullscreen' ? '100%' : preset.height,
  }
})

const totalVariants = computed(() => props.variants.length)

const passingVariants = computed(() => props.variants.filter(v => v.passing).length)

const headerBadgeClass = computed(() => {
  if (passingVariants.value === 0) {
    return 'badge-error'
  }
  if (passingVariants.value < totalVariants.value) {
    return 'badge-warning'
  }
  return 'badge-success'
})

const summaryClass = computed(() => {
  if (passingVariants.value === 0) {
    return 'summary-error'
  }
  if (passingVariants.value < totalVariants.value) {
    return 'summary-warning'
  }
  return 'summary-success'
})

const summaryIcon = computed(() => {
  if (passingVariants.value === 0) {
    return '❌'
  }
  if (passingVariants.value < totalVariants.value) {
    return '⚠️'
  }
  return '✅'
})

const summaryHeadline = computed(() => {
  if (passingVariants.value === 0) {
    return t('feedback.correctnessModal.summaryHeadlineNone')
  }
  if (passingVariants.value < totalVariants.value) {
    return t('feedback.correctnessModal.summaryHeadlinePartial')
  }
  return t('feedback.correctnessModal.summaryHeadlineAll')
})

const summaryExplanation = computed(() => {
  const params = { total: totalVariants.value, passing: passingVariants.value }
  if (passingVariants.value === 0) {
    return t('feedback.correctnessModal.summaryExplanationNone', params)
  }
  if (passingVariants.value < totalVariants.value) {
    return t('feedback.correctnessModal.summaryExplanationPartial', params)
  }
  return t('feedback.correctnessModal.summaryExplanationAll', params)
})

// Methods
function testAriaLabel(test: Test): string {
  const status = test.passed ? 'passed' : 'failed'
  const got = test.error || (test.actual ?? test.expected)
  return `${test.call}: expected ${test.expected}, got ${got}, ${status}`
}

function announceVersion(index: number): void {
  const v = props.variants[index]
  if (!v) return
  const status = v.passing ? 'passing' : 'failing'
  const msg = `Version ${index + 1} of ${props.variants.length}, ${status}, ${v.testsPassed} of ${v.testsTotal} tests passed`
  versionAnnouncement.value = ''
  nextTick(() => {
    versionAnnouncement.value = msg
  })
}

function closeModal(): void {
  emit('close')
}

function setModalSize(sizeName: SizePreset): void {
  currentSize.value = sizeName
  localStorage.setItem('correctness-modal-size', sizeName)
}

function selectVersion(index: number): void {
  localSelectedVersion.value = index
  emit('update:selectedVersion', index)
  announceVersion(index)
  nextTick(() => {
    const tab = document.getElementById(`version-tab-${index}`)
    tab?.focus()
  })
}

function selectPreviousVersion(): void {
  if (localSelectedVersion.value > 0) {
    selectVersion(localSelectedVersion.value - 1)
  }
}

function selectNextVersion(): void {
  if (localSelectedVersion.value < props.variants.length - 1) {
    selectVersion(localSelectedVersion.value + 1)
  }
}

function _handleDebug(variant: Variant): void {
  emit('debug', variant)
}

// Watchers
watch(() => props.selectedVersion, (newVal) => {
  if (newVal !== undefined) {
    localSelectedVersion.value = newVal
  }
})

// Lifecycle
onMounted(() => {
  const savedSize = localStorage.getItem('correctness-modal-size') as SizePreset | null
  if (savedSize && sizePresets.value.find(s => s.name === savedSize)) {
    currentSize.value = savedSize
  }
})
</script>

<style scoped>
/* Screen reader only utility */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Modal Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-content {
  transition: transform 0.3s ease;
}

.modal-fade-enter-from .modal-content {
  transform: scale(0.9);
}

/* Modal Structure - Matches SegmentAnalysisModal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.modal-overlay.fullscreen-overlay {
  padding: 0;
}

.modal-content {
  background-color: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: var(--modal-width, 1000px);
  height: var(--modal-height, auto);
  max-width: var(--modal-max-width, 90vw);
  max-height: var(--modal-max-height, 85vh);
  min-height: 400px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: var(--transition-base);
}

.modal-content:focus {
  outline: none;
}

.modal-content.fullscreen-mode {
  border-radius: 0;
  width: 100% !important;
  height: 100% !important;
  max-width: 100% !important;
  max-height: 100% !important;
}

/* Modal Header - Matches SegmentAnalysisModal exactly */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--color-bg-header);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 2px solid var(--color-bg-input);
}

.header-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.modal-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.header-badges {
  display: flex;
  gap: var(--spacing-sm);
}

.badge-level {
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.badge-level.badge-success {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.badge-level.badge-warning {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.badge-level.badge-error {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}

.modal-actions {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
}

.size-controls-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  transition: var(--transition-fast);
}

.size-controls-group:hover .size-label {
  opacity: 1;
  color: var(--color-text-secondary);
}

.size-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: 500;
  user-select: none;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.size-controls {
  display: flex;
  gap: var(--spacing-xs);
  background: var(--color-bg-dark);
  padding: var(--spacing-xs);
  border-radius: var(--radius-sm);
}

.size-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  width: 28px;
  height: 28px;
  border-radius: var(--radius-xs);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
  font-size: 14px;
  padding: 0;
}

.size-btn:hover {
  background: var(--color-bg-input);
  color: var(--color-text-secondary);
}

.size-btn.active {
  background: var(--color-primary);
  color: var(--color-text-primary);
}

.close-button {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: 24px;
  cursor: pointer;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
}

.close-button:hover {
  background: var(--color-error-bg);
  color: var(--color-error);
}

/* Analysis Summary - Amber warning banner */
.analysis-summary {
  display: flex;
  gap: var(--spacing-sm);
  align-items: flex-start;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-border);
}

.analysis-summary.summary-success {
  background: var(--color-success-overlay);
  border: 1px solid var(--color-success-border);
  border-bottom: 1px solid var(--color-success-border);
}

.analysis-summary.summary-warning {
  background: var(--color-warning-overlay);
  border: 1px solid var(--color-warning-border);
  border-bottom: 1px solid var(--color-warning-border);
}

.analysis-summary.summary-error {
  background: var(--color-error-overlay);
  border: 1px solid var(--color-error-border);
  border-bottom: 1px solid var(--color-error-border);
}

.summary-icon {
  font-size: var(--font-size-base);
  flex-shrink: 0;
}

.summary-content {
  flex: 1;
}

.summary-headline {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
  line-height: 1.5;
}

.summary-explanation {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

/* Modal Body */
.modal-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: var(--spacing-lg);
}

/* Version Selector Pills - Fixed vertical centering */
.version-selector {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding-bottom: 24px;
  margin-bottom: 0;
}

.selector-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  line-height: 1;
}

.version-pills {
  display: flex;
  gap: var(--spacing-xs);
  align-items: center;
}

.version-pill {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-input);
  border: 2px solid transparent;
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-fast);
  font-family: inherit;
  font-size: var(--font-size-sm);
  line-height: 1;
}

.version-pill .pill-icon {
  font-size: var(--font-size-xs);
}

.version-pill .pill-label {
  font-weight: 600;
  color: var(--color-text-secondary);
}

.version-pill.passing .pill-icon {
  color: var(--color-success);
}

.version-pill.failing .pill-icon {
  color: var(--color-error);
}

.version-pill:hover {
  background: var(--color-bg-hover);
}

.version-pill:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.version-pill.active {
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-hover);
}

.version-pill.active.passing {
  border-color: var(--color-success);
}

.version-pill.active.failing {
  border-color: var(--color-error);
}

/* Version Panel */
.version-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* Two-column layout - Equal heights */
.version-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-lg);
  flex: 1;
  min-height: 300px;
}

.details-code,
.details-tests {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  min-height: 0;
}

.code-wrapper {
  position: relative;
  flex: 1;
  min-height: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-bg-input);
  flex-shrink: 0;
}

h4.section-title {
  margin: 0;
}

.section-title {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-meta {
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.section-meta.passing {
  color: var(--color-success);
}

.section-meta.failing {
  color: var(--color-error);
}

/* Accessible code overlay - transparent over the Ace editor, visible focus ring */
.code-accessible {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  margin: 0;
  padding: var(--spacing-sm);
  color: transparent;
  background: transparent;
  overflow: auto;
  z-index: 1;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--font-size-sm);
  white-space: pre-wrap;
  word-wrap: break-word;
  border: 2px solid transparent;
  border-radius: var(--radius-base);
  cursor: default;
}

.code-accessible:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: -2px;
}

/* Code Block - Container for Ace Editor */
.code-block {
  border-radius: var(--radius-base);
  overflow: hidden;
  height: 100%;
}

/* Tests List - Row-based layout for better readability */
ul.tests-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.tests-list {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
}

.test-item {
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: 1px solid var(--color-bg-border);
}

.test-item:last-child {
  border-bottom: none;
}

.test-item:hover {
  background: var(--color-bg-hover);
}

.test-item:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: -2px;
  background: var(--color-bg-hover);
}

.test-call-row {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.test-status {
  flex-shrink: 0;
  font-size: var(--font-size-sm);
  line-height: 1.4;
}

.status-pass {
  color: var(--color-success);
}

.status-fail {
  color: var(--color-error);
}

.test-call {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--font-size-xs);
  color: var(--color-text-primary);
  word-break: break-word;
  line-height: 1.4;
  background: var(--color-bg-dark);
  padding: 2px 8px;
  border-radius: var(--radius-xs);
}

.test-values-row {
  display: flex;
  gap: var(--spacing-lg);
  padding-left: 20px;
}

.test-value {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.value-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-text-muted);
}

.value-content {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  background: var(--color-bg-dark);
  padding: 2px 8px;
  border-radius: var(--radius-xs);
}

.value-content.mismatch {
  color: var(--color-error);
  background: var(--color-error-overlay);
}

.value-content.is-error {
  font-style: italic;
}

/* Responsive */
@media (max-width: 1024px) {
  .modal-overlay {
    padding: var(--spacing-md);
  }

  .modal-content {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
  }

  .size-controls-group {
    display: none;
  }
}

@media (max-width: 768px) {
  .modal-overlay {
    padding: 0;
  }

  .modal-content {
    border-radius: 0;
  }

  .modal-header {
    padding: var(--spacing-sm) var(--spacing-md);
    flex-wrap: wrap;
    gap: var(--spacing-sm);
  }

  .header-content {
    flex: 1;
    min-width: 0;
  }

  .header-badges {
    flex-wrap: wrap;
  }

  .modal-actions {
    gap: var(--spacing-sm);
  }

  .version-details {
    grid-template-columns: 1fr;
  }

  .version-selector {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
