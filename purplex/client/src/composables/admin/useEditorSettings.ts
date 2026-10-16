/**
 * useEditorSettings - Manages code editor settings.
 *
 * This composable handles editor preferences:
 * - Font size (with increase/decrease controls)
 *
 * The editor theme is not managed here; Editor.vue follows the app theme.
 */

import { ref, type Ref } from 'vue';

// ===== TYPES =====

export interface UseEditorSettingsReturn {
  /** Current font size */
  fontSize: Ref<number>;

  /** Increase font size */
  increaseFontSize: () => void;
  /** Decrease font size */
  decreaseFontSize: () => void;
  /** Set font size directly */
  setFontSize: (size: number) => void;
  /** Reset to defaults */
  reset: () => void;
}

// ===== CONSTANTS =====

const MIN_FONT_SIZE = 10;
const MAX_FONT_SIZE = 24;
const DEFAULT_FONT_SIZE = 14;

// ===== COMPOSABLE =====

export const useEditorSettings = (): UseEditorSettingsReturn => {
  const fontSize = ref(DEFAULT_FONT_SIZE);

  /**
   * Increase font size (max 24)
   */
  const increaseFontSize = (): void => {
    if (fontSize.value < MAX_FONT_SIZE) {
      fontSize.value += 2;
    }
  };

  /**
   * Decrease font size (min 10)
   */
  const decreaseFontSize = (): void => {
    if (fontSize.value > MIN_FONT_SIZE) {
      fontSize.value -= 2;
    }
  };

  /**
   * Set font size directly (clamped to min/max)
   */
  const setFontSize = (size: number): void => {
    fontSize.value = Math.max(MIN_FONT_SIZE, Math.min(MAX_FONT_SIZE, size));
  };

  /**
   * Reset to defaults
   */
  const reset = (): void => {
    fontSize.value = DEFAULT_FONT_SIZE;
  };

  return {
    fontSize,
    increaseFontSize,
    decreaseFontSize,
    setFontSize,
    reset,
  };
};
