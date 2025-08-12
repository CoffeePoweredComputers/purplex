/**
 * Vue composable for clean EiPL submissions.
 * 
 * Simple, reactive interface for the new pipeline.
 */

import { ref, reactive, onUnmounted } from 'vue';
import cleanSubmissionService, { 
  EiPLSubmissionRequest,
  TaskStatus 
} from '@/services/cleanSubmissionService';

export interface SubmissionState {
  isSubmitting: boolean;
  taskId: string | null;
  status: string;
  progress: {
    current: number;
    total: number;
    percentage: number;
    message: string;
  } | null;
  result: any | null;
  error: string | null;
}

export function useCleanSubmission() {
  const state = reactive<SubmissionState>({
    isSubmitting: false,
    taskId: null,
    status: 'idle',
    progress: null,
    result: null,
    error: null
  });

  let eventSource: EventSource | null = null;

  /**
   * Submit an EiPL solution.
   */
  const submit = async (data: EiPLSubmissionRequest) => {
    // Reset state
    state.isSubmitting = true;
    state.taskId = null;
    state.status = 'submitting';
    state.progress = null;
    state.result = null;
    state.error = null;

    try {
      // Submit the task
      const response = await cleanSubmissionService.submitEiPL(data);
      state.taskId = response.task_id;
      state.status = 'processing';

      // Start streaming updates
      eventSource = cleanSubmissionService.streamTaskUpdates(
        response.task_id,
        (event) => {
          handleEvent(event);
        },
        (error) => {
          state.error = error.message || 'Stream error occurred';
          state.status = 'error';
          state.isSubmitting = false;
        },
        () => {
          state.isSubmitting = false;
        }
      );

    } catch (error: any) {
      state.error = error.response?.data?.error || error.message || 'Submission failed';
      state.status = 'error';
      state.isSubmitting = false;
    }
  };

  /**
   * Handle SSE events.
   */
  const handleEvent = (event: any) => {
    switch (event.type) {
      case 'started':
        state.status = 'started';
        state.progress = {
          current: 0,
          total: 100,
          percentage: 0,
          message: event.message || 'Processing started...'
        };
        break;

      case 'progress':
        state.status = 'processing';
        if (event.progress) {
          state.progress = event.progress;
        }
        break;

      case 'completed':
        state.status = 'completed';
        state.result = event.result;
        state.progress = {
          current: 100,
          total: 100,
          percentage: 100,
          message: 'Completed!'
        };
        break;

      case 'failed':
        state.status = 'failed';
        state.error = event.error || event.message || 'Task failed';
        break;

      default:
        console.log('Unknown event type:', event.type, event);
    }
  };

  /**
   * Poll for task status (alternative to SSE).
   */
  const pollStatus = async (taskId: string) => {
    state.taskId = taskId;
    state.status = 'polling';

    const poll = async () => {
      try {
        const status = await cleanSubmissionService.getTaskStatus(taskId);
        
        state.status = status.status.toLowerCase();
        
        if (status.progress) {
          state.progress = status.progress;
        }

        if (status.ready) {
          if (status.successful) {
            state.result = status.result;
            state.status = 'completed';
          } else {
            state.error = status.error || 'Task failed';
            state.status = 'failed';
          }
          state.isSubmitting = false;
          return; // Stop polling
        }

        // Continue polling
        setTimeout(poll, 1000);
        
      } catch (error: any) {
        state.error = error.message || 'Failed to get status';
        state.status = 'error';
        state.isSubmitting = false;
      }
    };

    poll();
  };

  /**
   * Cancel the current submission.
   */
  const cancel = () => {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    state.isSubmitting = false;
    state.status = 'cancelled';
  };

  /**
   * Reset the state.
   */
  const reset = () => {
    cancel();
    state.taskId = null;
    state.status = 'idle';
    state.progress = null;
    state.result = null;
    state.error = null;
  };

  // Cleanup on unmount
  onUnmounted(() => {
    cancel();
  });

  return {
    state,
    submit,
    pollStatus,
    cancel,
    reset
  };
}