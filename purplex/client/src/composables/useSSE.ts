/**
 * Server-Sent Events (SSE) composable for real-time task status updates.
 * 
 * This replaces the polling-based useTaskPolling composable with a more
 * efficient SSE-based approach that provides real-time updates with lower
 * server load and better user experience.
 */

import { ref, onUnmounted, Ref } from 'vue';
import { log } from '../utils/logger';
import { firebaseAuth } from '../firebaseConfig';
import { getIdToken } from 'firebase/auth';

export interface SSEOptions {
  onProgress?: (progress: { current: number; total: number; description: string }) => void;
  onError?: (error: any) => void;
  onTimeout?: () => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

export interface TaskResult {
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'retrying';
  result?: any;
  error?: string;
  progress?: {
    current: number;
    total: number;
    description: string;
  };
}

export function useSSE() {
  const isConnected = ref(false);
  const currentStatus = ref<TaskResult | null>(null);
  const error = ref<string | null>(null);
  
  let eventSource: EventSource | null = null;
  let reconnectCount = 0;
  let reconnectTimer: NodeJS.Timeout | null = null;

  /**
   * Connect to SSE endpoint for real-time task updates
   */
  const connectToTask = async (
    taskId: string,
    onComplete: (result: TaskResult) => void,
    options: SSEOptions = {}
  ) => {
    const {
      onProgress,
      onError,
      onTimeout,
      reconnectAttempts = 3,
      reconnectDelay = 2000
    } = options;

    // Clean up any existing connection
    disconnect();

    // Reset state
    isConnected.value = false;
    error.value = null;
    currentStatus.value = null;
    reconnectCount = 0;

    const connect = async () => {
      log.info('Connecting to SSE endpoint', { taskId });

      // Get Firebase token for authentication
      let url = `/api/tasks/${taskId}/stream/`;
      if (firebaseAuth.currentUser) {
        try {
          const token = await getIdToken(firebaseAuth.currentUser);
          url += `?token=${encodeURIComponent(token)}`;
        } catch (err) {
          log.error('Failed to get Firebase token for SSE', err);
        }
      }
      
      // Create SSE connection with token in query parameter
      eventSource = new EventSource(url, { withCredentials: true } as any);

      // Connection opened
      eventSource.onopen = () => {
        log.info('SSE connection established', { taskId });
        isConnected.value = true;
        reconnectCount = 0; // Reset reconnect count on successful connection
      };

      // Handle messages (default events)
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          log.debug('SSE message received', { taskId, data });
        } catch (err: any) {
          log.error('Error parsing SSE message', { taskId, error: err });
        }
      };

      // Handle named events
      eventSource.addEventListener('connected', (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        log.debug('SSE connected event', { taskId, data });
        isConnected.value = true;
      });

      eventSource.addEventListener('subscribed', (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        log.debug('SSE subscribed event', { taskId, data });
      });

      eventSource.addEventListener('update', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          log.debug('SSE update event', { taskId, data });

          // Update current status
          currentStatus.value = {
            status: data.status || 'processing',
            result: data.result,
            error: data.error,
            progress: data.progress
          };

          // Handle progress updates
          if (data.progress && onProgress) {
            onProgress({
              current: data.progress * 100,
              total: 100,
              description: data.message || 'Processing...'
            });
          }
        } catch (err: any) {
          log.error('Error parsing SSE update', { taskId, error: err });
        }
      });

      eventSource.addEventListener('completed', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          log.info('Task completed successfully', { taskId, data });
          
          onComplete({
            status: 'completed',
            result: data.result
          });
          disconnect();
        } catch (err: any) {
          log.error('Error parsing SSE completed event', { taskId, error: err });
        }
      });

      eventSource.addEventListener('failed', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          const errorMsg = data.error || 'Task failed';
          log.error('Task failed', { taskId, error: errorMsg });
          
          error.value = errorMsg;
          if (onError) {
            onError({ error: errorMsg, status: 'failed' });
          }
          disconnect();
        } catch (err: any) {
          log.error('Error parsing SSE failed event', { taskId, error: err });
        }
      });

      eventSource.addEventListener('error', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          log.error('SSE error event', { taskId, data });
          
          if (onError) {
            onError(data);
          }
        } catch (err: any) {
          log.error('Error parsing SSE error event', { taskId, error: err });
        }
      });

      // Handle errors
      eventSource.onerror = (err) => {
        // Check if we already completed successfully
        if (currentStatus.value?.status === 'completed' || currentStatus.value?.status === 'failed') {
          // Normal close after completion, not an error
          log.debug('SSE connection closed after task completion', { taskId });
          disconnect();
          return;
        }

        log.error('SSE connection error', { taskId, error: err });
        isConnected.value = false;

        if (eventSource?.readyState === EventSource.CLOSED) {
          // Connection closed, attempt reconnect
          if (reconnectCount < reconnectAttempts) {
            reconnectCount++;
            log.info(`Attempting reconnect ${reconnectCount}/${reconnectAttempts}`, { taskId });
            
            reconnectTimer = setTimeout(async () => {
              await connect();
            }, reconnectDelay * reconnectCount); // Exponential backoff
          } else {
            // Max reconnects reached
            const errorMsg = 'Connection lost, max reconnect attempts reached';
            log.error(errorMsg, { taskId });
            error.value = errorMsg;
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
  };

  /**
   * Connect to SSE endpoint for batch task updates
   */
  const connectToBatchTasks = async (
    taskIds: string[],
    onBatchComplete: (summary: any) => void,
    options: SSEOptions = {}
  ) => {
    const { onProgress, onError } = options;

    // Clean up any existing connection
    disconnect();

    // Reset state
    isConnected.value = false;
    error.value = null;
    const taskStatuses: Map<string, TaskResult> = new Map();

    log.info('Connecting to batch SSE endpoint', { taskCount: taskIds.length });

    // Create batch SSE connection with authentication
    let url = `/api/tasks/batch/stream/?task_ids=${taskIds.join(',')}`;
    if (firebaseAuth.currentUser) {
      try {
        const token = await getIdToken(firebaseAuth.currentUser);
        url += `&token=${encodeURIComponent(token)}`;
      } catch (err) {
        log.error('Failed to get Firebase token for batch SSE', err);
      }
    }
    eventSource = new EventSource(url, { withCredentials: true } as any);

    eventSource.onopen = () => {
      log.info('Batch SSE connection established');
      isConnected.value = true;
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'batch_complete') {
          log.info('All batch tasks completed', data.summary);
          onBatchComplete(data.summary);
          disconnect();
        } else if (data.task_id) {
          // Update individual task status
          taskStatuses.set(data.task_id, {
            status: data.status,
            result: data.result,
            error: data.error,
            progress: data.progress
          });

          if (data.progress && onProgress) {
            onProgress(data.progress);
          }
        }
      } catch (err: any) {
        log.error('Error parsing batch SSE message', err);
      }
    };

    eventSource.onerror = (err) => {
      log.error('Batch SSE connection error', err);
      isConnected.value = false;
      
      const errorMsg = 'Batch connection lost';
      error.value = errorMsg;
      if (onError) {
        onError({ error: errorMsg });
      }
      disconnect();
    };
  };

  /**
   * Connect to EiPL submission SSE stream
   */
  const connectToEiPLSubmission = async (
    requestId: string,
    onSuccess: (variations: string[], testResults: any[]) => void,
    options: SSEOptions = {}
  ) => {
    await connectToTask(
      requestId,
      (result) => {
        if (result.status === 'completed' && result.result) {
          // Check if this is the final submission task with test results
          const { variations, test_results, submission_id } = result.result;
          
          // Only call onSuccess when we have the final submission with test results
          if (submission_id && variations && test_results) {
            // This is the final submission result
            onSuccess(variations, test_results);
          } else if (result.result.status === 'testing') {
            // Generation complete, but testing still in progress
            log.debug('Variations generated, waiting for test results...', { requestId });
            // Don't disconnect - keep waiting for the final results
          } else if (!variations) {
            const errorMsg = result.result.error || 'No variations generated';
            log.error('EiPL submission failed', { requestId, error: errorMsg });
            if (options.onError) {
              options.onError({ error: errorMsg });
            }
          }
        }
      },
      options
    );
  };

  /**
   * Disconnect SSE connection
   */
  const disconnect = () => {
    if (eventSource) {
      log.debug('Closing SSE connection');
      eventSource.close();
      eventSource = null;
    }
    
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    
    isConnected.value = false;
  };

  // Clean up on component unmount
  onUnmounted(() => {
    disconnect();
  });

  return {
    isConnected,
    currentStatus,
    error,
    connectToTask,
    connectToBatchTasks,
    connectToEiPLSubmission,
    disconnect
  };
}

export default useSSE;