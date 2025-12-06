/**
 * useProblemForm - Manages problem form state for the admin editor.
 *
 * This composable handles the core form data for creating/editing problems.
 * It provides atomic state management with clear mutation paths.
 *
 * Design:
 * - Single reactive form state object
 * - Validation computed properties
 * - Normalization helpers for API communication
 */

import { computed, reactive, readonly, type DeepReadonly, type ComputedRef } from 'vue';
import type { DifficultyLevel, ProblemType, ProblemDetailed } from '@/types';

// ===== TYPES =====

/**
 * Form state for universal problem metadata.
 *
 * Note: test_cases is NOT included here - it's owned by useTestCases composable.
 * This follows the principle that each feature composable owns its state exclusively.
 */
export interface ProblemFormState {
  title: string;
  description: string;
  difficulty: DifficultyLevel;
  problem_type: ProblemType;
  category_ids: number[];
  function_signature: string;
  reference_solution: string;
  tags: string[];
}

export interface UseProblemFormReturn {
  /** Readonly form state - use mutation methods to update */
  form: DeepReadonly<ProblemFormState>;
  /** Whether form has unsaved changes */
  isDirty: ComputedRef<boolean>;
  /** Set entire form state (used when loading) */
  setForm: (data: Partial<ProblemFormState>) => void;
  /** Reset form to initial state */
  resetForm: () => void;
  /** Update a single field */
  updateField: <K extends keyof ProblemFormState>(key: K, value: ProblemFormState[K]) => void;
  /** Update tags from comma-separated string */
  updateTags: (input: string) => void;
  /** Update reference solution with string coercion */
  updateReferenceSolution: (code: string | unknown) => void;
  /** Check if form can be saved (basic validation) */
  canSave: ComputedRef<boolean>;
  /** Get validation errors */
  validationErrors: ComputedRef<string[]>;
  /** Normalize problem data from API response */
  normalizeFromLoad: (data: ProblemDetailed) => ProblemFormState;
  /** Get API-safe string (trim, handle null) */
  getApiSafeString: (value: string | null | undefined) => string;
}

// ===== INITIAL STATE =====

const createInitialState = (): ProblemFormState => ({
  title: '',
  description: '',
  difficulty: 'beginner',
  problem_type: 'eipl',
  category_ids: [],
  function_signature: '',
  reference_solution: '',
  tags: [],
});

// ===== COMPOSABLE =====

export const useProblemForm = (): UseProblemFormReturn => {
  // Single reactive form state
  const state = reactive<ProblemFormState>(createInitialState());

  // Track original state for dirty checking
  let originalState: string = JSON.stringify(createInitialState());

  /**
   * Check if form has unsaved changes
   */
  const isDirty = computed<boolean>(() => {
    return JSON.stringify(state) !== originalState;
  });

  /**
   * Basic validation - check required form fields.
   * Note: Test case validation is handled by useTestCases.canTest
   */
  const canSave = computed<boolean>(() => {
    const hasTitle = state.title.trim().length > 0;
    const hasFunctionSignature = state.function_signature.trim().length > 0;
    const hasReferenceSolution = state.reference_solution.trim().length > 0;

    return hasTitle && hasFunctionSignature && hasReferenceSolution;
  });

  /**
   * Get validation error messages for form fields.
   * Note: Test case validation errors are provided by useTestCases.canTestReason
   */
  const validationErrors = computed<string[]>(() => {
    const errors: string[] = [];

    if (!state.title.trim()) {
      errors.push('Title is required');
    }
    if (!state.function_signature.trim()) {
      errors.push('Function signature is required');
    }
    if (!state.reference_solution.trim()) {
      errors.push('Reference solution is required');
    }

    return errors;
  });

  /**
   * Set entire form state (partial update)
   */
  const setForm = (data: Partial<ProblemFormState>): void => {
    if (data.title !== undefined) state.title = data.title;
    if (data.difficulty !== undefined) state.difficulty = data.difficulty;
    if (data.problem_type !== undefined) state.problem_type = data.problem_type;
    if (data.category_ids !== undefined) state.category_ids = data.category_ids;
    if (data.function_signature !== undefined) state.function_signature = data.function_signature;
    if (data.reference_solution !== undefined) state.reference_solution = data.reference_solution;
    if (data.tags !== undefined) state.tags = data.tags;

    // Update original state snapshot after loading
    originalState = JSON.stringify(state);
  };

  /**
   * Reset form to initial state
   */
  const resetForm = (): void => {
    const initial = createInitialState();
    Object.assign(state, initial);
    originalState = JSON.stringify(initial);
  };

  /**
   * Update a single field
   */
  const updateField = <K extends keyof ProblemFormState>(
    key: K,
    value: ProblemFormState[K]
  ): void => {
    state[key] = value;
  };

  /**
   * Update tags from comma-separated input
   */
  const updateTags = (input: string): void => {
    state.tags = input
      .split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0);
  };

  /**
   * Update reference solution with string coercion
   */
  const updateReferenceSolution = (code: string | unknown): void => {
    state.reference_solution = typeof code === 'string' ? code : String(code ?? '');
  };

  /**
   * Get API-safe string (trim, handle null/undefined)
   */
  const getApiSafeString = (value: string | null | undefined): string => {
    if (value === null || value === undefined) return '';
    return String(value).trim();
  };

  /**
   * Normalize problem data from API response for form use.
   * Note: test_cases is handled separately by useTestCases.loadFromBackend()
   */
  const normalizeFromLoad = (data: ProblemDetailed): ProblemFormState => {
    // Extract category IDs from category objects
    let categoryIds: number[] = [];
    if (data.categories && Array.isArray(data.categories)) {
      categoryIds = data.categories.map(cat => cat.id);
    } else if (data.category_ids) {
      categoryIds = data.category_ids;
    }

    // Ensure tags is an array
    const tags = Array.isArray(data.tags) ? data.tags : [];

    // Ensure problem_type has a default
    const problemType = data.problem_type || 'eipl';

    // Ensure reference_solution is a string
    const referenceSolution = typeof data.reference_solution === 'string'
      ? data.reference_solution
      : String(data.reference_solution ?? '');

    return {
      title: data.title || '',
      description: data.description || '',
      difficulty: data.difficulty || 'beginner',
      problem_type: problemType,
      category_ids: categoryIds,
      function_signature: data.function_signature || '',
      reference_solution: referenceSolution,
      tags,
    };
  };

  return {
    form: readonly(state),
    isDirty,
    setForm,
    resetForm,
    updateField,
    updateTags,
    updateReferenceSolution,
    canSave,
    validationErrors,
    normalizeFromLoad,
    getApiSafeString,
  };
};
