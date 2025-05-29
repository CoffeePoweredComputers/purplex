import {
  ValidationError,
  TestCaseValidation,
  ProblemCreateRequest,
  TestCaseDisplay
} from '../types';

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

export interface JSONValidationResult {
  isValid: boolean;
  parsed?: unknown;
  error?: string;
}

class ValidationServiceImpl {
  /**
   * Validate complete problem data
   * @param problem - Partial problem data to validate
   * @returns Validation result with errors and warnings
   */
  validateProblem(problem: Partial<ProblemCreateRequest>): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationError[] = [];

    // Required field validations
    if (!problem.title?.trim()) {
      errors.push({
        field: 'title',
        message: 'Title is required',
        code: 'REQUIRED'
      });
    }

    if (!problem.function_name?.trim()) {
      errors.push({
        field: 'function_name',
        message: 'Function name is required',
        code: 'REQUIRED'
      });
    } else if (!this.validateFunctionName(problem.function_name)) {
      errors.push({
        field: 'function_name',
        message: 'Function name must be a valid Python identifier',
        code: 'INVALID_FORMAT'
      });
    }

    if (!problem.reference_solution?.trim()) {
      errors.push({
        field: 'reference_solution',
        message: 'Reference solution is required',
        code: 'REQUIRED'
      });
    }

    // Test case validations
    if (!problem.test_cases || problem.test_cases.length === 0) {
      errors.push({
        field: 'test_cases',
        message: 'At least one test case is required',
        code: 'MIN_LENGTH'
      });
    } else {
      // Validate each test case
      problem.test_cases.forEach((testCase, index) => {
        const tcValidation = this.validateTestCase({
          ...testCase,
          inputsString: JSON.stringify(testCase.inputs),
          expectedString: JSON.stringify(testCase.expected_output)
        } as TestCaseDisplay);

        if (!tcValidation.isValid) {
          tcValidation.errors.forEach(error => {
            errors.push({
              field: `test_cases.${index}`,
              message: error,
              code: 'INVALID_TEST_CASE'
            });
          });
        }
      });

      // Check for sample test cases
      const hasSampleTestCase = problem.test_cases.some(tc => tc.is_sample);
      if (!hasSampleTestCase) {
        warnings.push({
          field: 'test_cases',
          message: 'Consider marking at least one test case as a sample',
          code: 'NO_SAMPLE_TESTS'
        });
      }
    }

    // Numeric field validations
    if (problem.memory_limit !== undefined && problem.memory_limit < 32) {
      errors.push({
        field: 'memory_limit',
        message: 'Memory limit must be at least 32 MB',
        code: 'MIN_VALUE'
      });
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Validate a single test case
   * @param testCase - Test case to validate
   * @returns Test case validation result
   */
  validateTestCase(testCase: TestCaseDisplay): TestCaseValidation {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Validate inputs JSON
    const inputsValidation = this.validateJSON(testCase.inputsString);
    if (!inputsValidation.isValid) {
      errors.push(`Invalid inputs JSON: ${inputsValidation.error}`);
    } else if (!Array.isArray(inputsValidation.parsed)) {
      errors.push('Inputs must be an array');
    }

    // Validate expected output JSON
    const outputValidation = this.validateJSON(testCase.expectedString);
    if (!outputValidation.isValid) {
      errors.push(`Invalid expected output JSON: ${outputValidation.error}`);
    }

    // Check for description
    if (!testCase.description?.trim()) {
      warnings.push('Consider adding a description for this test case');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Validate JSON string
   * @param jsonString - JSON string to validate
   * @returns JSON validation result with parsed value if valid
   */
  validateJSON(jsonString: string): JSONValidationResult {
    try {
      const parsed = JSON.parse(jsonString);
      return {
        isValid: true,
        parsed
      };
    } catch (error) {
      return {
        isValid: false,
        error: error instanceof Error ? error.message : 'Invalid JSON'
      };
    }
  }

  /**
   * Validate Python function name
   * @param name - Function name to validate
   * @returns True if valid Python identifier
   */
  validateFunctionName(name: string): boolean {
    if (!name) return false;
    
    // Python identifier regex: starts with letter or underscore, 
    // followed by letters, digits, or underscores
    const pythonIdentifierRegex = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
    
    // Check against Python keywords
    const pythonKeywords = [
      'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
      'elif', 'else', 'except', 'exec', 'finally', 'for', 'from', 'global',
      'if', 'import', 'in', 'is', 'lambda', 'not', 'or', 'pass', 'print',
      'raise', 'return', 'try', 'while', 'with', 'yield'
    ];

    return pythonIdentifierRegex.test(name) && !pythonKeywords.includes(name.toLowerCase());
  }
}

// Export singleton instance
export const validationService = new ValidationServiceImpl();