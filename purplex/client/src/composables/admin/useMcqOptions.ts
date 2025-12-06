/**
 * useMcqOptions - Manages MCQ options for the admin editor.
 *
 * This composable handles multiple choice question options including:
 * - Adding/removing options (2-6 options)
 * - Setting the correct answer
 * - Managing explanation text
 */

import { ref, computed, type Ref, type ComputedRef } from 'vue';

// ===== TYPES =====

export interface McqOption {
  id: string;
  text: string;
  is_correct: boolean;
  explanation: string;
}

export interface UseMcqOptionsReturn {
  /** MCQ options array */
  options: Ref<McqOption[]>;
  /** Whether there is a correct answer selected */
  hasCorrectAnswer: ComputedRef<boolean>;
  /** Whether more options can be added (max 6) */
  canAddMore: ComputedRef<boolean>;
  /** Whether options can be removed (min 2) */
  canRemove: ComputedRef<boolean>;

  /** Add a new option */
  addOption: () => void;
  /** Remove an option by index */
  removeOption: (index: number) => void;
  /** Set the correct answer by index */
  setCorrect: (index: number) => void;
  /** Set all options */
  setOptions: (newOptions: McqOption[]) => void;
  /** Get options for API (filtered) */
  getOptionsForApi: () => McqOption[];
  /** Reset to initial state */
  reset: () => void;
}

// ===== COMPOSABLE =====

export const useMcqOptions = (): UseMcqOptionsReturn => {
  const options = ref<McqOption[]>([
    { id: '1', text: '', is_correct: false, explanation: '' },
  ]);

  /**
   * Check if there is a correct answer
   */
  const hasCorrectAnswer = computed<boolean>(() => {
    return options.value.some(opt => opt.is_correct);
  });

  /**
   * Check if more options can be added (max 6)
   */
  const canAddMore = computed<boolean>(() => {
    return options.value.length < 6;
  });

  /**
   * Check if options can be removed (min 2)
   */
  const canRemove = computed<boolean>(() => {
    return options.value.length > 2;
  });

  /**
   * Add a new option
   */
  const addOption = (): void => {
    if (!canAddMore.value) return;

    options.value.push({
      id: String(Date.now()),
      text: '',
      is_correct: false,
      explanation: '',
    });
  };

  /**
   * Remove an option by index
   */
  const removeOption = (index: number): void => {
    if (!canRemove.value) return;

    options.value.splice(index, 1);
  };

  /**
   * Set the correct answer by index
   */
  const setCorrect = (index: number): void => {
    // Unset all others first
    options.value.forEach((opt, i) => {
      opt.is_correct = i === index;
    });
  };

  /**
   * Set all options (used when loading)
   */
  const setOptions = (newOptions: McqOption[]): void => {
    options.value = newOptions.length > 0 ? newOptions : [
      { id: '1', text: '', is_correct: false, explanation: '' },
    ];
  };

  /**
   * Get options for API (filter out empty options)
   */
  const getOptionsForApi = (): McqOption[] => {
    return options.value.filter(opt => opt.text.trim());
  };

  /**
   * Reset to initial state
   */
  const reset = (): void => {
    options.value = [
      { id: '1', text: '', is_correct: false, explanation: '' },
    ];
  };

  return {
    options,
    hasCorrectAnswer,
    canAddMore,
    canRemove,
    addOption,
    removeOption,
    setCorrect,
    setOptions,
    getOptionsForApi,
    reset,
  };
};
