/**
 * Python Tutor Service
 * Centralized service for generating Python Tutor URLs and managing debugger configuration
 */

export class PythonTutorService {
  // Configuration constants
  static CONFIG = {
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
   * @param {string} code - Python code to debug
   * @param {string} testCase - Optional test case to append
   * @returns {string} Python Tutor embed URL
   */
  static generateEmbedUrl(code, testCase = '') {
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
   * @param {string} code - Python code to debug
   * @param {string} testCase - Optional test case to append
   * @returns {string} Python Tutor regular URL
   */
  static generateRegularUrl(code, testCase = '') {
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
   * @param {string} solutionCode - The solution code
   * @param {object} testCase - Test case object with function_call
   * @returns {string} Formatted code
   */
  static formatCodeWithTest(solutionCode, testCase) {
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
   * @returns {Promise<boolean>}
   */
  static async isAvailable() {
    try {
      const response = await fetch(this.CONFIG.BASE_URL, {
        method: 'HEAD',
        mode: 'no-cors'
      });
      return true;
    } catch (error) {
      console.warn('Python Tutor may be unavailable:', error);
      return false;
    }
  }

  /**
   * Get optimized options for specific code patterns
   * @param {string} code - Python code
   * @returns {object} Optimized options
   */
  static getOptimizedOptions(code) {
    const options = { ...this.CONFIG.DEFAULT_OPTIONS };

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