<template>
  <ContentEditorLayout
    :page-title="ctx.getPageTitle('Problems').value"
    :show-breadcrumb="false"
  >
    <template #header-actions>
      <button class="action-button add-button" @click="createNewProblem">
        Add New Problem
      </button>
    </template>

    <!-- Status Messages -->
    <div class="status-container">
      <div v-if="loading" class="loading-indicator">
        Loading problems...
      </div>
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>

    <!-- Problems Table -->
    <div v-if="!loading && !error" class="table-responsive">
      <table class="problems-table">
        <thead>
          <tr>
            <th>Type</th>
            <th>Title</th>
            <th>Difficulty</th>
            <th>Problem Sets</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="problem in problems" :key="problem.slug">
            <td>
              <span class="type-badge" :class="problemTypeClass(problem.problem_type)">
                {{ getProblemTypeLabel(problem.problem_type) }}
              </span>
            </td>
            <td>{{ problem.title }}</td>
            <td>
              <span class="badge" :class="difficultyClass(problem.difficulty)">
                {{ problem.difficulty }}
              </span>
            </td>
            <td>{{ getProblemSetNames(problem) }}</td>
            <td class="actions-cell">
              <button class="action-button edit-button" @click="editProblem(problem.slug)">
                Edit
              </button>
              <button class="action-button delete-button" @click="confirmDelete(problem)">
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <p v-if="problems.length === 0" class="no-data">
        {{ ctx.isInstructor.value
          ? "You haven't created any problems yet. Create your first one!"
          : "No problems found. Create your first one!"
        }}
      </p>
    </div>
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { useNotification } from '@/composables/useNotification';
import { log } from '@/utils/logger';
import type { ProblemDetailed } from '@/types';

// Provide role-aware context (page-level components must provide, not inject)
const ctx = provideContentContext();
const router = useRouter();
const { notify } = useNotification();

// State
const problems = ref<ProblemDetailed[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Problem type labels
const problemTypeLabels: Record<string, string> = {
  mcq: 'Multiple Choice Question',
  eipl: 'Explain in Plain Language',
  prompt: 'Prompt Problem',
  debug_fix: 'Debug and Fix Code',
  probeable_code: 'Probeable Problem (Code)',
  probeable_spec: 'Probeable Problem (Explanation)',
  refute: 'Refute: Find Counterexample',
};

// Fetch problems using the context's API
async function fetchProblems(): Promise<void> {
  try {
    loading.value = true;
    error.value = null;
    log.debug(`Fetching problems from ${ctx.api.value.baseURL}/problems/`);
    problems.value = await ctx.api.value.getProblems();
    log.debug('Problems fetched successfully', { count: problems.value.length });
  } catch (err) {
    const apiError = err as { error?: string; status?: number };
    log.error('Failed to fetch problems', { error: err });

    if (apiError.status === 401) {
      error.value = 'Authentication required. Please log in again.';
    } else if (apiError.status === 403) {
      error.value = 'Access denied. You do not have permission to view these problems.';
    } else {
      error.value = apiError.error || 'Failed to load problems. Please try again.';
    }
  } finally {
    loading.value = false;
  }
}

// Helper functions
function getProblemTypeLabel(type: string): string {
  return problemTypeLabels[type] || type || 'Unknown';
}

function getProblemSetNames(problem: ProblemDetailed): string {
  if (!problem.problem_sets || problem.problem_sets.length === 0) {
    return 'None';
  }
  return problem.problem_sets.map(ps => ps.title || 'Unknown').join(', ');
}

function difficultyClass(difficulty: string): string {
  switch (difficulty?.toLowerCase()) {
    case 'easy':
    case 'beginner':
      return 'easy-badge';
    case 'intermediate':
      return 'medium-badge';
    case 'advanced':
    case 'hard':
      return 'hard-badge';
    default:
      return 'default-badge';
  }
}

function problemTypeClass(type: string): string {
  switch (type) {
    case 'eipl':
      return 'eipl-badge';
    default:
      return 'default-type-badge';
  }
}

// Navigation
function createNewProblem(): void {
  router.push(ctx.paths.newProblem.value);
}

function editProblem(slug: string): void {
  router.push(ctx.paths.editProblem(slug));
}

// Delete handling
function confirmDelete(problem: ProblemDetailed): void {
  if (confirm(`Are you sure you want to delete "${problem.title}"? This action cannot be undone.`)) {
    deleteProblem(problem);
  }
}

async function deleteProblem(problem: ProblemDetailed): Promise<void> {
  try {
    await ctx.api.value.deleteProblem(problem.slug);
    problems.value = problems.value.filter(p => p.slug !== problem.slug);
    notify.success('Problem deleted', `"${problem.title}" has been removed.`);
  } catch (err) {
    const apiError = err as { error?: string };
    if (apiError.error?.includes('submission')) {
      notify.error(
        `"${problem.title}" has existing submissions`,
        'Deactivate the problem instead to hide it from students.'
      );
    } else {
      notify.error('Delete failed', apiError.error || 'Please try again.');
    }
    log.error('Error deleting problem', { error: err });
  }
}

// Load problems on mount
onMounted(fetchProblems);
</script>

<style scoped>
/* Status messages */
.status-container {
  margin-bottom: var(--spacing-xl);
}

.loading-indicator {
  padding: var(--spacing-xl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
  text-align: center;
  box-shadow: var(--shadow-md);
}

.error-message {
  padding: var(--spacing-xl);
  background: var(--color-error-bg);
  border-radius: var(--radius-lg);
  color: var(--color-error-text);
  text-align: center;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-error);
}

/* Table */
.table-responsive {
  overflow-x: auto;
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 2px solid transparent;
  transition: var(--transition-base);
}

.table-responsive:hover {
  border-color: var(--color-bg-input);
}

.problems-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.problems-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-lg) var(--spacing-xl);
  font-weight: 600;
  font-size: var(--font-size-base);
  border-bottom: 2px solid var(--color-bg-input);
}

.problems-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.problems-table tr:hover {
  background: var(--color-bg-hover);
}

.problems-table tr:last-child td {
  border-bottom: none;
}

/* Badges */
.badge,
.type-badge {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-weight: 600;
  font-size: var(--font-size-xs);
  display: inline-block;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.easy-badge {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.medium-badge {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.hard-badge {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.default-badge {
  background: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}

.eipl-badge {
  background: var(--color-info-bg);
  color: var(--color-info-text);
  border: 1px solid var(--color-info);
}

.default-type-badge {
  background: var(--color-bg-hover);
  color: var(--color-text-muted);
  border: 1px solid var(--color-bg-border);
}

/* Actions */
.actions-cell {
  display: flex;
  gap: var(--spacing-md);
}

.action-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-base);
}

.add-button {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  box-shadow: var(--shadow-colored);
}

.add-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.add-button::before {
  content: "+";
  font-size: 18px;
  font-weight: bold;
}

.edit-button {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.edit-button:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.delete-button {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.delete-button:hover {
  background: var(--color-error);
  color: var(--color-text-primary);
  transform: translateY(-1px);
}

.no-data {
  text-align: center;
  padding: var(--spacing-xxl);
  color: var(--color-text-muted);
  font-size: var(--font-size-md);
}

/* Responsive */
@media (max-width: 768px) {
  .problems-table {
    font-size: var(--font-size-sm);
  }

  .problems-table th,
  .problems-table td {
    padding: var(--spacing-md);
  }

  .actions-cell {
    flex-direction: column;
  }
}
</style>
