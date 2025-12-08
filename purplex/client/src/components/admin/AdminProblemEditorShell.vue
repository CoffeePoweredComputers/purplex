<template>
  <div class="admin-problem-editor">
    <!-- Breadcrumb navigation -->
    <nav class="breadcrumb border-default">
      <router-link
        to="/admin/problems"
        class="breadcrumb-link transition-fast"
      >
        ← Back to Problems
      </router-link>
    </nav>

    <div class="header rounded-lg border-default">
      <h2>{{ editor.isEditing.value ? 'Edit Problem' : 'Create New Problem' }}</h2>
      <div class="actions">
        <button
          :disabled="!canSave || editor.ui.ui.loading"
          class="btn btn-primary rounded-base"
          @click="handleSave"
        >
          {{ editor.ui.ui.loading ? 'Saving...' : 'Save Problem' }}
        </button>
      </div>
    </div>

    <form
      class="problem-form"
      @submit.prevent="handleSave"
    >
      <!-- Problem Type Selector - Always visible at top -->
      <div class="form-section rounded-lg border-default transition-fast">
        <h3>Problem Type</h3>
        <div class="form-group">
          <label for="problem_type">Select the type of problem to create</label>
          <select
            id="problem_type"
            :value="editor.form.form.problem_type"
            :disabled="editor.loadingTypes.value || editor.isEditing.value"
            @change="handleTypeChange"
          >
            <option
              v-for="actType in editor.availableTypes.value"
              :key="actType.type"
              :value="actType.type"
            >
              {{ actType.label }}
            </option>
          </select>
          <p
            v-if="editor.isEditing.value"
            class="type-locked-hint"
          >
            Problem type cannot be changed after creation
          </p>
        </div>
      </div>

      <!-- Dynamic Type-Specific Editor -->
      <Suspense>
        <component
          :is="currentEditorComponent"
          v-if="currentEditorComponent"
          ref="editorRef"
          :editor="editor"
          :slug="slugFromRoute"
          :is-editing="editor.isEditing.value"
          @save="handleSave"
          @test="handleTest"
          @validation-change="handleValidationChange"
        />
        <template #fallback>
          <div class="loading-editor">
            <div class="spinner" />
            <p>Loading editor...</p>
          </div>
        </template>
      </Suspense>
    </form>

    <!-- Notification toast integration -->
    <NotificationToast />
  </div>
</template>

<script setup lang="ts">
import { type Component, computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProblemEditor } from '@/composables/admin'
import { getProblemEditor } from './editors'
import NotificationToast from '@/components/NotificationToast.vue'
import { log } from '@/utils/logger'

// Router
const route = useRoute()
const router = useRouter()

// Use the orchestrator composable - this is the key integration
const editor = useProblemEditor()

// Template ref for the type-specific editor
const editorRef = ref<{ validate?: () => boolean } | null>(null)

// Local validation state (can be overridden by type-specific editor)
const isTypeEditorValid = ref(true)

// Get slug from route
const slugFromRoute = computed(() => route.params.slug as string | undefined ?? null)

// Dynamic component based on problem type
const currentEditorComponent = computed<Component | null>(() => {
  const problemType = editor.form.form.problem_type
  const loader = getProblemEditor(problemType)
  if (!loader) {
    log.warn(`No editor registered for problem type: ${problemType}`)
    return null
  }
  return defineAsyncComponent(loader)
})

// Can save computed - combines form validation with type-specific validation
const canSave = computed(() => {
  if (editor.ui.ui.loading) {return false}
  if (!isTypeEditorValid.value) {return false}

  // Basic validation - title required
  const title = (editor.form.form.title || '').toString().trim()
  if (!title) {return false}

  return true
})

// Watch route changes to load/reset problem
watch(slugFromRoute, async (newSlug, oldSlug) => {
  if (newSlug && newSlug !== oldSlug) {
    log.info('Loading problem from route', { slug: newSlug })
    await editor.loadProblem(newSlug)
  } else if (!newSlug && oldSlug) {
    log.info('Resetting editor for new problem')
    editor.reset()
  }
}, { immediate: true })

// Initialize on mount
onMounted(async () => {
  log.info('AdminProblemEditorShell mounted')

  // Load activity types and categories in parallel
  await Promise.all([
    editor.loadActivityTypes(),
    editor.categories.loadCategories(),
  ])

  log.info('Shell initialization complete', {
    availableTypes: editor.availableTypes.value.length,
    categories: editor.categories.categories.value.length,
  })
})

// Handle problem type change
function handleTypeChange(event: Event) {
  const select = event.target as HTMLSelectElement
  editor.form.updateField('problem_type', select.value)
}

// Handle save
async function handleSave() {
  if (!canSave.value) {
    log.warn('Cannot save - validation failed')
    return
  }

  // Call type-specific validation if available
  if (editorRef.value?.validate && !editorRef.value.validate()) {
    log.warn('Type-specific validation failed')
    return
  }

  try {
    const saved = await editor.saveProblem()

    // If creating new problem, navigate to edit mode
    if (!editor.isEditing.value && saved?.slug) {
      log.info('Created new problem, navigating to edit', { slug: saved.slug })
      router.push(`/admin/problems/${saved.slug}/edit`)
    }
  } catch (error) {
    log.error('Save failed', error)
  }
}

// Handle test
async function handleTest() {
  try {
    await editor.testProblem()
  } catch (error) {
    log.error('Test failed', error)
  }
}

// Handle validation change from type-specific editor
function handleValidationChange(isValid: boolean) {
  isTypeEditorValid.value = isValid
}
</script>

<style scoped>
/* Common Utilities */
.transition-fast {
  transition: var(--transition-fast);
}

.rounded-base {
  border-radius: var(--radius-base);
}

.rounded-lg {
  border-radius: var(--radius-lg);
}

.border-default {
  border: 2px solid var(--color-bg-border);
}

/* Main Container */
.admin-problem-editor {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: var(--spacing-lg);
  min-height: 100vh;
}

/* Navigation */
.breadcrumb {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-md) 0;
  border-bottom: 2px solid var(--color-bg-border);
}

.breadcrumb-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--color-text-muted);
  text-decoration: none;
  font-weight: 500;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-xs);
}

.breadcrumb-link:hover {
  background: var(--color-bg-hover);
}

/* Header Section */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xxl);
  padding: var(--spacing-xl);
  background: var(--color-bg-panel);
  box-shadow: var(--shadow-base);
}

.header h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
  font-weight: 600;
  margin: 0;
}

.actions {
  display: flex;
  gap: var(--spacing-md);
}

/* Button Styling */
.btn {
  padding: var(--spacing-md) var(--spacing-lg);
  border: 2px solid transparent;
  font-weight: 600;
  font-size: var(--font-size-base);
  cursor: pointer;
  transition: var(--transition-base);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  text-decoration: none;
  outline: none;
}

.btn:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-colored);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

/* Form Sections */
.problem-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xxl);
}

.form-section {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-base);
}

.form-section h3 {
  margin: 0 0 var(--spacing-xl) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-border);
}

/* Form Groups */
.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
}

.form-group select {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-base);
}

.form-group select:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

.form-group select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.type-locked-hint {
  margin-top: var(--spacing-sm);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-style: italic;
}

/* Loading Editor */
.loading-editor {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  border: 2px solid var(--color-bg-border);
}

.loading-editor p {
  margin-top: var(--spacing-md);
  color: var(--color-text-muted);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-bg-border);
  border-top-color: var(--color-primary-gradient-start);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
