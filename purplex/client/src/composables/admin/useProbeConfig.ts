/**
 * useProbeConfig - Base composable for probe configuration shared by
 * Probeable Code and Probeable Spec problem types.
 *
 * This composable handles the common probe settings:
 * - showFunctionSignature: Whether to show function params/types to student
 * - probeMode: 'block' | 'cooldown' | 'explore' - how probes are limited
 * - maxProbes: Initial probe budget (default 10)
 * - cooldownAttempts: Number of submissions before probe refill
 * - cooldownRefill: Number of probes granted after cooldown
 *
 * This is shared logic extracted from useProbeableCodeConfig and useProbeableSpecConfig
 * to avoid duplication. Type-specific composables wrap this for their specific needs.
 */

import { computed, type ComputedRef, type DeepReadonly, reactive, readonly } from 'vue';
import { useI18n } from 'vue-i18n';

// ===== TYPES =====

export type ProbeMode = 'block' | 'cooldown' | 'explore';

export interface ProbeConfig {
  show_function_signature: boolean;
  probe_mode: ProbeMode;
  max_probes: number;
  cooldown_attempts: number;
  cooldown_refill: number;
}

export interface UseProbeConfigReturn {
  /** Readonly probe config */
  config: DeepReadonly<ProbeConfig>;

  /** Whether to show function signature to student */
  showFunctionSignature: ComputedRef<boolean>;
  /** Probe mode: block, cooldown, or explore */
  probeMode: ComputedRef<ProbeMode>;
  /** Initial probe budget */
  maxProbes: ComputedRef<number>;
  /** Submissions before refill (cooldown mode) */
  cooldownAttempts: ComputedRef<number>;
  /** Probes granted after cooldown */
  cooldownRefill: ComputedRef<number>;

  /** Whether cooldown fields are relevant */
  showCooldownFields: ComputedRef<boolean>;
  /** Whether max probes field is relevant */
  showMaxProbesField: ComputedRef<boolean>;
  /** Validation error message (if any) */
  validationError: ComputedRef<string | null>;

  /** Set show function signature */
  setShowFunctionSignature: (show: boolean) => void;
  /** Set probe mode */
  setProbeMode: (mode: ProbeMode) => void;
  /** Set max probes */
  setMaxProbes: (count: number) => void;
  /** Set cooldown attempts */
  setCooldownAttempts: (count: number) => void;
  /** Set cooldown refill */
  setCooldownRefill: (count: number) => void;

  /** Load config from problem data */
  loadConfig: (config: Partial<ProbeConfig> | null | undefined) => void;
  /** Get config for API */
  getConfigForApi: () => ProbeConfig;
  /** Validate the configuration */
  validate: () => { valid: boolean; errors: string[] };
  /** Reset to initial state */
  reset: () => void;
}

// ===== CONSTANTS =====

const DEFAULT_MAX_PROBES = 10;
const DEFAULT_COOLDOWN_ATTEMPTS = 3;
const DEFAULT_COOLDOWN_REFILL = 5;

export const PROBE_MODES: { value: ProbeMode; labelKey: string; descriptionKey: string }[] = [
  {
    value: 'block',
    labelKey: 'admin.editors.probeSettings.modes.block.label',
    descriptionKey: 'admin.editors.probeSettings.modes.block.description',
  },
  {
    value: 'cooldown',
    labelKey: 'admin.editors.probeSettings.modes.cooldown.label',
    descriptionKey: 'admin.editors.probeSettings.modes.cooldown.description',
  },
  {
    value: 'explore',
    labelKey: 'admin.editors.probeSettings.modes.explore.label',
    descriptionKey: 'admin.editors.probeSettings.modes.explore.description',
  },
];

// ===== COMPOSABLE =====

export const useProbeConfig = (): UseProbeConfigReturn => {
  const { t } = useI18n();
  const state = reactive<ProbeConfig>({
    show_function_signature: true,
    probe_mode: 'block',
    max_probes: DEFAULT_MAX_PROBES,
    cooldown_attempts: DEFAULT_COOLDOWN_ATTEMPTS,
    cooldown_refill: DEFAULT_COOLDOWN_REFILL,
  });

  // ===== Computed =====

  const showFunctionSignature = computed(() => state.show_function_signature);
  const probeMode = computed(() => state.probe_mode);
  const maxProbes = computed(() => state.max_probes);
  const cooldownAttempts = computed(() => state.cooldown_attempts);
  const cooldownRefill = computed(() => state.cooldown_refill);

  const showCooldownFields = computed(() => state.probe_mode === 'cooldown');
  const showMaxProbesField = computed(() => state.probe_mode !== 'explore');

  const validationError = computed((): string | null => {
    if (state.probe_mode !== 'explore' && state.max_probes < 1) {
      return t('admin.editors.probeSettings.validation.maxProbesMin');
    }
    if (state.probe_mode === 'cooldown') {
      if (state.cooldown_attempts < 1) {
        return t('admin.editors.probeSettings.validation.cooldownAttemptsMin');
      }
      if (state.cooldown_refill < 1) {
        return t('admin.editors.probeSettings.validation.cooldownRefillMin');
      }
    }
    return null;
  });

  // ===== Methods =====

  const setShowFunctionSignature = (show: boolean): void => {
    state.show_function_signature = show;
  };

  const setProbeMode = (mode: ProbeMode): void => {
    state.probe_mode = mode;
  };

  const setMaxProbes = (count: number): void => {
    state.max_probes = Math.max(1, Math.floor(count));
  };

  const setCooldownAttempts = (count: number): void => {
    state.cooldown_attempts = Math.max(1, Math.floor(count));
  };

  const setCooldownRefill = (count: number): void => {
    state.cooldown_refill = Math.max(1, Math.floor(count));
  };

  const loadConfig = (config: Partial<ProbeConfig> | null | undefined): void => {
    if (!config) {
      reset();
      return;
    }

    state.show_function_signature = config.show_function_signature ?? true;
    state.probe_mode = config.probe_mode || 'block';
    state.max_probes = config.max_probes ?? DEFAULT_MAX_PROBES;
    state.cooldown_attempts = config.cooldown_attempts ?? DEFAULT_COOLDOWN_ATTEMPTS;
    state.cooldown_refill = config.cooldown_refill ?? DEFAULT_COOLDOWN_REFILL;
  };

  const getConfigForApi = (): ProbeConfig => {
    return {
      show_function_signature: state.show_function_signature,
      probe_mode: state.probe_mode,
      max_probes: state.max_probes,
      cooldown_attempts: state.cooldown_attempts,
      cooldown_refill: state.cooldown_refill,
    };
  };

  const validate = (): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];

    if (state.probe_mode !== 'explore') {
      if (state.max_probes < 1) {
        errors.push(t('admin.editors.probeSettings.validation.maxProbesMin'));
      }
    }

    if (state.probe_mode === 'cooldown') {
      if (state.cooldown_attempts < 1) {
        errors.push(t('admin.editors.probeSettings.validation.cooldownAttemptsMin'));
      }
      if (state.cooldown_refill < 1) {
        errors.push(t('admin.editors.probeSettings.validation.cooldownRefillMin'));
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  };

  const reset = (): void => {
    state.show_function_signature = true;
    state.probe_mode = 'block';
    state.max_probes = DEFAULT_MAX_PROBES;
    state.cooldown_attempts = DEFAULT_COOLDOWN_ATTEMPTS;
    state.cooldown_refill = DEFAULT_COOLDOWN_REFILL;
  };

  return {
    config: readonly(state),
    showFunctionSignature,
    probeMode,
    maxProbes,
    cooldownAttempts,
    cooldownRefill,
    showCooldownFields,
    showMaxProbesField,
    validationError,
    setShowFunctionSignature,
    setProbeMode,
    setMaxProbes,
    setCooldownAttempts,
    setCooldownRefill,
    loadConfig,
    getConfigForApi,
    validate,
    reset,
  };
};
