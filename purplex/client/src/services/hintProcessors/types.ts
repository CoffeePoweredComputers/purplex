/**
 * Unified Hint Processor Types
 * Defines the contract for all hint processors in the system
 */

export enum HintRenderStrategy {
  MODIFY_CODE = 'modify_code',      // Variable Fade - replaces text in code
  ANNOTATE_CODE = 'annotate_code',  // Subgoal Highlighting - adds comments and highlights
  OVERLAY_UI = 'overlay_ui'         // Suggested Trace - shows UI overlay
}

export interface EditorMarker {
  row: number;                    // 0-indexed line number
  className: string;              // CSS class for the marker
}

export interface HintMetadata {
  strategy: HintRenderStrategy;
  canStack: boolean;              // Can this hint be applied with others?
  affectsLineNumbers: boolean;    // Does this hint change line numbers?
  processorVersion?: string;      // For future compatibility
  markers?: EditorMarker[];       // Line markers for editor highlighting
}

export interface HintResult {
  success: boolean;

  // For MODIFY_CODE and ANNOTATE_CODE strategies
  code?: string;                  // Modified code (if applicable)

  // For OVERLAY_UI strategy
  overlayComponent?: string;      // Component name to render
  overlayProps?: Record<string, unknown>;  // Props for the overlay component

  // Metadata for all strategies
  metadata?: HintMetadata;

  // Error handling
  error?: string;                 // Error message if success is false

  // Line number adjustments (for ANNOTATE_CODE)
  lineAdjustments?: Map<number, number>;  // Original line -> New line mapping
}

export interface HintProcessor<T = unknown> {
  strategy: HintRenderStrategy;
  processHint(hintData: T): HintResult;
  validateHintData?(hintData: T): boolean;
  cleanup?(): void;
}

// Specific hint data types
export interface VariableFadeData {
  code: string;
  variable_mappings?: Array<{ from: string; to: string }>;
  mappings?: Array<{ from: string; to: string }>;  // Support both formats
}

export interface SubgoalData {
  code: string;
  subgoals: Array<{
    line_start: number;
    line_end: number;
    comment?: string;
    title?: string;
    explanation?: string;
    id?: string;
  }>;
}

export interface SuggestedTraceData {
  suggested_call: string;
  explanation?: string;
  expected_output?: unknown;
}

export interface CounterexampleData {
  input: Record<string, unknown>;
  explanation?: string;
}
