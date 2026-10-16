<template>
  <div class="abstraction-card">
    <button
      class="metric-card"
      :class="[abstractionClass, { 'expanded': showModal && !locked }]"
      :aria-expanded="showModal"
      :aria-disabled="locked"
      :aria-haspopup="locked ? undefined : 'dialog'"
      @click="handleClick"
      @keydown.enter="handleClick"
      @keydown.space.prevent="handleClick"
    >
      <div class="card-content">
        <div
          id="abstraction-label"
          class="card-label"
        >
          {{ $t('feedback.abstraction.label') }}
        </div>

        <div
          class="progress-bar-container"
          role="progressbar"
          :aria-valuenow="abstractionFill"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="locked ? ($t('feedback.abstraction.label') + ': ' + $t('feedback.abstraction.status.locked')) : ($t('feedback.abstraction.label') + ': ' + $t('feedback.abstraction.segments', { count: segmentCount }))"
        >
          <div
            class="progress-bar-fill"
            :style="{ width: abstractionFill + '%' }"
            :class="abstractionBarClass"
          />
        </div>

        <div class="card-status">
          <span
            class="status-icon"
            aria-hidden="true"
          >{{ abstractionStatus.icon }}</span>
          <span class="status-label">{{ abstractionStatus.label }}</span>
          <span
            v-if="!locked"
            class="status-metric"
          >
            {{ $t('feedback.abstraction.segments', { count: segmentCount }) }}
            <span
              v-if="segmentCount > segmentThreshold"
              class="metric-hint"
            >{{ $t('feedback.abstraction.segmentThreshold', { threshold: segmentThreshold }) }}</span>
          </span>
        </div>
        <div class="card-description">
          {{ abstractionStatus.description }}
        </div>
      </div>
      <div
        v-if="!locked"
        class="card-action"
        :class="abstractionClass"
        :title="$t('feedback.nextStep.viewAnalysis')"
      >
        <span class="action-icon">→</span>
      </div>
    </button>

    <!-- Live region for announcements -->
    <div
      class="sr-only"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {{ announcement }}
    </div>

    <SegmentAnalysisModal
      v-if="segmentation"
      :is-visible="showModal"
      :segmentation="segmentation as never"
      :reference-code="referenceCode"
      :user-prompt="userPrompt"
      @close="showModal = false"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * AbstractionCard - the "Abstraction" metric card and its segment analysis.
 *
 * Shows how many segments the student's explanation maps to (fewer = more
 * abstract) and opens the SegmentAnalysisModal. Locked until the code built
 * from the explanation passes every test.
 *
 * Used by Feedback.vue (EiPL/Prompt: locked unless all versions pass) and by
 * ProbeableFeedback.vue for probeable_spec (locked unless the single version
 * passes).
 */
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import SegmentAnalysisModal from '@/components/segmentation/SegmentAnalysisModal.vue'
import type { SegmentationData } from '../types'

interface Props {
  /** Segmentation analysis of the explanation */
  segmentation?: SegmentationData | null
  /** Locked: the card is inert and the analysis stays hidden */
  locked?: boolean
  /** Reference solution, shown alongside the segments */
  referenceCode?: string
  /** The student's explanation */
  userPrompt?: string
}

const props = withDefaults(defineProps<Props>(), {
  segmentation: null,
  locked: false,
  referenceCode: '',
  userPrompt: '',
})

const { t } = useI18n()

const showModal = ref(false)
const announcement = ref('')

const segmentCount = computed(() => props.segmentation?.segment_count ?? 0)
const segmentThreshold = computed(() => props.segmentation?.threshold ?? 2)
const isHighLevel = computed(() => segmentCount.value <= segmentThreshold.value)

const abstractionFill = computed(() => {
  if (props.locked) {return 0}
  if (isHighLevel.value) {return 100}
  return Math.max(0, 100 - (segmentCount.value - segmentThreshold.value) * 20)
})

const abstractionStatus = computed(() => {
  if (props.locked) {
    return { icon: '🔒', label: t('feedback.abstraction.status.locked'), description: t('feedback.abstraction.status.lockedDesc') }
  }
  if (isHighLevel.value) {
    return { icon: '✓', label: t('feedback.abstraction.status.highLevel'), description: t('feedback.abstraction.status.highLevelDesc') }
  }
  return { icon: '✗', label: t('feedback.abstraction.status.tooDetailed'), description: t('feedback.abstraction.status.tooDetailedDesc') }
})

const abstractionClass = computed(() => {
  if (props.locked) {return 'status-locked'}
  return isHighLevel.value ? 'status-success' : 'status-error'
})

const abstractionBarClass = computed(() => {
  if (props.locked) {return 'bar-locked'}
  return isHighLevel.value ? 'bar-success' : 'bar-error'
})

function announce(message: string): void {
  announcement.value = ''
  nextTick(() => {
    announcement.value = message
  })
}

/** Open the segment analysis (no-op while locked). */
function open(): void {
  if (props.locked) {return}
  showModal.value = true
}

function handleClick(): void {
  if (props.locked) {
    announce(t('feedback.announcement.abstractionLocked'))
    return
  }
  open()
  announce(t('feedback.announcement.abstractionOpened'))
}

defineExpose({ open })
</script>

<style scoped>
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

.metric-card {
  display: flex;
  align-items: stretch;
  width: calc(100% - calc(var(--spacing-lg) * 2));
  margin: var(--spacing-md) var(--spacing-lg);
  padding: 0;
  background: var(--color-bg-section);
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: var(--transition-fast);
  border: none;
  border-left: 4px solid transparent;
  text-align: left;
  font-family: inherit;
  overflow: hidden;
}

.card-content {
  flex: 1;
  padding: var(--spacing-sm) var(--spacing-md);
  min-width: 0;
}

.metric-card:hover {
  background: var(--color-bg-input);
}

.metric-card:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.metric-card.status-error {
  border-left-color: var(--color-error);
}

.metric-card.status-success {
  border-left-color: var(--color-success);
}

.metric-card.status-locked {
  border-left-color: var(--color-bg-disabled);
  opacity: 0.6;
  cursor: not-allowed;
}

.metric-card.status-locked:hover {
  background: var(--color-bg-section);
}

.card-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  letter-spacing: 0.5px;
  margin-bottom: var(--spacing-md);
}

.progress-bar-container {
  height: 8px;
  background: var(--color-bg-dark);
  border-radius: var(--radius-xs);
  overflow: hidden;
  margin-bottom: var(--spacing-md);
}

.progress-bar-fill {
  height: 100%;
  border-radius: var(--radius-xs);
  transition: width 0.4s ease;
}

.progress-bar-fill.bar-error {
  background: linear-gradient(90deg, var(--color-error), var(--color-error-dark));
}

.progress-bar-fill.bar-success {
  background: linear-gradient(90deg, var(--color-success), var(--color-success-dark));
}

.progress-bar-fill.bar-locked {
  background: var(--color-bg-border);
}

.card-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.status-icon {
  font-size: var(--font-size-base);
}

.status-label {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.status-metric {
  margin-left: auto;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.metric-hint {
  color: var(--color-text-muted);
  opacity: 0.7;
}

.card-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.card-action {
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  align-self: stretch;
  border-left: 1px solid var(--color-overlay-medium);
  transition: all 0.2s ease;
  flex-shrink: 0;
  margin: 0;
}

.card-action.status-success {
  background: var(--color-success-overlay);
  border-left-color: var(--color-success-border);
}

.card-action.status-error {
  background: var(--color-error-overlay);
  border-left-color: var(--color-error-border);
}

.action-icon {
  font-size: 18px;
  font-weight: 600;
  transition: transform 0.2s ease;
}

.card-action.status-success .action-icon {
  color: var(--color-success);
}

.card-action.status-error .action-icon {
  color: var(--color-error);
}

.metric-card:hover .card-action .action-icon {
  transform: translateX(3px);
}
</style>
