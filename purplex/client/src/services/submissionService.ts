import axios from 'axios';
import { log } from '../utils/logger';
import type { BaseSubmission, CodeVariation, SubmissionDetailed, SubmissionHistoryResponse, SubmissionTestResult } from '../types';

// Re-export submission types for convenience
export type { BaseSubmission, SubmissionDetailed, CodeVariation, SubmissionTestResult };

// ===== SUBMISSION TYPES =====

/**
 * Response from async submissions (EiPL, Prompt)
 * These return a task_id for polling/SSE
 */
export interface AsyncSubmissionResponse {
  task_id: string;
  request_id: string;
  status: 'processing';
  problem_type: string;
  stream_url: string;
  message: string;
}

/**
 * Response from sync submissions (MCQ)
 * These return the result immediately
 */
export interface SyncSubmissionResponse {
  status: 'complete';
  submission_id: string;
  problem_type: string;
  score: number;
  is_correct: boolean;
  completion_status: string;
  problem_slug: string;
  user_input: string;
  selected_option?: {
    id: string;
    text: string;
  };
  correct_option?: {
    id: string;
    text: string;
    explanation: string;
  };
  result?: Record<string, unknown>;
}

/**
 * Union type for all submission responses
 */
export type SubmissionResponse = AsyncSubmissionResponse | SyncSubmissionResponse;

/**
 * Type guard to check if response is synchronous (complete)
 */
export function isSyncResponse(response: SubmissionResponse): response is SyncSubmissionResponse {
  return response.status === 'complete';
}

/**
 * Type guard to check if response is asynchronous (processing)
 */
export function isAsyncResponse(response: SubmissionResponse): response is AsyncSubmissionResponse {
  return response.status === 'processing';
}

export interface ActivitySubmissionRequest {
  problem_slug: string;
  raw_input: string;
  problem_set_slug?: string;
  course_id?: string;
  activated_hints?: Array<{
    hint_type: string;
    trigger_type?: string;
    hint_id?: number;  // Optional - backend looks up by hint_type
    duration_seconds?: number;
  }>;
}

// ===== SUBMISSION SERVICE =====

class SubmissionService {
  private baseURL = '/api';

  /**
   * Submit an activity problem solution (generic endpoint for all activity types)
   *
   * Returns either:
   * - SyncSubmissionResponse: For instant results (MCQ) - status='complete'
   * - AsyncSubmissionResponse: For background processing (EiPL, Prompt) - status='processing'
   *
   * Use isSyncResponse() / isAsyncResponse() type guards to discriminate.
   */
  async submitActivity(data: ActivitySubmissionRequest): Promise<SubmissionResponse> {
    try {
      log.info('Submitting activity solution', { problemSlug: data.problem_slug });
      const response = await axios.post(`${this.baseURL}/submit/`, data);

      if (response.data.status === 'complete') {
        log.info('Sync submission complete', {
          submissionId: response.data.submission_id,
          score: response.data.score
        });
      } else {
        log.info('Async submission started', { taskId: response.data.task_id });
      }

      return response.data;
    } catch (error: unknown) {
      log.error('Failed to submit activity solution', error);
      const axiosError = error as { response?: { data?: { error?: string }; status?: number } };
      throw {
        error: axiosError.response?.data?.error || 'Failed to submit activity solution',
        status: axiosError.response?.status || 500
      };
    }
  }

  /**
   * Get submission history for a specific problem
   * Fetches all attempts for the current user
   */
  async getSubmissionHistory(
    problemSlug: string,
    problemSetSlug?: string,
    courseId?: string,
    limit?: number
  ): Promise<SubmissionHistoryResponse> {
    try {
      const params: Record<string, string | number> = {};

      if (problemSetSlug) {
        params.problem_set_slug = problemSetSlug;
      }
      if (courseId) {
        params.course_id = courseId;
      }
      if (limit) {
        params.limit = limit;
      }

      const url = `${this.baseURL}/submissions/history/${problemSlug}/`;

      const response = await axios.get(url, { params });

      log.info('Fetched submission history', {
        problemSlug,
        totalAttempts: response.data.total_attempts
      });

      return response.data;
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: unknown; status?: number } };
      log.error('Failed to fetch submission history', {
        problemSlug,
        error,
        response: axiosError.response?.data,
        status: axiosError.response?.status
      });
      throw error;
    }
  }
}

// Export singleton instance
export const submissionService = new SubmissionService();
