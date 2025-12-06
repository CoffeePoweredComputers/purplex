/**
 * Type definitions for the admin problem editor registry.
 *
 * This follows the same pattern as ActivityComponentRegistry in
 * src/components/activities/index.ts for student-facing components.
 */

import type { Component } from 'vue'
import type { UseProblemEditorReturn } from '@/composables/admin'

/**
 * Props interface that ALL type-specific editors must accept.
 * The shell passes these via v-bind to the dynamic component.
 */
export interface ProblemEditorProps {
  /** The orchestrating composable - provides ALL state and methods */
  editor: UseProblemEditorReturn
  /** Current problem slug (null for new problems) */
  slug: string | null
  /** Whether currently editing vs creating */
  isEditing: boolean
}

/**
 * Events that type-specific editors can emit to the shell.
 */
export interface ProblemEditorEmits {
  (e: 'save'): void
  (e: 'test'): void
  (e: 'validation-change', isValid: boolean): void
}

/**
 * Component loader type - matches ActivityComponentRegistry pattern.
 * Returns a Promise for lazy loading / code splitting.
 */
export type EditorComponentLoader = () => Promise<{ default: Component }>

/**
 * Registry entry for a problem type editor.
 */
export interface ProblemEditorDefinition {
  /** Lazy loader for the editor component */
  editor: EditorComponentLoader
  /** Display label for the problem type */
  label: string
  /** Optional description shown in UI */
  description?: string
}

/**
 * The registry type - maps problem_type string to editor definition.
 */
export type ProblemEditorRegistry = Record<string, ProblemEditorDefinition>
