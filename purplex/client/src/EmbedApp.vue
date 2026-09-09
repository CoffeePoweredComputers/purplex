<template>
  <div
    ref="rootEl"
    class="embed-page"
  >
    <div
      v-if="loading"
      class="embed-state"
    >
      <div class="loading-spinner" />
      <p>{{ t('embed.loading') }}</p>
    </div>
    <div
      v-else-if="error"
      class="embed-state embed-state--error"
    >
      <p class="embed-error-title">
        {{ t('embed.error.title') }}
      </p>
      <p class="embed-error-body">
        {{ error }}
      </p>
    </div>
    <div
      v-else-if="problem"
      class="embed-problem"
    >
      <h1 class="embed-problem__title">
        {{ problem.title }}
      </h1>

      <!-- eslint-disable vue/no-v-html -- admin-authored markdown rendered via marked() -->
      <div
        v-if="problem.description"
        class="embed-problem__description"
        v-html="renderedDescription"
      />
      <!-- eslint-enable vue/no-v-html -->

      <div class="embed-problem__input">
        <InputSelector
          v-model="inputValue"
          :activity-type="problem.problem_type"
          :problem="problem"
          :disabled="submitting"
          @submit="handleSubmit"
        />
      </div>

      <p
        v-if="submitError"
        class="embed-submit-error"
      >
        {{ submitError }}
      </p>

      <div
        v-if="submitting"
        class="embed-state embed-state--inline"
      >
        <div class="loading-spinner" />
        <p>{{ t('embed.submitting') }}</p>
      </div>

      <FeedbackSelector
        v-if="hasResult"
        class="embed-problem__feedback"
        :activity-type="problem.problem_type"
        :progress="feedback.promptCorrectness"
        :notches="6"
        :code-results="feedback.codeResults as never"
        :test-results="feedback.testResults as never"
        :comprehension-results="feedback.comprehensionResults"
        :user-prompt="feedback.userPrompt"
        :segmentation="feedback.segmentationData as never"
        :reference-code="problem.reference_solution || ''"
        :segmentation-enabled="problem.feedback_config?.show_segmentation === true"
        :is-loading="submitting"
        :title="t('embed.results')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Chromeless single-problem shell for the embed Vite entry (embed.html).
 *
 * No NavBar/footer/modals, no vue-router, no Vuex — the LMS host page is
 * the surrounding "chrome". This component owns only the composition: it
 * loads the problem, hands input to the activity registry's components,
 * delegates submit->SSE->completion to useEmbedSubmission (#145), and routes
 * everything host-facing through useSpliceBridge (#144).
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { marked } from 'marked'
import InputSelector from '@/components/activities/InputSelector.vue'
import FeedbackSelector from '@/components/activities/FeedbackSelector.vue'
import type { ActivityProblem } from '@/components/activities/types'
import { getEmbedProblem } from '@/services/embedService'
import { useSpliceBridge } from '@/composables/useSpliceBridge'
import { useEmbedSubmission } from '@/composables/useEmbedSubmission'
import { isEmbeddableType, restoreInputFromState } from '@/embed/adapters'
import { log } from '@/utils/logger'

const { t } = useI18n()

const rootEl = ref<HTMLElement | null>(null)
const loading = ref(true)
const error = ref('')
const problem = ref<ActivityProblem | null>(null)
const inputValue = ref('')
// Tracks whether the learner has typed, so a late-arriving host state never
// clobbers work in progress.
const inputDirty = ref(false)

const bridge = useSpliceBridge()

const {
  submitting,
  error: submitError,
  feedback,
  hasResult,
  submit,
} = useEmbedSubmission({
  problem,
  onCompleted: (result, state) => {
    // Submission.score is 0-100; the bridge normalizes it to SPLICE's 0..1.
    bridge.reportScoreAndState(result.score ?? 0, state)
  },
  onTelemetry: (event) => bridge.sendEvent(event.name, event.data),
  onFailed: (message) => bridge.sendEvent('submission.failed', null, message),
})

const renderedDescription = computed(() =>
  problem.value?.description ? marked.parse(problem.value.description) : '',
)

function applyLaunchTheme(): void {
  const theme = new URLSearchParams(window.location.search).get('theme')
  if (theme === 'light' || theme === 'dark') {
    document.documentElement.setAttribute('data-theme', theme)
  }
}

async function loadProblem(): Promise<void> {
  const slug = new URLSearchParams(window.location.search).get('problem')

  if (!slug) {
    error.value = t('embed.error.missingSlug')
    loading.value = false
    return
  }

  try {
    const loaded = await getEmbedProblem(slug)

    // The embed is scoped to the EiPL + Probeable families. Anything else has
    // no adapter, so refuse it here rather than rendering an input that can
    // never report a score back to the host.
    if (!isEmbeddableType(loaded.problem_type)) {
      error.value = t('embed.error.unsupportedType', { type: loaded.problem_type })
      bridge.sendEvent('problem.unsupported', { problem_type: loaded.problem_type })
      return
    }

    problem.value = loaded
  } catch (err) {
    log.error('Failed to load embed problem', err)
    error.value = t('embed.error.body')
  } finally {
    loading.value = false
  }
}

function handleSubmit(): void {
  submit(inputValue.value)
}

watch(inputValue, () => {
  inputDirty.value = true
})

/**
 * Restore the learner's previous answer once the host replies to getState.
 *
 * Render is never blocked on this — per the SPLICE spec the response "may not
 * even return" — so it arrives (or doesn't) independently of the problem load.
 */
watch([() => bridge.restoredState.value, problem], ([state, loaded]) => {
  if (!state || !loaded || inputDirty.value || hasResult.value) {
    return
  }

  const restored = restoreInputFromState(state, loaded.slug)
  if (restored === null) {
    return
  }

  inputValue.value = restored
  // Restoring is not the learner typing; keep accepting later host state.
  inputDirty.value = false
})

onMounted(() => {
  applyLaunchTheme()
  loadProblem()
  bridge.observeElement(rootEl.value)
})
</script>

<style scoped>
.embed-page {
  padding: var(--spacing-lg);
}

.embed-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  min-height: 60vh;
  text-align: center;
  color: var(--color-text-muted);
}

/* Inline variant sits between the input and the results, so it must not
   claim the 60vh the standalone loading/error states use. */
.embed-state--inline {
  min-height: 0;
  padding: var(--spacing-lg) 0;
}

.embed-state--error {
  color: var(--color-error);
}

.embed-error-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  margin: 0;
}

.embed-error-body {
  margin: 0;
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--color-bg-input);
  border-top-color: var(--color-primary-gradient-start);
  border-radius: var(--radius-circle);
  animation: embed-spin 0.8s linear infinite;
}

@keyframes embed-spin {
  to { transform: rotate(360deg); }
}

.embed-problem__title {
  font-size: var(--font-size-lg);
  margin: 0 0 var(--spacing-md);
  color: var(--color-text-primary);
}

.embed-problem__description {
  margin-bottom: var(--spacing-lg);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.embed-problem__feedback {
  margin-top: var(--spacing-lg);
}

.embed-submit-error {
  margin: var(--spacing-md) 0 0;
  color: var(--color-error);
}
</style>
