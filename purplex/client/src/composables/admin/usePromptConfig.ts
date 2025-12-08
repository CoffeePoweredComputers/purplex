/**
 * usePromptConfig - Manages prompt (image-based EiPL) configuration.
 *
 * This composable handles the configuration for prompt-type problems:
 * - Image URL
 * - Alt text for accessibility
 */

import { computed, type ComputedRef, type DeepReadonly, reactive, readonly } from 'vue';

// ===== TYPES =====

export interface PromptConfig {
  image_url: string;
  image_alt_text: string;
}

export interface UsePromptConfigReturn {
  /** Readonly prompt config */
  config: DeepReadonly<PromptConfig>;
  /** Image URL */
  imageUrl: ComputedRef<string>;
  /** Alt text */
  altText: ComputedRef<string>;
  /** Whether config has an image URL */
  hasImage: ComputedRef<boolean>;
  /** Whether the image URL is valid */
  isValidUrl: ComputedRef<boolean>;

  /** Set image URL */
  setImageUrl: (url: string) => void;
  /** Set alt text */
  setAltText: (text: string) => void;
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
    image_url: '',
    image_alt_text: '',
  });

  // ===== Computed =====

  const imageUrl = computed(() => state.image_url);
  const altText = computed(() => state.image_alt_text);

  const hasImage = computed(() => state.image_url.trim().length > 0);

  const isValidUrl = computed(() => {
    if (!state.image_url.trim()) {return true;} // Empty is valid
    try {
      new URL(state.image_url);
      return true;
    } catch {
      return false;
    }
  });

  // ===== Methods =====

  const setImageUrl = (url: string): void => {
    state.image_url = url;
  };

  const setAltText = (text: string): void => {
    state.image_alt_text = text;
  };

  const loadConfig = (config: PromptConfig | null | undefined): void => {
    if (!config) {
      reset();
      return;
    }

    state.image_url = config.image_url || '';
    state.image_alt_text = config.image_alt_text || '';
  };

  const getConfigForApi = (): PromptConfig => {
    return {
      image_url: state.image_url.trim(),
      image_alt_text: state.image_alt_text.trim(),
    };
  };

  const reset = (): void => {
    state.image_url = '';
    state.image_alt_text = '';
  };

  return {
    config: readonly(state),
    imageUrl,
    altText,
    hasImage,
    isValidUrl,
    setImageUrl,
    setAltText,
    loadConfig,
    getConfigForApi,
    reset,
  };
};
