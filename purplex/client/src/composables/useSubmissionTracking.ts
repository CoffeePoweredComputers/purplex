/**
 * useSubmissionTracking - Tracks in-flight submission state for multiple problems.
 *
 * Supports the multi-problem submission pattern where a user can:
 * - Submit problem A
 * - Navigate to problem B while A is still processing
 * - Both A and B submissions tracked independently
 *
 * This composable manages:
 * - Which problems have active submissions (submittingProblems Set)
 * - SSE connection handles for each submission (submissionConnections Map)
 * - Cleanup on unmount to prevent memory leaks
 */

import { onUnmounted, shallowRef } from 'vue';

// ===== TYPES =====

/**
 * SSE connection handle with disconnect capability.
 */
export interface SubmissionConnection {
  disconnect: () => void;
}

// ===== COMPOSABLE =====

export interface UseSubmissionTrackingReturn {
  /**
   * Check if a problem is currently being submitted.
   */
  isSubmitting: (problemSlug: string) => boolean;

  /**
   * Check if any problem is currently being submitted.
   */
  hasActiveSubmissions: () => boolean;

  /**
   * Mark a problem as being submitted.
   */
  addSubmission: (problemSlug: string) => void;

  /**
   * Mark a problem as no longer being submitted.
   */
  removeSubmission: (problemSlug: string) => void;

  /**
   * Store an SSE connection handle for cleanup.
   */
  setConnection: (problemSlug: string, connection: SubmissionConnection) => void;

  /**
   * Get and remove an SSE connection handle.
   */
  getAndRemoveConnection: (problemSlug: string) => SubmissionConnection | undefined;

  /**
   * Cancel all active submissions and clean up connections.
   * Called automatically on unmount, but can be called manually.
   */
  cancelAll: () => void;

  /**
   * Get the raw Set of submitting problems (for reactive binding).
   * Use isSubmitting() for checking specific problems.
   */
  getSubmittingSet: () => Set<string>;
}

/**
 * Creates a submission tracking manager.
 *
 * @returns Submission tracking methods
 *
 * @example
 * ```typescript
 * const {
 *   isSubmitting,
 *   addSubmission,
 *   removeSubmission,
 *   setConnection,
 *   getAndRemoveConnection
 * } = useSubmissionTracking();
 *
 * // Start submission
 * addSubmission('two-sum');
 *
 * // Store SSE connection for cleanup
 * const disconnect = await sseService.connectToTask(...);
 * setConnection('two-sum', { disconnect });
 *
 * // Check if submitting
 * if (isSubmitting('two-sum')) { ... }
 *
 * // On completion
 * removeSubmission('two-sum');
 * const conn = getAndRemoveConnection('two-sum');
 * conn?.disconnect();
 * ```
 */
export const useSubmissionTracking = (): UseSubmissionTrackingReturn => {
  // Track which problems have active submissions
  // Using shallowRef with Set replacement pattern for Vue reactivity
  const submittingProblems = shallowRef<Set<string>>(new Set());

  // Track SSE connections per problem for cleanup
  const submissionConnections = shallowRef<Map<string, SubmissionConnection>>(new Map());

  /**
   * Check if a problem is currently being submitted.
   */
  const isSubmitting = (problemSlug: string): boolean => {
    return submittingProblems.value.has(problemSlug);
  };

  /**
   * Check if any problem is currently being submitted.
   */
  const hasActiveSubmissions = (): boolean => {
    return submittingProblems.value.size > 0;
  };

  /**
   * Mark a problem as being submitted.
   * Replaces the Set to trigger Vue reactivity.
   */
  const addSubmission = (problemSlug: string): void => {
    const newSet = new Set(submittingProblems.value);
    newSet.add(problemSlug);
    submittingProblems.value = newSet;
  };

  /**
   * Mark a problem as no longer being submitted.
   * Replaces the Set to trigger Vue reactivity.
   */
  const removeSubmission = (problemSlug: string): void => {
    const newSet = new Set(submittingProblems.value);
    newSet.delete(problemSlug);
    submittingProblems.value = newSet;
  };

  /**
   * Store an SSE connection handle for later cleanup.
   */
  const setConnection = (problemSlug: string, connection: SubmissionConnection): void => {
    submissionConnections.value.set(problemSlug, connection);
  };

  /**
   * Get and remove an SSE connection handle.
   * Returns undefined if not found.
   */
  const getAndRemoveConnection = (problemSlug: string): SubmissionConnection | undefined => {
    const connection = submissionConnections.value.get(problemSlug);
    if (connection) {
      submissionConnections.value.delete(problemSlug);
    }
    return connection;
  };

  /**
   * Cancel all active submissions and clean up connections.
   */
  const cancelAll = (): void => {
    // Disconnect all active SSE connections
    for (const [, connection] of submissionConnections.value) {
      connection.disconnect();
    }
    submissionConnections.value.clear();

    // Clear submitting set
    submittingProblems.value = new Set();
  };

  /**
   * Get the raw submitting Set for reactive template bindings.
   */
  const getSubmittingSet = (): Set<string> => {
    return submittingProblems.value;
  };

  // Clean up on unmount to prevent memory leaks
  onUnmounted(() => {
    cancelAll();
  });

  return {
    isSubmitting,
    hasActiveSubmissions,
    addSubmission,
    removeSubmission,
    setConnection,
    getAndRemoveConnection,
    cancelAll,
    getSubmittingSet,
  };
};
