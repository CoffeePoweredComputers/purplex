<template>
  <ContentEditorLayout
    :page-title="ctx.getPageTitle('Problem Sets').value"
    :back-path="ctx.basePath.value"
    :back-label="ctx.isInstructor.value ? 'Back to Dashboard' : 'Back to Admin'"
    :show-breadcrumb="false"
  >
    <template #header-actions>
      <router-link :to="ctx.paths.newProblemSet.value" class="action-button add-button">
        Add New Problem Set
      </router-link>
    </template>

    <!-- Status Messages -->
    <div class="status-container">
      <div v-if="loading" class="loading-indicator">
        Loading problem sets...
      </div>
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>

    <!-- Problem Sets Table -->
    <div v-if="!loading && !error" class="table-responsive">
      <table class="problem-sets-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Description</th>
            <th>Problems</th>
            <th>Visibility</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="set in problemSets" :key="set.slug">
            <td>{{ set.title }}</td>
            <td>{{ set.description || 'No description' }}</td>
            <td>{{ set.problems_count || set.problems?.length || 0 }}</td>
            <td>
              <span :class="['visibility-badge', set.is_public ? 'public' : 'private']">
                {{ set.is_public ? 'Public' : 'Private' }}
              </span>
            </td>
            <td class="actions-cell">
              <router-link
                :to="ctx.paths.editProblemSet(set.slug)"
                class="action-button edit-button"
              >
                Edit
              </router-link>
              <button class="action-button delete-button" @click="confirmDelete(set)">
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <p v-if="problemSets.length === 0" class="no-data">
        {{ ctx.isInstructor.value
          ? "You haven't created any problem sets yet. Create your first one!"
          : "No problem sets found. Create your first one!"
        }}
      </p>
    </div>

    <!-- Delete Confirmation Dialog -->
    <div v-if="showDeleteDialog" class="dialog-overlay">
      <div class="dialog">
        <h3>Delete Problem Set?</h3>
        <p>
          Are you sure you want to delete "{{ deleteTarget?.title }}"?
          This will not delete the problems inside.
        </p>
        <div class="dialog-actions">
          <button class="btn btn-secondary" @click="showDeleteDialog = false">
            Cancel
          </button>
          <button class="btn btn-danger" :disabled="deleting" @click="performDelete">
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import ContentEditorLayout from './ContentEditorLayout.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { log } from '@/utils/logger';
import type { ProblemSet } from '@/types';

// Provide role-aware context (page-level components must provide, not inject)
const ctx = provideContentContext();

// State
const problemSets = ref<ProblemSet[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const deleting = ref(false);

// Delete dialog state (kept as dialog per user request)
const showDeleteDialog = ref(false);
const deleteTarget = ref<ProblemSet | null>(null);

// Fetch problem sets
async function fetchProblemSets(): Promise<void> {
  try {
    loading.value = true;
    error.value = null;
    problemSets.value = await ctx.api.value.getProblemSets();
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || 'Failed to load problem sets';
    log.error('Failed to fetch problem sets', { error: err });
  } finally {
    loading.value = false;
  }
}

// Delete handlers
function confirmDelete(set: ProblemSet): void {
  deleteTarget.value = set;
  showDeleteDialog.value = true;
}

async function performDelete(): Promise<void> {
  if (!deleteTarget.value) return;

  deleting.value = true;
  try {
    await ctx.api.value.deleteProblemSet(deleteTarget.value.slug);
    problemSets.value = problemSets.value.filter(s => s.slug !== deleteTarget.value!.slug);
    showDeleteDialog.value = false;
    deleteTarget.value = null;
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || 'Failed to delete problem set';
    log.error('Error deleting problem set', { error: err });
  } finally {
    deleting.value = false;
  }
}

// Load on mount
onMounted(fetchProblemSets);
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

.problem-sets-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.problem-sets-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-lg) var(--spacing-xl);
  font-weight: 600;
  font-size: var(--font-size-base);
  border-bottom: 2px solid var(--color-bg-input);
}

.problem-sets-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.problem-sets-table tr:hover {
  background: var(--color-bg-hover);
}

.problem-sets-table tr:last-child td {
  border-bottom: none;
}

/* Visibility badge */
.visibility-badge {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-weight: 600;
  font-size: var(--font-size-xs);
  display: inline-block;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.visibility-badge.public {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.visibility-badge.private {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
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
  text-decoration: none;
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

/* Delete Dialog */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
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
  margin: 0 0 var(--spacing-lg) 0;
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
  margin-top: var(--spacing-lg);
}

/* Buttons */
.btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: var(--transition-base);
}

.btn-secondary {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.btn-danger {
  background: var(--color-error);
  color: var(--color-text-primary);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 768px) {
  .problem-sets-table {
    font-size: var(--font-size-sm);
  }

  .problem-sets-table th,
  .problem-sets-table td {
    padding: var(--spacing-md);
  }

  .actions-cell {
    flex-direction: column;
  }
}
</style>
