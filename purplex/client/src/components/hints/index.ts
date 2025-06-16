// Export all hint components
export { default as HintButton } from './HintButton.vue'
export { default as HintModal } from './HintModal.vue'
export { default as VariableFadeHint } from './VariableFadeHint.vue'
export { default as SubgoalHighlight } from './SubgoalHighlight.vue'
export { default as SuggestedTrace } from './SuggestedTrace.vue'

// Re-export hint types for convenience
export type { 
  HintType, 
  HintConfig, 
  VariableMapping,
  VariableFadeHintData,
  SubgoalHighlightData,
  Subgoal,
  LineRange,
  SuggestedTraceData,
  HintRequest,
  HintResponse
} from '../../types'