import { ref, computed, watch, nextTick } from 'vue'
import { VariableFadeProcessor } from '../services/hintProcessors/VariableFadeProcessor.js'
import { SubgoalHighlightProcessor } from '../services/hintProcessors/SubgoalHighlightProcessor.js'
import { InputSuggestionProcessor } from '../services/hintProcessors/InputSuggestionProcessor.js'

/**
 * Composable for managing hint-based editor modifications
 * Handles state, transformations, and coordination between different hint types
 */
export function useEditorHints(editorRef, originalCode) {
  // Reactive state
  const activeHints = ref([])
  const modifiedCode = ref(originalCode?.value || '')
  const hintHistory = ref([])
  const processingState = ref(false)
  const errorState = ref(null)

  // Track editor modifications
  const editorMarkers = ref([])
  const editorAnnotations = ref([])
  const editorTooltips = ref([])

  // Computed states
  const hasActiveHints = computed(() => activeHints.value.length > 0)
  const canToggleOriginal = computed(() => hasActiveHints.value)
  const hintsByType = computed(() => {
    const byType = {}
    activeHints.value.forEach(hint => {
      byType[hint.hintType] = hint
    })
    return byType
  })

  // Watch for original code changes
  watch(originalCode, (newCode) => {
    if (newCode && !hasActiveHints.value) {
      modifiedCode.value = newCode
    }
  }, { immediate: true })

  /**
   * Get processor instance for a hint type
   * @param {string} hintType - Type of hint to process
   * @returns {Object} Processor class
   */
  const getProcessor = (hintType) => {
    const processors = {
      'variable_fade': VariableFadeProcessor,
      'subgoal_highlight': SubgoalHighlightProcessor,
      'input_suggestion': InputSuggestionProcessor
    }
    
    const processor = processors[hintType]
    if (!processor) {
      throw new Error(`Unknown hint type: ${hintType}`)
    }
    
    return processor
  }

  /**
   * Apply a hint to the editor
   * @param {string} hintType - Type of hint to apply
   * @param {Object} hintData - Hint configuration data
   * @returns {Promise<boolean>} Success status
   */
  const applyHint = async (hintType, hintData) => {
    try {
      processingState.value = true
      errorState.value = null

      // Validate hintData
      if (!hintData) {
        throw new Error(`No hint data provided for ${hintType}`)
      }

      console.log(`Applying hint ${hintType} with data:`, hintData)

      // Check if hint is already active
      if (hintsByType.value[hintType]) {
        await removeHint(hintType)
      }

      // Get the appropriate processor
      const processor = getProcessor(hintType)
      
      // Get current code state (may have other hints applied)
      const currentCode = modifiedCode.value || originalCode.value
      
      // Process the hint
      const result = processor.process(currentCode, hintData)
      
      if (!result.success) {
        throw new Error(result.error || `Failed to process ${hintType} hint`)
      }

      // Create hint application record
      const hintApplication = {
        id: `${hintType}_${Date.now()}`,
        hintType,
        hintData,
        result,
        appliedAt: new Date(),
        appliedToCode: currentCode
      }

      // Update state
      activeHints.value.push(hintApplication)
      
      // Update code if it was modified
      if (result.code !== currentCode) {
        modifiedCode.value = result.code
      }

      // Apply visual modifications to editor
      await applyEditorModifications(result)
      
      // Record in history
      hintHistory.value.push({
        action: 'apply',
        hintType,
        timestamp: new Date()
      })

      return true
    } catch (error) {
      console.error('Error applying hint:', error)
      errorState.value = error.message
      return false
    } finally {
      processingState.value = false
    }
  }

  /**
   * Remove a hint from the editor
   * @param {string} hintType - Type of hint to remove
   * @returns {Promise<boolean>} Success status
   */
  const removeHint = async (hintType) => {
    try {
      processingState.value = true
      
      const hintIndex = activeHints.value.findIndex(h => h.hintType === hintType)
      if (hintIndex === -1) {
        return true // Hint not active, nothing to remove
      }

      const hintToRemove = activeHints.value[hintIndex]
      
      // Remove from active hints
      activeHints.value.splice(hintIndex, 1)
      
      // Recompute the code state without this hint
      await recomputeCodeState()
      
      // Record in history
      hintHistory.value.push({
        action: 'remove',
        hintType,
        timestamp: new Date()
      })

      return true
    } catch (error) {
      console.error('Error removing hint:', error)
      errorState.value = error.message
      return false
    } finally {
      processingState.value = false
    }
  }

  /**
   * Toggle a hint on/off
   * @param {string} hintType - Type of hint to toggle
   * @param {Object} hintData - Hint configuration (required for applying)
   * @returns {Promise<boolean>} New state (true = applied, false = removed)
   */
  const toggleHint = async (hintType, hintData) => {
    const isActive = !!hintsByType.value[hintType]
    
    if (isActive) {
      await removeHint(hintType)
      return false
    } else {
      await applyHint(hintType, hintData)
      return true
    }
  }

  /**
   * Remove all active hints
   * @returns {Promise<boolean>} Success status
   */
  const removeAllHints = async () => {
    try {
      processingState.value = true
      
      // Clear all hints
      activeHints.value = []
      
      // Reset to original code
      modifiedCode.value = originalCode.value
      
      // Clear editor modifications
      await clearEditorModifications()
      
      // Record in history
      hintHistory.value.push({
        action: 'remove_all',
        timestamp: new Date()
      })

      return true
    } catch (error) {
      console.error('Error removing all hints:', error)
      errorState.value = error.message
      return false
    } finally {
      processingState.value = false
    }
  }

  /**
   * Restore original code (same as removeAllHints)
   * @returns {Promise<boolean>} Success status
   */
  const restoreOriginal = async () => {
    return removeAllHints()
  }

  /**
   * Recompute code state by reapplying all active hints
   * Used when hints are removed or reordered
   */
  const recomputeCodeState = async () => {
    if (activeHints.value.length === 0) {
      modifiedCode.value = originalCode.value
      await clearEditorModifications()
      return
    }

    // Start with original code
    let currentCode = originalCode.value
    const allMarkers = []
    const allAnnotations = []
    const allTooltips = []

    // Reapply all hints in order
    for (const hint of activeHints.value) {
      const processor = getProcessor(hint.hintType)
      const result = processor.process(currentCode, hint.hintData)
      
      if (result.success) {
        currentCode = result.code
        
        // Collect all visual modifications
        if (result.markers) allMarkers.push(...result.markers)
        if (result.annotations) allAnnotations.push(...result.annotations)
        if (result.tooltips) allTooltips.push(...result.tooltips)
      }
    }

    // Update state
    modifiedCode.value = currentCode
    editorMarkers.value = allMarkers
    editorAnnotations.value = allAnnotations
    editorTooltips.value = allTooltips

    // Apply to editor
    await applyToEditor()
  }

  /**
   * Apply visual modifications to the editor
   * @param {Object} result - Processing result with modifications
   */
  const applyEditorModifications = async (result) => {
    // Collect new modifications
    if (result.markers) {
      editorMarkers.value.push(...result.markers)
    }
    if (result.annotations) {
      editorAnnotations.value.push(...result.annotations)
    }
    if (result.tooltips) {
      editorTooltips.value.push(...result.tooltips)
    }

    await applyToEditor()
  }

  /**
   * Apply all modifications to the ACE editor
   * Note: Markers are applied via reactive props to the Editor component
   */
  const applyToEditor = async () => {
    if (!editorRef.value) return

    await nextTick()

    try {
      const editor = editorRef.value

      // Update code content using the exposed method
      if (typeof editor.setCode === 'function' && editor.getValue() !== modifiedCode.value) {
        editor.setCode(modifiedCode.value)
      }

      // Markers are automatically applied via the reactive hintMarkers prop
      console.log('Editor markers updated via reactive prop:', editorMarkers.value)

      // Apply annotations if the editor supports it
      if (editorAnnotations.value.length > 0 && editor.session) {
        editor.session.setAnnotations(editorAnnotations.value)
      }

    } catch (error) {
      console.error('Error applying modifications to editor:', error)
    }
  }

  /**
   * Clear all editor modifications
   */
  const clearEditorModifications = async () => {
    editorMarkers.value = []
    editorAnnotations.value = []
    editorTooltips.value = []

    if (!editorRef.value) return

    await nextTick()

    try {
      const editor = editorRef.value

      // Markers are automatically cleared via the reactive hintMarkers prop
      console.log('Cleared editor markers via reactive prop')

      // Clear annotations
      if (editor.session) {
        editor.session.clearAnnotations()
      }

      // Reset code using the exposed method
      if (typeof editor.setCode === 'function' && editor.getValue() !== originalCode.value) {
        editor.setCode(originalCode.value)
      }

    } catch (error) {
      console.error('Error clearing editor modifications:', error)
    }
  }

  /**
   * Get current hint status
   * @returns {Object} Status information
   */
  const getStatus = () => {
    return {
      hasActiveHints: hasActiveHints.value,
      activeHintTypes: activeHints.value.map(h => h.hintType),
      totalHints: activeHints.value.length,
      isProcessing: processingState.value,
      hasError: !!errorState.value,
      error: errorState.value,
      codeModified: modifiedCode.value !== originalCode.value
    }
  }

  /**
   * Check if a specific hint type is active
   * @param {string} hintType - Hint type to check
   * @returns {boolean} Whether the hint is active
   */
  const isHintActive = (hintType) => {
    return !!hintsByType.value[hintType]
  }

  /**
   * Get data for a specific active hint
   * @param {string} hintType - Hint type to get data for
   * @returns {Object|null} Hint data or null if not active
   */
  const getHintData = (hintType) => {
    return hintsByType.value[hintType] || null
  }

  // Cleanup function
  const cleanup = () => {
    activeHints.value = []
    hintHistory.value = []
    editorMarkers.value = []
    editorAnnotations.value = []
    editorTooltips.value = []
    processingState.value = false
    errorState.value = null
  }

  return {
    // Reactive state (readonly)
    activeHints: computed(() => activeHints.value),
    modifiedCode: computed(() => modifiedCode.value),
    hasActiveHints,
    canToggleOriginal,
    processingState: computed(() => processingState.value),
    errorState: computed(() => errorState.value),
    
    // Methods
    applyHint,
    removeHint,
    toggleHint,
    removeAllHints,
    restoreOriginal,
    isHintActive,
    getHintData,
    getStatus,
    cleanup,
    
    // For debugging/development
    hintHistory: computed(() => hintHistory.value),
    editorMarkers: computed(() => editorMarkers.value),
    editorAnnotations: computed(() => editorAnnotations.value)
  }
}