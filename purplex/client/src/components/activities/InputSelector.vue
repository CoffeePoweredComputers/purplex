<template>
  <!--
    InputSelector renders the activity input component directly.
    No wrapper - the loaded component's elements become children of the parent.
    Parent (.submission-section) provides the panel chrome.
  -->
  <component
    :is="InputComponent"
    v-if="InputComponent"
    :key="activityType"
    v-model="inputValue"
    :problem="problem"
    :disabled="disabled"
    :theme="theme"
    :draft-saved="draftSaved"
    @submit="$emit('submit')"
  />
  <div
    v-else
    class="activity-input-fallback"
  >
    <p>{{ $t('problems.activity.unknownType', { type: activityType }) }}</p>
  </div>
</template>

<script setup lang="ts">
/**
 * InputSelector - Dynamic activity input component loader.
 *
 * Loads the appropriate input component based on the activity type.
 * Renders the component directly without any wrapper - parent provides the container.
 */
import { computed } from 'vue'
import { getActivityInput, isActivityTypeRegistered } from './index'
import type { ActivityProblem } from './types'

interface Props {
  /** Activity type identifier (e.g., 'eipl') */
  activityType: string
  /** User's current input value (v-model) */
  modelValue: string
  /** Current problem data */
  problem: ActivityProblem
  /** Whether input is disabled */
  disabled?: boolean
  /** Editor theme name */
  theme?: string
  /** Whether draft has been saved */
  draftSaved?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  theme: 'dark',
  draftSaved: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}>()

// Computed property for v-model binding
const inputValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})

// Get the appropriate input component for the activity type
const InputComponent = computed(() => {
  if (!isActivityTypeRegistered(props.activityType)) {
    return null
  }
  return getActivityInput(props.activityType)
})
</script>

<style scoped>
.activity-input-fallback {
  padding: var(--spacing-lg);
  text-align: center;
  color: var(--color-text-muted);
}
</style>
