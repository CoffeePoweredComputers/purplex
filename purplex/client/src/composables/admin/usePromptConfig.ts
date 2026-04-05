/**
 * usePromptConfig - Manages prompt problem display configuration.
 *
 * This composable handles the configuration for prompt-type problems:
 * - Display mode (image, terminal, function_table)
 * - Image URL and alt text (image mode)
 * - Terminal interactions (terminal mode)
 * - Function call table (function_table mode)
 */

import { computed, type ComputedRef, type DeepReadonly, reactive, readonly } from 'vue';
import type { FunctionCall, TerminalRun } from '@/types';

// ===== TYPES =====

export type DisplayMode = 'image' | 'terminal' | 'function_table';

export interface PromptConfig {
  display_mode: DisplayMode;
  display_data: Record<string, unknown>;
  image_url: string;
  image_alt_text: string;
}

export interface UsePromptConfigReturn {
  /** Readonly prompt config */
  config: DeepReadonly<PromptConfig>;
  /** Display mode */
  displayMode: ComputedRef<DisplayMode>;
  /** Image URL */
  imageUrl: ComputedRef<string>;
  /** Alt text */
  altText: ComputedRef<string>;
  /** Whether config has an image URL */
  hasImage: ComputedRef<boolean>;
  /** Whether the image URL is valid */
  isValidUrl: ComputedRef<boolean>;
  /** Mode checks */
  isImageMode: ComputedRef<boolean>;
  isTerminalMode: ComputedRef<boolean>;
  isFunctionTableMode: ComputedRef<boolean>;
  /** Terminal runs */
  terminalRuns: ComputedRef<TerminalRun[]>;
  /** Function calls */
  functionCalls: ComputedRef<FunctionCall[]>;
  /** Whether mode-specific data is present */
  hasRequiredData: ComputedRef<boolean>;

  /** Set display mode */
  setDisplayMode: (mode: DisplayMode) => void;
  /** Set image URL */
  setImageUrl: (url: string) => void;
  /** Set alt text */
  setAltText: (text: string) => void;
  /** Set terminal runs */
  setTerminalRuns: (runs: TerminalRun[]) => void;
  /** Set function calls */
  setFunctionCalls: (calls: FunctionCall[]) => void;
  /** Load config from problem data */
  loadConfig: (config: PromptConfig | null | undefined) => void;
  /** Get config for API */
  getConfigForApi: () => PromptConfig;
  /** Reset to initial state */
  reset: () => void;
}

// ===== COMPOSABLE =====

export const usePromptConfig = (): UsePromptConfigReturn => {
  const state = reactive<PromptConfig>({
    display_mode: 'image',
    display_data: {},
    image_url: '',
    image_alt_text: '',
  });

  // ===== Computed =====

  const displayMode = computed(() => state.display_mode);
  const imageUrl = computed(() => state.image_url);
  const altText = computed(() => state.image_alt_text);

  const isImageMode = computed(() => state.display_mode === 'image');
  const isTerminalMode = computed(() => state.display_mode === 'terminal');
  const isFunctionTableMode = computed(() => state.display_mode === 'function_table');

  const hasImage = computed(() => state.image_url.trim().length > 0);

  const isValidUrl = computed(() => {
    if (!isImageMode.value) {return true;} // Only validate in image mode
    if (!state.image_url.trim()) {return true;} // Empty is valid (caught by hasRequiredData)
    try {
      new URL(state.image_url);
      return true;
    } catch {
      return false;
    }
  });

  const terminalRuns = computed<TerminalRun[]>(() => {
    const data = state.display_data as { runs?: TerminalRun[] };
    return data?.runs ?? [];
  });

  const functionCalls = computed<FunctionCall[]>(() => {
    const data = state.display_data as { calls?: FunctionCall[] };
    return data?.calls ?? [];
  });

  const hasRequiredData = computed(() => {
    if (isImageMode.value) {
      return hasImage.value && isValidUrl.value;
    }
    if (isTerminalMode.value) {
      return terminalRuns.value.length > 0 &&
        terminalRuns.value.every(r =>
          r.interactions &&
          r.interactions.length > 0 &&
          r.interactions.every(
            i => typeof i.text === 'string' && i.text.trim().length > 0,
          ),
        );
    }
    if (isFunctionTableMode.value) {
      return functionCalls.value.length > 0;
    }
    return false;
  });

  // ===== Methods =====

  const setDisplayMode = (mode: DisplayMode): void => {
    state.display_mode = mode;
    // Reset display_data when switching modes
    if (mode === 'terminal' && !terminalRuns.value.length) {
      state.display_data = {
        schema_version: 1,
        runs: [{ interactions: [{ type: 'output', text: '' }] }],
      };
    } else if (mode === 'function_table' && !functionCalls.value.length) {
      state.display_data = {
        schema_version: 1,
        calls: [{ args: [], return_value: '' }],
      };
    } else if (mode === 'image') {
      state.display_data = {};
    }
  };

  const setImageUrl = (url: string): void => {
    state.image_url = url;
  };

  const setAltText = (text: string): void => {
    state.image_alt_text = text;
  };

  const setTerminalRuns = (runs: TerminalRun[]): void => {
    state.display_data = { schema_version: 1, runs };
  };

  const setFunctionCalls = (calls: FunctionCall[]): void => {
    state.display_data = { schema_version: 1, calls };
  };

  const loadConfig = (config: PromptConfig | null | undefined): void => {
    if (!config) {
      reset();
      return;
    }

    state.display_mode = config.display_mode || 'image';
    state.display_data = config.display_data || {};
    state.image_url = config.image_url || '';
    state.image_alt_text = config.image_alt_text || '';
  };

  const getConfigForApi = (): PromptConfig => {
    return {
      display_mode: state.display_mode,
      display_data: state.display_mode === 'image' ? {} : state.display_data,
      image_url: state.image_url.trim(),
      image_alt_text: state.image_alt_text.trim(),
    };
  };

  const reset = (): void => {
    state.display_mode = 'image';
    state.display_data = {};
    state.image_url = '';
    state.image_alt_text = '';
  };

  return {
    config: readonly(state),
    displayMode,
    imageUrl,
    altText,
    hasImage,
    isValidUrl,
    isImageMode,
    isTerminalMode,
    isFunctionTableMode,
    terminalRuns,
    functionCalls,
    hasRequiredData,
    setDisplayMode,
    setImageUrl,
    setAltText,
    setTerminalRuns,
    setFunctionCalls,
    loadConfig,
    getConfigForApi,
    reset,
  };
};
