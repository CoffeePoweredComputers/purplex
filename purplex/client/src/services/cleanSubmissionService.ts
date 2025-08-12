/**
 * Clean submission service for the redesigned pipeline.
 * 
 * This replaces the complex submission logic with simple,
 * maintainable API calls.
 */

import axios from 'axios';

export interface EiPLSubmissionRequest {
  problem_slug: string;
  user_prompt: string;
  problem_set_slug?: string;
  course_id?: string;
}

export interface EiPLSubmissionResponse {
  task_id: string;
  status: string;
  message: string;
  status_url: string;
  stream_url: string;
}

export interface TaskStatus {
  task_id: string;
  status: string;
  ready: boolean;
  successful?: boolean;
  result?: any;
  error?: string;
  progress?: {
    current: number;
    total: number;
    percentage: number;
    message: string;
  };
}

class CleanSubmissionService {
  private baseURL = '/api/clean';

  /**
   * Submit an EiPL problem solution.
   */
  async submitEiPL(data: EiPLSubmissionRequest): Promise<EiPLSubmissionResponse> {
    const response = await axios.post<EiPLSubmissionResponse>(
      `${this.baseURL}/submit/eipl/`,
      data
    );
    return response.data;
  }

  /**
   * Get the status of a task.
   */
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await axios.get<TaskStatus>(
      `${this.baseURL}/tasks/${taskId}/status/`
    );
    return response.data;
  }

  /**
   * Stream task updates via Server-Sent Events.
   */
  streamTaskUpdates(
    taskId: string,
    onMessage: (event: any) => void,
    onError?: (error: any) => void,
    onComplete?: () => void
  ): EventSource {
    const eventSource = new EventSource(
      `${this.baseURL}/tasks/${taskId}/stream/`
    );

    // Handle different event types
    eventSource.addEventListener('started', (event) => {
      const data = JSON.parse(event.data);
      onMessage({ type: 'started', ...data });
    });

    eventSource.addEventListener('progress', (event) => {
      const data = JSON.parse(event.data);
      onMessage({ type: 'progress', ...data });
    });

    eventSource.addEventListener('completed', (event) => {
      const data = JSON.parse(event.data);
      onMessage({ type: 'completed', ...data });
      if (onComplete) onComplete();
      eventSource.close();
    });

    eventSource.addEventListener('failed', (event) => {
      const data = JSON.parse(event.data);
      onMessage({ type: 'failed', ...data });
      if (onError) onError(data);
      eventSource.close();
    });

    eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      if (onError) onError(error);
      eventSource.close();
    };

    return eventSource;
  }

  /**
   * Submit and track an EiPL submission.
   * 
   * This combines submission and streaming for a complete flow.
   */
  async submitAndTrack(
    data: EiPLSubmissionRequest,
    onProgress: (update: any) => void
  ): Promise<any> {
    // Submit the task
    const submission = await this.submitEiPL(data);
    
    return new Promise((resolve, reject) => {
      // Stream updates
      const eventSource = this.streamTaskUpdates(
        submission.task_id,
        (event) => {
          onProgress(event);
          
          // Resolve when completed
          if (event.type === 'completed') {
            resolve(event.result);
          }
        },
        (error) => {
          reject(error);
        }
      );

      // Cleanup on unmount
      return () => eventSource.close();
    });
  }
}

export default new CleanSubmissionService();