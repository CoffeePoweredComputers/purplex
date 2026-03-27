<template>
  <div class="submission-detail-content">
    <!-- Type-specific content (before the generic code/test layout) -->
    <div
      v-if="hasTypeData"
      class="type-specific-section"
    >
      <McqDetail
        v-if="submissionType === 'mcq'"
        :type-data="(submission.type_data as McqTypeData)"
      />
      <RefuteDetail
        v-else-if="submissionType === 'refute'"
        :type-data="(submission.type_data as RefuteTypeData)"
        :submission="submission"
      />
      <DebugFixDetail
        v-else-if="submissionType === 'debug_fix'"
        :type-data="(submission.type_data as DebugFixTypeData)"
        :submission="submission"
      />
      <PromptDetail
        v-else-if="submissionType === 'prompt'"
        :type-data="(submission.type_data as PromptTypeData)"
        :submission="submission"
      />
      <ProbeableCodeDetail
        v-else-if="submissionType === 'probeable_code'"
        :type-data="(submission.type_data as ProbeableTypeData)"
        :submission="submission"
      />
      <ProbeableSpecDetail
        v-else-if="submissionType === 'probeable_spec'"
        :type-data="(submission.type_data as ProbeableTypeData)"
        :submission="submission"
      />
    </div>

    <!-- Generic code + test results layout (for types that have code/tests) -->
    <div
      v-if="showGenericLayout"
      class="generic-layout"
    >
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import McqDetail from './types/McqDetail.vue';
import RefuteDetail from './types/RefuteDetail.vue';
import DebugFixDetail from './types/DebugFixDetail.vue';
import PromptDetail from './types/PromptDetail.vue';
import ProbeableCodeDetail from './types/ProbeableCodeDetail.vue';
import ProbeableSpecDetail from './types/ProbeableSpecDetail.vue';
import type {
  DebugFixTypeData,
  McqTypeData,
  ProbeableTypeData,
  PromptTypeData,
  RefuteTypeData,
} from '@/types';

const props = defineProps<{
  submission: Record<string, unknown>;
}>();

const submissionType = computed(() =>
  (props.submission?.submission_type as string) || ''
);

const hasTypeData = computed(() => {
  const td = props.submission?.type_data as Record<string, unknown> | undefined;
  return td && Object.keys(td).length > 0;
});

// MCQ and Refute don't show generic code/test layout — they have their own display
// All other types show the generic two-column code+tests layout
const showGenericLayout = computed(() => {
  if (!submissionType.value) {return true;}
  return !['mcq', 'refute'].includes(submissionType.value);
});
</script>

<style scoped>
.submission-detail-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.type-specific-section {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-bg-input);
}

/* When MCQ/Refute have no generic layout following, remove border */
.type-specific-section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
</style>
