/**
 * useDebugFixConfig - Manages Debug Fix problem configuration.
 *
 * This composable handles the configuration for debug_fix-type problems:
 * - buggyCode: The intentionally buggy code students see initially
 * - bugHints: Progressive hints array [{ level: 1, text: "Check line 5" }]
 * - allowCompleteRewrite: Whether student can rewrite entirely or must make minimal fixes
 *
 * Note: reference_solution and function_signature are handled by the main form composable
 * since they are inherited from SpecProblem (shared with eipl, refute, etc.)
 */

import { computed, type ComputedRef, type DeepReadonly, reactive, readonly, type Ref, ref } from 'vue';

// ===== TYPES =====

export interface BugHint {
  level: 1 | 2 | 3;
  text: string;
}

export interface DebugFixConfig {
  buggy_code: string;
  bug_hints: BugHint[];
  allow_complete_rewrite: boolean;
}

export interface UseDebugFixConfigReturn {
  /** Readonly debug fix config */
  config: DeepReadonly<DebugFixConfig>;
  /** Buggy code (what student sees initially) */
  buggyCode: ComputedRef<string>;
  /** Progressive hints array */
  bugHints: ComputedRef<BugHint[]>;
  /** Whether student can rewrite entirely */
  allowCompleteRewrite: ComputedRef<boolean>;
  /** Whether config has buggy code */
  hasBuggyCode: ComputedRef<boolean>;
  /** Whether buggy code differs from reference solution */
  codesDiffer: (referenceSolution: string) => boolean;
  /** Validation error message (if any) */
  validationError: ComputedRef<string | null>;
  /** New hint being added */
  newHint: Ref<{ level: 1 | 2 | 3; text: string }>;

  /** Set buggy code */
  setBuggyCode: (code: string) => void;
  /** Set allow complete rewrite */
  setAllowCompleteRewrite: (allow: boolean) => void;
  /** Add a bug hint */
  addHint: (hint: BugHint) => void;
  /** Remove a bug hint by index */
  removeHint: (index: number) => void;
  /** Update a bug hint */
  updateHint: (index: number, hint: Partial<BugHint>) => void;
  /** Reorder hints by level */
  sortHintsByLevel: () => void;
  /** Load config from problem data */
  loadConfig: (config: Partial<DebugFixConfig> | null | undefined) => void;
  /** Get config for API */
  getConfigForApi: () => DebugFixConfig;
  /** Validate the configuration */
  validate: (referenceSolution: string) => { valid: boolean; errors: string[] };
  /** Reset to initial state */
  reset: () => void;
}

// ===== CONSTANTS =====

const DEFAULT_NEW_HINT: { level: 1 | 2 | 3; text: string } = {
  level: 1,
  text: '',
};

// ===== COMPOSABLE =====

export const useDebugFixConfig = (): UseDebugFixConfigReturn => {
  const state = reactive<DebugFixConfig>({
    buggy_code: '',
    bug_hints: [],
    allow_complete_rewrite: false,
  });

  // New hint being edited (for add form)
  const newHint = ref<{ level: 1 | 2 | 3; text: string }>({ ...DEFAULT_NEW_HINT });

  // ===== Computed =====

  const buggyCode = computed(() => state.buggy_code);
  const bugHints = computed(() => state.bug_hints);
  const allowCompleteRewrite = computed(() => state.allow_complete_rewrite);

  const hasBuggyCode = computed(() => state.buggy_code.trim().length > 0);

  const validationError = computed((): string | null => {
    if (!hasBuggyCode.value) {
      return 'Buggy code is required';
    }
    return null;
  });

  // ===== Methods =====

  const codesDiffer = (referenceSolution: string): boolean => {
    const buggy = state.buggy_code.trim();
    const reference = (referenceSolution || '').trim();
    return buggy !== reference;
  };

  const setBuggyCode = (code: string): void => {
    state.buggy_code = code;
  };

  const setAllowCompleteRewrite = (allow: boolean): void => {
    state.allow_complete_rewrite = allow;
  };

  const addHint = (hint: BugHint): void => {
    // Validate hint
    if (!hint.text.trim()) {return;}
    if (hint.level < 1 || hint.level > 3) {return;}

    state.bug_hints.push({
      level: hint.level,
      text: hint.text.trim(),
    });
  };

  const removeHint = (index: number): void => {
    if (index >= 0 && index < state.bug_hints.length) {
      state.bug_hints.splice(index, 1);
    }
  };

  const updateHint = (index: number, hint: Partial<BugHint>): void => {
    if (index >= 0 && index < state.bug_hints.length) {
      if (hint.level !== undefined) {
        state.bug_hints[index].level = hint.level;
      }
      if (hint.text !== undefined) {
        state.bug_hints[index].text = hint.text;
      }
    }
  };

  const sortHintsByLevel = (): void => {
    state.bug_hints.sort((a, b) => a.level - b.level);
  };

  const loadConfig = (config: Partial<DebugFixConfig> | null | undefined): void => {
    if (!config) {
      reset();
      return;
    }

    state.buggy_code = config.buggy_code || '';
    state.allow_complete_rewrite = config.allow_complete_rewrite ?? false;

    // Load hints, ensuring proper structure
    if (Array.isArray(config.bug_hints)) {
      state.bug_hints = config.bug_hints.map(h => ({
        level: (h.level >= 1 && h.level <= 3 ? h.level : 1) as 1 | 2 | 3,
        text: h.text || '',
      }));
    } else {
      state.bug_hints = [];
    }
  };

  const getConfigForApi = (): DebugFixConfig => {
    return {
      buggy_code: state.buggy_code,
      bug_hints: state.bug_hints.map(h => ({
        level: h.level,
        text: h.text.trim(),
      })),
      allow_complete_rewrite: state.allow_complete_rewrite,
    };
  };

  const validate = (referenceSolution: string): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];

    if (!hasBuggyCode.value) {
      errors.push('Buggy code is required');
    }

    if (!codesDiffer(referenceSolution)) {
      errors.push('Buggy code must be different from the reference solution');
    }

    // Validate hints structure
    for (let i = 0; i < state.bug_hints.length; i++) {
      const hint = state.bug_hints[i];
      if (!hint.text.trim()) {
        errors.push(`Hint ${i + 1} has empty text`);
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  };

  const reset = (): void => {
    state.buggy_code = '';
    state.bug_hints = [];
    state.allow_complete_rewrite = false;
    newHint.value = { ...DEFAULT_NEW_HINT };
  };

  return {
    config: readonly(state),
    buggyCode,
    bugHints,
    allowCompleteRewrite,
    hasBuggyCode,
    codesDiffer,
    validationError,
    newHint,
    setBuggyCode,
    setAllowCompleteRewrite,
    addHint,
    removeHint,
    updateHint,
    sortHintsByLevel,
    loadConfig,
    getConfigForApi,
    validate,
    reset,
  };
};
