/**
 * Input Suggestion Processor
 * Handles adding contextual input suggestions and test case hints to code
 * Creates inline comments and interactive elements for better problem understanding
 */
export class InputSuggestionProcessor {
  /**
   * Process input suggestion hint and generate code with suggestions
   * @param {string} code - Original code to enhance
   * @param {Object} hintData - Hint configuration with test cases and instructions
   * @returns {Object} Processed result with enhanced code and metadata
   */
  static process(code, hintData) {
    console.log('InputSuggestionProcessor received hintData:', JSON.stringify(hintData, null, 2))
    
    try {
      if (!hintData || !hintData.content) {
        throw new Error(`Invalid input suggestion hint data. Expected: {content: {test_cases: [...]}}, Received: ${JSON.stringify(hintData)}`)
      }

      const { test_cases = [], instructions = '' } = hintData.content
      
      if (test_cases.length === 0) {
        return {
          success: true,
          code,
          modifications: [],
          markers: [],
          tooltips: []
        }
      }

      const insertionPoints = this.findInsertionPoints(code)
      const suggestions = this.generateSuggestions(test_cases, instructions)
      const modifications = this.applySuggestions(code, insertionPoints, suggestions)

      return {
        success: true,
        code: modifications.enhancedCode,
        modifications: modifications.changes,
        markers: modifications.markers,
        tooltips: modifications.tooltips,
        metadata: {
          hintType: 'input_suggestion',
          testCaseCount: test_cases.length,
          insertionCount: modifications.changes.length
        }
      }
    } catch (error) {
      console.error('Input suggestion processing error:', error)
      return {
        success: false,
        error: error.message,
        code,
        modifications: [],
        markers: [],
        tooltips: []
      }
    }
  }

  /**
   * Find strategic insertion points for suggestions in the code
   * @param {string} code - Code to analyze
   * @returns {Array} Insertion points with context
   */
  static findInsertionPoints(code) {
    const lines = code.split('\n')
    const insertionPoints = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      const lineNumber = i + 1
      
      // Function definition start
      if (line.match(/^def\s+\w+\s*\(/)) {
        insertionPoints.push({
          lineNumber,
          position: 'after',
          type: 'function_start',
          context: 'function_definition',
          priority: 10
        })
      }
      
      // Return statements
      if (line.match(/^\s*return\s+/)) {
        insertionPoints.push({
          lineNumber,
          position: 'before',
          type: 'return_statement',
          context: 'function_end',
          priority: 8
        })
      }
      
      // Input processing (variable assignments)
      if (line.match(/^\s*\w+\s*=/) && i < 3) { // Early in function
        insertionPoints.push({
          lineNumber,
          position: 'after',
          type: 'input_processing',
          context: 'variable_assignment',
          priority: 6
        })
      }
      
      // Loop structures
      if (line.match(/^\s*(for|while)\s+/)) {
        insertionPoints.push({
          lineNumber,
          position: 'before',
          type: 'loop_structure',
          context: 'iteration',
          priority: 7
        })
      }
      
      // Conditional statements
      if (line.match(/^\s*if\s+/)) {
        insertionPoints.push({
          lineNumber,
          position: 'before',
          type: 'conditional',
          context: 'decision_point',
          priority: 5
        })
      }
    }

    // Sort by priority and line number
    return insertionPoints.sort((a, b) => {
      if (a.priority !== b.priority) {
        return b.priority - a.priority // Higher priority first
      }
      return a.lineNumber - b.lineNumber
    })
  }

  /**
   * Generate suggestion content from test cases and instructions
   * @param {Array} testCases - Test case data
   * @param {string} instructions - Additional instructions
   * @returns {Array} Generated suggestions
   */
  static generateSuggestions(testCases, instructions) {
    const suggestions = []

    // Add general instructions if provided
    if (instructions && instructions.trim()) {
      suggestions.push({
        type: 'instructions',
        content: `# Hint: ${instructions}`,
        priority: 10
      })
    }

    // Generate test case suggestions
    if (testCases.length > 0) {
      // Pick 1-2 most representative test cases
      const selectedCases = this.selectRepresentativeTestCases(testCases)
      
      for (let i = 0; i < selectedCases.length; i++) {
        const testCase = selectedCases[i]
        const suggestion = this.formatTestCaseSuggestion(testCase, i)
        suggestions.push(suggestion)
      }
    }

    return suggestions
  }

  /**
   * Select most representative test cases for suggestions
   * @param {Array} testCases - All available test cases
   * @returns {Array} Selected test cases
   */
  static selectRepresentativeTestCases(testCases) {
    // Limit to 2 test cases to avoid cluttering
    const maxCases = 2
    
    if (testCases.length <= maxCases) {
      return testCases
    }

    // Select first test case (usually simplest)
    const selected = [testCases[0]]
    
    // Select a middle or more complex test case
    if (testCases.length > 2) {
      const middleIndex = Math.floor(testCases.length / 2)
      selected.push(testCases[middleIndex])
    } else {
      selected.push(testCases[1])
    }

    return selected
  }

  /**
   * Format test case as suggestion comment
   * @param {Object} testCase - Test case data from backend
   * @param {number} index - Test case index
   * @returns {Object} Formatted suggestion
   */
  static formatTestCaseSuggestion(testCase, index) {
    try {
      // Extract inputs and expected output from test case
      const inputs = testCase.inputs || []
      const expectedOutput = testCase.expected_output
      
      // Format inputs as function call parameters
      const inputsStr = inputs.map(input => {
        if (typeof input === 'string') {
          return `"${input}"`
        } else if (Array.isArray(input)) {
          return JSON.stringify(input)
        } else {
          return String(input)
        }
      }).join(', ')

      // Format expected output
      let outputStr = expectedOutput
      if (typeof expectedOutput === 'string') {
        outputStr = `"${expectedOutput}"`
      } else if (Array.isArray(expectedOutput)) {
        outputStr = JSON.stringify(expectedOutput)
      }

      const caseNumber = index + 1
      return {
        type: 'test_case',
        content: `# Test case ${caseNumber}: inputs=(${inputsStr}) → expected=${outputStr}`,
        priority: 8 - index, // Earlier test cases have higher priority
        testCaseData: testCase
      }
    } catch (error) {
      console.warn('Error formatting test case suggestion:', error)
      return {
        type: 'test_case',
        content: `# Test case ${index + 1}: Check the test data`,
        priority: 5,
        testCaseData: testCase
      }
    }
  }

  /**
   * Apply suggestions to code at insertion points
   * @param {string} code - Original code
   * @param {Array} insertionPoints - Where to insert suggestions
   * @param {Array} suggestions - What to insert
   * @returns {Object} Modified code and metadata
   */
  static applySuggestions(code, insertionPoints, suggestions) {
    const lines = code.split('\n')
    const changes = []
    const markers = []
    const tooltips = []
    
    // Apply suggestions at appropriate insertion points
    let suggestionIndex = 0
    let lineOffset = 0 // Track how many lines we've added

    for (const point of insertionPoints) {
      if (suggestionIndex >= suggestions.length) break

      const suggestion = suggestions[suggestionIndex]
      const actualLineNumber = point.lineNumber + lineOffset
      
      // Determine insertion position
      let insertAtLine
      if (point.position === 'before') {
        insertAtLine = actualLineNumber - 1
      } else { // 'after'
        insertAtLine = actualLineNumber
      }

      // Insert the suggestion
      const suggestionLine = `    ${suggestion.content}` // Add indentation
      lines.splice(insertAtLine, 0, suggestionLine)
      
      // Track the change
      changes.push({
        type: 'suggestion_insertion',
        originalLine: point.lineNumber,
        insertedLine: insertAtLine + 1, // 1-indexed
        content: suggestion.content,
        context: point.context,
        suggestionType: suggestion.type
      })

      // Create marker for highlighting
      markers.push({
        startLine: insertAtLine,
        endLine: insertAtLine,
        startColumn: 0,
        endColumn: Number.MAX_SAFE_INTEGER,
        className: `input-suggestion suggestion-${suggestion.type}`,
        type: 'fullLine',
        tooltipText: `Suggestion: ${suggestion.content.replace(/^# /, '')}`,
        hintType: 'input_suggestion'
      })

      // Create tooltip
      tooltips.push({
        type: 'input_suggestion',
        lineNumber: insertAtLine + 1,
        content: suggestion.content,
        context: point.context
      })

      suggestionIndex++
      lineOffset++ // We added one line
    }

    return {
      enhancedCode: lines.join('\n'),
      changes,
      markers,
      tooltips
    }
  }

  /**
   * Remove all suggestions from enhanced code
   * @param {string} enhancedCode - Code with suggestions
   * @param {Array} changes - Changes that were made
   * @returns {string} Original code without suggestions
   */
  static removeSuggestions(enhancedCode, changes) {
    const lines = enhancedCode.split('\n')
    
    // Remove suggestion lines in reverse order to maintain line numbers
    const suggestedLines = changes
      .map(change => change.insertedLine - 1) // Convert to 0-indexed
      .sort((a, b) => b - a) // Sort in descending order

    for (const lineIndex of suggestedLines) {
      if (lineIndex >= 0 && lineIndex < lines.length) {
        lines.splice(lineIndex, 1)
      }
    }

    return lines.join('\n')
  }

  /**
   * Create interactive widget data for test cases
   * @param {Array} testCases - Test cases to create widgets for
   * @returns {Array} Widget configuration objects
   */
  static createInteractiveWidgets(testCases) {
    return testCases.map((testCase, index) => ({
      id: `test-case-widget-${index}`,
      type: 'test_case_widget',
      testCase,
      interactive: true,
      actions: [
        {
          type: 'run_test',
          label: 'Test This Case',
          action: 'runSpecificTestCase'
        },
        {
          type: 'visualize',
          label: 'Visualize Execution',
          action: 'openPythonTutor'
        }
      ]
    }))
  }

  /**
   * Analyze code structure to suggest better insertion points
   * @param {string} code - Code to analyze
   * @returns {Object} Analysis results
   */
  static analyzeCodeStructure(code) {
    const lines = code.split('\n')
    const structure = {
      functionCount: 0,
      loopCount: 0,
      conditionalCount: 0,
      returnCount: 0,
      complexity: 'simple'
    }

    lines.forEach(line => {
      const trimmed = line.trim()
      if (trimmed.match(/^def\s+\w+/)) structure.functionCount++
      if (trimmed.match(/^\s*(for|while)\s+/)) structure.loopCount++
      if (trimmed.match(/^\s*if\s+/)) structure.conditionalCount++
      if (trimmed.match(/^\s*return\s+/)) structure.returnCount++
    })

    // Determine complexity
    const complexityScore = structure.loopCount + structure.conditionalCount
    if (complexityScore === 0) structure.complexity = 'simple'
    else if (complexityScore <= 2) structure.complexity = 'moderate'
    else structure.complexity = 'complex'

    return structure
  }
}