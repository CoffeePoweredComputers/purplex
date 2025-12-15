<template>
  <div class="form-section rounded-lg border-default">
    <h3>Probe Settings</h3>
    <p class="section-description">
      {{ sectionDescription }}
    </p>

    <!-- Show Function Signature Toggle - Compact -->
    <div class="toggle-setting-compact">
      <label class="toggle-label-compact">
        <input
          :checked="config.showFunctionSignature.value"
          type="checkbox"
          class="toggle-checkbox"
          @change="config.setShowFunctionSignature(($event.target as HTMLInputElement).checked)"
        >
        <span class="toggle-text">Show Function Signature</span>
        <span class="toggle-hint">
          {{ config.showFunctionSignature.value ? 'Students see types' : 'Types hidden' }}
        </span>
      </label>
    </div>

    <!-- Probe Mode Selection - Segmented Control -->
    <div class="probe-mode-section">
      <div class="probe-mode-header">
        <span class="probe-mode-label">Probe Mode</span>
      </div>

      <div class="segmented-control">
        <button
          v-for="(mode, index) in probeModes"
          :key="mode.value"
          :class="[
            'segment',
            { 'selected': config.probeMode.value === mode.value },
            { 'first': index === 0 },
            { 'last': index === probeModes.length - 1 }
          ]"
          type="button"
          @click="config.setProbeMode(mode.value)"
        >
          {{ mode.label.replace(' Mode', '') }}
        </button>
      </div>

      <p class="mode-description-text">
        {{ selectedModeDescription }}
      </p>
    </div>

    <!-- Probe Limits - Horizontal Row -->
    <div
      v-if="config.showMaxProbesField.value"
      class="probe-limits-section"
    >
      <div class="probe-limits-header">
        <span class="probe-limits-label">Probe Limits</span>
      </div>

      <div class="limits-row">
        <div class="limit-field">
          <label for="max_probes">Budget</label>
          <input
            id="max_probes"
            :value="config.maxProbes.value"
            type="number"
            min="1"
            max="100"
            required
            @input="config.setMaxProbes(parseInt(($event.target as HTMLInputElement).value) || 10)"
          >
        </div>

        <template v-if="config.showCooldownFields.value">
          <div class="limit-field">
            <label for="cooldown_attempts">Submissions to refill</label>
            <input
              id="cooldown_attempts"
              :value="config.cooldownAttempts.value"
              type="number"
              min="1"
              max="10"
              required
              @input="config.setCooldownAttempts(parseInt(($event.target as HTMLInputElement).value) || 3)"
            >
          </div>

          <div class="limit-field">
            <label for="cooldown_refill">Probes per refill</label>
            <input
              id="cooldown_refill"
              :value="config.cooldownRefill.value"
              type="number"
              min="1"
              max="20"
              required
              @input="config.setCooldownRefill(parseInt(($event.target as HTMLInputElement).value) || 5)"
            >
          </div>
        </template>
      </div>
    </div>

    <!-- Validation Warning -->
    <div
      v-if="config.validationError.value"
      class="validation-warning"
    >
      <span class="warning-icon">!</span>
      {{ config.validationError.value }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ProbeMode, UseProbeConfigReturn } from '@/composables/admin/useProbeConfig';

interface Props {
  /** Probe configuration composable */
  config: UseProbeConfigReturn;
  /** Probe modes with descriptions */
  probeModes: { value: ProbeMode; label: string; description: string }[];
  /** Custom section description (optional) */
  sectionDescription?: string;
  /** Custom cooldown attempts hint (optional) */
  cooldownAttemptsHint?: string;
}

const props = withDefaults(defineProps<Props>(), {
  sectionDescription: 'Configure how students can query the oracle function to discover its behavior.',
  cooldownAttemptsHint: 'Number of submissions required before probes are refilled',
});

// Get description for currently selected mode
const selectedModeDescription = computed(() => {
  const selected = props.probeModes.find(m => m.value === props.config.probeMode.value);
  return selected?.description || '';
});
</script>

<style scoped>
/* Common Utilities */
.rounded-lg {
  border-radius: var(--radius-lg);
}

.border-default {
  border: 2px solid var(--color-bg-border);
}

/* Form Section */
.form-section {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-base);
}

.form-section h3 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-border);
}

.section-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-lg);
}

/* Compact Toggle Setting */
.toggle-setting-compact {
  margin-bottom: var(--spacing-lg);
}

.toggle-label-compact {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}

.toggle-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  flex-shrink: 0;
}

.toggle-text {
  font-weight: 500;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.toggle-hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  padding-left: var(--spacing-sm);
  border-left: 1px solid var(--color-bg-border);
}

/* Probe Mode Section */
.probe-mode-section {
  margin-bottom: var(--spacing-lg);
}

.probe-mode-header {
  margin-bottom: var(--spacing-sm);
}

.probe-mode-label {
  font-weight: 500;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

/* Segmented Control */
.segmented-control {
  display: flex;
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: 2px;
  gap: 2px;
}

.segment {
  flex: 1;
  padding: var(--spacing-sm) var(--spacing-md);
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  border-radius: calc(var(--radius-base) - 4px);
}

.segment:hover:not(.selected) {
  background: var(--color-bg-panel);
  color: var(--color-text-primary);
}

.segment.selected {
  background: var(--color-primary-gradient-start);
  color: white;
}

.mode-description-text {
  margin: var(--spacing-sm) 0 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

/* Probe Limits Section */
.probe-limits-section {
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

.probe-limits-header {
  margin-bottom: var(--spacing-sm);
}

.probe-limits-label {
  font-weight: 500;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.limits-row {
  display: flex;
  gap: var(--spacing-lg);
  flex-wrap: wrap;
}

.limit-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.limit-field label {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.limit-field input[type="number"] {
  width: 80px;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-family: inherit;
  transition: var(--transition-base);
}

.limit-field input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

/* Validation Warning */
.validation-warning {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: var(--radius-base);
  color: var(--color-warning);
  font-size: var(--font-size-sm);
}

.warning-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  background: var(--color-warning);
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: var(--font-size-xs);
  flex-shrink: 0;
}
</style>
