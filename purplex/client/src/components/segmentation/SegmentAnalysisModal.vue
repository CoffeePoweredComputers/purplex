<template>
  <Teleport to="body">
    <transition name="modal-fade">
      <div
        v-if="isVisible"
        class="modal-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="segment-modal-title"
        aria-describedby="segment-modal-description"
        @click.self="closeModal"
      >
        <div
          ref="modalContentRef"
          class="modal-content"
          :style="modalStyle"
          @keydown.esc="closeModal"
        >
          <div class="modal-header">
            <div class="header-content">
              <h3
                id="segment-modal-title"
                class="modal-title"
              >
                {{ $t('feedback.segmentModal.title') }}
              </h3>
              <div class="header-badges">
                <span
                  class="badge-level"
                  :class="levelBadgeClass"
                >
                  {{ $t('feedback.segmentModal.levelUnderstanding', { level: formatLevel(segmentation.comprehension_level) }) }}
                </span>
              </div>
            </div>
            <div class="modal-actions">
              <div class="size-controls-group">
                <span class="size-label">{{ $t('feedback.segmentModal.sizeLabel') }}</span>
                <div class="size-controls" role="group" aria-label="Modal size">
                  <button
                    v-for="size in sizePresets"
                    :key="size.name"
                    :class="['size-btn', { active: currentSize === size.name }]"
                    :title="`${size.label} view`"
                    :aria-label="`Set ${size.label.toLowerCase()} window size`"
                    :aria-pressed="currentSize === size.name"
                    @click="setModalSize(size.name)"
                  >
                    <span aria-hidden="true">{{ size.icon }}</span>
                  </button>
                </div>
              </div>
              <button
                class="action-button"
                :title="$t('feedback.segmentModal.openInNewTab')"
                :aria-label="$t('feedback.segmentModal.openInNewTabAriaLabel')"
                @click="openInNewTab"
              >
                <span class="icon" aria-hidden="true">⬈</span>
              </button>
              <button
                ref="closeButtonRef"
                class="close-button"
                :title="$t('feedback.segmentModal.closeEsc')"
                :aria-label="$t('feedback.segmentModal.closeModal')"
                @click="closeModal"
              >
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          </div>

          <div class="modal-body">
            <div class="analysis-header">
              <div class="feedback-content">
                <span class="feedback-icon" aria-hidden="true">{{ getFeedbackIcon() }}</span>
                <div class="feedback-text">
                  <p id="segment-modal-description" class="feedback-message">
                    <template v-if="segmentation.comprehension_level === 'relational'">
                      <i18n-t keypath="feedback.segmentModal.relationalFeedback" tag="span">
                        <template #count>
                          <span class="segment-badge segment-badge-success">{{ segmentation.segment_count }}</span>
                        </template>
                      </i18n-t>
                    </template>
                    <template v-else-if="segmentation.comprehension_level === 'multi_structural'">
                      <i18n-t keypath="feedback.segmentModal.multiStructuralFeedback" tag="span">
                        <template #count>
                          <span class="segment-badge segment-badge-warning">{{ segmentation.segment_count }}</span>
                        </template>
                        <template #goal>
                          <span class="segment-badge segment-badge-goal">{{ segmentThreshold }}</span>
                        </template>
                      </i18n-t>
                    </template>
                    <template v-else>
                      {{ segmentation.feedback }}
                    </template>
                  </p>
                  <p class="feedback-explanation">
                    {{ getExplanation() }}
                  </p>
                </div>
              </div>
            </div>

            <div class="analysis-content">
              <SegmentMapping
                :segments="segmentation.segments"
                :reference-code="referenceCode"
                :user-prompt="segmentation.user_prompt || userPrompt || ''"
                class="segment-mapping-modal"
              />
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import SegmentMapping from './SegmentMapping.vue'
import { useFocusTrap } from '@/composables/useFocusTrap'

type ComprehensionLevel = 'relational' | 'multi_structural'
type SizePreset = 'small' | 'medium' | 'large' | 'fullscreen'

interface Segment {
  id: number
  text: string
  code_lines: number[]
}

interface Segmentation {
  segments: Segment[]
  segment_count: number
  comprehension_level: ComprehensionLevel
  feedback: string
  user_prompt?: string
  threshold?: number
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
  segmentation: Segmentation
  referenceCode: string
  userPrompt?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const { t } = useI18n()

// Focus trap composable — focus the close button on open (Fix 6, WCAG 2.4.3)
const closeButtonRef = ref<HTMLElement | null>(null)
const { modalContentRef } = useFocusTrap(toRef(() => props.isVisible), closeButtonRef)

// Size state
const currentSize = ref<SizePreset>('medium')
const sizePresets = computed<SizePresetConfig[]>(() => [
  { name: 'small', label: t('feedback.segmentModal.sizePresets.small'), icon: '◻', width: '800px', height: 'auto' },
  { name: 'medium', label: t('feedback.segmentModal.sizePresets.medium'), icon: '◼', width: '1000px', height: 'auto' },
  { name: 'large', label: t('feedback.segmentModal.sizePresets.large'), icon: '⬛', width: '1200px', height: 'auto' },
  { name: 'fullscreen', label: t('feedback.segmentModal.sizePresets.fullscreen'), icon: '⛶', width: '100%', height: '100vh' }
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

const levelBadgeClass = computed(() => {
  return `badge-${props.segmentation.comprehension_level.replace('_', '-')}`
})

const segmentThreshold = computed(() => {
  return props.segmentation.threshold ?? 2
})

// Methods
function closeModal(): void {
  emit('close')
}

function setModalSize(sizeName: SizePreset): void {
  currentSize.value = sizeName
  localStorage.setItem('segment-analysis-modal-size', sizeName)

  // Handle fullscreen mode classes
  const modalContent = modalContentRef.value
  const modalOverlay = document.querySelector('.modal-overlay') as HTMLElement

  if (sizeName === 'fullscreen') {
    modalContent?.classList.add('fullscreen-mode')
    modalOverlay?.classList.add('fullscreen-overlay')
  } else {
    modalContent?.classList.remove('fullscreen-mode')
    modalOverlay?.classList.remove('fullscreen-overlay')
  }
}

function openInNewTab(): void {
  const newWindow = window.open('', '_blank', 'width=1200,height=800')
  if (newWindow) {
    newWindow.document.write(`
      <html>
        <head>
          <title>Understanding Analysis - ${formatLevel(props.segmentation.comprehension_level)}</title>
          <style>
            body { font-family: Inter, system-ui, sans-serif; margin: 20px; }
            .header { margin-bottom: 20px; }
            .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 8px; }
            .segments { margin: 20px 0; }
            .segment { margin: 10px 0; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
            .code { font-family: Monaco, monospace; background: #f5f5f5; padding: 10px; border-radius: 4px; }
          </style>
        </head>
        <body>
          <div class="header">
            <h1>Understanding Analysis</h1>
            <span class="badge">${formatLevel(props.segmentation.comprehension_level)} Understanding</span>
            <p><strong>Feedback:</strong> ${props.segmentation.feedback}</p>
            <p><strong>Explanation:</strong> ${getExplanation()}</p>
          </div>
          <div class="segments">
            <h2>Segments</h2>
            ${props.segmentation.segments.map(segment => `
              <div class="segment">
                <strong>Segment ${segment.id}:</strong> ${segment.text}
                <br><small>Lines: ${segment.code_lines.join(', ')}</small>
              </div>
            `).join('')}
          </div>
          <div class="code">
            <h2>Reference Code</h2>
            <pre>${props.referenceCode}</pre>
          </div>
        </body>
      </html>
    `)
  }
  closeModal()
}

function getFeedbackIcon(): string {
  switch (props.segmentation.comprehension_level) {
    case 'relational':
      return '🎯'
    case 'multi_structural':
      return '🔍'
    default:
      return '📝'
  }
}

function formatLevel(level: ComprehensionLevel): string {
  switch (level) {
    case 'relational':
      return t('feedback.segmentModal.levelExcellent')
    case 'multi_structural':
      return t('feedback.segmentModal.levelDetailed')
    default:
      return t('feedback.segmentModal.levelUnknown')
  }
}

function getExplanation(): string {
  switch (props.segmentation.comprehension_level) {
    case 'relational':
      return t('feedback.segmentModal.explanationRelational')
    case 'multi_structural':
      return t('feedback.segmentModal.explanationMultiStructural')
    default:
      return ''
  }
}

// Load saved size preference on mount
onMounted(() => {
  const savedSize = localStorage.getItem('segment-analysis-modal-size') as SizePreset | null
  if (savedSize && sizePresets.value.find(s => s.name === savedSize)) {
    currentSize.value = savedSize
  }
})
</script>

<style scoped>
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

/* Modal Structure */
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

.modal-content.fullscreen-mode {
  border-radius: 0;
  width: 100% !important;
  height: 100% !important;
  max-width: 100% !important;
  max-height: 100% !important;
}

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

.badge-count,
.badge-level {
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.badge-count {
  background: #404040;
  color: #b0b0b0;
}


.badge-level.badge-relational {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.badge-level.badge-multi-structural {
  background: #6b2d2d;
  color: #ffc5c5;
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
  color: #b0b0b0;
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
  color: #b0b0b0;
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

.action-button {
  background: var(--color-bg-input);
  border: none;
  color: var(--color-text-secondary);
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
}

.action-button:hover {
  background: var(--color-primary);
  color: var(--color-text-primary);
  transform: translateY(-1px);
}

.icon {
  font-size: 18px;
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

.modal-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.analysis-header {
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-bg-border);
}

.feedback-content {
  display: flex;
  gap: var(--spacing-sm);
  align-items: flex-start;
}

.feedback-icon {
  font-size: var(--font-size-base);
  flex-shrink: 0;
}

.feedback-text {
  flex: 1;
}

.feedback-message {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
  line-height: 1.5;
}

/* Segment count badge - wraps entire phrase */
.segment-badge {
  display: inline-block;
  padding: 4px 12px;
  font-size: 15px;
  font-weight: 700;
  border-radius: 8px;
  margin: 0 4px;
  white-space: nowrap;
  vertical-align: baseline;
}

.segment-badge-success {
  background: #1e6f3f;
  color: #ffffff;
  box-shadow: none;
}

.segment-badge-warning {
  background: #9a4419;
  color: #ffffff;
  box-shadow: none;
}

.segment-badge-goal {
  background: #5a3a9d;
  color: #ffffff;
  box-shadow: none;
}

.feedback-explanation {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

.analysis-content {
  flex: 1;
  overflow: hidden;
}

.segment-mapping-modal {
  height: 100%;
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
    display: none; /* Hide size controls on tablet */
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

  .analysis-header {
    padding: var(--spacing-md);
  }
}
</style>
