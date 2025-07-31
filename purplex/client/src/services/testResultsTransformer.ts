import type { EiPLSubmissionResponse, TestResult, VariationTestResult } from '@/types';

/**
 * Service to transform and normalize test result data structures
 * between backend API responses and frontend components
 */
export class TestResultsTransformer {
  /**
   * Normalize EiPL submission response from the API
   */
  static normalizeSubmissionResponse(response: any): EiPLSubmissionResponse {
    return {
      submission_id: response.submission_id,
      score: response.score || 0,
      variations: response.variations || response.code_variations || [],
      results: (response.results || response.test_results || []).map(this.normalizeVariationResult),
      passing_variations: response.passing_variations || 0,
      total_variations: response.total_variations || response.variations?.length || 0,
      progress: {
        status: response.progress?.status || 'not_started',
        best_score: response.progress?.best_score || 0,
        attempts: response.progress?.attempts || 0,
        is_completed: response.progress?.is_completed || false
      },
      segmentation: response.segmentation || null
    };
  }
  
  /**
   * Normalize a single variation's test result
   */
  static normalizeVariationResult(result: any): VariationTestResult {
    return {
      success: result.success ?? false,
      error: result.error,
      passed: result.passed ?? 0,
      total: result.total ?? 0,
      score: result.score ?? 0,
      results: Array.isArray(result.results) 
        ? result.results.map(TestResultsTransformer.normalizeTestResult)
        : []
    };
  }
  
  /**
   * Normalize individual test result
   */
  static normalizeTestResult(test: any): TestResult {
    return {
      pass: test.pass ?? false,
      test_number: test.test_number ?? 0,
      inputs: test.inputs || [],
      expected_output: test.expected_output,
      actual_output: test.actual_output,
      error: test.error,
      execution_time: test.execution_time,
      description: test.description,
      function_call: test.function_call
    };
  }
  
  /**
   * Normalize last submission response
   */
  static normalizeLastSubmission(data: any) {
    return {
      has_submission: data.has_submission ?? false,
      submission_id: data.submission_id,
      score: data.score || 0,
      variations: data.variations || data.code_variations || [],
      results: (data.results || data.test_results || []).map(this.normalizeVariationResult),
      passing_variations: data.passing_variations || 0,
      submitted_at: data.submitted_at,
      user_prompt: data.user_prompt || data.prompt || ''
    };
  }
  
  /**
   * Create an empty/error response structure
   */
  static createEmptyResponse(): EiPLSubmissionResponse {
    return {
      submission_id: 0,
      score: 0,
      variations: [],
      results: [],
      passing_variations: 0,
      total_variations: 0,
      progress: {
        status: 'not_started',
        best_score: 0,
        attempts: 0,
        is_completed: false
      }
    };
  }
}

export default TestResultsTransformer;