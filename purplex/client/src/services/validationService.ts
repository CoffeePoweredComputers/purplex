import {
  ProblemCreateRequest,
  TestCaseDisplay,
  TestCaseValidation,
  ValidationError
} from '../types';
import {
  autoDetectAndConvert,
  autoDetectTypeFromInput,
  getPlaceholderForType,
  parseTypeAnnotation,
  validateValueAgainstType
} from '../utils/typeSystem';

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
   * Validate a single test case with enhanced type checking
   * @param testCase - Test case to validate
   * @param functionSignature - Optional function signature for parameter validation
   * @returns Test case validation result
   */
  validateTestCase(testCase: TestCaseDisplay, functionSignature?: string): TestCaseValidation {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Validate inputs JSON
    const inputsValidation = this.validateJSON(testCase.inputsString);
    if (!inputsValidation.isValid) {
      errors.push(`Invalid inputs JSON: ${inputsValidation.error}`);
    } else if (!Array.isArray(inputsValidation.parsed)) {
      errors.push('Inputs must be an array');
    } else if (functionSignature) {
      // Enhanced parameter type validation
      const parameterErrors = this.validateParameterTypes(inputsValidation.parsed, functionSignature);
      errors.push(...parameterErrors);
    }

    // Validate expected output JSON with type checking
    const outputValidation = this.validateJSON(testCase.expectedString);
    if (!outputValidation.isValid) {
      errors.push(`Invalid expected output JSON: ${outputValidation.error}`);
    } else if (functionSignature) {
      // Enhanced return type validation
      const returnTypeErrors = this.validateReturnType(outputValidation.parsed, functionSignature);
      errors.push(...returnTypeErrors);
    }

    // Check for description
    if (!testCase.description?.trim()) {
      warnings.push('Consider adding a description for this test case');
    }

    // Check for edge cases
    if (inputsValidation.isValid && Array.isArray(inputsValidation.parsed)) {
      if (inputsValidation.parsed.length === 0) {
        warnings.push('Test case has no input parameters');
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Validate parameter types against function signature
   * @param inputs - Array of input values
   * @param functionSignature - Function signature string
   * @returns Array of validation error messages
   */
  private validateParameterTypes(inputs: unknown[], functionSignature: string): string[] {
    const errors: string[] = [];
    
    try {
      const parameters = this.parseFunctionParameters(functionSignature);
      
      if (parameters.length !== inputs.length) {
        errors.push(`Expected ${parameters.length} parameters, got ${inputs.length}`);
        return errors;
      }

      inputs.forEach((input, index) => {
        if (index < parameters.length) {
          const param = parameters[index];
          const typeSpec = parseTypeAnnotation(param.type);
          const validationResult = validateValueAgainstType(input, typeSpec);
          
          if (!validationResult.valid) {
            const paramName = param.name || `parameter ${index + 1}`;
            let errorMsg = `${paramName}: ${validationResult.error}`;
            if (validationResult.suggestion) {
              errorMsg += ` (try: ${validationResult.suggestion})`;
            }
            errors.push(errorMsg);
          }
        }
      });
    } catch (error) {
      errors.push(`Failed to parse function signature: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }

    return errors;
  }

  /**
   * Validate return type against function signature
   * @param output - Expected output value
   * @param functionSignature - Function signature string
   * @returns Array of validation error messages
   */
  private validateReturnType(output: unknown, functionSignature: string): string[] {
    const errors: string[] = [];
    
    try {
      const returnType = this.parseFunctionReturnType(functionSignature);
      if (returnType && returnType !== 'Any') {
        const typeSpec = parseTypeAnnotation(returnType);
        const validationResult = validateValueAgainstType(output, typeSpec);
        
        if (!validationResult.valid) {
          let errorMsg = `Return value: ${validationResult.error}`;
          if (validationResult.suggestion) {
            errorMsg += ` (try: ${validationResult.suggestion})`;
          }
          errors.push(errorMsg);
        }
      }
    } catch (error) {
      errors.push(`Failed to parse return type: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }

    return errors;
  }

  /**
   * Parse function parameters from signature
   * @param functionSignature - Function signature string
   * @returns Array of parameter objects with name and type
   */
  private parseFunctionParameters(functionSignature: string): Array<{name: string; type: string}> {
    const regex = /def\s+\w+\s*\((.*?)\)/;
    const match = functionSignature.match(regex);
    
    if (!match) {
      return [];
    }
    
    const paramsStr = match[1].trim();
    if (!paramsStr) {
      return [];
    }
    
    const params: Array<{name: string; type: string}> = [];
    const paramRegex = /(\w+)\s*:\s*([^,]+)/g;
    let paramMatch;
    
    while ((paramMatch = paramRegex.exec(paramsStr)) !== null) {
      params.push({
        name: paramMatch[1],
        type: paramMatch[2].trim()
      });
    }
    
    return params;
  }

  /**
   * Parse return type from function signature
   * @param functionSignature - Function signature string
   * @returns Return type string or null if not specified
   */
  private parseFunctionReturnType(functionSignature: string): string | null {
    const regex = /def\s+\w+\s*\([^)]*\)\s*->\s*([^:]+):/;
    const match = functionSignature.match(regex);
    
    return match ? match[1].trim() : null;
  }

  /**
   * Validate JSON string with enhanced error reporting
   * @param jsonString - JSON string to validate
   * @returns JSON validation result with parsed value if valid
   */
  validateJSON(jsonString: string): JSONValidationResult {
    if (!jsonString.trim()) {
      return {
        isValid: false,
        error: 'Empty JSON string'
      };
    }

    try {
      const parsed = JSON.parse(jsonString);
      return {
        isValid: true,
        parsed
      };
    } catch (error) {
      let errorMessage = 'Invalid JSON';
      
      if (error instanceof SyntaxError) {
        // Provide more specific JSON syntax error messages
        const message = error.message.toLowerCase();
        if (message.includes('unexpected token')) {
          errorMessage = 'Invalid JSON syntax - check for missing quotes, commas, or brackets';
        } else if (message.includes('unexpected end')) {
          errorMessage = 'Incomplete JSON - missing closing bracket or quote';
        } else {
          errorMessage = `JSON syntax error: ${error.message}`;
        }
      }

      return {
        isValid: false,
        error: errorMessage
      };
    }
  }

  /**
   * Validate and suggest improvements for input values
   * @param inputValue - Raw input value as string
   * @param expectedType - Expected Python type annotation
   * @returns Validation result with suggestions
   */
  validateInputValue(inputValue: string, expectedType?: string): {
    isValid: boolean;
    parsed?: unknown;
    error?: string;
    suggestion?: string;
    confidence?: 'high' | 'medium' | 'low';
  } {
    if (!inputValue.trim()) {
      return {
        isValid: false,
        error: 'Empty input value',
        suggestion: expectedType ? getPlaceholderForType(expectedType) : 'Enter a value'
      };
    }

    // Auto-detect type from input
    const typeInfo = autoDetectTypeFromInput(inputValue);
    
    if (typeInfo.detected === 'invalid') {
      return {
        isValid: false,
        error: 'Invalid input format',
        suggestion: expectedType ? 
          `Expected ${expectedType}. Try: ${getPlaceholderForType(expectedType)}` :
          'Check your input syntax',
        confidence: typeInfo.confidence
      };
    }

    // Try to convert the value
    try {
      const converted = autoDetectAndConvert(inputValue);
      
      // If expected type is provided, validate against it
      if (expectedType) {
        const typeSpec = parseTypeAnnotation(expectedType);
        const validationResult = validateValueAgainstType(converted, typeSpec);
        
        if (!validationResult.valid) {
          return {
            isValid: false,
            parsed: converted,
            error: validationResult.error,
            suggestion: validationResult.suggestion,
            confidence: typeInfo.confidence
          };
        }
      }

      return {
        isValid: true,
        parsed: converted,
        confidence: typeInfo.confidence
      };
    } catch (error) {
      return {
        isValid: false,
        error: error instanceof Error ? error.message : 'Conversion failed',
        suggestion: expectedType ? getPlaceholderForType(expectedType) : 'Check your input format',
        confidence: typeInfo.confidence
      };
    }
  }

  /**
   * Validate Python function name
   * @param name - Function name to validate
   * @returns True if valid Python identifier
   */
  validateFunctionName(name: string): boolean {
    if (!name) {return false;}
    
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