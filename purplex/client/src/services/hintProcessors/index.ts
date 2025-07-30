/**
 * Hint Processors Index
 * Central export point for all hint processors
 */

import VariableFadeProcessor from './VariableFadeProcessor';
import SubgoalHighlightProcessor from './SubgoalHighlightProcessor';
import SuggestedTraceProcessor from './SuggestedTraceProcessor';

export * from './types';

export {
  VariableFadeProcessor,
  SubgoalHighlightProcessor,
  SuggestedTraceProcessor
};

// Processor registry for easy lookup
export const HintProcessors = {
  'variable_fade': VariableFadeProcessor,
  'subgoal_highlight': SubgoalHighlightProcessor,
  'suggested_trace': SuggestedTraceProcessor
} as const;

export type HintType = keyof typeof HintProcessors;