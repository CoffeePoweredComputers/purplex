/**
 * Activity Component Registry
 *
 * Provides dynamic loading of activity-type-specific components.
 * New activity types register their input and feedback components here.
 *
 * Usage:
 *   import { getActivityInput, getActivityFeedback, isActivityTypeRegistered } from '@/components/activities'
 *
 *   // In a component
 *   const InputComponent = computed(() =>
 *     isActivityTypeRegistered(problemType) ? getActivityInput(problemType) : null
 *   )
 */

import { type Component, defineAsyncComponent } from 'vue'
import type { ActivityComponentRegistry } from './types'
import AsyncLoader from '@/components/ui/AsyncLoader.vue'
import AsyncError from '@/components/ui/AsyncError.vue'
import { log } from '@/utils/logger'

// Re-export types for convenience
export * from './types'

/**
 * Registry of activity-type-specific components.
 *
 * To add a new activity type:
 * 1. Create input component in ./inputs/
 * 2. Create feedback component in ./feedback/
 * 3. Add entry here with lazy loaders
 */
const ACTIVITY_COMPONENTS: ActivityComponentRegistry = {
  eipl: {
    input: () => import('./inputs/EiplInput.vue'),
    feedback: () => import('./feedback/EiplFeedback.vue'),
  },
  mcq: {
    input: () => import('./inputs/McqInput.vue'),
    feedback: () => import('./feedback/McqFeedback.vue'),
  },
}

/**
 * Check if an activity type has registered components.
 *
 * @param activityType - The activity type identifier (e.g., 'eipl')
 * @returns true if the type has registered components
 */
export function isActivityTypeRegistered(activityType: string): boolean {
  return activityType in ACTIVITY_COMPONENTS
}

/**
 * Get the input component for an activity type.
 *
 * Returns an async component that will be loaded on demand.
 *
 * @param activityType - The activity type identifier
 * @returns Async component for the input, or undefined if not registered
 */
export function getActivityInput(activityType: string): Component | undefined {
  const definition = ACTIVITY_COMPONENTS[activityType]
  if (!definition) {
    log.warn(`No input component registered for activity type: ${activityType}`)
    return undefined
  }

  return defineAsyncComponent({
    loader: definition.input,
    loadingComponent: AsyncLoader,
    errorComponent: AsyncError,
    delay: 200,
    timeout: 10000,
  })
}

/**
 * Get the feedback component for an activity type.
 *
 * Returns an async component that will be loaded on demand.
 *
 * @param activityType - The activity type identifier
 * @returns Async component for feedback, or undefined if not registered
 */
export function getActivityFeedback(activityType: string): Component | undefined {
  const definition = ACTIVITY_COMPONENTS[activityType]
  if (!definition) {
    log.warn(`No feedback component registered for activity type: ${activityType}`)
    return undefined
  }

  return defineAsyncComponent({
    loader: definition.feedback,
    loadingComponent: AsyncLoader,
    errorComponent: AsyncError,
    delay: 200,
    timeout: 10000,
  })
}
