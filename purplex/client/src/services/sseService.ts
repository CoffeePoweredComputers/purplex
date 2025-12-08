/**
 * Server-Sent Events (SSE) service for real-time task status updates.
 *
 * Service pattern - no Vue dependencies. Can be called from anywhere.
 * Caller is responsible for cleanup via returned disconnect function.
 */

import { log } from '../utils/logger';
import { firebaseAuth } from '../firebaseConfig';
import type { UnifiedSubmissionResult } from '../types';

// Helper to extract error message from unknown error
function getErrorMessage(err: unknown): string {
  if (err instanceof Error) {return err.message;}
  if (typeof err === 'string') {return err;}
  return String(err);
}

export interface SSEErrorPayload {
  error: string;
  timeout?: boolean;
  connectionLost?: boolean;
  status?: string;
}

export interface SSEOptions {
  onProgress?: (progress: { current: number; total: number; description: string }) => void;
  onError?: (error: SSEErrorPayload) => void;
  onTimeout?: () => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

export interface TaskResult {
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'retrying';
  result?: UnifiedSubmissionResult | { error?: string };
  error?: string;
  progress?: {
    current: number;
    total: number;
    description: string;
  };
}

/**
 * SSE Service - manages Server-Sent Event connections for task updates.
 *
 * Usage:
 *   const disconnect = await sseService.connectToSubmission(taskId, onSuccess, options);
 *   // Later, when done:
 *   disconnect();
 */
class SSEService {
  // Track completed/failed tasks to prevent reconnection loops
  private completedTasks: Set<string> = new Set();

  /**
   * Get SSE session token from backend
   */
  private async getSSEToken(): Promise<string | null> {
    if (!firebaseAuth.currentUser) {
      return null;
    }

    try {
      const firebaseToken = await firebaseAuth.currentUser.getIdToken();
      const response = await fetch('/api/auth/sse-token/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${firebaseToken}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        return data.sse_token;
      } else {
        log.error('Failed to get SSE session token', response.status);
        return null;
      }
    } catch (err) {
      log.error('Failed to get SSE session token', err);
      return null;
    }
  }

  /**
   * Connect to SSE endpoint for real-time task updates.
   * Returns a disconnect function - caller must call it to clean up.
   */
  async connectToTask(
    taskId: string,
    onComplete: (result: TaskResult) => void,
    options: SSEOptions = {}
  ): Promise<() => void> {
    const {
      onProgress,
      onError,
      onTimeout,
      reconnectAttempts = 3,
      reconnectDelay = 2000
    } = options;

    // Clear any previous completion state for this task
    this.completedTasks.delete(taskId);

    let eventSource: EventSource | null = null;
    let reconnectCount = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let activityTimer: ReturnType<typeof setTimeout> | null = null;
    let _lastError: string | null = null;

    /**
     * Reset activity timeout timer
     */
    const resetActivityTimer = (maxIdleMs: number, onTimeoutCallback?: () => void) => {
      if (activityTimer) {
        clearTimeout(activityTimer);
        activityTimer = null;
      }

      if (onTimeoutCallback) {
        activityTimer = setTimeout(() => {
          log.warn('SSE activity timeout - no updates received', { maxIdleMs });
          onTimeoutCallback();
        }, maxIdleMs);
      }
    };

    /**
     * Disconnect and clean up
     */
    const disconnect = () => {
      if (eventSource) {
        log.debug('Closing SSE connection', { taskId });
        eventSource.close();
        eventSource = null;
      }

      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }

      if (activityTimer) {
        clearTimeout(activityTimer);
        activityTimer = null;
      }
    };

    /**
     * Internal connect function (for reconnection)
     */
    const connect = async () => {
      log.info('Connecting to SSE endpoint', { taskId });

      // Build URL with SSE token
      let url = `/api/tasks/${taskId}/stream/`;
      const sseToken = await this.getSSEToken();
      if (sseToken) {
        url += `?sse_token=${encodeURIComponent(sseToken)}`;
      }

      // EventSourceInit type doesn't include withCredentials in all TS versions
      // but browsers support it - cast to suppress the warning
      eventSource = new EventSource(url, { withCredentials: true } as EventSourceInit);

      // Connection opened
      eventSource.onopen = () => {
        log.info('SSE connection established', { taskId });
        reconnectCount = 0;

        // Start activity timeout (2 minutes max with no updates)
        const MAX_IDLE_TIME_MS = 2 * 60 * 1000;
        resetActivityTimer(MAX_IDLE_TIME_MS, () => {
          const timeoutMsg = 'No response from server after 2 minutes. The task may be stuck.';
          log.error(timeoutMsg, { taskId });
          _lastError = timeoutMsg;

          if (onTimeout) {
            onTimeout();
          } else if (onError) {
            onError({ error: timeoutMsg, timeout: true });
          }

          disconnect();
        });
      };

      // Handle default messages (no-op, we use named events)
      eventSource.onmessage = () => {};

      // Handle named events
      eventSource.addEventListener('connected', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          log.debug('SSE connected event', { taskId, data });
        } catch (err) {
          log.error('Error parsing SSE connected event', { taskId, error: getErrorMessage(err) });
        }
      });

      eventSource.addEventListener('subscribed', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          log.debug('SSE subscribed event', { taskId, data });
        } catch (err) {
          log.error('Error parsing SSE subscribed event', { taskId, error: getErrorMessage(err) });
        }
      });

      eventSource.addEventListener('update', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);

          // Reset activity timer
          const MAX_IDLE_TIME_MS = 2 * 60 * 1000;
          resetActivityTimer(MAX_IDLE_TIME_MS, () => {
            const timeoutMsg = 'No response from server after 2 minutes. The task may be stuck.';
            log.error(timeoutMsg, { taskId });
            _lastError = timeoutMsg;

            if (onTimeout) {
              onTimeout();
            } else if (onError) {
              onError({ error: timeoutMsg, timeout: true });
            }

            disconnect();
          });

          // Handle progress updates
          if (data.progress && onProgress) {
            onProgress({
              current: data.progress * 100,
              total: 100,
              description: data.message || 'Processing...'
            });
          }
        } catch (err) {
          log.error('Error parsing SSE update', { taskId, error: getErrorMessage(err) });
        }
      });

      eventSource.addEventListener('completed', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          log.info('Task completed successfully', { taskId, data });

          // Mark task as completed BEFORE disconnect to prevent reconnection
          this.completedTasks.add(taskId);

          onComplete({
            status: 'completed',
            result: data.result
          });
          disconnect();
        } catch (err) {
          log.error('Error parsing SSE completed event', { taskId, error: getErrorMessage(err) });
        }
      });

      eventSource.addEventListener('failed', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          const errorMsg = data.error || 'Task failed';
          log.error('Task failed', { taskId, error: errorMsg });

          // Mark task as completed (failed) BEFORE disconnect to prevent reconnection
          this.completedTasks.add(taskId);
          _lastError = errorMsg;

          if (onError) {
            onError({ error: errorMsg, status: 'failed' });
          }
          disconnect();
        } catch (err) {
          log.error('Error parsing SSE failed event', { taskId, error: getErrorMessage(err) });
        }
      });

      eventSource.addEventListener('error', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          log.error('SSE error event', { taskId, data });

          if (onError) {
            onError(data);
          }
        } catch (err) {
          log.error('Error parsing SSE error event', { taskId, error: getErrorMessage(err) });
        }
      });

      // Handle connection errors
      eventSource.onerror = () => {
        // Check if task already completed - don't reconnect
        if (this.completedTasks.has(taskId)) {
          log.debug('SSE connection closed after task completion', { taskId });
          disconnect();
          return;
        }

        log.error('SSE connection error', { taskId });

        if (eventSource?.readyState === EventSource.CLOSED) {
          // Connection closed, attempt reconnect
          if (reconnectCount < reconnectAttempts) {
            reconnectCount++;
            log.info(`Attempting reconnect ${reconnectCount}/${reconnectAttempts}`, { taskId });

            reconnectTimer = setTimeout(async () => {
              await connect();
            }, reconnectDelay * reconnectCount);
          } else {
            const errorMsg = 'Connection lost, max reconnect attempts reached';
            log.error(errorMsg, { taskId });
            _lastError = errorMsg;
            if (onError) {
              onError({ error: errorMsg, connectionLost: true });
            }
            disconnect();
          }
        }
      };
    };

    // Initial connection
    await connect();

    // Return disconnect function for caller to use
    return disconnect;
  }

  /**
   * Unified submission SSE handler for all activity types.
   * Returns a disconnect function.
   *
   * This method works with the unified backend completion event structure
   * that includes both common metadata and type-specific result data.
   */
  connectToSubmission(
    requestId: string,
    onSuccess: (result: UnifiedSubmissionResult) => void,
    options: SSEOptions = {}
  ): Promise<() => void> {
    return this.connectToTask(
      requestId,
      (taskResult) => {
        if (taskResult.status === 'completed' && taskResult.result) {
          const unified = taskResult.result as UnifiedSubmissionResult;

          if (unified.submission_id) {
            log.info('Submission completed', {
              requestId,
              problem_type: unified.problem_type,
              is_correct: unified.is_correct,
              score: unified.score
            });
            onSuccess(unified);
          } else {
            const errorMsg = taskResult.result.error || 'Submission failed';
            log.error('Submission failed', { requestId, error: errorMsg });
            if (options.onError) {
              options.onError({ error: errorMsg });
            }
          }
        }
      },
      options
    );
  }
}

// Export singleton instance
export const sseService = new SSEService();
