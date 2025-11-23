import axios from 'axios';
import { log } from '../utils/logger';
import type { BaseSubmission, CodeVariation, SubmissionDetailed, SubmissionHistoryResponse, SubmissionTestResult } from '../types';

// ===== SUBMISSION TYPES =====

export interface SubmissionSummary {
  problem_slug: string;
  problem_title: string;
  problem_set_slug: string;
  problem_set_title: string;
  best_score: number;
  total_attempts: number;
  last_attempt: string;
  completed: boolean;
}

// Re-export submission types for convenience
export type { BaseSubmission, SubmissionDetailed, CodeVariation, SubmissionTestResult };

export interface ProblemSetProgress {
  slug: string;
  title: string;
  completed_problems: number;
  total_problems: number;
  average_score: number;
  percentage: number;
  last_activity: string | null;
}

export interface SubmissionRequest {
  problem_slug: string;
  problem_set_slug: string;
  user_code: string;
  prompt?: string;
  time_spent?: number;
  course_id?: string;
  activated_hints?: Array<{
    hint_id: number;
    hint_type: string;
    trigger_type?: string;
    duration_seconds?: number;
  }>;
}

export interface SubmissionResponse {
  task_id: string;
  status: 'processing';
  stream_url: string;
  message: string;
}

export interface TestSolutionResponse {
  task_id: string;
  status: 'processing';
  stream_url: string;
  message: string;
}

export interface EiPLSubmissionRequest {
  problem_slug: string;
  problem_set_slug?: string;
  activated_hints?: Array<{
    hint_id: number;
    hint_type: string;
    trigger_type?: string;
    duration_seconds?: number;
  }>;
  user_prompt: string;
  course_id?: string;
}

export interface EiPLSubmissionResponse {
  request_id: string;
  generation_task_id?: string;
  segmentation_task_id?: string;
  status: string;
  stream_url: string;
  message?: string;
}


// ===== SUBMISSION SERVICE =====

class SubmissionService {
  private baseURL = '/api';

  /**
   * Get all user progress summary
   */
  async getSubmissionsSummary(): Promise<SubmissionSummary[]> {
    try {
      const response = await axios.get(`${this.baseURL}/progress/`);
      return response.data;
    } catch (error) {
      log.error('Failed to fetch progress summary', error);
      throw error;
    }
  }

  /**
   * Get progress for all problem sets
   * Note: This endpoint might not exist in backend - consider removing
   */
  async getProblemSetsProgress(): Promise<ProblemSetProgress[]> {
    try {
      // TODO: Verify if this endpoint exists or if we should use /api/progress/ instead
      const response = await axios.get(`${this.baseURL}/progress/`);
      return response.data;
    } catch (error) {
      log.error('Failed to fetch problem sets progress', error);
      throw error;
    }
  }

  /**
   * Get progress for a specific problem set
   */
  async getProblemSetProgress(problemSetSlug: string): Promise<ProblemSetProgress> {
    try {
      const response = await axios.get(`${this.baseURL}/problem-sets/${problemSetSlug}/progress/`);
      return response.data;
    } catch (error) {
      log.error('Failed to fetch progress for problem set', { problemSetSlug, error });
      throw error;
    }
  }

  /**
   * Submit an EiPL (Explain in Plain Language) problem solution
   * This triggers async processing with Celery
   */
  async submitEiPL(data: EiPLSubmissionRequest): Promise<EiPLSubmissionResponse> {
    try {
      log.info('Submitting EiPL solution', { problemSlug: data.problem_slug });
      const response = await axios.post(`${this.baseURL}/submit-eipl/`, data);
      log.info('EiPL submission successful', { requestId: response.data.request_id });
      return response.data;
    } catch (error: any) {
      log.error('Failed to submit EiPL solution', error);
      throw {
        error: error.response?.data?.error || 'Failed to submit EiPL solution',
        status: error.response?.status || 500
      };
    }
  }


  /**
   * Get submissions/progress for a specific problem
   */
  async getProblemSubmissions(problemSlug: string): Promise<SubmissionSummary[]> {
    try {
      const response = await axios.get(`${this.baseURL}/progress/${problemSlug}/`);
      return response.data;
    } catch (error) {
      log.error('Failed to fetch submissions for problem', { problemSlug, error });
      throw error;
    }
  }

  /**
   * Calculate progress percentage for a problem set based on submissions
   */
  calculateProgressPercentage(completedProblems: number, totalProblems: number): number {
    if (totalProblems === 0) {return 0;}
    return Math.round((completedProblems / totalProblems) * 100);
  }

  /**
   * Get user's best score for a specific problem
   */
  async getProblemBestScore(problemSlug: string): Promise<number> {
    try {
      const submissions = await this.getProblemSubmissions(problemSlug);
      if (submissions.length === 0) {return 0;}
      
      const bestSubmission = submissions.reduce((best, current) => 
        current.best_score > best.best_score ? current : best
      );
      
      return bestSubmission.best_score;
    } catch (error) {
      log.error('Failed to get best score for problem', { problemSlug, error });
      return 0;
    }
  }

  /**
   * Check if a problem is completed (score >= 80% or configurable threshold)
   */
  isProblemCompleted(score: number, threshold: number = 100): boolean {
    return score >= threshold;
  }

  /**
   * Format submission data for UI display
   */
  formatSubmissionForDisplay(submission: SubmissionSummary) {
    return {
      ...submission,
      completion_status: this.isProblemCompleted(submission.best_score) ? 'completed' : 'in_progress',
      last_activity: submission.last_attempt ? new Date(submission.last_attempt).toLocaleDateString() : null,
      progress_text: `${submission.best_score}% (${submission.total_attempts} attempts)`
    };
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
      const params: any = {};

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
    } catch (error: any) {
      log.error('Failed to fetch submission history', {
        problemSlug,
        error,
        response: error.response?.data,
        status: error.response?.status
      });
      throw error;
    }
  }

  /**
   * Get the primary code variation (first variation)
   */
  getPrimaryCode(submission: BaseSubmission): string {
    if (submission.code_variations && Array.isArray(submission.code_variations) && submission.code_variations.length > 0) {
      const firstVariation = submission.code_variations[0];
      if (typeof firstVariation === 'string') {
        return firstVariation;
      }
      if (typeof firstVariation === 'object' && firstVariation.code) {
        return firstVariation.code;
      }
    }
    
    return '';
  }

  /**
   * Calculate success rate for code variations
   */
  calculateSuccessRate(submission: BaseSubmission): number {
    const passing = submission.passing_variations || 0;
    const total = submission.total_variations || 0;
    
    if (total === 0) {return 0;}
    return Math.round((passing / total) * 100);
  }

  /**
   * Get formatted test results summary
   */
  getTestResultsSummary(submission: BaseSubmission): string {
    if (!submission.test_results || !Array.isArray(submission.test_results)) {
      return 'No test results available';
    }

    const passed = submission.test_results.filter(r => r.isSuccessful).length;
    const total = submission.test_results.length;
    const percentage = total > 0 ? Math.round((passed / total) * 100) : 0;
    
    return `${passed}/${total} tests passed (${percentage}%)`;
  }
}

// Export singleton instance
export const submissionService = new SubmissionService();
export default submissionService;