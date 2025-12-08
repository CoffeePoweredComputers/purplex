<template>
  <div class="form-section rounded-lg border-default">
    <h3>Probe Settings</h3>
    <p class="section-description">
      {{ sectionDescription }}
    </p>

    <!-- Show Function Signature Toggle -->
    <div class="toggle-setting">
      <label class="toggle-label">
        <input
          :checked="config.showFunctionSignature.value"
          type="checkbox"
          class="toggle-checkbox"
          @change="config.setShowFunctionSignature(($event.target as HTMLInputElement).checked)"
        >
        <span class="toggle-text">Show Function Signature to Students</span>
      </label>
      <p class="setting-description">
        <span v-if="config.showFunctionSignature.value">
          Students will see the function name and parameter types.
        </span>
        <span v-else>
          Students will only see parameter names without type information.
          This makes the problem more challenging.
        </span>
      </p>
    </div>

    <!-- Probe Mode Selection -->
    <div class="probe-mode-section">
      <h4>Probe Mode</h4>
      <p class="subsection-description">
        Choose how probe attempts are limited for students.
      </p>

      <div class="probe-mode-options">
        <div
          v-for="mode in probeModes"
          :key="mode.value"
          :class="['probe-mode-option', { selected: config.probeMode.value === mode.value }]"
          @click="config.setProbeMode(mode.value)"
        >
          <div class="mode-header">
            <input
              type="radio"
              :checked="config.probeMode.value === mode.value"
              :value="mode.value"
              name="probe_mode"
              @change="config.setProbeMode(mode.value)"
            >
            <span class="mode-label">{{ mode.label }}</span>
          </div>
          <p class="mode-description">
            {{ mode.description }}
          </p>
        </div>
      </div>
    </div>

    <!-- Conditional Fields Based on Mode -->
    <div
      v-if="config.showMaxProbesField.value"
      class="probe-limits-section"
    >
      <h4>Probe Limits</h4>

      <div class="form-group">
        <label for="max_probes">Initial Probe Budget *</label>
        <input
          id="max_probes"
          :value="config.maxProbes.value"
          type="number"
          min="1"
          max="100"
          required
          @input="config.setMaxProbes(parseInt(($event.target as HTMLInputElement).value) || 10)"
        >
        <p class="field-hint">
          Number of probe queries students start with (recommended: 5-15)
        </p>
      </div>

      <!-- Cooldown-specific fields -->
      <template v-if="config.showCooldownFields.value">
        <div class="cooldown-fields">
          <div class="form-group">
            <label for="cooldown_attempts">Submissions Before Refill *</label>
            <input
              id="cooldown_attempts"
              :value="config.cooldownAttempts.value"
              type="number"
              min="1"
              max="10"
              required
              @input="config.setCooldownAttempts(parseInt(($event.target as HTMLInputElement).value) || 3)"
            >
            <p class="field-hint">
              {{ cooldownAttemptsHint }}
            </p>
          </div>

          <div class="form-group">
            <label for="cooldown_refill">Probes Per Refill *</label>
            <input
              id="cooldown_refill"
              :value="config.cooldownRefill.value"
              type="number"
              min="1"
              max="20"
              required
              @input="config.setCooldownRefill(parseInt(($event.target as HTMLInputElement).value) || 5)"
            >
            <p class="field-hint">
              Number of probes granted after each cooldown cycle
            </p>
          </div>
        </div>
      </template>
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
import type { UseProbeConfigReturn, ProbeMode } from '@/composables/admin/useProbeConfig';

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
  margin: 0 0 var(--spacing-xl) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-border);
}

.form-section h4 {
  margin: var(--spacing-lg) 0 var(--spacing-md) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
}

.section-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-lg);
}

.subsection-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-md);
}

/* Form Groups */
.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
}

/* Input Styling */
.form-group input[type="number"] {
  max-width: 120px;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-family: inherit;
  transition: var(--transition-base);
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

.field-hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

/* Toggle Setting */
.toggle-setting {
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-lg);
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  margin-bottom: var(--spacing-sm);
}

.toggle-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.toggle-text {
  font-weight: 500;
  color: var(--color-text-primary);
}

.setting-description {
  margin: 0;
  padding-left: 26px;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

/* Probe Mode Section */
.probe-mode-section {
  margin-bottom: var(--spacing-lg);
}

.probe-mode-options {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.probe-mode-option {
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-base);
}

.probe-mode-option:hover {
  border-color: var(--color-text-muted);
}

.probe-mode-option.selected {
  border-color: var(--color-primary-gradient-start);
  background: rgba(99, 102, 241, 0.1);
}

.mode-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.mode-header input[type="radio"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.mode-label {
  font-weight: 600;
  color: var(--color-text-primary);
}

.mode-description {
  margin: 0;
  padding-left: 26px;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

/* Probe Limits Section */
.probe-limits-section {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

.probe-limits-section h4 {
  margin-top: 0;
}

.cooldown-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-lg);
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-bg-border);
}

/* Validation Warning */
.validation-warning {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
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
  width: 20px;
  height: 20px;
  background: var(--color-warning);
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: var(--font-size-xs);
}
</style>
