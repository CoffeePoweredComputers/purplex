/**
 * Instructor-specific content management service.
 * Uses instructor endpoints which are ownership-scoped.
 */
import axios, { AxiosResponse } from 'axios';
import type { APIError, Course, Problem, ProblemSet, TestExecutionResult } from '@/types';

const BASE_URL = '/api/instructor';

class InstructorContentServiceImpl {
  // === PROBLEMS ===

  /**
   * Get all problems created by the current instructor
   */
  async getMyProblems(): Promise<Problem[]> {
    try {
      const response: AxiosResponse<Problem[]> = await axios.get(`${BASE_URL}/problems/`);
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load your problems');
    }
  }

  /**
   * Get a specific problem by slug (only if owned)
   */
  async getProblem(slug: string): Promise<Problem> {
    try {
      const response: AxiosResponse<Problem> = await axios.get(`${BASE_URL}/problems/${slug}/`);
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to load problem: ${slug}`);
    }
  }

  /**
   * Create a new problem (current user becomes creator)
   */
  async createProblem(data: Record<string, unknown>): Promise<Problem> {
    try {
      const response: AxiosResponse<Problem> = await axios.post(`${BASE_URL}/problems/`, data);
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to create problem');
    }
  }

  /**
   * Update an existing problem (only if owned)
   */
  async updateProblem(slug: string, data: Record<string, unknown>): Promise<Problem> {
    try {
      const response: AxiosResponse<Problem> = await axios.put(`${BASE_URL}/problems/${slug}/`, data);
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to update problem: ${slug}`);
    }
  }

  /**
   * Delete a problem (only if owned)
   */
  async deleteProblem(slug: string): Promise<void> {
    try {
      await axios.delete(`${BASE_URL}/problems/${slug}/`);
    } catch (error) {
      throw this._handleError(error, `Failed to delete problem: ${slug}`);
    }
  }

  /**
   * Test a problem's reference solution
   */
  async testProblem(data: Record<string, unknown>): Promise<TestExecutionResult> {
    try {
      const response: AxiosResponse<TestExecutionResult> = await axios.post(
        `${BASE_URL}/test-problem/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to test problem solution');
    }
  }

  // === PROBLEM SETS ===

  /**
   * Get all problem sets created by the current instructor
   */
  async getMyProblemSets(): Promise<ProblemSet[]> {
    try {
      const response: AxiosResponse<ProblemSet[]> = await axios.get(`${BASE_URL}/problem-sets/`);
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load your problem sets');
    }
  }

  /**
   * Get a specific problem set by slug (only if owned)
   */
  async getProblemSet(slug: string): Promise<ProblemSet> {
    try {
      const response: AxiosResponse<ProblemSet> = await axios.get(`${BASE_URL}/problem-sets/${slug}/`);
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to load problem set: ${slug}`);
    }
  }

  /**
   * Create a new problem set (current user becomes creator)
   */
  async createProblemSet(data: Record<string, unknown>): Promise<ProblemSet> {
    try {
      const response: AxiosResponse<ProblemSet> = await axios.post(`${BASE_URL}/problem-sets/`, data);
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to create problem set');
    }
  }

  /**
   * Update an existing problem set (only if owned)
   */
  async updateProblemSet(slug: string, data: Record<string, unknown>): Promise<ProblemSet> {
    try {
      const response: AxiosResponse<ProblemSet> = await axios.put(
        `${BASE_URL}/problem-sets/${slug}/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to update problem set: ${slug}`);
    }
  }

  /**
   * Delete a problem set (only if owned)
   */
  async deleteProblemSet(slug: string): Promise<void> {
    try {
      await axios.delete(`${BASE_URL}/problem-sets/${slug}/`);
    } catch (error) {
      throw this._handleError(error, `Failed to delete problem set: ${slug}`);
    }
  }

  // === COURSES ===

  /**
   * Create a new course (current user becomes instructor/owner)
   */
  async createCourse(data: Record<string, unknown>): Promise<Course> {
    try {
      const response: AxiosResponse<Course> = await axios.post(`${BASE_URL}/courses/create/`, data);
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to create course');
    }
  }

  /**
   * Add a problem set to a course
   */
  async addProblemSetToCourse(courseId: string, problemSetSlug: string, order = 0): Promise<void> {
    try {
      await axios.post(`${BASE_URL}/courses/${courseId}/problem-sets/manage/`, {
        problem_set_slug: problemSetSlug,
        order
      });
    } catch (error) {
      throw this._handleError(error, 'Failed to add problem set to course');
    }
  }

  /**
   * Remove a problem set from a course
   */
  async removeProblemSetFromCourse(courseId: string, problemSetSlug: string): Promise<void> {
    try {
      await axios.delete(`${BASE_URL}/courses/${courseId}/problem-sets/manage/${problemSetSlug}/`);
    } catch (error) {
      throw this._handleError(error, 'Failed to remove problem set from course');
    }
  }

  /**
   * Handle and format API errors
   */
  private _handleError(error: unknown, defaultMessage: string): APIError {
    const axiosError = error as {
      response?: {
        status: number;
        data?: { error?: string; details?: unknown } & Record<string, unknown>;
      };
      request?: unknown;
      message?: string;
    };

    if (axiosError.response) {
      const { response } = axiosError;

      // Handle validation errors from Django REST framework
      if (response.status === 400 && response.data && typeof response.data === 'object') {
        const validationErrors: string[] = [];
        for (const [field, messages] of Object.entries(response.data)) {
          if (Array.isArray(messages)) {
            validationErrors.push(`${field}: ${messages.join(', ')}`);
          } else if (field === 'error' && typeof messages === 'string') {
            validationErrors.push(messages);
          }
        }

        if (validationErrors.length > 0) {
          return {
            error: validationErrors.join('; '),
            details: response.data,
            status: response.status
          };
        }
      }

      return {
        error: response.data?.error || defaultMessage,
        details: response.data?.details,
        status: response.status
      };
    } else if (axiosError.request) {
      return {
        error: 'Network error - please check your connection',
        status: 0
      };
    } else {
      return {
        error: axiosError.message || defaultMessage,
        status: -1
      };
    }
  }
}

// Export singleton instance
export const instructorContentService = new InstructorContentServiceImpl();

export default instructorContentService;
