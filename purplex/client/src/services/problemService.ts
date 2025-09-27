import axios, { AxiosResponse } from 'axios';
import {
  APIError,
  HintConfig,
  ProblemCategory,
  ProblemCreateRequest,
  ProblemDetailed,
  ProblemUpdateRequest,
  TestExecutionResult,
  TestProblemRequest
} from '../types';

class ProblemServiceImpl {
  private readonly baseURL = '/api/admin/problems';

  /**
   * Load a single problem by slug
   * @param slug - Problem slug identifier
   * @returns Promise resolving to detailed problem data
   * @throws APIError on request failure
   */
  async loadProblem(slug: string): Promise<ProblemDetailed> {
    try {
      const response: AxiosResponse<ProblemDetailed> = await axios.get(
        `${this.baseURL}/${slug}/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to load problem: ${slug}`);
    }
  }

  /**
   * Create a new problem with test cases
   * @param data - Problem creation data
   * @returns Promise resolving to created problem
   * @throws APIError on validation or creation failure
   */
  async createProblem(data: ProblemCreateRequest): Promise<ProblemDetailed> {
    try {
      // Validate data before sending
      this._validateProblemData(data);
      
      const response: AxiosResponse<ProblemDetailed> = await axios.post(
        this.baseURL + '/',
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to create problem');
    }
  }

  /**
   * Update an existing problem
   * @param slug - Problem slug to update
   * @param data - Updated problem data
   * @returns Promise resolving to updated problem
   * @throws APIError on validation or update failure
   */
  async updateProblem(
    slug: string, 
    data: ProblemUpdateRequest
  ): Promise<ProblemDetailed> {
    try {
      const response: AxiosResponse<ProblemDetailed> = await axios.put(
        `${this.baseURL}/${slug}/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to update problem: ${slug}`);
    }
  }

  /**
   * Delete a problem
   * @param slug - Problem slug to delete
   * @returns Promise resolving when deletion is complete
   * @throws APIError on deletion failure
   */
  async deleteProblem(slug: string): Promise<void> {
    try {
      await axios.delete(`${this.baseURL}/${slug}/`);
    } catch (error) {
      throw this._handleError(error, `Failed to delete problem: ${slug}`);
    }
  }

  /**
   * Test a problem's reference solution against test cases
   * @param data - Test problem request data
   * @returns Promise resolving to test execution results
   * @throws APIError on test execution failure
   */
  async testProblem(data: TestProblemRequest): Promise<TestExecutionResult> {
    try {
      const response: AxiosResponse<TestExecutionResult> = await axios.post(
        '/api/admin/test-problem/',
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to test problem solution');
    }
  }


  /**
   * Load all problem categories
   * @returns Promise resolving to array of categories
   * @throws APIError on load failure
   */
  async loadCategories(): Promise<ProblemCategory[]> {
    try {
      const response: AxiosResponse<ProblemCategory[]> = await axios.get(
        '/api/admin/categories/'
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load categories');
    }
  }

  /**
   * Create a new problem category
   * @param data - Category creation data
   * @returns Promise resolving to created category
   * @throws APIError on creation failure
   */
  async createCategory(data: { name: string; color?: string; description?: string }): Promise<ProblemCategory> {
    try {
      const response: AxiosResponse<ProblemCategory> = await axios.post(
        '/api/admin/categories/',
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to create category');
    }
  }

  /**
   * Validate problem data before submission
   * @param data - Problem data to validate
   * @throws Error on validation failure
   */
  private _validateProblemData(data: ProblemCreateRequest): void {
    const errors: string[] = [];

    if (!data.title?.trim()) {
      errors.push('Title is required');
    }

    if (!data.function_name?.trim()) {
      errors.push('Function name is required');
    } else if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(data.function_name)) {
      errors.push('Function name must be a valid Python identifier');
    }

    if (!data.reference_solution?.trim()) {
      errors.push('Reference solution is required');
    }

    if (!data.test_cases || data.test_cases.length === 0) {
      errors.push('At least one test case is required');
    }

    if (errors.length > 0) {
      throw new Error(`Validation failed: ${errors.join(', ')}`);
    }
  }

  /**
   * Handle and format API errors
   * @param error - Axios error object
   * @param defaultMessage - Default error message
   * @returns Formatted APIError
   */
  private _handleError(error: any, defaultMessage: string): APIError {
    if (error.response) {
      // Handle validation errors from Django REST framework
      if (error.response.status === 400 && error.response.data && typeof error.response.data === 'object') {
        // Check if it's a validation error with field-specific messages
        const validationErrors = [];
        for (const [field, messages] of Object.entries(error.response.data)) {
          if (Array.isArray(messages)) {
            validationErrors.push(`${field}: ${messages.join(', ')}`);
          } else if (field === 'error') {
            // Direct error message
            validationErrors.push(messages);
          }
        }

        if (validationErrors.length > 0) {
          return {
            error: validationErrors.join('; '),
            details: error.response.data,
            status: error.response.status
          };
        }
      }

      return {
        error: error.response.data?.error || defaultMessage,
        details: error.response.data?.details,
        status: error.response.status
      };
    } else if (error.request) {
      return {
        error: 'Network error - please check your connection',
        status: 0
      };
    } else {
      return {
        error: error.message || defaultMessage,
        status: -1
      };
    }
  }

  /**
   * Get hints for a problem with optional course context
   * @param problemSlug - Problem slug identifier
   * @param context - Optional course context
   * @returns Promise resolving to hints data
   * @throws APIError on request failure
   */
  async getHints(
    problemSlug: string, 
    context?: { courseId?: string; problemSetSlug?: string }
  ): Promise<{
    available_hints: Array<{
      type: 'variable_fade' | 'subgoal_highlight' | 'suggested_trace';
      unlocked: boolean;
      title: string;
      description: string;
    }>;
    hints_used: string[];
    current_attempts: number;
  }> {
    try {
      const params: any = {};
      if (context?.courseId) {
        params.course_id = context.courseId;
      }
      if (context?.problemSetSlug) {
        params.problem_set_slug = context.problemSetSlug;
      }
      
      const response = await axios.get(
        `/api/problems/${problemSlug}/hints/`,
        { params }
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to get hints for problem: ${problemSlug}`);
    }
  }

  /**
   * Get specific hint content for a problem
   * @param problemSlug - Problem slug identifier
   * @param hintType - Type of hint to retrieve
   * @returns Promise resolving to hint content
   * @throws APIError on request failure
   */
  async getHintContent(
    problemSlug: string, 
    hintType: 'variable_fade' | 'subgoal_highlight' | 'suggested_trace'
  ): Promise<{
    type: string;
    content: Record<string, any>;
    min_attempts: number;
  }> {
    try {
      const response = await axios.get(
        `/api/problems/${problemSlug}/hints/${hintType}/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to get ${hintType} hint for problem: ${problemSlug}`);
    }
  }

  /**
   * Update hints for a problem
   * @param slug - Problem slug
   * @param hints - Array of hint configurations
   * @returns Promise resolving to updated hints
   * @throws APIError on update failure
   */
  async updateHints(slug: string, hints: HintConfig[]): Promise<{
    problem_slug: string;
    hints: Array<HintConfig & { created: boolean }>;
  }> {
    try {
      const response = await axios.put(
        `${this.baseURL}/${slug}/hints/`,
        { hints }
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to update hints for problem: ${slug}`);
    }
  }

  /**
   * Get hints configuration for a problem
   * @param slug - Problem slug
   * @returns Promise resolving to hints configuration
   * @throws APIError on request failure
   */
  async getProblemHints(slug: string): Promise<HintConfig[]> {
    try {
      // Use the admin endpoint to get full hint configurations
      const response = await axios.get(
        `${this.baseURL}/${slug}/hints/`
      );
      
      return response.data.hints || [];
    } catch (error) {
      // If hints endpoint doesn't exist yet, return empty array
      if (error && typeof error === 'object' && 'response' in error && 
          error.response && typeof error.response === 'object' && 'status' in error.response &&
          error.response.status === 404) {
        return [];
      }
      throw this._handleError(error, `Failed to get hints for problem: ${slug}`);
    }
  }
}

// Export singleton instance
export const problemService = new ProblemServiceImpl();