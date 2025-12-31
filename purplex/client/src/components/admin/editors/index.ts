/**
 * Problem Editor Registry
 *
 * Maps problem types to their type-specific admin editor components.
 * Follows the same pattern as ActivityComponentRegistry in
 * src/components/activities/index.ts for student-facing components.
 */

import type {
  EditorComponentLoader,
  ProblemEditorDefinition,
  ProblemEditorRegistry,
} from './types'

/**
 * Registry of problem type editors.
 * Each entry uses lazy loading for code splitting.
 */
const PROBLEM_EDITORS: ProblemEditorRegistry = {
  mcq: {
    editor: () => import('./McqProblemEditor.vue'),
    label: 'Multiple Choice Question',
    description: 'Multiple choice questions with explanations',
  },
  eipl: {
    editor: () => import('./EiplProblemEditor.vue'),
    label: 'Explain in Plain Language',
    description: 'Code explanation problems with test cases and hints',
  },
  prompt: {
    editor: () => import('./PromptProblemEditor.vue'),
    label: 'Prompt Problem',
    description: 'Image-based explanation problems',
  },
  debug_fix: {
    editor: () => import('./DebugFixProblemEditor.vue'),
    label: 'Debug and Fix Code',
    description: 'Student fixes buggy code to pass test cases',
  },
  probeable_code: {
    editor: () => import('./ProbeableCodeProblemEditor.vue'),
    label: 'Probeable Problem (Code)',
    description: 'Student discovers behavior via oracle, writes code',
  },
  probeable_spec: {
    editor: () => import('./ProbeableSpecProblemEditor.vue'),
    label: 'Probeable Problem (Explanation)',
    description: 'Student probes oracle, writes NL explanation',
  },
  refute: {
    editor: () => import('./RefuteProblemEditor.vue'),
    label: 'Refute: Find Counterexample',
    description: 'Student finds input that disproves a claim about a function',
  },
}

/**
 * Get the editor component loader for a problem type.
 */
export function getProblemEditor(type: string): EditorComponentLoader | undefined {
  return PROBLEM_EDITORS[type]?.editor
}

/**
 * Get the full definition for a problem type.
 */
export function getProblemEditorDefinition(type: string): ProblemEditorDefinition | undefined {
  return PROBLEM_EDITORS[type]
}

/**
 * Check if a problem type has a registered editor.
 */
export function isProblemTypeRegistered(type: string): boolean {
  return type in PROBLEM_EDITORS
}

/**
 * Get all registered problem types.
 */
export function getRegisteredProblemTypes(): string[] {
  return Object.keys(PROBLEM_EDITORS)
}

/**
 * Get the full registry (for iteration).
 */
export function getProblemEditorRegistry(): ProblemEditorRegistry {
  return { ...PROBLEM_EDITORS }
}

// Re-export types
export * from './types'

// Export the registry itself for direct access if needed
export { PROBLEM_EDITORS }
