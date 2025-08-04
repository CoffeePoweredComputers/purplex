import { computed, nextTick, Ref, ref, toRaw, watch } from 'vue'
import { 
  HintProcessors,
  HintRenderStrategy,
  HintResult,
  HintType,
  EditorMarker as HintMarker
} from '../services/hintProcessors'
import { log } from '../utils/logger'

// Types
interface HintData {
  hintId?: string
  hintType?: string
  content?: any
  [key: string]: any
}


interface EditorAnnotation {
  row: number
  text: string
  type: string
}

interface EditorTooltip {
  row: number
  column: number
  text: string
}


/**
 * Composable for managing hint-based editor modifications
 * Handles state, transformations, and coordination between different hint types
 */
export function useEditorHints(editorRef: Ref<any>, originalCode: Ref<string>) {
  // Reactive state
  const activeHints = ref<HintData[]>([])
  const modifiedCode = ref<string>(originalCode?.value || '')
  const hintHistory = ref<HintData[]>([])
  const processingState = ref<boolean>(false)
  const errorState = ref<string | null>(null)

  // Track editor modifications
  const editorMarkers = ref<HintMarker[]>([])
  const editorAnnotations = ref<EditorAnnotation[]>([])
  const editorTooltips = ref<EditorTooltip[]>([])

  // Computed states
  const hasActiveHints = computed(() => activeHints.value.length > 0)
  const canToggleOriginal = computed(() => hasActiveHints.value)
  const hintsByType = computed(() => {
    const byType: Record<string, HintData> = {}
    activeHints.value.forEach(hint => {
      if (hint.hintType) {
        byType[hint.hintType] = hint
      }
    })
    return byType
  })

  // Track UI overlays for OVERLAY_UI strategy hints
  const activeOverlays = ref<Array<{ component: string; props: any }>>([])  

  // Watch for original code changes
  watch(originalCode, (newCode) => {
    if (newCode && !hasActiveHints.value) {
      modifiedCode.value = newCode
    }
  }, { immediate: true })

  /**
   * Get processor class for a hint type
   * @param {string} hintType - Type of hint to process
   * @returns {Object} Processor class
   */
  const getProcessor = (hintType: HintType) => {
    return HintProcessors[hintType] || null
  }

  /**
   * Apply a hint to the editor
   * @param {Object} hintData - Hint data containing type and content
   * @returns {boolean} Success status
   */
  const applyHint = async (hintType: string, hintData: HintData): Promise<boolean> => {
    if (!hintType || !hintData) {
      errorState.value = 'Invalid hint type or data provided'
      return false
    }

    try {
      processingState.value = true
      errorState.value = null

      log.debug(`Applying hint ${hintType} with data:`, hintData)

      // Check if hint is already active
      if (activeHints.value.some(h => h.hintType === hintType)) {
        errorState.value = `Hint type ${hintType} is already active`
        return false
      }

      // Get processor for hint type
      const processor = getProcessor(hintType as HintType)
      if (!processor) {
        errorState.value = `No processor found for hint type: ${hintType}`
        return false
      }

      // Process the hint
      const baseCode = activeHints.value.length === 0 ? originalCode.value : modifiedCode.value
      
      // Prepare data for processor - unwrap Vue reactivity
      const rawContent = toRaw(hintData.content || {})
      const processorInput = {
        code: baseCode,
        ...rawContent
      }
      
      // Create processor instance and call processHint method
      const processorInstance = new processor()
      const result: HintResult = processorInstance.processHint(processorInput)
      
      // Check if processing was successful
      if (!result || !result.success) {
        errorState.value = result?.error || 'Failed to process hint'
        return false
      }

      // Apply based on render strategy
      if (result.metadata) {
        switch (result.metadata.strategy) {
          case HintRenderStrategy.MODIFY_CODE:
          case HintRenderStrategy.ANNOTATE_CODE:
            // Update editor content
            if (result.code) {
              modifiedCode.value = result.code
            }
            // Apply markers if any
            if (result.markers) {
              editorMarkers.value = [...editorMarkers.value, ...result.markers]
            }
            break
            
          case HintRenderStrategy.OVERLAY_UI:
            // Add overlay component
            if (result.overlayComponent && result.overlayProps) {
              activeOverlays.value.push({
                component: result.overlayComponent,
                props: result.overlayProps
              })
            }
            break
        }
      }

      // Add to active hints with result
      activeHints.value.push({
        ...hintData,
        hintType: hintType,
        timestamp: Date.now(),
        result
      })

      // Add to history
      hintHistory.value.push({
        ...hintData,
        hintType: hintType,
        timestamp: Date.now(),
        action: 'applied'
      } as HintData)

      // Apply modifications to editor
      await nextTick()
      applyModificationsToEditor()

      return true
    } catch (error) {
      log.error('Error applying hint', error)
      errorState.value = error instanceof Error ? error.message : 'Unknown error'
      return false
    } finally {
      processingState.value = false
    }
  }

  /**
   * Remove a specific hint
   * @param {string} hintType - Type of hint to remove
   * @returns {boolean} Success status
   */
  const removeHint = async (hintType: string): Promise<boolean> => {
    try {
      processingState.value = true
      errorState.value = null

      const hintIndex = activeHints.value.findIndex(h => h.hintType === hintType)
      if (hintIndex === -1) {
        errorState.value = `Hint type ${hintType} is not active`
        return false
      }

      // Get the hint data before removing
      const hintData = activeHints.value[hintIndex]
      
      // Remove hint from active list
      activeHints.value.splice(hintIndex, 1)

      // Remove associated overlays if hint used OVERLAY_UI strategy
      if (hintData.result?.metadata?.strategy === HintRenderStrategy.OVERLAY_UI) {
        // Remove all overlays associated with this hint's component
        activeOverlays.value = activeOverlays.value.filter(
          overlay => overlay.component !== hintData.result?.overlayComponent
        )
      }

      // Record in history
      hintHistory.value.push({
        hintType,
        timestamp: Date.now(),
        action: 'removed'
      } as HintData)

      // Reapply all remaining hints from scratch
      await reapplyAllHints()

      return true
    } catch (error) {
      log.error('Error removing hint', error)
      errorState.value = error instanceof Error ? error.message : 'Unknown error'
      return false
    } finally {
      processingState.value = false
    }
  }

  /**
   * Toggle a hint (apply if not active, remove if active)
   * @param {Object} hintData - Hint data
   * @returns {boolean} Success status
   */
  const toggleHint = async (hintData: HintData): Promise<boolean> => {
    if (!hintData.hintType) {
      errorState.value = 'Hint type is required'
      return false
    }
    
    const isActive = activeHints.value.some(h => h.hintType === hintData.hintType)
    
    if (isActive) {
      return await removeHint(hintData.hintType)
    } else {
      return await applyHint(hintData.hintType, hintData)
    }
  }

  /**
   * Remove all active hints
   * @returns {boolean} Success status
   */
  const removeAllHints = async (): Promise<boolean> => {
    try {
      processingState.value = true
      errorState.value = null

      // Clear all hints
      activeHints.value = []
      
      // Clear all overlays
      activeOverlays.value = []
      
      // Reset to original code
      modifiedCode.value = originalCode.value

      // Clear all editor modifications
      clearEditorModifications()

      // Record in history
      hintHistory.value.push({
        hintType: 'all',
        timestamp: Date.now(),
        action: 'cleared'
      } as HintData)

      return true
    } catch (error) {
      log.error('Error removing all hints', error)
      errorState.value = error instanceof Error ? error.message : 'Unknown error'
      return false
    } finally {
      processingState.value = false
    }
  }

  /**
   * Check if a specific hint type is active
   * @param {string} hintType - Type of hint to check
   * @returns {boolean} Whether the hint is active
   */
  const isHintActive = (hintType: string): boolean => {
    return activeHints.value.some(h => h.hintType === hintType)
  }

  /**
   * Get active hint data by type
   * @param {string} hintType - Type of hint
   * @returns {Object|null} Hint data if active, null otherwise
   */
  const getHintData = (hintType: string): HintData | null => {
    return activeHints.value.find(h => h.hintType === hintType) || null
  }

  /**
   * Reapply all active hints from scratch
   * Used when hints are removed to ensure proper layering
   */
  const reapplyAllHints = async (): Promise<void> => {
    // Start with original code
    modifiedCode.value = originalCode.value
    
    // Clear all editor modifications
    editorMarkers.value = []
    editorAnnotations.value = []
    editorTooltips.value = []

    // Reapply each hint in order (excluding UI-only hints)
    const hintsToReapply = activeHints.value.filter(
      h => h.result?.metadata?.strategy !== HintRenderStrategy.OVERLAY_UI
    )
    
    for (const hint of hintsToReapply) {
      const processor = getProcessor(hint.hintType as HintType)
      if (processor) {
        // Prepare data for processor - unwrap Vue reactivity
        const rawContent = toRaw(hint.content || {})
        const processorInput = {
          code: modifiedCode.value,
          ...rawContent
        }
        
        // Create processor instance and call processHint method
        const processorInstance = new processor()
        const result: HintResult = processorInstance.processHint(processorInput)
        
        // Only apply if successful
        if (result && result.success) {
          if (result.code) {
            modifiedCode.value = result.code
          }
          
          if (result.markers) {
            editorMarkers.value = [...editorMarkers.value, ...result.markers]
          }
          // Annotations are not part of HintResult interface
          // if (result.annotations) {
          //   editorAnnotations.value = [...editorAnnotations.value, ...result.annotations]
          // }
        }
      }
    }

    // Apply modifications to editor
    await nextTick()
    applyModificationsToEditor()
  }

  /**
   * Apply visual modifications to the editor
   * (markers, annotations, tooltips)
   */
  const applyModificationsToEditor = (): void => {
    try {
      if (!editorRef.value) return

      // The ref points to the Editor Vue component, not the Ace instance
      // Markers are automatically applied via the reactive hintMarkers prop
      log.debug('Editor markers updated via reactive prop:', editorMarkers.value)

      // Note: The Editor component handles markers through its hintMarkers prop
      // We don't need to manually call setHintMarkers as it watches the prop

    } catch (error) {
      log.error('Error applying modifications to editor', error)
    }
  }

  /**
   * Clear all visual modifications from the editor
   */
  const clearEditorModifications = (): void => {
    try {
      // Clear markers - the Editor component will react to this change
      editorMarkers.value = []
      
      // Clear annotations
      editorAnnotations.value = []
      
      // Clear tooltips
      editorTooltips.value = []

      log.debug('Cleared all editor modifications')

    } catch (error) {
      log.error('Error clearing editor modifications', error)
    }
  }

  /**
   * Get hint statistics
   * @returns {Object} Statistics about hint usage
   */
  const getHintStats = (): Record<string, any> => {
    const stats: Record<string, any> = {
      activeCount: activeHints.value.length,
      historyCount: hintHistory.value.length,
      byType: {}
    }

    // Count by type
    activeHints.value.forEach(hint => {
      if (hint.hintType) {
        stats.byType[hint.hintType] = (stats.byType[hint.hintType] || 0) + 1
      }
    })

    return stats
  }
  
  /**
   * Save current hint state
   * @returns {Object} Serializable hint state
   */
  const saveState = () => {
    return {
      activeHints: activeHints.value.map(hint => ({
        hintType: hint.hintType,
        content: hint.content,
        timestamp: hint.timestamp
      })),
      hasHints: hasActiveHints.value
    }
  }
  
  /**
   * Restore hint state
   * @param {Object} state - Previously saved state
   */
  const restoreState = async (state: any) => {
    // Always clear current state first
    await removeAllHints()
    
    // If no state to restore, we're done (hints are cleared)
    if (!state || !state.activeHints || state.activeHints.length === 0) return
    
    // Reapply each saved hint
    for (const savedHint of state.activeHints) {
      await applyHint(savedHint.hintType, { content: savedHint.content })
    }
  }

  return {
    // State
    activeHints: computed(() => activeHints.value),
    activeOverlays: computed(() => activeOverlays.value),
    modifiedCode: computed(() => modifiedCode.value),
    hasActiveHints,
    canToggleOriginal,
    hintsByType,
    processingState: computed(() => processingState.value),
    errorState: computed(() => errorState.value),
    editorMarkers: computed(() => editorMarkers.value),
    editorAnnotations: computed(() => editorAnnotations.value),
    
    // Methods
    applyHint,
    removeHint,
    toggleHint,
    removeAllHints,
    isHintActive,
    getHintData,
    getHintStats,
    
    // State management
    saveState,
    restoreState,
    
    // Utility
    reapplyAllHints
  }
}