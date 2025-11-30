import axios from 'axios';
import { log } from '../utils/logger';
import type { BaseSubmission, CodeVariation, SubmissionDetailed, SubmissionHistoryResponse, SubmissionTestResult } from '../types';

// Re-export submission types for convenience
export type { BaseSubmission, SubmissionDetailed, CodeVariation, SubmissionTestResult };

// ===== SUBMISSION TYPES =====

export interface SubmissionResponse {
  task_id: string;
  status: 'processing';
  stream_url: string;
  message: string;
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
   * This triggers async processing with Celery
   */
  async submitActivity(data: ActivitySubmissionRequest): Promise<SubmissionResponse> {
    try {
      log.info('Submitting activity solution', { problemSlug: data.problem_slug });
      const response = await axios.post(`${this.baseURL}/submit/`, data);
      log.info('Activity submission successful', { taskId: response.data.task_id });
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
export default submissionService;
