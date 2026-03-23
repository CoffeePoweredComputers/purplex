<template>
  <ContentEditorLayout
    :back-path="ctx.paths.problemSets.value"
    :back-label="ctx.isInstructor.value ? $t('admin.contentLayout.backToMyProblemSets') : $t('admin.contentLayout.backToProblemSets')"
    :show-header="false"
  >
    <!-- Header -->
    <div class="header rounded-lg border-default">
      <h2>{{ isEditing ? $t('admin.problemSets.editProblemSet') : $t('admin.problemSets.createProblemSet') }}</h2>
      <div class="actions">
        <button
          v-if="isEditing"
          class="btn btn-danger"
          @click="handleDelete"
        >
          {{ $t('common.delete') }}
        </button>
        <button
          :disabled="!canSave || saving"
          class="btn btn-primary rounded-base"
          @click="handleSave"
        >
          {{ saving ? $t('admin.problemSets.saving') : $t('admin.problemSets.saveProblemSet') }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="spinner" />
      <p>{{ $t('admin.problemSets.loading') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- Form -->
    <form v-else class="problem-set-form" @submit.prevent="handleSave">
      <!-- Basic Info Section -->
      <div class="form-section rounded-lg border-default">
        <h3>{{ $t('admin.problemSets.basicInfo') }}</h3>

        <div class="form-row">
          <div class="form-group flex-grow">
            <label for="title">{{ $t('admin.problemSets.titleLabel') }}</label>
            <input
              id="title"
              v-model="formData.title"
              type="text"
              required
              :placeholder="$t('admin.problemSets.titlePlaceholder')"
            />
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="formData.is_public" type="checkbox" />
              <span>{{ $t('admin.problemSets.public') }}</span>
            </label>
          </div>
        </div>

        <div class="form-group">
          <label for="description">{{ $t('admin.problemSets.descriptionLabel') }}</label>
          <textarea
            id="description"
            v-model="formData.description"
            rows="3"
            :placeholder="$t('admin.problemSets.descriptionPlaceholder')"
          />
        </div>
      </div>

      <!-- Problems Section -->
      <div class="form-section rounded-lg border-default">
        <h3>{{ $t('admin.problemSets.problemsSection') }}</h3>

        <div v-if="loadingProblems" class="problems-loading">
          <div class="spinner-small" />
          <span>{{ $t('admin.problemSets.loadingProblems') }}</span>
        </div>

        <div v-else class="problems-container">
          <!-- Selected problems (sortable list) -->
          <div class="selected-problems-section">
            <label class="section-label">{{ $t('admin.problemSets.selectedProblems', { count: selectedProblemSlugs.length }) }}</label>
            <div class="selected-problems">
              <div v-if="selectedProblemSlugs.length === 0" class="no-problems">
                {{ $t('admin.problemSets.noProblemsSelected') }}
              </div>
              <div
                v-for="(slug, index) in selectedProblemSlugs"
                :key="slug"
                class="problem-item selected"
              >
                <span class="problem-order">{{ index + 1 }}</span>
                <span class="problem-title">{{ getProblemTitle(slug) }}</span>
                <span class="problem-type">{{ getProblemType(slug) }}</span>
                <div class="problem-actions">
                  <button
                    type="button"
                    class="move-btn"
                    :disabled="index === 0"
                    :title="$t('admin.problemSets.moveUp')"
                    @click="moveProblem(index, -1)"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    class="move-btn"
                    :disabled="index === selectedProblemSlugs.length - 1"
                    :title="$t('admin.problemSets.moveDown')"
                    @click="moveProblem(index, 1)"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    class="remove-btn"
                    :title="$t('common.remove')"
                    @click="removeProblem(slug)"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Available problems -->
          <div class="available-problems-section">
            <label class="section-label">{{ $t('admin.problemSets.availableProblems') }}</label>
            <input
              v-model="problemSearch"
              type="text"
              class="problem-search"
              :placeholder="$t('admin.problemSets.searchProblems')"
            />
            <div class="problem-list">
              <div
                v-for="problem in filteredAvailableProblems"
                :key="problem.slug"
                class="problem-item available"
                @click="addProblem(problem.slug)"
              >
                <span class="problem-title">{{ problem.title }}</span>
                <span class="problem-type">{{ problem.problem_type }}</span>
                <span class="add-indicator">+</span>
              </div>
              <div v-if="filteredAvailableProblems.length === 0" class="no-problems">
                {{ problemSearch ? $t('admin.problemSets.noMatchingProblems') : $t('admin.problemSets.allProblemsAdded') }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </form>

    <!-- Delete Confirmation Dialog -->
    <div v-if="showDeleteDialog" class="dialog-overlay">
      <div class="dialog">
        <h3>{{ $t('admin.problemSets.deleteProblemSet') }}</h3>
        <p>
          {{ $t('admin.problemSets.deleteConfirmMessage', { title: formData.title }) }}
        </p>
        <div class="dialog-actions">
          <button class="btn btn-secondary" @click="showDeleteDialog = false">
            {{ $t('common.cancel') }}
          </button>
          <button class="btn btn-danger" :disabled="deleting" @click="confirmDelete">
            {{ deleting ? $t('admin.problemSets.deleting') : $t('common.delete') }}
          </button>
        </div>
      </div>
    </div>
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { log } from '@/utils/logger';
import type { ProblemSet, ProblemDetailed } from '@/types';

// Router
const route = useRoute();

const { t } = useI18n();

// Provide role-aware context
const ctx = provideContentContext();

// Get slug from route params
const slugFromRoute = computed(() => (route.params.slug as string | undefined) ?? null);
const isEditing = computed(() => Boolean(slugFromRoute.value));

// State
const loading = ref(false);
const loadingProblems = ref(false);
const saving = ref(false);
const deleting = ref(false);
const error = ref<string | null>(null);
const showDeleteDialog = ref(false);

const availableProblems = ref<ProblemDetailed[]>([]);
const selectedProblemSlugs = ref<string[]>([]);
const problemSearch = ref('');

// Form data
const formData = reactive({
  title: '',
  description: '',
  is_public: false,
});

// Computed: filter available problems (not already selected and matching search)
const filteredAvailableProblems = computed(() => {
  const search = problemSearch.value.toLowerCase();
  return availableProblems.value.filter(p => {
    const notSelected = !selectedProblemSlugs.value.includes(p.slug);
    const matchesSearch = !search ||
      p.title.toLowerCase().includes(search) ||
      p.problem_type.toLowerCase().includes(search);
    return notSelected && matchesSearch;
  });
});

// Validation
const canSave = computed(() => {
  const title = (formData.title || '').trim();
  return Boolean(title);
});

// Helpers
function getProblemTitle(slug: string): string {
  const problem = availableProblems.value.find(p => p.slug === slug);
  return problem?.title || slug;
}

function getProblemType(slug: string): string {
  const problem = availableProblems.value.find(p => p.slug === slug);
  return problem?.problem_type || '';
}

// Fetch available problems
async function fetchProblems(): Promise<void> {
  try {
    loadingProblems.value = true;
    availableProblems.value = await ctx.api.value.getProblems();
  } catch (err) {
    log.error('Failed to fetch problems', { error: err });
  } finally {
    loadingProblems.value = false;
  }
}

// Load problem set for editing
async function loadProblemSet(slug: string): Promise<void> {
  try {
    loading.value = true;
    error.value = null;

    const problemSet = await ctx.api.value.getProblemSet(slug);

    // Populate form
    formData.title = problemSet.title;
    formData.description = problemSet.description || '';
    formData.is_public = problemSet.is_public ?? false;

    // Extract problem slugs in order (slug is nested under problem object)
    if (problemSet.problems_detail) {
      const sorted = [...problemSet.problems_detail].sort((a, b) => (a.order || 0) - (b.order || 0));
      selectedProblemSlugs.value = sorted.map(p => p.problem.slug);
    }

    log.info('Loaded problem set for editing', { slug, problemCount: selectedProblemSlugs.value.length });
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || t('admin.problemSets.loading');
    log.error('Failed to load problem set', { error: err });
  } finally {
    loading.value = false;
  }
}

// Reset form for new problem set
function resetForm(): void {
  formData.title = '';
  formData.description = '';
  formData.is_public = false;
  selectedProblemSlugs.value = [];
  problemSearch.value = '';
  error.value = null;
}

// Problem management
function addProblem(slug: string): void {
  if (!selectedProblemSlugs.value.includes(slug)) {
    selectedProblemSlugs.value.push(slug);
  }
}

function removeProblem(slug: string): void {
  selectedProblemSlugs.value = selectedProblemSlugs.value.filter(s => s !== slug);
}

function moveProblem(index: number, direction: number): void {
  const newIndex = index + direction;
  if (newIndex >= 0 && newIndex < selectedProblemSlugs.value.length) {
    const items = [...selectedProblemSlugs.value];
    const [item] = items.splice(index, 1);
    items.splice(newIndex, 0, item);
    selectedProblemSlugs.value = items;
  }
}

// Save handler
async function handleSave(): Promise<void> {
  if (!canSave.value || saving.value) return;

  saving.value = true;
  error.value = null;

  try {
    const payload = {
      title: formData.title.trim(),
      description: formData.description.trim(),
      is_public: formData.is_public,
      problem_slugs: selectedProblemSlugs.value,
    };

    if (isEditing.value && slugFromRoute.value) {
      await ctx.api.value.updateProblemSet(slugFromRoute.value, payload);
      log.info('Updated problem set', { slug: slugFromRoute.value });
    } else {
      const created = await ctx.api.value.createProblemSet(payload);
      log.info('Created problem set', { slug: created.slug });
    }

    // Navigate back to list
    ctx.navigateToList('problem-sets');
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || t('admin.problemSets.saving');
    log.error('Error saving problem set', { error: err });
  } finally {
    saving.value = false;
  }
}

// Delete handlers
function handleDelete(): void {
  showDeleteDialog.value = true;
}

async function confirmDelete(): Promise<void> {
  if (!slugFromRoute.value) return;

  deleting.value = true;

  try {
    await ctx.api.value.deleteProblemSet(slugFromRoute.value);
    log.info('Deleted problem set', { slug: slugFromRoute.value });
    ctx.navigateToList('problem-sets');
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || t('admin.problemSets.deleting');
    log.error('Error deleting problem set', { error: err });
    showDeleteDialog.value = false;
  } finally {
    deleting.value = false;
  }
}

// Watch route changes
watch(
  slugFromRoute,
  async (newSlug, oldSlug) => {
    if (newSlug && newSlug !== oldSlug) {
      await loadProblemSet(newSlug);
    } else if (!newSlug && oldSlug) {
      resetForm();
    }
  },
  { immediate: true }
);

// Initialize on mount
onMounted(async () => {
  log.info('ProblemSetEditorShell mounted', { role: ctx.role.value, editing: isEditing.value });

  // Load available problems
  await fetchProblems();

  // If creating new, form is already reset
  if (!slugFromRoute.value) {
    resetForm();
  }
});
</script>

<style scoped>
/* Common Utilities */
.rounded-base {
  border-radius: var(--radius-base);
}

.rounded-lg {
  border-radius: var(--radius-lg);
}

.border-default {
  border: 2px solid var(--color-bg-border);
}

/* Header */
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

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  border: 2px solid var(--color-bg-border);
}

.loading-container p {
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

.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-bg-border);
  border-top-color: var(--color-primary-gradient-start);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error */
.error-message {
  padding: var(--spacing-xl);
  background: var(--color-error-bg);
  border-radius: var(--radius-lg);
  color: var(--color-error-text);
  text-align: center;
  border: 1px solid var(--color-error);
}

/* Form */
.problem-set-form {
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

.form-row {
  display: flex;
  gap: var(--spacing-lg);
  align-items: flex-end;
}

.flex-grow {
  flex: 1;
}

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

.form-group input[type="text"],
.form-group textarea {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-base);
}

.form-group input[type="text"]:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  padding: var(--spacing-md) 0;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary-gradient-start);
}

/* Problems Section */
.problems-loading {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  color: var(--color-text-muted);
}

.problems-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.section-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-sm);
  display: block;
  font-weight: 500;
}

.selected-problems-section,
.available-problems-section {
  display: flex;
  flex-direction: column;
}

.selected-problems {
  background: var(--color-bg-main);
  border-radius: var(--radius-base);
  padding: var(--spacing-md);
  min-height: 100px;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--color-bg-border);
}

.available-problems-section {
  border-top: 1px solid var(--color-bg-border);
  padding-top: var(--spacing-lg);
}

.problem-search {
  width: 100%;
  padding: var(--spacing-md);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-base);
}

.problem-search:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

.problem-list {
  max-height: 250px;
  overflow-y: auto;
  background: var(--color-bg-main);
  border-radius: var(--radius-base);
  padding: var(--spacing-md);
  border: 1px solid var(--color-bg-border);
}

.problem-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-sm);
}

.problem-item:last-child {
  margin-bottom: 0;
}

.problem-item.selected {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
}

.problem-item.available {
  cursor: pointer;
  transition: var(--transition-fast);
}

.problem-item.available:hover {
  background: var(--color-bg-hover);
}

.problem-order {
  width: 28px;
  height: 28px;
  background: var(--color-primary-gradient-start);
  color: var(--color-text-on-filled);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: 600;
  flex-shrink: 0;
}

.problem-title {
  flex: 1;
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.problem-type {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  padding: 4px 8px;
  background: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  flex-shrink: 0;
  text-transform: uppercase;
}

.problem-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.move-btn,
.remove-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--radius-xs);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: var(--transition-fast);
}

.move-btn {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
}

.move-btn:hover:not(:disabled) {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.move-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.remove-btn {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.remove-btn:hover {
  background: var(--color-error);
  color: var(--color-text-on-filled);
}

.add-indicator {
  color: var(--color-success);
  font-weight: bold;
  font-size: 20px;
  flex-shrink: 0;
}

.no-problems {
  padding: var(--spacing-lg);
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

/* Buttons */
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
  border-radius: var(--radius-base);
}

.btn:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-on-filled);
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
  color: var(--color-text-on-filled);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
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

/* Responsive */
@media (max-width: 768px) {
  .header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-lg);
  }

  .actions {
    width: 100%;
  }

  .actions .btn {
    flex: 1;
    justify-content: center;
  }

  .form-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
