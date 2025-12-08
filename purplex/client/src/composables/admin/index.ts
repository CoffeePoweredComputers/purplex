/**
 * Admin Composables - Public API
 *
 * Primary entry point: useProblemEditor
 * This orchestrator composes all feature composables internally.
 *
 * Individual composables below are exported for advanced use cases
 * (testing, custom editors) but should generally not be used directly.
 */

// ===== PUBLIC API =====
// Main orchestrator - use this in components
export { useProblemEditor } from './useProblemEditor';
export type { UseProblemEditorReturn, ActivityTypeConfig } from './useProblemEditor';

// Shared utilities
export { COLOR_OPTIONS } from './useCategoryManager';

// ===== INTERNAL COMPOSABLES =====
// These are implementation details of useProblemEditor.
// Exported for testing and advanced customization only.

// @internal - Core form management
export { useProblemForm } from './useProblemForm';
export type { UseProblemFormReturn, ProblemFormData } from './useProblemForm';

// @internal - UI state (loading, tabs, dialogs)
export { useUIState } from './useUIState';
export type { UseUIStateReturn, UIState } from './useUIState';

// @internal - Function signature parsing
export { useFunctionSignature } from './useFunctionSignature';
export type { UseFunctionSignatureReturn, FunctionParameter } from './useFunctionSignature';

// @internal - Test case management
export { useTestCases } from './useTestCases';
export type {
  UseTestCasesReturn,
  TestCase,
  TestCaseParameter,
  TestCaseParameterType,
} from './useTestCases';

// @internal - Hints configuration (Variable Fade, Subgoal, Trace)
export { useHintsConfig } from './useHintsConfig';
export type {
  UseHintsConfigReturn,
  HintsState,
  VariableFadeConfig,
  SubgoalHighlightConfig,
  SuggestedTraceConfig,
} from './useHintsConfig';

// @internal - MCQ options management
export { useMcqOptions } from './useMcqOptions';
export type { UseMcqOptionsReturn, McqOption } from './useMcqOptions';

// @internal - Segmentation configuration
export { useSegmentation } from './useSegmentation';
export type {
  UseSegmentationReturn,
  SegmentationConfig,
  SegmentationExample,
} from './useSegmentation';

// @internal - Category management
export { useCategoryManager } from './useCategoryManager';
export type {
  UseCategoryManagerReturn,
  CategoryForm,
  PopupPosition,
} from './useCategoryManager';

// @internal - Prompt type configuration
export { usePromptConfig } from './usePromptConfig';
export type { UsePromptConfigReturn, PromptConfig } from './usePromptConfig';

// @internal - Editor settings
export { useEditorSettings } from './useEditorSettings';
export type { UseEditorSettingsReturn } from './useEditorSettings';

// @internal - Refute type configuration
export { useRefuteConfig } from './useRefuteConfig';
export type { UseRefuteConfigReturn, RefuteConfig } from './useRefuteConfig';

// @internal - Debug Fix type configuration
export { useDebugFixConfig } from './useDebugFixConfig';
export type { UseDebugFixConfigReturn, DebugFixConfig, BugHint } from './useDebugFixConfig';

// @internal - Base probe configuration (shared by Probeable Code and Probeable Spec)
export { useProbeConfig, PROBE_MODES as BASE_PROBE_MODES } from './useProbeConfig';
export type {
  UseProbeConfigReturn,
  ProbeConfig,
  ProbeMode,
} from './useProbeConfig';

// @internal - Probeable Code type configuration
export { useProbeableCodeConfig, PROBE_MODES } from './useProbeableCodeConfig';
export type {
  UseProbeableCodeConfigReturn,
  ProbeableCodeConfig,
} from './useProbeableCodeConfig';

// @internal - Probeable Spec type configuration (probe + segmentation)
export { useProbeableSpecConfig, PROBE_MODES as PROBEABLE_SPEC_PROBE_MODES } from './useProbeableSpecConfig';
export type {
  UseProbeableSpecConfigReturn,
  ProbeableSpecConfig,
} from './useProbeableSpecConfig';
