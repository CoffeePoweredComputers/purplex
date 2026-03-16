/**
 * useRefuteConfig - Manages refute (counterexample) problem configuration.
 *
 * This composable handles the configuration for refute-type problems:
 * - Claim text: The false claim students must disprove
 * - Expected counterexample: Optional JSON hint for known counterexamples
 */

import { computed, type ComputedRef, type DeepReadonly, reactive, readonly } from 'vue';
import { useI18n } from 'vue-i18n';

// ===== TYPES =====

export interface RefuteConfig {
  claim_text: string;
  claim_predicate: string; // Python expression that's True when claim holds
  expected_counterexample: string; // JSON string
}

export interface UseRefuteConfigReturn {
  /** Readonly refute config */
  config: DeepReadonly<RefuteConfig>;
  /** Claim text */
  claimText: ComputedRef<string>;
  /** Claim predicate (Python expression) */
  claimPredicate: ComputedRef<string>;
  /** Expected counterexample (JSON string) */
  expectedCounterexample: ComputedRef<string>;
  /** Whether config has a claim */
  hasClaim: ComputedRef<boolean>;
  /** Whether config has a predicate */
  hasPredicate: ComputedRef<boolean>;
  /** Whether the claim follows good patterns (contains "always", "never", "for all", etc.) */
  hasGoodClaimPattern: ComputedRef<boolean>;
  /** Warning message for claim quality */
  claimWarning: ComputedRef<string | null>;
  /** Whether expected counterexample is valid JSON */
  isValidJson: ComputedRef<boolean>;
  /** Parsed counterexample object (or null if invalid) */
  parsedCounterexample: ComputedRef<Record<string, unknown> | null>;
  /** JSON parse error message */
  jsonError: ComputedRef<string | null>;
  /** Predicate validation error */
  predicateError: ComputedRef<string | null>;

  /** Set claim text */
  setClaimText: (text: string) => void;
  /** Set claim predicate */
  setClaimPredicate: (predicate: string) => void;
  /** Set expected counterexample JSON */
  setExpectedCounterexample: (json: string) => void;
  /** Load config from problem data */
  loadConfig: (config: Partial<RefuteConfig> | null | undefined) => void;
  /** Get config for API */
  getConfigForApi: () => RefuteConfig;
  /** Reset to initial state */
  reset: () => void;
}

// ===== CONSTANTS =====

// Patterns that indicate a well-formed claim (universal/absolute statements)
const GOOD_CLAIM_PATTERNS = [
  /\balways\b/i,
  /\bnever\b/i,
  /\bfor all\b/i,
  /\bevery\b/i,
  /\bany\b/i,
  /\ball\b/i,
  /\bno\b/i,
  /\bnone\b/i,
  /\bguaranteed\b/i,
  /\bmust\b/i,
  /\bwill\b/i,
  /\bcannot\b/i,
];

// ===== COMPOSABLE =====

export const useRefuteConfig = (): UseRefuteConfigReturn => {
  const { t } = useI18n();
  const state = reactive<RefuteConfig>({
    claim_text: '',
    claim_predicate: '',
    expected_counterexample: '',
  });

  // ===== Computed =====

  const claimText = computed(() => state.claim_text);
  const claimPredicate = computed(() => state.claim_predicate);
  const expectedCounterexample = computed(() => state.expected_counterexample);

  const hasClaim = computed(() => state.claim_text.trim().length > 0);
  const hasPredicate = computed(() => state.claim_predicate.trim().length > 0);

  // Basic predicate syntax validation (just checks for obvious issues)
  const predicateError = computed((): string | null => {
    const predicate = state.claim_predicate.trim();
    if (!predicate) {return null;} // Empty is valid (optional for backwards compatibility)

    // Check for common dangerous patterns
    if (predicate.includes('import ') || predicate.includes('__')) {
      return t('admin.editors.refuteValidation.predicateDangerousPattern');
    }

    // Check for basic syntax issues
    const openParens = (predicate.match(/\(/g) || []).length;
    const closeParens = (predicate.match(/\)/g) || []).length;
    if (openParens !== closeParens) {
      return t('admin.editors.refuteValidation.mismatchedParentheses');
    }

    return null;
  });

  const hasGoodClaimPattern = computed(() => {
    if (!hasClaim.value) {return true;} // Don't warn on empty
    return GOOD_CLAIM_PATTERNS.some(pattern => pattern.test(state.claim_text));
  });

  const claimWarning = computed((): string | null => {
    if (!hasClaim.value) {return null;}
    if (hasGoodClaimPattern.value) {return null;}
    return t('admin.editors.refuteValidation.claimWarning');
  });

  const parsedCounterexample = computed((): Record<string, unknown> | null => {
    const json = state.expected_counterexample.trim();
    if (!json) {return null;}
    try {
      const parsed = JSON.parse(json);
      if (typeof parsed === 'object' && parsed !== null) {
        return parsed as Record<string, unknown>;
      }
      return null;
    } catch {
      return null;
    }
  });

  const isValidJson = computed(() => {
    const json = state.expected_counterexample.trim();
    if (!json) {return true;} // Empty is valid (optional field)
    return parsedCounterexample.value !== null;
  });

  const jsonError = computed((): string | null => {
    const json = state.expected_counterexample.trim();
    if (!json) {return null;}
    try {
      const parsed = JSON.parse(json);
      if (typeof parsed !== 'object' || parsed === null) {
        return t('admin.editors.refuteValidation.expectedJsonObject');
      }
      return null;
    } catch (e) {
      return t('admin.editors.refuteValidation.invalidJson', { message: (e as Error).message });
    }
  });

  // ===== Methods =====

  const setClaimText = (text: string): void => {
    state.claim_text = text;
  };

  const setClaimPredicate = (predicate: string): void => {
    state.claim_predicate = predicate;
  };

  const setExpectedCounterexample = (json: string): void => {
    state.expected_counterexample = json;
  };

  const loadConfig = (config: Partial<RefuteConfig> | null | undefined): void => {
    if (!config) {
      reset();
      return;
    }

    state.claim_text = config.claim_text || '';
    state.claim_predicate = config.claim_predicate || '';
    // Handle both string and object for expected_counterexample
    if (typeof config.expected_counterexample === 'string') {
      state.expected_counterexample = config.expected_counterexample;
    } else if (config.expected_counterexample) {
      state.expected_counterexample = JSON.stringify(config.expected_counterexample, null, 2);
    } else {
      state.expected_counterexample = '';
    }
  };

  const getConfigForApi = (): RefuteConfig => {
    return {
      claim_text: state.claim_text.trim(),
      claim_predicate: state.claim_predicate.trim(),
      expected_counterexample: state.expected_counterexample.trim(),
    };
  };

  const reset = (): void => {
    state.claim_text = '';
    state.claim_predicate = '';
    state.expected_counterexample = '';
  };

  return {
    config: readonly(state),
    claimText,
    claimPredicate,
    expectedCounterexample,
    hasClaim,
    hasPredicate,
    hasGoodClaimPattern,
    claimWarning,
    isValidJson,
    parsedCounterexample,
    jsonError,
    predicateError,
    setClaimText,
    setClaimPredicate,
    setExpectedCounterexample,
    loadConfig,
    getConfigForApi,
    reset,
  };
};
