/**
 * Subgoal Highlight Processor
 * Handles highlighting code sections with step-by-step explanations
 * Creates visual markers and annotations for progressive code understanding
 */
export class SubgoalHighlightProcessor {
  /**
   * Process subgoal highlight hint and generate visual markers
   * @param {string} code - Original code to highlight
   * @param {Object} hintData - Hint configuration with subgoals
   * @returns {Object} Processed result with markers and annotations
   */
  static process(code, hintData) {
    console.log('SubgoalHighlightProcessor received hintData:', JSON.stringify(hintData, null, 2))
    
    try {
      if (!hintData || !hintData.content || !hintData.content.subgoals) {
        throw new Error(`Invalid subgoal highlight hint data. Expected: {content: {subgoals: [...]}}, Received: ${JSON.stringify(hintData)}`)
      }

      const subgoals = hintData.content.subgoals
      const lines = code.split('\n')
      const markers = []
      const annotations = []
      const tooltips = []

      // Process each subgoal
      for (let i = 0; i < subgoals.length; i++) {
        const subgoal = subgoals[i]
        
        if (!this.validateSubgoal(subgoal, lines.length)) {
          console.warn('Skipping invalid subgoal:', subgoal)
          continue
        }

        // Generate marker for highlighting
        const marker = this.createSubgoalMarker(subgoal, i)
        markers.push(marker)
        console.log(`Created marker for subgoal ${i}:`, marker)

        // Generate annotation for gutter
        const annotation = this.createSubgoalAnnotation(subgoal, i)
        annotations.push(annotation)

        // Generate tooltip information
        tooltips.push({
          type: 'subgoal_highlight',
          subgoalIndex: i,
          title: subgoal.title,
          explanation: subgoal.explanation,
          lineRange: `Lines ${subgoal.line_start}-${subgoal.line_end}`
        })
      }

      console.log(`SubgoalHighlightProcessor: Generated ${markers.length} markers:`, markers)

      // Add inline comments to the code and get updated line mappings
      const { code: codeWithComments, adjustedMarkers } = this.addInlineCommentsAndAdjustMarkers(code, subgoals)

      return {
        success: true,
        code: codeWithComments, // Code with inline comments added
        markers: adjustedMarkers, // Use adjusted markers that account for comments
        annotations,
        tooltips,
        metadata: {
          hintType: 'subgoal_highlight',
          subgoalCount: subgoals.length,
          highlightedLines: subgoals.reduce((total, s) => 
            total + (s.line_end - s.line_start + 1), 0
          )
        }
      }
    } catch (error) {
      console.error('Subgoal highlight processing error:', error)
      return {
        success: false,
        error: error.message,
        code,
        markers: [],
        annotations: [],
        tooltips: []
      }
    }
  }

  /**
   * Create ACE Editor marker for subgoal highlighting
   * @param {Object} subgoal - Subgoal configuration
   * @param {number} index - Subgoal index for unique styling
   * @returns {Object} Marker object for ACE Editor
   */
  static createSubgoalMarker(subgoal, index) {
    // Create a safe class name from the title
    const safeTitle = subgoal.title ? subgoal.title.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase() : 'step'
    
    return {
      startLine: subgoal.line_start - 1, // ACE uses 0-indexed lines
      endLine: subgoal.line_end - 1,
      startColumn: 0,
      endColumn: Number.MAX_SAFE_INTEGER, // Full line width
      className: `subgoal-highlight subgoal-${index} subgoal-title-${safeTitle}`,
      type: 'fullLine',
      tooltipText: `Step ${index + 1}: ${subgoal.title}: ${subgoal.explanation}`,
      hintType: 'subgoal_highlight',
      subgoalIndex: index,
      subgoalData: subgoal,
      // Add data for CSS custom properties
      stepNumber: index + 1,
      stepTitle: subgoal.title || `Step ${index + 1}`,
      stepLabel: `Step ${index + 1}: ${subgoal.title || 'Untitled'}`
    }
  }

  /**
   * Create annotation for code gutter
   * @param {Object} subgoal - Subgoal configuration
   * @param {number} index - Subgoal index
   * @returns {Object} Annotation object for ACE Editor
   */
  static createSubgoalAnnotation(subgoal, index) {
    return {
      row: subgoal.line_start - 1, // ACE uses 0-indexed rows
      column: 0,
      text: `Step ${index + 1}: ${subgoal.title}`,
      type: 'info',
      className: `subgoal-annotation subgoal-annotation-${index}`,
      hintType: 'subgoal_highlight',
      subgoalIndex: index
    }
  }

  /**
   * Generate progressive subgoal sequence for step-by-step revelation
   * @param {Array} subgoals - All subgoals
   * @param {number} currentStep - Current step to show (0-indexed)
   * @returns {Array} Markers for current and previous steps
   */
  static generateProgressiveSequence(subgoals, currentStep) {
    const markers = []
    
    for (let i = 0; i <= currentStep && i < subgoals.length; i++) {
      const subgoal = subgoals[i]
      const marker = this.createSubgoalMarker(subgoal, i)
      
      // Add state information
      marker.isCurrentStep = (i === currentStep)
      marker.isCompleted = (i < currentStep)
      marker.className += marker.isCurrentStep 
        ? ' subgoal-current' 
        : marker.isCompleted 
          ? ' subgoal-completed' 
          : ''
          
      markers.push(marker)
    }
    
    return markers
  }

  /**
   * Validate subgoal configuration
   * @param {Object} subgoal - Subgoal to validate
   * @param {number} totalLines - Total lines in the code
   * @returns {boolean} Whether the subgoal is valid
   */
  static validateSubgoal(subgoal, totalLines) {
    if (!subgoal) return false
    
    const { line_start, line_end, title, explanation } = subgoal
    
    // Check required fields
    if (!title || !explanation) return false
    
    // Check line numbers
    if (!Number.isInteger(line_start) || !Number.isInteger(line_end)) return false
    
    // Check line range validity
    if (line_start < 1 || line_end < line_start || line_end > totalLines) return false
    
    return true
  }

  /**
   * Detect overlapping subgoals
   * @param {Array} subgoals - Array of subgoals to check
   * @returns {Array} Overlapping pairs
   */
  static detectOverlaps(subgoals) {
    const overlaps = []
    
    for (let i = 0; i < subgoals.length; i++) {
      for (let j = i + 1; j < subgoals.length; j++) {
        const a = subgoals[i]
        const b = subgoals[j]
        
        // Check if ranges overlap
        if (this.rangesOverlap(a.line_start, a.line_end, b.line_start, b.line_end)) {
          overlaps.push({
            subgoal1: { index: i, ...a },
            subgoal2: { index: j, ...b },
            overlapType: this.getOverlapType(a.line_start, a.line_end, b.line_start, b.line_end)
          })
        }
      }
    }
    
    return overlaps
  }

  /**
   * Check if two line ranges overlap
   * @param {number} start1 - Start of first range
   * @param {number} end1 - End of first range
   * @param {number} start2 - Start of second range
   * @param {number} end2 - End of second range
   * @returns {boolean} Whether ranges overlap
   */
  static rangesOverlap(start1, end1, start2, end2) {
    return !(end1 < start2 || end2 < start1)
  }

  /**
   * Determine the type of overlap between two ranges
   * @param {number} start1 - Start of first range
   * @param {number} end1 - End of first range
   * @param {number} start2 - Start of second range
   * @param {number} end2 - End of second range
   * @returns {string} Type of overlap
   */
  static getOverlapType(start1, end1, start2, end2) {
    if (start1 === start2 && end1 === end2) return 'identical'
    if (start1 <= start2 && end1 >= end2) return 'contains'
    if (start2 <= start1 && end2 >= end1) return 'contained'
    return 'partial'
  }

  /**
   * Sort subgoals by line position for logical ordering
   * @param {Array} subgoals - Subgoals to sort
   * @returns {Array} Sorted subgoals
   */
  static sortSubgoals(subgoals) {
    return [...subgoals].sort((a, b) => {
      // Primary sort: start line
      if (a.line_start !== b.line_start) {
        return a.line_start - b.line_start
      }
      // Secondary sort: end line (shorter ranges first)
      return a.line_end - b.line_end
    })
  }

  /**
   * Generate navigation controls for subgoal sequence
   * @param {Array} subgoals - All subgoals
   * @param {number} currentStep - Current active step
   * @returns {Object} Navigation control data
   */
  static generateNavigationControls(subgoals, currentStep) {
    return {
      currentStep,
      totalSteps: subgoals.length,
      hasPrevious: currentStep > 0,
      hasNext: currentStep < subgoals.length - 1,
      progress: subgoals.length > 0 ? ((currentStep + 1) / subgoals.length) * 100 : 0,
      currentSubgoal: subgoals[currentStep] || null,
      navigationItems: subgoals.map((subgoal, index) => ({
        index,
        title: subgoal.title,
        isActive: index === currentStep,
        isCompleted: index < currentStep,
        lineRange: `${subgoal.line_start}-${subgoal.line_end}`
      }))
    }
  }

  /**
   * Create summary of all subgoals for overview
   * @param {Array} subgoals - All subgoals
   * @returns {Object} Summary information
   */
  static createSummary(subgoals) {
    const totalLines = subgoals.reduce((total, s) => 
      total + (s.line_end - s.line_start + 1), 0
    )
    
    const lineRanges = subgoals.map(s => ({
      start: s.line_start,
      end: s.line_end,
      title: s.title
    }))
    
    return {
      totalSubgoals: subgoals.length,
      totalHighlightedLines: totalLines,
      averageLinesPerSubgoal: Math.round(totalLines / subgoals.length) || 0,
      lineRanges,
      overlaps: this.detectOverlaps(subgoals)
    }
  }

  /**
   * Add inline comments to code and create adjusted markers
   * @param {string} code - Original code
   * @param {Array} subgoals - Subgoal configurations
   * @returns {Object} Code with comments and adjusted markers
   */
  static addInlineCommentsAndAdjustMarkers(code, subgoals) {
    const lines = code.split('\n')
    const adjustedMarkers = []
    let lineOffset = 0
    
    // Process subgoals in original order to maintain step numbering
    for (let i = 0; i < subgoals.length; i++) {
      const subgoal = subgoals[i]
      const stepNumber = i + 1
      
      // Create comment text
      const commentText = `# Step ${stepNumber}: ${subgoal.title}`
      
      // Calculate current insertion position (accounting for previous insertions)
      const targetLineIndex = subgoal.line_start - 1 + lineOffset // Convert to 0-indexed + offset
      
      if (targetLineIndex >= 0 && targetLineIndex < lines.length + lineOffset) {
        // Get the indentation of the target line
        const targetLine = lines[targetLineIndex]
        const indentation = targetLine.match(/^(\s*)/)[1]
        
        // Insert comment with same indentation
        lines.splice(targetLineIndex, 0, `${indentation}${commentText}`)
        
        console.log(`Added comment "${commentText}" before line ${subgoal.line_start} (now at index ${targetLineIndex})`)
        
        // Create markers for both the comment and the subgoal lines
        const commentMarker = this.createCommentMarker(stepNumber, targetLineIndex, i)
        const subgoalMarker = this.createAdjustedSubgoalMarker(subgoal, i, targetLineIndex + 1, lineOffset + 1)
        
        adjustedMarkers.push(commentMarker, subgoalMarker)
        
        // Increment offset for next insertion
        lineOffset++
      }
    }
    
    return {
      code: lines.join('\n'),
      adjustedMarkers
    }
  }

  /**
   * Create marker for comment line
   * @param {number} stepNumber - Step number
   * @param {number} commentLineIndex - Line index of the comment
   * @param {number} subgoalIndex - Original subgoal index for styling
   * @returns {Object} Comment marker
   */
  static createCommentMarker(stepNumber, commentLineIndex, subgoalIndex) {
    return {
      startLine: commentLineIndex,
      endLine: commentLineIndex,
      startColumn: 0,
      endColumn: Number.MAX_SAFE_INTEGER,
      className: `subgoal-comment subgoal-comment-${subgoalIndex}`,
      type: 'fullLine',
      tooltipText: `Step ${stepNumber} guidance`,
      hintType: 'subgoal_comment',
      subgoalIndex,
      stepNumber
    }
  }

  /**
   * Create adjusted marker for subgoal lines (accounting for inserted comments)
   * @param {Object} subgoal - Original subgoal
   * @param {number} index - Subgoal index
   * @param {number} adjustedStartLine - New start line after comment insertion
   * @param {number} lineOffset - Total offset from all previous comment insertions
   * @returns {Object} Adjusted subgoal marker
   */
  static createAdjustedSubgoalMarker(subgoal, index, adjustedStartLine, lineOffset) {
    const adjustedEndLine = adjustedStartLine + (subgoal.line_end - subgoal.line_start)
    
    return {
      startLine: adjustedStartLine,
      endLine: adjustedEndLine,
      startColumn: 0,
      endColumn: Number.MAX_SAFE_INTEGER,
      className: `subgoal-highlight subgoal-${index}`,
      type: 'fullLine',
      tooltipText: `Step ${index + 1}: ${subgoal.title}: ${subgoal.explanation}`,
      hintType: 'subgoal_highlight',
      subgoalIndex: index,
      subgoalData: subgoal,
      stepNumber: index + 1,
      stepTitle: subgoal.title || `Step ${index + 1}`,
      stepLabel: `Step ${index + 1}: ${subgoal.title || 'Untitled'}`
    }
  }
}