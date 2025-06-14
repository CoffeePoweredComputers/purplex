/**
 * Variable Fade Processor
 * Handles replacing variable names with more meaningful alternatives
 * Provides transformations and tooltip information for enhanced code readability
 */
export class VariableFadeProcessor {
  /**
   * Process variable fade hint and generate code transformations
   * @param {string} code - Original code to transform
   * @param {Object} hintData - Hint configuration with mappings
   * @returns {Object} Processed result with transformed code and metadata
   */
  static process(code, hintData) {
    console.log('VariableFadeProcessor received hintData:', JSON.stringify(hintData, null, 2))
    
    try {
      if (!hintData || !hintData.content || !hintData.content.mappings) {
        throw new Error(`Invalid variable fade hint data. Expected: {content: {mappings: [...]}}, Received: ${JSON.stringify(hintData)}`)
      }

      const mappings = hintData.content.mappings
      let transformedCode = code
      const transformations = []
      const tooltips = []

      // Apply each variable mapping
      for (const mapping of mappings) {
        const { from, to } = mapping
        
        if (!from || !to) {
          console.warn('Skipping invalid mapping:', mapping)
          continue
        }

        // Validate variable names
        if (!this.isValidVariableName(from) || !this.isValidVariableName(to)) {
          console.warn(`Invalid variable names: ${from} -> ${to}`)
          continue
        }

        // Create regex for word boundary matching to avoid partial replacements
        const regex = new RegExp(`\\b${this.escapeRegex(from)}\\b`, 'g')
        
        // Track all replacements for tooltip generation
        const matches = [...transformedCode.matchAll(regex)]
        
        if (matches.length > 0) {
          // Apply transformation
          transformedCode = transformedCode.replace(regex, to)
          
          // Record transformation for undo and tooltips
          transformations.push({
            original: from,
            replacement: to,
            occurrences: matches.length,
            positions: matches.map(match => ({
              start: match.index,
              end: match.index + from.length
            }))
          })

          // Generate tooltip information
          tooltips.push({
            type: 'variable_fade',
            original: from,
            replacement: to,
            message: `Variable '${to}' was originally '${from}'`
          })
        }
      }

      // Generate markers for ACE Editor highlighting
      const markers = this.generateVariableMarkers(transformedCode, transformations)

      return {
        success: true,
        code: transformedCode,
        transformations,
        tooltips,
        markers,
        metadata: {
          hintType: 'variable_fade',
          transformationCount: transformations.length,
          totalReplacements: transformations.reduce((sum, t) => sum + t.occurrences, 0)
        }
      }
    } catch (error) {
      console.error('Variable fade processing error:', error)
      return {
        success: false,
        error: error.message,
        code,
        transformations: [],
        tooltips: [],
        markers: []
      }
    }
  }

  /**
   * Generate ACE Editor markers for variable highlighting
   * @param {string} code - Transformed code
   * @param {Array} transformations - List of transformations applied
   * @returns {Array} Marker objects for ACE Editor
   */
  static generateVariableMarkers(code, transformations) {
    const markers = []
    const lines = code.split('\n')

    for (const transformation of transformations) {
      const { replacement } = transformation
      
      // Find all instances of the replacement variable in the code
      lines.forEach((line, lineIndex) => {
        const regex = new RegExp(`\\b${this.escapeRegex(replacement)}\\b`, 'g')
        let match

        while ((match = regex.exec(line)) !== null) {
          markers.push({
            startLine: lineIndex,
            endLine: lineIndex,
            startColumn: match.index,
            endColumn: match.index + replacement.length,
            className: 'variable-fade-highlight',
            type: 'text',
            tooltipText: `Originally '${transformation.original}'`,
            hintType: 'variable_fade'
          })
        }
      })
    }

    return markers
  }

  /**
   * Reverse variable fade transformations
   * @param {string} transformedCode - Code with transformations applied
   * @param {Array} transformations - Transformations to reverse
   * @returns {string} Original code
   */
  static reverse(transformedCode, transformations) {
    let originalCode = transformedCode

    // Reverse transformations in opposite order
    for (let i = transformations.length - 1; i >= 0; i--) {
      const { original, replacement } = transformations[i]
      const regex = new RegExp(`\\b${this.escapeRegex(replacement)}\\b`, 'g')
      originalCode = originalCode.replace(regex, original)
    }

    return originalCode
  }

  /**
   * Validate if a string is a valid variable name
   * @param {string} name - Variable name to validate
   * @returns {boolean} Whether the name is valid
   */
  static isValidVariableName(name) {
    if (!name || typeof name !== 'string') return false
    
    // Python variable name rules: start with letter or underscore, followed by letters, digits, or underscores
    const pythonVarRegex = /^[a-zA-Z_][a-zA-Z0-9_]*$/
    return pythonVarRegex.test(name)
  }

  /**
   * Escape special regex characters in variable names
   * @param {string} str - String to escape
   * @returns {string} Escaped string
   */
  static escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  }

  /**
   * Get variable usage statistics from code
   * @param {string} code - Code to analyze
   * @param {string} variableName - Variable to analyze
   * @returns {Object} Usage statistics
   */
  static getVariableUsage(code, variableName) {
    const regex = new RegExp(`\\b${this.escapeRegex(variableName)}\\b`, 'g')
    const matches = [...code.matchAll(regex)]
    const lines = code.split('\n')
    
    const usageLines = []
    matches.forEach(match => {
      let currentPos = 0
      for (let i = 0; i < lines.length; i++) {
        if (currentPos <= match.index && match.index < currentPos + lines[i].length) {
          usageLines.push(i + 1) // 1-indexed line numbers
          break
        }
        currentPos += lines[i].length + 1 // +1 for newline
      }
    })

    return {
      variableName,
      totalOccurrences: matches.length,
      usageLines,
      firstUsage: usageLines[0] || null,
      lastUsage: usageLines[usageLines.length - 1] || null
    }
  }

  /**
   * Check if transformations would cause conflicts
   * @param {Array} mappings - Variable mappings to check
   * @returns {Array} Conflicts found
   */
  static checkConflicts(mappings) {
    const conflicts = []
    const usedTargets = new Set()
    const usedSources = new Set()

    for (const mapping of mappings) {
      const { from, to } = mapping

      // Check for duplicate targets
      if (usedTargets.has(to)) {
        conflicts.push({
          type: 'duplicate_target',
          message: `Multiple variables mapping to '${to}'`,
          mapping
        })
      }
      usedTargets.add(to)

      // Check for duplicate sources
      if (usedSources.has(from)) {
        conflicts.push({
          type: 'duplicate_source',
          message: `Variable '${from}' mapped multiple times`,
          mapping
        })
      }
      usedSources.add(from)

      // Check for circular mappings (A -> B, B -> A)
      if (usedSources.has(to) && usedTargets.has(from)) {
        conflicts.push({
          type: 'circular_mapping',
          message: `Circular mapping detected: ${from} <-> ${to}`,
          mapping
        })
      }
    }

    return conflicts
  }
}