/**
 * useHintsConfig - Manages hints configuration for the admin editor.
 *
 * This composable handles the three hint types:
 * - Variable Fade: Renames variables to help students focus
 * - Subgoal Highlight: Highlights code sections with explanations
 * - Suggested Trace: Shows a function call for Python Tutor
 */

import { type DeepReadonly, reactive, readonly, type Ref, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import type {
  HintConfig,
  SubgoalHighlight,
  SubgoalHighlightHint,
  SuggestedTraceHint,
  VariableFadeHint,
  VariableFadeMapping,
} from '@/types';
import { problemService } from '@/services/problemService';
import { log } from '@/utils/logger';

// ===== TYPES =====

export type HintTabType = 'variable_fade' | 'subgoal_highlight' | 'suggested_trace';

export interface HintsState {
  variable_fade: VariableFadeHint;
  subgoal_highlight: SubgoalHighlightHint;
  suggested_trace: SuggestedTraceHint;
}

export interface UseHintsConfigReturn {
  /** Readonly hints state */
  hints: DeepReadonly<HintsState>;
  /** Currently active tab */
  activeTab: Ref<HintTabType>;
  /** Python Tutor modal visibility */
  pyTutorVisible: Ref<boolean>;
  /** Python Tutor URL */
  pyTutorUrl: Ref<string>;
  /** Function call validation error */
  functionCallError: Ref<string | null>;

  // Variable Fade API
  variableFade: {
    /** Add a new variable mapping */
    addMapping: (from: string, to: string) => void;
    /** Remove a mapping by index */
    removeMapping: (index: number) => void;
    /** Validate a variable name */
    validateName: (name: string) => boolean;
    /** Set enabled state */
    setEnabled: (enabled: boolean) => void;
    /** Set min attempts */
    setMinAttempts: (attempts: number) => void;
  };

  // Subgoal Highlight API
  subgoalHighlight: {
    /** Add a new subgoal */
    addSubgoal: (subgoal: Omit<SubgoalHighlight, 'id'>) => void;
    /** Remove a subgoal by index */
    removeSubgoal: (index: number) => void;
    /** Set enabled state */
    setEnabled: (enabled: boolean) => void;
    /** Set min attempts */
    setMinAttempts: (attempts: number) => void;
  };

  // Suggested Trace API
  suggestedTrace: {
    /** Set the suggested call */
    setCall: (call: string) => void;
    /** Validate the function call */
    validateCall: (call: string, expectedFunctionName?: string) => void;
    /** Open Python Tutor preview */
    openPyTutor: (code: string) => void;
    /** Close Python Tutor modal */
    closePyTutor: () => void;
    /** Set enabled state */
    setEnabled: (enabled: boolean) => void;
    /** Set min attempts */
    setMinAttempts: (attempts: number) => void;
  };

  // Persistence
  /** Load hints for a problem */
  load: (problemSlug: string) => Promise<void>;
  /** Save hints for a problem */
  save: (problemSlug: string) => Promise<void>;
  /** Reset to initial state */
  reset: () => void;
  /** Set hints from loaded data */
  setHints: (hintsArray: HintConfig[]) => void;
  /** Get hints as array for saving */
  getHintsArray: () => HintConfig[];
}

// ===== INITIAL STATE =====

const createInitialState = (): HintsState => ({
  variable_fade: {
    type: 'variable_fade',
    is_enabled: false,
    min_attempts: 0,
    content: {
      mappings: [],
    },
  },
  subgoal_highlight: {
    type: 'subgoal_highlight',
    is_enabled: false,
    min_attempts: 0,
    content: {
      subgoals: [],
    },
  },
  suggested_trace: {
    type: 'suggested_trace',
    is_enabled: false,
    min_attempts: 0,
    content: {
      suggested_call: '',
    },
  },
});

// ===== COMPOSABLE =====

export const useHintsConfig = (): UseHintsConfigReturn => {
  const { t } = useI18n();
  const state = reactive<HintsState>(createInitialState());
  const activeTab = ref<HintTabType>('variable_fade');
  const pyTutorVisible = ref(false);
  const pyTutorUrl = ref('');
  const functionCallError = ref<string | null>(null);

  // ===== Variable Fade =====

  const variableFade = {
    addMapping: (from: string, to: string): void => {
      state.variable_fade.content.mappings.push({ from, to });
    },

    removeMapping: (index: number): void => {
      state.variable_fade.content.mappings.splice(index, 1);
    },

    validateName: (name: string): boolean => {
      // Python variable naming rules
      return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
    },

    setEnabled: (enabled: boolean): void => {
      state.variable_fade.is_enabled = enabled;
    },

    setMinAttempts: (attempts: number): void => {
      state.variable_fade.min_attempts = attempts;
    },
  };

  // ===== Subgoal Highlight =====

  const subgoalHighlight = {
    addSubgoal: (subgoal: Omit<SubgoalHighlight, 'id'>): void => {
      state.subgoal_highlight.content.subgoals.push({
        ...subgoal,
        id: `subgoal-${Date.now()}`,
      });
    },

    removeSubgoal: (index: number): void => {
      state.subgoal_highlight.content.subgoals.splice(index, 1);
    },

    setEnabled: (enabled: boolean): void => {
      state.subgoal_highlight.is_enabled = enabled;
    },

    setMinAttempts: (attempts: number): void => {
      state.subgoal_highlight.min_attempts = attempts;
    },
  };

  // ===== Suggested Trace =====

  const suggestedTrace = {
    setCall: (call: string): void => {
      state.suggested_trace.content.suggested_call = call;
    },

    validateCall: (call: string, expectedFunctionName?: string): void => {
      if (!call.trim()) {
        functionCallError.value = null;
        return;
      }

      // Basic function call validation
      const functionCallRegex = /^(\w+)\s*\(/;
      const match = call.match(functionCallRegex);

      if (!match) {
        functionCallError.value = t('admin.editors.hintsValidation.invalidFunctionCall');
        return;
      }

      const calledFunction = match[1];

      // Check if function name matches expected
      if (expectedFunctionName && calledFunction !== expectedFunctionName) {
        functionCallError.value = t('admin.editors.hintsValidation.functionNameMismatch', { called: calledFunction, expected: expectedFunctionName });
        return;
      }

      // Check for balanced parentheses
      let depth = 0;
      for (const char of call) {
        if (char === '(') {depth++;}
        if (char === ')') {depth--;}
        if (depth < 0) {
          functionCallError.value = t('admin.editors.hintsValidation.unbalancedParentheses');
          return;
        }
      }
      if (depth !== 0) {
        functionCallError.value = t('admin.editors.hintsValidation.unbalancedParentheses');
        return;
      }

      functionCallError.value = null;
    },

    openPyTutor: (code: string): void => {
      const call = state.suggested_trace.content.suggested_call;
      const fullCode = `${code}\n\nprint(${call})`;
      const encoded = encodeURIComponent(fullCode);
      pyTutorUrl.value = `https://pythontutor.com/iframe-embed.html#code=${encoded}&cumulative=false&heapPrimitives=nevernest&mode=edit&origin=opt-frontend.js&py=3&rawInputLstJSON=%5B%5D&textReferences=false`;
      pyTutorVisible.value = true;
    },

    closePyTutor: (): void => {
      pyTutorVisible.value = false;
      pyTutorUrl.value = '';
    },

    setEnabled: (enabled: boolean): void => {
      state.suggested_trace.is_enabled = enabled;
    },

    setMinAttempts: (attempts: number): void => {
      state.suggested_trace.min_attempts = attempts;
    },
  };

  // ===== Persistence =====

  const load = async (problemSlug: string): Promise<void> => {
    try {
      const hintsArray = await problemService.getProblemHints(problemSlug);
      setHints(hintsArray);
    } catch (error) {
      log.error('Failed to load hints', error);
    }
  };

  const save = async (problemSlug: string): Promise<void> => {
    try {
      const hintsArray = getHintsArray();
      await problemService.updateHints(problemSlug, hintsArray);
    } catch (error) {
      log.error('Failed to save hints', error);
      throw error;
    }
  };

  const setHints = (hintsArray: HintConfig[]): void => {
    hintsArray.forEach(hint => {
      if (hint.type === 'variable_fade') {
        state.variable_fade = hint as VariableFadeHint;
      } else if (hint.type === 'subgoal_highlight') {
        state.subgoal_highlight = hint as SubgoalHighlightHint;
      } else if (hint.type === 'suggested_trace') {
        state.suggested_trace = hint as SuggestedTraceHint;
      }
    });
  };

  const getHintsArray = (): HintConfig[] => {
    return [
      state.variable_fade,
      state.subgoal_highlight,
      state.suggested_trace,
    ];
  };

  const reset = (): void => {
    const initial = createInitialState();
    Object.assign(state, initial);
    activeTab.value = 'variable_fade';
    pyTutorVisible.value = false;
    pyTutorUrl.value = '';
    functionCallError.value = null;
  };

  return {
    hints: readonly(state),
    activeTab,
    pyTutorVisible,
    pyTutorUrl,
    functionCallError,
    variableFade,
    subgoalHighlight,
    suggestedTrace,
    load,
    save,
    reset,
    setHints,
    getHintsArray,
  };
};
