/**
 * Hint Processors Index
 * Central export point for all hint processors
 */

import VariableFadeProcessor from './VariableFadeProcessor';
import SubgoalHighlightProcessor from './SubgoalHighlightProcessor';
import SuggestedTraceProcessor from './SuggestedTraceProcessor';
import CounterexampleProcessor from './CounterexampleProcessor';

export * from './types';

export {
  VariableFadeProcessor,
  SubgoalHighlightProcessor,
  SuggestedTraceProcessor,
  CounterexampleProcessor
};

// Processor registry for easy lookup
export const HintProcessors = {
  'variable_fade': VariableFadeProcessor,
  'subgoal_highlight': SubgoalHighlightProcessor,
  'suggested_trace': SuggestedTraceProcessor,
  'counterexample': CounterexampleProcessor
} as const;

export type HintType = keyof typeof HintProcessors;
