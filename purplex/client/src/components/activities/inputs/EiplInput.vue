<template>
  <DescriptionInput
    v-model="inputValue"
    :problem="problem"
    :disabled="disabled"
    :theme="theme"
    :draft-saved="draftSaved"
    :section-label="t('problems.eipl.sectionLabel')"
    @submit="$emit('submit')"
  />
</template>

<script setup lang="ts">
/**
 * EiplInput - Input component for EiPL (Explain in Plain Language) activities.
 *
 * Thin wrapper around DescriptionInput with EiPL-specific label.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import DescriptionInput from './DescriptionInput.vue'
import type { ActivityProblem } from '../types'

interface Props {
  /** User's input text (v-model) */
  modelValue: string
  /** Current problem data */
  problem: ActivityProblem
  /** Whether input is disabled (during submission) */
  disabled?: boolean
  /** Editor theme */
  theme?: string
  /** Whether draft has been saved */
  draftSaved?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  theme: 'dark',
  draftSaved: false,
})

const { t } = useI18n()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}>()

// Computed value for v-model binding
const inputValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})
</script>
