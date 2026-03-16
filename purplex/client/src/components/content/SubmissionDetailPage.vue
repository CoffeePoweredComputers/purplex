<template>
  <ContentEditorLayout
    :page-title="pageTitle"
    :back-path="backPath"
    :back-label="$t('admin.submissions.backToSubmissions')"
    :show-header="true"
    :show-breadcrumb="true"
  >
    <div v-if="loading" class="loading-state">
      {{ $t('admin.submissions.loadingDetails') }}
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchSubmission">
        {{ $t('common.retry') }}
      </button>
    </div>

    <template v-else-if="submission">
      <!-- Metrics bar -->
      <div class="metrics-bar">
        <div class="metric">
          <span class="metric-label">{{ $t('admin.submissions.score') }}</span>
          <span class="metric-value" :class="getScoreClass(submission.score)">
            {{ submission.score || 0 }}%
          </span>
        </div>
        <div class="metric">
          <span class="metric-label">{{ $t('admin.submissions.status') }}</span>
          <span class="metric-value">
            {{ submission.completion_status || submission.status || $t('admin.submissions.unknown') }}
          </span>
        </div>
        <div class="metric">
          <span class="metric-label">{{ $t('admin.submissions.typeLabel') }}</span>
          <span class="metric-value type-badge">{{ formatType(submission.submission_type) }}</span>
        </div>
        <div v-if="submission.execution_time_ms" class="metric">
          <span class="metric-label">{{ $t('admin.submissions.time') }}</span>
          <span class="metric-value">{{ $t('common.units.ms', { value: submission.execution_time_ms }) }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">{{ $t('admin.submissions.studentLabel') }}</span>
          <span class="metric-value">{{ submission.user }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">{{ $t('admin.submissions.problemLabel') }}</span>
          <span class="metric-value">{{ submission.problem?.title || submission.problem }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">{{ $t('admin.submissions.submittedLabel') }}</span>
          <span class="metric-value">{{ formatDate(submission.submitted_at) }}</span>
        </div>
      </div>

      <!-- Type-specific + generic content reusing the modal's SubmissionDetailContent -->
      <SubmissionDetailContent :submission="(submission as Record<string, unknown>)">
        <!-- Generic code + tests layout -->
        <div class="full-page-content">
          <!-- NL Prompt -->
          <div v-if="submission.raw_input" class="code-section">
            <div class="section-header">
              <span class="section-title">{{ $t('admin.submissions.naturalLanguagePrompt') }}</span>
            </div>
            <div class="prompt-box">{{ submission.raw_input }}</div>
          </div>

          <!-- Variation nav -->
          <div v-if="hasVariations" class="variation-nav">
            <span class="variation-label">
              {{ $t('admin.submissions.variationOf', { current: currentVariationIndex + 1, total: variationsCount }) }}
            </span>
            <div class="nav-controls">
              <button
                class="nav-btn"
                :disabled="currentVariationIndex === 0"
                @click="currentVariationIndex--"
              >
                {{ $t('admin.submissions.previous') }}
              </button>
              <button
                class="nav-btn"
                :disabled="currentVariationIndex >= variationsCount - 1"
                @click="currentVariationIndex++"
              >
                {{ $t('admin.submissions.next') }}
              </button>
            </div>
          </div>

          <!-- Code editor -->
          <div class="code-section">
            <div class="section-header">
              <span class="section-title">
                {{ hasVariations ? $t('admin.submissions.generatedCodeVariation', { index: currentVariationIndex + 1 }) : (submission.raw_input ? $t('admin.submissions.generatedCode') : $t('admin.submissions.submittedCode')) }}
              </span>
            </div>
            <Editor
              :value="currentCode || t('admin.submissions.noCodeAvailable')"
              :read-only="true"
              height="450px"
              width="100%"
              theme="tomorrow_night"
            />
          </div>

          <!-- Test results -->
          <div v-if="currentTests.length > 0" class="code-section">
            <div class="section-header">
              <span class="section-title">
                {{ $t('admin.submissions.testResults', { passing: currentTests.filter(tc => tc.passed || tc.isSuccessful).length, total: currentTests.length }) }}
              </span>
            </div>
            <div class="test-list">
              <div
                v-for="(test, i) in currentTests"
                :key="i"
                class="test-item"
                :class="(test.passed || test.isSuccessful) ? 'passing' : 'failing'"
              >
                <span class="test-status">{{ (test.passed || test.isSuccessful) ? '&#10003;' : '&#10007;' }}</span>
                <code class="test-call">{{ test.description || `${$t('admin.submissions.testCase')} ${i + 1}` }}</code>
                <template v-if="!(test.passed || test.isSuccessful)">
                  <span class="test-expected">{{ $t('admin.submissions.expected') }} {{ formatValue(test.expected_output || test.expected) }}</span>
                  <span class="test-actual">{{ $t('admin.submissions.got') }} {{ formatValue(test.actual_output || test.actual) }}</span>
                </template>
              </div>
            </div>
          </div>

          <!-- Segmentation -->
          <div v-if="submission.segmentation" class="code-section">
            <div class="section-header">
              <span class="section-title">{{ $t('admin.submissions.segmentationAnalysis') }}</span>
            </div>
            <div class="segmentation-info">
              <div class="seg-metric">
                <span>{{ $t('admin.submissions.comprehension') }}</span>
                <strong>{{ submission.segmentation.comprehension_level }}</strong>
              </div>
              <div class="seg-metric">
                <span>{{ $t('admin.submissions.segments') }}</span>
                <strong>{{ submission.segmentation.segment_count }}</strong>
                ({{ $t('admin.submissions.threshold', { value: submission.segmentation.threshold }) }})
              </div>
              <div v-if="submission.segmentation.feedback_message" class="seg-feedback">
                {{ submission.segmentation.feedback_message }}
              </div>
            </div>
          </div>
        </div>
      </SubmissionDetailContent>
    </template>
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import Editor from '@/features/editor/Editor.vue';
import SubmissionDetailContent from '@/modals/submission-detail/SubmissionDetailContent.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { formatTestValue } from '@/utils/testValueFormatter';
import { log } from '@/utils/logger';

const ctx = provideContentContext();
const route = useRoute();
const { t } = useI18n();

const submissionId = computed(() => route.params.submissionId as string);
const courseId = computed(() => route.params.courseId as string | undefined);

const submission = ref<Record<string, unknown> | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const currentVariationIndex = ref(0);

const pageTitle = computed(() => {
  if (!submission.value) return t('admin.submissions.title');
  const problem = submission.value.problem as { title?: string } | string | undefined;
  const title = typeof problem === 'object' ? problem?.title : problem;
  return t('admin.submissions.submissionTitle', { title: title || t('admin.submissions.unknown') });
});

const backPath = computed(() => {
  if (courseId.value) {
    return ctx.isAdmin.value
      ? `/admin/courses/${courseId.value}/submissions`
      : `/instructor/courses/${courseId.value}/submissions`;
  }
  return ctx.isAdmin.value ? '/admin/submissions' : '/instructor';
});

// Variation helpers
const variations = computed(() =>
  (submission.value?.code_variations as Array<Record<string, unknown>>) || []
);

const hasVariations = computed(() => variations.value.length > 1);
const variationsCount = computed(() => variations.value.length || 1);

const currentCode = computed(() => {
  if (hasVariations.value && variations.value[currentVariationIndex.value]) {
    return (variations.value[currentVariationIndex.value].code as string) || '';
  }
  return (submission.value?.processed_code as string) || (submission.value?.raw_input as string) || '';
});

const currentTests = computed(() => {
  if (hasVariations.value && variations.value[currentVariationIndex.value]) {
    return (variations.value[currentVariationIndex.value].test_results as Array<Record<string, unknown>>) || [];
  }
  return (submission.value?.test_results as Array<Record<string, unknown>>) || [];
});

async function fetchSubmission(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    const data = await ctx.api.value.getSubmission(submissionId.value as unknown as number, courseId.value);
    submission.value = data as unknown as Record<string, unknown>;
  } catch (err) {
    log.error('Failed to load submission', { error: err, submissionId: submissionId.value });
    error.value = t('admin.submissions.failedToLoad');
  } finally {
    loading.value = false;
  }
}

function getScoreClass(score: number | undefined): string {
  if (!score) return 'error';
  if (score >= 100) return 'success';
  if (score >= 60) return 'warning';
  return 'error';
}

function formatType(type: string | undefined): string {
  const map: Record<string, string> = {
    eipl: 'EiPL', mcq: 'MCQ', prompt: 'Prompt', refute: 'Refute',
    debug_fix: 'Debug Fix', probeable_code: 'Probeable Code', probeable_spec: 'Probeable Spec',
  };
  return type ? (map[type] || type) : '';
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return t('admin.submissions.unknown');
  return new Date(dateStr as string).toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

function formatValue(value: unknown): string {
  return formatTestValue(value);
}

onMounted(fetchSubmission);
</script>

<style scoped>
.loading-state,
.error-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-secondary);
  font-size: 16px;
}

.retry-btn {
  margin-top: 16px;
  padding: 8px 20px;
  background: var(--color-primary-gradient-start);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.metrics-bar {
  display: flex;
  gap: 24px;
  padding: 16px 20px;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: 8px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.metric {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.metric-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.metric-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.metric-value.success { color: var(--color-success); }
.metric-value.warning { color: var(--color-warning); }
.metric-value.error { color: var(--color-error); }

.type-badge {
  padding: 1px 6px;
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.full-page-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.code-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.prompt-box {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-text-primary);
}

.variation-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
}

.variation-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.nav-controls {
  display: flex;
  gap: 8px;
}

.nav-btn {
  padding: 6px 12px;
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  color: var(--color-text-primary);
}

.nav-btn:hover:not(:disabled) {
  background: var(--color-bg-input);
}

.nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.test-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.test-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid var(--color-bg-input);
  flex-wrap: wrap;
}

.test-item.passing {
  background: var(--color-success-bg);
  border-color: rgba(76, 175, 80, 0.3);
}

.test-item.failing {
  background: var(--color-error-bg);
  border-color: rgba(220, 53, 69, 0.3);
}

.test-status {
  font-weight: 700;
  font-size: 14px;
}

.test-item.passing .test-status { color: var(--color-success); }
.test-item.failing .test-status { color: var(--color-error); }

.test-call {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  color: var(--color-text-primary);
}

.test-expected,
.test-actual {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-family: monospace;
}

.segmentation-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: 4px;
}

.seg-metric {
  font-size: 14px;
  color: var(--color-text-primary);
}

.seg-metric span {
  color: var(--color-text-secondary);
  margin-right: 8px;
}

.seg-feedback {
  font-size: 13px;
  color: var(--color-text-primary);
  line-height: 1.5;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--color-bg-input);
}
</style>
