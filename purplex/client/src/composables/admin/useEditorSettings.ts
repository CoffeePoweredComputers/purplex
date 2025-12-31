/**
 * useEditorSettings - Manages code editor settings.
 *
 * This composable handles editor preferences:
 * - Font size (with increase/decrease controls)
 * - Theme selection
 */

import { ref, type Ref } from 'vue';

// ===== TYPES =====

export interface UseEditorSettingsReturn {
  /** Current font size */
  fontSize: Ref<number>;
  /** Current theme */
  theme: Ref<string>;

  /** Increase font size */
  increaseFontSize: () => void;
  /** Decrease font size */
  decreaseFontSize: () => void;
  /** Set font size directly */
  setFontSize: (size: number) => void;
  /** Set theme */
  setTheme: (theme: string) => void;
  /** Reset to defaults */
  reset: () => void;
}

// ===== CONSTANTS =====

const MIN_FONT_SIZE = 10;
const MAX_FONT_SIZE = 24;
const DEFAULT_FONT_SIZE = 14;
const DEFAULT_THEME = 'monokai';

// ===== COMPOSABLE =====

export const useEditorSettings = (): UseEditorSettingsReturn => {
  const fontSize = ref(DEFAULT_FONT_SIZE);
  const theme = ref(DEFAULT_THEME);

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
   * Set editor theme
   */
  const setTheme = (newTheme: string): void => {
    theme.value = newTheme;
  };

  /**
   * Reset to defaults
   */
  const reset = (): void => {
    fontSize.value = DEFAULT_FONT_SIZE;
    theme.value = DEFAULT_THEME;
  };

  return {
    fontSize,
    theme,
    increaseFontSize,
    decreaseFontSize,
    setFontSize,
    setTheme,
    reset,
  };
};
