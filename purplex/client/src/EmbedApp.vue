<template>
  <div class="embed-page">
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
      <InputSelector
        v-model="inputValue"
        :activity-type="problem.problem_type"
        :problem="problem"
        :disabled="submitting"
        @submit="handleSubmit"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Chromeless single-problem shell for the embed Vite entry (embed.html).
 *
 * No NavBar/footer/modals, no vue-router, no Vuex — the LMS host page is
 * the surrounding "chrome". Submit -> SSE -> completion wiring lands in
 * #145 (F3); this component only renders the problem and its input.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import InputSelector from '@/components/activities/InputSelector.vue'
import type { ActivityProblem } from '@/components/activities/types'
import { getEmbedProblem } from '@/services/embedService'
import { log } from '@/utils/logger'

const { t } = useI18n()

const loading = ref(true)
const error = ref('')
const problem = ref<ActivityProblem | null>(null)
const inputValue = ref('')
const submitting = ref(false)

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
    problem.value = await getEmbedProblem(slug)
  } catch (err) {
    log.error('Failed to load embed problem', err)
    error.value = t('embed.error.body')
  } finally {
    loading.value = false
  }
}

function handleSubmit(): void {
  // Submit -> SSE -> completion orchestration lands in #145 (F3).
  log.warn(t('embed.submitNotReady'))
}

onMounted(() => {
  applyLaunchTheme()
  loadProblem()
})
</script>

<style scoped>
.embed-page {
  min-height: 100vh;
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
  margin: 0 0 var(--spacing-lg);
  color: var(--color-text-primary);
}
</style>
