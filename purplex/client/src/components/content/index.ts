/**
 * Content Management Components
 *
 * Unified components for content management that work across admin and instructor roles.
 * These components use useContentContext() to determine role-specific behavior.
 */

export { default as ContentEditorLayout } from './ContentEditorLayout.vue';
export { default as ProblemList } from './ProblemList.vue';
export { default as ProblemEditorShell } from './ProblemEditorShell.vue';
export { default as ProblemSetManager } from './ProblemSetManager.vue';

// Re-export type-specific editors from admin folder (they're role-agnostic)
export { getProblemEditor, isProblemTypeRegistered } from '@/components/admin/editors';
