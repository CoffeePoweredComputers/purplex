/**
 * useTestCases - Manages test case state and operations for the admin editor.
 *
 * This composable handles all test case-related operations including:
 * - CRUD operations for test cases
 * - Parameter and output value management
 * - Type detection and validation
 * - Conversion between frontend and backend formats
 */

import { computed, type ComputedRef, type Ref, ref } from 'vue';
import type { TestCaseDisplay, TestExecutionResult } from '@/types';
import {
  autoDetectAndConvert,
  autoDetectTypeFromInput,
  formatValueForInput,
  getPlaceholderForType,
  parseTypeAnnotation,
  validateValueAgainstType,
} from '@/utils/typeSystem';
import type { FunctionParameter, TypeSpec } from './useFunctionSignature';

// ===== TYPES =====

export interface UseTestCasesReturn {
  /** Test cases array - SINGLE SOURCE OF TRUTH */
  testCases: Ref<TestCaseDisplay[]>;
  /** Whether tests can be run */
  canTest: ComputedRef<boolean>;
  /** Reason why tests cannot be run (null if can test) */
  canTestReason: ComputedRef<string | null>;

  // CRUD operations
  /** Add a new test case with specified number of input fields */
  addTestCase: (inputCount?: number) => void;
  /** Remove a test case by index */
  removeTestCase: (index: number) => void;
  /** Set all test cases (direct assignment) */
  setTestCases: (cases: TestCaseDisplay[]) => void;
  /** Load test cases from backend format (converts and sets) */
  loadFromBackend: (backendCases: TestCaseDisplay[]) => void;

  // Parameter methods
  /** Get parameter value for display */
  getParameterDisplayValue: (testCase: TestCaseDisplay, paramIndex: number) => string;
  /** Update parameter value */
  updateParameterValue: (testCase: TestCaseDisplay, paramIndex: number, value: string) => void;
  /** Get validation error for a parameter */
  getParameterValidationError: (
    testCase: TestCaseDisplay,
    paramIndex: number,
    functionParameters: FunctionParameter[]
  ) => string | null;
  /** Get detected type for a parameter */
  getParameterDetectedType: (testCase: TestCaseDisplay, paramIndex: number) => string;
  /** Get CSS class for parameter type badge */
  getParameterTypeClass: (
    testCase: TestCaseDisplay,
    paramIndex: number,
    functionParameters: FunctionParameter[]
  ) => string;
  /** Get type info tooltip for parameter */
  getParameterTypeInfo: (
    testCase: TestCaseDisplay,
    paramIndex: number,
    functionParameters: FunctionParameter[]
  ) => string;
  /** Get placeholder for parameter input */
  getParameterPlaceholder: (type: string) => string;

  // Output methods
  /** Get expected output display value */
  getExpectedDisplay: (testCase: TestCaseDisplay) => string;
  /** Update expected output */
  updateExpected: (testCase: TestCaseDisplay, value: string) => void;
  /** Get validation error for output */
  getOutputValidationError: (testCase: TestCaseDisplay, returnType: string) => string | null;
  /** Get detected type for output */
  getOutputDetectedType: (testCase: TestCaseDisplay) => string;
  /** Get CSS class for output type badge */
  getOutputTypeClass: (testCase: TestCaseDisplay, returnType: string) => string;
  /** Get type info tooltip for output */
  getOutputTypeInfo: (testCase: TestCaseDisplay, returnType: string) => string;
  /** Get placeholder for output input */
  getOutputPlaceholder: (returnType: string) => string;

  // Test result methods
  /** Check if test at index passed */
  isTestPassed: (index: number, testResults: TestExecutionResult | null) => boolean;
  /** Check if test at index failed */
  isTestFailed: (index: number, testResults: TestExecutionResult | null) => boolean;
  /** Get CSS class for test status */
  getStatusClass: (index: number, testResults: TestExecutionResult | null) => string;
  /** Get status text for test */
  getStatusText: (index: number, testResults: TestExecutionResult | null) => string;

  // Conversion methods
  /** Convert test cases for backend API */
  convertForBackend: () => Array<{
    inputs: unknown[];
    expected_output: unknown;
    description: string;
    order: number;
  }>;
  /** Convert backend test cases for editing */
  convertFromBackend: (backendCases: TestCaseDisplay[]) => TestCaseDisplay[];

  // Utility
  /** Get CSS class for type badge */
  getTypeClass: (detectedType: string, hasError?: boolean) => string;
}

// ===== COMPOSABLE =====

export const useTestCases = (): UseTestCasesReturn => {
  const testCases = ref<TestCaseDisplay[]>([]);

  /**
   * Check if tests can be run
   */
  const canTest = computed<boolean>(() => {
    return testCases.value.length > 0 && testCases.value.every(tc => !tc.error);
  });

  /**
   * Get reason why tests cannot be run
   */
  const canTestReason = computed<string | null>(() => {
    if (testCases.value.length === 0) {
      return 'Add at least one test case';
    }
    if (testCases.value.some(tc => tc.error)) {
      return 'Fix test case errors first';
    }
    return null;
  });

  /**
   * Add a new test case with specified number of input fields.
   * @param inputCount - Number of input fields based on function parameters (default 0)
   */
  const addTestCase = (inputCount: number = 0): void => {
    testCases.value.push({
      inputs: new Array(inputCount).fill(''),
      expected_output: '',
      description: '',
      is_hidden: false,
      is_sample: true,
      order: testCases.value.length,
      error: null,
    });
  };

  /**
   * Remove a test case by index
   */
  const removeTestCase = (index: number): void => {
    testCases.value.splice(index, 1);
    // Reorder remaining test cases
    testCases.value.forEach((tc, i) => {
      tc.order = i;
    });
  };

  /**
   * Set all test cases (direct assignment)
   */
  const setTestCases = (cases: TestCaseDisplay[]): void => {
    testCases.value = cases;
  };

  /**
   * Load test cases from backend format.
   * Converts backend format to display format and sets the state.
   */
  const loadFromBackend = (backendCases: TestCaseDisplay[]): void => {
    testCases.value = convertFromBackend(backendCases);
  };

  // ===== Parameter Methods =====

  /**
   * Get parameter value for display
   */
  const getParameterDisplayValue = (testCase: TestCaseDisplay, paramIndex: number): string => {
    if (!testCase.inputs || paramIndex >= testCase.inputs.length) {
      return '';
    }
    return String(testCase.inputs[paramIndex] ?? '');
  };

  /**
   * Update parameter value
   */
  const updateParameterValue = (
    testCase: TestCaseDisplay,
    paramIndex: number,
    value: string
  ): void => {
    if (!testCase.inputs) {
      testCase.inputs = [];
    }
    while (testCase.inputs.length <= paramIndex) {
      testCase.inputs.push('');
    }
    testCase.inputs[paramIndex] = value;
  };

  /**
   * Get validation error for a parameter
   */
  const getParameterValidationError = (
    testCase: TestCaseDisplay,
    paramIndex: number,
    functionParameters: FunctionParameter[]
  ): string | null => {
    if (!testCase.inputs || paramIndex >= testCase.inputs.length) {
      return null;
    }

    const rawString = String(testCase.inputs[paramIndex] || '');
    const expectedType = functionParameters[paramIndex]?.type;

    if (!expectedType || expectedType === 'Any' || !rawString.trim()) {
      return null;
    }

    try {
      const convertedValue = autoDetectAndConvert(rawString);
      const typeSpec = parseTypeAnnotation(expectedType);
      const validationResult = validateValueAgainstType(convertedValue, typeSpec as TypeSpec);
      return validationResult.valid ? null : (validationResult.error ?? null);
    } catch {
      return 'Invalid input format';
    }
  };

  /**
   * Get detected type for a parameter
   */
  const getParameterDetectedType = (testCase: TestCaseDisplay, paramIndex: number): string => {
    if (!testCase.inputs || paramIndex >= testCase.inputs.length) {
      return 'Any';
    }

    const rawString = String(testCase.inputs[paramIndex] || '');
    if (!rawString.trim()) {
      return 'Any';
    }

    const typeInfo = autoDetectTypeFromInput(rawString);
    return typeInfo.annotation;
  };

  /**
   * Get CSS class for type badge
   */
  const getTypeClass = (detectedType: string, hasError = false): string => {
    if (hasError) {return 'type-error';}

    const baseType = detectedType.toLowerCase().split('[')[0];

    if (['int', 'float'].includes(baseType)) {return 'type-number';}
    if (baseType === 'str') {return 'type-string';}
    if (baseType === 'bool') {return 'type-boolean';}
    if (['list', 'dict', 'tuple', 'set'].includes(baseType)) {return 'type-collection';}
    if (baseType === 'none') {return 'type-none';}
    if (baseType === 'invalid') {return 'type-invalid';}
    if (baseType === 'optional') {return 'type-optional';}

    return 'type-any';
  };

  /**
   * Get CSS class for parameter type badge
   */
  const getParameterTypeClass = (
    testCase: TestCaseDisplay,
    paramIndex: number,
    functionParameters: FunctionParameter[]
  ): string => {
    const detectedType = getParameterDetectedType(testCase, paramIndex);
    const hasError = !!getParameterValidationError(testCase, paramIndex, functionParameters);
    return getTypeClass(detectedType, hasError);
  };

  /**
   * Get type info tooltip for parameter
   */
  const getParameterTypeInfo = (
    testCase: TestCaseDisplay,
    paramIndex: number,
    functionParameters: FunctionParameter[]
  ): string => {
    const detectedType = getParameterDetectedType(testCase, paramIndex);
    const expectedType = functionParameters[paramIndex]?.type || 'Any';
    const error = getParameterValidationError(testCase, paramIndex, functionParameters);

    if (error) {return error;}
    return `Detected: ${detectedType} | Expected: ${expectedType}`;
  };

  /**
   * Get placeholder for parameter input
   */
  const getParameterPlaceholder = (type: string): string => {
    return getPlaceholderForType(type);
  };

  // ===== Output Methods =====

  /**
   * Get expected output display value
   */
  const getExpectedDisplay = (testCase: TestCaseDisplay): string => {
    return String(testCase.expected_output ?? '');
  };

  /**
   * Update expected output
   */
  const updateExpected = (testCase: TestCaseDisplay, value: string): void => {
    testCase.expected_output = value;
  };

  /**
   * Get validation error for output
   */
  const getOutputValidationError = (
    testCase: TestCaseDisplay,
    returnType: string
  ): string | null => {
    const rawString = String(testCase.expected_output || '');

    if (!returnType || returnType === 'Any' || !rawString.trim()) {
      return null;
    }

    try {
      const convertedValue = autoDetectAndConvert(rawString);
      const typeSpec = parseTypeAnnotation(returnType);
      const validationResult = validateValueAgainstType(convertedValue, typeSpec as TypeSpec);
      return validationResult.valid ? null : (validationResult.error ?? null);
    } catch {
      return 'Invalid input format';
    }
  };

  /**
   * Get detected type for output
   */
  const getOutputDetectedType = (testCase: TestCaseDisplay): string => {
    const rawString = String(testCase.expected_output || '');
    if (!rawString.trim()) {
      return 'Any';
    }

    const typeInfo = autoDetectTypeFromInput(rawString);
    return typeInfo.annotation;
  };

  /**
   * Get CSS class for output type badge
   */
  const getOutputTypeClass = (testCase: TestCaseDisplay, returnType: string): string => {
    const detectedType = getOutputDetectedType(testCase);
    const hasError = !!getOutputValidationError(testCase, returnType);
    return getTypeClass(detectedType, hasError);
  };

  /**
   * Get type info tooltip for output
   */
  const getOutputTypeInfo = (testCase: TestCaseDisplay, returnType: string): string => {
    const detectedType = getOutputDetectedType(testCase);
    const error = getOutputValidationError(testCase, returnType);

    if (error) {return error;}
    return `Detected: ${detectedType} | Expected: ${returnType}`;
  };

  /**
   * Get placeholder for output input
   */
  const getOutputPlaceholder = (returnType: string): string => {
    return getPlaceholderForType(returnType);
  };

  // ===== Test Result Methods =====

  /**
   * Check if test at index passed
   */
  const isTestPassed = (index: number, testResults: TestExecutionResult | null): boolean => {
    if (!testResults?.results || index >= testResults.results.length) {
      return false;
    }
    return testResults.results[index]?.isSuccessful === true;
  };

  /**
   * Check if test at index failed
   */
  const isTestFailed = (index: number, testResults: TestExecutionResult | null): boolean => {
    if (!testResults?.results || index >= testResults.results.length) {
      return false;
    }
    return testResults.results[index]?.isSuccessful === false;
  };

  /**
   * Get CSS class for test status
   */
  const getStatusClass = (index: number, testResults: TestExecutionResult | null): string => {
    if (isTestPassed(index, testResults)) {return 'status-passed';}
    if (isTestFailed(index, testResults)) {return 'status-failed';}
    return '';
  };

  /**
   * Get status text for test
   */
  const getStatusText = (index: number, testResults: TestExecutionResult | null): string => {
    if (isTestPassed(index, testResults)) {return 'Passed';}
    if (isTestFailed(index, testResults)) {return 'Failed';}
    return '';
  };

  // ===== Conversion Methods =====

  /**
   * Convert test cases for backend API
   */
  const convertForBackend = (): Array<{
    inputs: unknown[];
    expected_output: unknown;
    description: string;
    order: number;
  }> => {
    return testCases.value.map(tc => {
      const convertedInputs = (tc.inputs || []).map(rawValue => {
        if (rawValue == null || !String(rawValue).trim()) {
          return null;
        }
        try {
          if (typeof rawValue === 'string') {
            return autoDetectAndConvert(rawValue);
          }
          return rawValue;
        } catch {
          return rawValue;
        }
      });

      let convertedOutput: unknown;
      const rawOutput = tc.expected_output;
      if (rawOutput == null || !String(rawOutput).trim()) {
        convertedOutput = null;
      } else {
        try {
          if (typeof rawOutput === 'string') {
            convertedOutput = autoDetectAndConvert(rawOutput);
          } else {
            convertedOutput = rawOutput;
          }
        } catch {
          convertedOutput = rawOutput;
        }
      }

      return {
        inputs: convertedInputs,
        expected_output: convertedOutput,
        description: tc.description || '',
        order: Number(tc.order) || 0,
      };
    });
  };

  /**
   * Convert backend test cases for editing
   */
  const convertFromBackend = (backendCases: TestCaseDisplay[]): TestCaseDisplay[] => {
    if (!Array.isArray(backendCases)) {
      return [];
    }
    return backendCases.map(tc => ({
      ...tc,
      inputs: (tc.inputs || []).map(value => formatValueForInput(value)),
      expected_output: formatValueForInput(tc.expected_output),
      error: null,
    }));
  };

  return {
    testCases,
    canTest,
    canTestReason,
    addTestCase,
    removeTestCase,
    setTestCases,
    loadFromBackend,
    getParameterDisplayValue,
    updateParameterValue,
    getParameterValidationError,
    getParameterDetectedType,
    getParameterTypeClass,
    getParameterTypeInfo,
    getParameterPlaceholder,
    getExpectedDisplay,
    updateExpected,
    getOutputValidationError,
    getOutputDetectedType,
    getOutputTypeClass,
    getOutputTypeInfo,
    getOutputPlaceholder,
    isTestPassed,
    isTestFailed,
    getStatusClass,
    getStatusText,
    convertForBackend,
    convertFromBackend,
    getTypeClass,
  };
};
