/**
 * Python Tutor Service
 * Centralized service for generating Python Tutor URLs and managing debugger configuration
 */

import type { PythonTutorConfig, PythonTutorOptions, TestCaseFormatted } from '../types';
import { log } from '../utils/logger';

export class PythonTutorService {
  // Configuration constants
  static readonly CONFIG: PythonTutorConfig = {
    BASE_URL: 'https://pythontutor.com',
    EMBED_PATH: '/iframe-embed.html',
    REGULAR_PATH: '/visualize.html',
    DEFAULT_OPTIONS: {
      cumulative: 'false',
      curInstr: '0',
      heapPrimitives: 'nevernest',
      mode: 'display',
      origin: 'opt-frontend.js',
      py: '3',
      rawInputLstJSON: '[]',
      textReferences: 'false'
    }
  };

  /**
   * Generate embed URL for iframe usage (cleaner interface)
   * @param code - Python code to debug
   * @param testCase - Optional test case to append
   * @returns Python Tutor embed URL
   */
  static generateEmbedUrl(code: string, testCase: string = ''): string {
    const fullCode = testCase
      ? `${code}\n\n# Test case\n${testCase}`
      : code;

    const params = new URLSearchParams({
      ...this.CONFIG.DEFAULT_OPTIONS,
      code: fullCode
    });

    return `${this.CONFIG.BASE_URL}${this.CONFIG.EMBED_PATH}#${params.toString()}`;
  }

  /**
   * Generate regular URL for opening in new tab
   * @param code - Python code to debug
   * @param testCase - Optional test case to append
   * @returns Python Tutor regular URL
   */
  static generateRegularUrl(code: string, testCase: string = ''): string {
    const fullCode = testCase
      ? `${code}\n\n# Test case\n${testCase}`
      : code;

    const params = new URLSearchParams({
      ...this.CONFIG.DEFAULT_OPTIONS,
      code: fullCode
    });

    return `${this.CONFIG.BASE_URL}${this.CONFIG.REGULAR_PATH}#${params.toString()}`;
  }

  /**
   * Format code for better display in Python Tutor
   * @param solutionCode - The solution code
   * @param testCase - Test case object with function_call
   * @returns Formatted code
   */
  static formatCodeWithTest(solutionCode: string, testCase: TestCaseFormatted): string {
    if (!testCase || !testCase.function_call) {
      return solutionCode;
    }

    // Add visual separator and test information
    const formattedCode = `${solutionCode}

# === Test Case ===
# Expected: ${testCase.expected_output || 'N/A'}
${testCase.function_call}`;

    return formattedCode;
  }

  /**
   * Check if Python Tutor is available (network check)
   * @returns Promise resolving to availability status
   */
  static async isAvailable(): Promise<boolean> {
    try {
      await fetch(this.CONFIG.BASE_URL, {
        method: 'HEAD',
        mode: 'no-cors'
      });
      return true;
    } catch (error) {
      log.warn('Python Tutor may be unavailable', error);
      return false;
    }
  }

  /**
   * Get optimized options for specific code patterns
   * @param code - Python code
   * @returns Optimized options
   */
  static getOptimizedOptions(code: string): PythonTutorOptions {
    const options: PythonTutorOptions = { ...this.CONFIG.DEFAULT_OPTIONS };

    // If code has recursion, adjust visualization
    if (code.includes('return') && code.includes('(')) {
      options.cumulative = 'true';
    }

    // If code has large data structures, optimize heap display
    if (code.includes('range(') && code.match(/range\(\d{3,}/)) {
      options.heapPrimitives = 'true';
    }

    return options;
  }
}

export default PythonTutorService;
