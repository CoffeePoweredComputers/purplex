import axios from 'axios';
import type { BaseSubmission, SubmissionDetailed, CodeVariation, TestResult } from '../types';

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
export type { BaseSubmission, SubmissionDetailed, CodeVariation, TestResult };

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
  user_code: string;
  prompt: string;
  time_spent?: number;
}

export interface SubmissionResponse {
  success: boolean;
  score: number;
  total_tests: number;
  passed_tests: number;
  execution_time: number;
  submission_id: number;
  message: string;
}

// ===== SUBMISSION SERVICE =====

class SubmissionService {
  private baseURL = '/api';

  /**
   * Get all user submissions summary
   */
  async getSubmissionsSummary(): Promise<SubmissionSummary[]> {
    try {
      const response = await axios.get(`${this.baseURL}/submissions/summary/`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch submissions summary:', error);
      throw error;
    }
  }

  /**
   * Get progress for all problem sets
   */
  async getProblemSetsProgress(): Promise<ProblemSetProgress[]> {
    try {
      const response = await axios.get(`${this.baseURL}/submissions/problem-sets-progress/`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch problem sets progress:', error);
      throw error;
    }
  }

  /**
   * Get progress for a specific problem set
   */
  async getProblemSetProgress(problemSetSlug: string): Promise<ProblemSetProgress> {
    try {
      const response = await axios.get(`${this.baseURL}/submissions/problem-sets/${problemSetSlug}/progress/`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch progress for problem set ${problemSetSlug}:`, error);
      throw error;
    }
  }

  /**
   * Submit a solution for a problem
   */
  async submitSolution(request: SubmissionRequest): Promise<SubmissionResponse> {
    try {
      const response = await axios.post(`${this.baseURL}/submissions/`, request);
      return response.data;
    } catch (error) {
      console.error('Failed to submit solution:', error);
      throw error;
    }
  }

  /**
   * Test a solution without saving (for preview)
   */
  async testSolution(problemSlug: string, userCode: string): Promise<any> {
    try {
      const response = await axios.post(`${this.baseURL}/test-solution/`, {
        problem_slug: problemSlug,
        user_code: userCode
      });
      return response.data;
    } catch (error) {
      console.error('Failed to test solution:', error);
      throw error;
    }
  }

  /**
   * Get submissions for a specific problem
   */
  async getProblemSubmissions(problemSlug: string): Promise<SubmissionSummary[]> {
    try {
      const response = await axios.get(`${this.baseURL}/submissions/`, {
        params: { problem_slug: problemSlug }
      });
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch submissions for problem ${problemSlug}:`, error);
      throw error;
    }
  }

  /**
   * Calculate progress percentage for a problem set based on submissions
   */
  calculateProgressPercentage(completedProblems: number, totalProblems: number): number {
    if (totalProblems === 0) return 0;
    return Math.round((completedProblems / totalProblems) * 100);
  }

  /**
   * Get user's best score for a specific problem
   */
  async getProblemBestScore(problemSlug: string): Promise<number> {
    try {
      const submissions = await this.getProblemSubmissions(problemSlug);
      if (submissions.length === 0) return 0;
      
      const bestSubmission = submissions.reduce((best, current) => 
        current.best_score > best.best_score ? current : best
      );
      
      return bestSubmission.best_score;
    } catch (error) {
      console.error(`Failed to get best score for problem ${problemSlug}:`, error);
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
    
    if (total === 0) return 0;
    return Math.round((passing / total) * 100);
  }

  /**
   * Get formatted test results summary
   */
  getTestResultsSummary(submission: BaseSubmission): string {
    if (!submission.test_results || !Array.isArray(submission.test_results)) {
      return 'No test results available';
    }

    const passed = submission.test_results.filter(r => r.pass).length;
    const total = submission.test_results.length;
    const percentage = total > 0 ? Math.round((passed / total) * 100) : 0;
    
    return `${passed}/${total} tests passed (${percentage}%)`;
  }
}

// Export singleton instance
export const submissionService = new SubmissionService();
export default submissionService;