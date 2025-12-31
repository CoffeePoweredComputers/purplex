/**
 * useUIState - Manages UI state for the admin problem editor.
 *
 * This composable handles loading states, errors, test results, and provides
 * a generic action executor with automatic loading/error handling.
 */

import { type DeepReadonly, reactive, readonly, type Ref, ref } from 'vue';
import type { TestExecutionResult } from '@/types';
import { useNotification } from '@/composables/useNotification';
import { log } from '@/utils/logger';

// ===== TYPES =====

export interface UIState {
  loading: boolean;
  error: string | null;
  testResults: TestExecutionResult | null;
}

export interface UseUIStateReturn {
  /** Readonly UI state */
  ui: DeepReadonly<UIState>;
  /** Set loading state */
  setLoading: (loading: boolean) => void;
  /** Set error message */
  setError: (error: string | null) => void;
  /** Clear error */
  clearError: () => void;
  /** Set test results */
  setTestResults: (results: TestExecutionResult | null) => void;
  /** Clear test results */
  clearTestResults: () => void;
  /** Execute an async action with automatic loading/error handling */
  executeAction: <T>(
    actionName: string,
    actionFn: () => Promise<T>,
    successMsg?: string | null
  ) => Promise<T | undefined>;
  /** Notification API reference */
  notify: Ref<ReturnType<typeof useNotification>['notify'] | null>;
}

// ===== INITIAL STATE =====

const createInitialState = (): UIState => ({
  loading: false,
  error: null,
  testResults: null,
});

// ===== COMPOSABLE =====

export const useUIState = (): UseUIStateReturn => {
  const state = reactive<UIState>(createInitialState());
  const { notify: notifyApi } = useNotification();
  const notify = ref<typeof notifyApi | null>(notifyApi);

  /**
   * Set loading state
   */
  const setLoading = (loading: boolean): void => {
    state.loading = loading;
  };

  /**
   * Set error message
   */
  const setError = (error: string | null): void => {
    state.error = error;
  };

  /**
   * Clear error
   */
  const clearError = (): void => {
    state.error = null;
  };

  /**
   * Set test results
   */
  const setTestResults = (results: TestExecutionResult | null): void => {
    state.testResults = results;
  };

  /**
   * Clear test results
   */
  const clearTestResults = (): void => {
    state.testResults = null;
  };

  /**
   * Execute an async action with automatic loading/error handling.
   *
   * @param actionName - Name of the action (for logging)
   * @param actionFn - Async function to execute
   * @param successMsg - Optional success message to show
   * @returns The result of actionFn, or undefined if it failed
   */
  const executeAction = async <T>(
    actionName: string,
    actionFn: () => Promise<T>,
    successMsg: string | null = null
  ): Promise<T | undefined> => {
    log.debug('Execute action started', {
      actionName,
      currentLoading: state.loading,
    });

    if (state.loading) {
      log.debug('Already loading, skipping action');
      return undefined;
    }

    state.loading = true;
    state.error = null;
    log.debug('Set loading to true');

    try {
      log.debug('Running action', { actionName });
      const result = await actionFn();
      log.info('Action completed successfully', { actionName });

      if (successMsg && notify.value) {
        log.debug('Showing success toast', { successMsg });
        notify.value.success(successMsg);
      }

      return result;
    } catch (error: unknown) {
      log.error('Action failed', { actionName, error });

      // Extract error message
      let errorMsg = `Failed to ${actionName}`;
      const err = error as Record<string, unknown>;

      if (err.error) {
        errorMsg = String(err.error);
      } else if (err.message) {
        errorMsg = String(err.message);
      } else if (err.response && typeof err.response === 'object') {
        const response = err.response as Record<string, unknown>;
        if (response.data && typeof response.data === 'object') {
          const data = response.data as Record<string, unknown>;
          errorMsg = String(data.error || data.message || errorMsg);
        }
      }

      // Add status code if available
      if (err.status) {
        errorMsg += ` (Status: ${err.status})`;
      }

      state.error = errorMsg;
      log.info('Showing error toast', { errorMsg });

      if (notify.value) {
        notify.value.error(errorMsg);
      }

      throw error;
    } finally {
      state.loading = false;
      log.debug('Set loading to false');
    }
  };

  return {
    ui: readonly(state),
    setLoading,
    setError,
    clearError,
    setTestResults,
    clearTestResults,
    executeAction,
    notify,
  };
};
