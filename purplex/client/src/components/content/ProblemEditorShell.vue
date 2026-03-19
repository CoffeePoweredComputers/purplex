<template>
  <ContentEditorLayout
    :back-path="ctx.paths.problems.value"
    :back-label="ctx.isInstructor.value ? $t('admin.contentLayout.backToMyProblems') : $t('admin.contentLayout.backToProblems')"
    :show-header="false"
  >
    <div class="header rounded-lg border-default">
      <h2>{{ editor.isEditing.value ? $t('admin.problems.edit') : $t('admin.problems.create') }}</h2>
      <div class="actions">
        <button
          v-if="editor.isEditing.value"
          class="btn btn-danger"
          @click="handleDelete"
        >
          {{ $t('common.delete') }}
        </button>
        <button
          :disabled="!canSave || editor.ui.ui.loading"
          class="btn btn-primary rounded-base"
          @click="handleSave"
        >
          {{ editor.ui.ui.loading ? $t('admin.problems.saving') : $t('admin.problems.saveProblem') }}
        </button>
      </div>
    </div>

    <form class="problem-form" @submit.prevent="handleSave">
      <!-- Problem Type Selector - Always visible at top -->
      <div class="form-section rounded-lg border-default transition-fast">
        <h3>{{ $t('admin.problems.problemType') }}</h3>
        <div class="form-group">
          <label for="problem_type">{{ $t('admin.problems.selectType') }}</label>
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
          <p v-if="editor.isEditing.value" class="type-locked-hint">
            {{ $t('admin.problems.typeLockedHint') }}
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
            <p>{{ $t('admin.problems.loadingEditor') }}</p>
          </div>
        </template>
      </Suspense>
    </form>

    <!-- Delete confirmation dialog -->
    <div v-if="showDeleteDialog" class="dialog-overlay">
      <div class="dialog">
        <h3>{{ $t('admin.problems.deleteProblemConfirm') }}</h3>
        <p>
          {{ $t('admin.problems.deleteConfirmMessage', { title: editor.form.form.title }) }}
        </p>
        <div class="dialog-actions">
          <button class="btn btn-secondary" @click="showDeleteDialog = false">
            {{ $t('common.cancel') }}
          </button>
          <button class="btn btn-danger" @click="confirmDelete">
            {{ $t('common.delete') }}
          </button>
        </div>
      </div>
    </div>
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { type Component, computed, defineAsyncComponent, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { useProblemEditor } from '@/composables/admin';
import { getProblemEditor } from '@/components/admin/editors';
import { log } from '@/utils/logger';

// Router
const route = useRoute();
const router = useRouter();

const { t } = useI18n();

// Provide role-aware context (page-level components must provide, not inject)
const ctx = provideContentContext();

// Use the problem editor with context's API injected
const editor = useProblemEditor({ api: ctx.api.value });

// Template ref for the type-specific editor
const editorRef = ref<{ validate?: () => boolean } | null>(null);

// Local state
const isTypeEditorValid = ref(true);
const showDeleteDialog = ref(false);

// Get slug from route
const slugFromRoute = computed(() => (route.params.slug as string | undefined) ?? null);

// Dynamic component based on problem type
const currentEditorComponent = computed<Component | null>(() => {
  const problemType = editor.form.form.problem_type;
  const loader = getProblemEditor(problemType);
  if (!loader) {
    log.warn(`No editor registered for problem type: ${problemType}`);
    return null;
  }
  return defineAsyncComponent(loader);
});

// Can save computed - combines form validation with type-specific validation
const canSave = computed(() => {
  if (editor.ui.ui.loading) {
    return false;
  }
  if (!isTypeEditorValid.value) {
    return false;
  }

  // Basic validation - title required
  const title = (editor.form.form.title || '').toString().trim();
  return Boolean(title);
});

// Watch route changes to load/reset problem
watch(
  slugFromRoute,
  async (newSlug, oldSlug) => {
    if (newSlug && newSlug !== oldSlug) {
      log.info('Loading problem from route', { slug: newSlug });
      await editor.loadProblem(newSlug);
    } else if (!newSlug && oldSlug) {
      log.info('Resetting editor for new problem');
      editor.reset();
    }
  },
  { immediate: true }
);

// Initialize on mount
onMounted(async () => {
  log.info('ProblemEditorShell mounted', { role: ctx.role.value });

  // Load activity types and categories in parallel
  await Promise.all([
    editor.loadActivityTypes(),
    editor.categories.loadCategories(),
  ]);

  // If creating new, set default type
  if (!slugFromRoute.value && editor.availableTypes.value.length > 0) {
    editor.form.setField('problem_type', editor.availableTypes.value[0].type);
  }

  log.info('Shell initialization complete', {
    availableTypes: editor.availableTypes.value.length,
    categories: editor.categories.categories.value.length,
  });
});

// Event handlers
function handleTypeChange(event: Event) {
  const select = event.target as HTMLSelectElement;
  editor.form.updateField('problem_type', select.value);
}

function handleValidationChange(isValid: boolean) {
  isTypeEditorValid.value = isValid;
}

async function handleSave() {
  if (!canSave.value) {
    log.warn('Cannot save - validation failed');
    return;
  }

  // Call type-specific validation if available
  if (editorRef.value?.validate && !editorRef.value.validate()) {
    log.warn('Type-specific validation failed');
    return;
  }

  try {
    const saved = await editor.saveProblem();

    // If creating new problem, navigate to edit mode
    if (!editor.isEditing.value && saved?.slug) {
      log.info('Created new problem, navigating to edit', { slug: saved.slug });
      router.push(ctx.paths.editProblem(saved.slug));
    }
  } catch (error) {
    log.error('Save failed', error);
  }
}

async function handleTest() {
  try {
    await editor.testProblem();
  } catch (error) {
    log.error('Test failed', error);
  }
}

function handleDelete() {
  showDeleteDialog.value = true;
}

async function confirmDelete() {
  if (!editor.currentSlug.value) {
    return;
  }

  showDeleteDialog.value = false;

  try {
    editor.ui.setLoading(true);
    await ctx.api.value.deleteProblem(editor.currentSlug.value);
    editor.ui.setSuccess(t('admin.problems.problemDeleted'));
    ctx.navigateToList('problems');
  } catch (error) {
    log.error('Failed to delete problem', error);
    editor.ui.setError(t('admin.problems.failedToDeleteProblem'));
  } finally {
    editor.ui.setLoading(false);
  }
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
  border-radius: var(--radius-base);
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
  box-shadow: 0 8px 25px var(--color-primary-glow);
}

.btn-secondary {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border-color: var(--color-bg-border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.btn-danger {
  background: var(--color-error-bg);
  color: var(--color-error);
  border-color: var(--color-error);
}

.btn-danger:hover:not(:disabled) {
  background: var(--color-error);
  color: var(--color-text-primary);
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

/* Dialog */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  max-width: 400px;
  width: 90%;
  box-shadow: var(--shadow-lg);
}

.dialog h3 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--color-text-primary);
}

.dialog p {
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-lg);
}

.dialog-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
}
</style>
