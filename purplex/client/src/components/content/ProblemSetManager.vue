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

    <DataTable
      :columns="columns"
      :items="items"
      :loading="loading"
      :error="error"
      :total-count="totalCount"
      :current-page="currentPage"
      :page-size="pageSize"
      :total-pages="totalPages"
      :has-next="hasNext"
      :has-previous="hasPrevious"
      :page-numbers="pageNumbers"
      :range-start="rangeStart"
      :range-end="rangeEnd"
      item-label="problem sets"
      row-key="slug"
      empty-title="No Problem Sets"
      :empty-message="ctx.isInstructor.value
        ? 'You haven\'t created any problem sets yet. Create your first one!'
        : 'No problem sets found. Create your first one!'"
      @go-to-page="goToPage"
      @page-size-change="handlePageSizeChange"
      @retry="refresh"
    >
      <!-- Search filter -->
      <template #filters>
        <div class="filters-section">
          <div class="filter-group">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search by title or description..."
              class="search-input"
              @input="debouncedSearch"
            >
          </div>
        </div>
      </template>

      <!-- Visibility badge -->
      <template #cell-visibility="{ item }">
        <StatusBadge
          :value="item.is_public ? 'Public' : 'Private'"
          :variant="item.is_public ? 'success' : 'error'"
        />
      </template>

      <!-- Actions -->
      <template #cell-actions="{ item }">
        <div class="actions-cell">
          <router-link
            :to="ctx.paths.editProblemSet(item.slug)"
            class="action-button edit-button"
          >
            Edit
          </router-link>
          <button class="action-button delete-button" @click="confirmDelete(item)">
            Delete
          </button>
        </div>
      </template>
    </DataTable>

    <!-- Delete Confirmation Dialog -->
    <ConfirmDialog
      :visible="showDeleteDialog"
      title="Delete Problem Set?"
      :message="`Are you sure you want to delete &quot;${deleteTarget?.title}&quot;? This will not delete the problems inside.`"
      confirm-label="Delete"
      :loading="deleting"
      @confirm="performDelete"
      @cancel="showDeleteDialog = false"
    />
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import ContentEditorLayout from './ContentEditorLayout.vue';
import DataTable from '@/components/ui/DataTable.vue';
import StatusBadge from '@/components/ui/StatusBadge.vue';
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { useDataTable } from '@/composables/useDataTable';
import { clientSidePaginate } from '@/utils/clientSidePaginate';
import { log } from '@/utils/logger';
import type { ProblemSet } from '@/types';
import type { DataTableColumn } from '@/types/datatable';

const ctx = provideContentContext();

// Cached data for client-side pagination
let allProblemSets: ProblemSet[] = [];
let needsRefetch = true;

const {
  items, loading, error, currentPage, pageSize, totalCount,
  totalPages, hasNext, hasPrevious, rangeStart, rangeEnd,
  pageNumbers, searchQuery, debouncedSearch, goToPage,
  handlePageSizeChange, fetch: fetchTable, refresh,
} = useDataTable<ProblemSet>({
  fetchFn: async (params) => {
    if (needsRefetch) {
      allProblemSets = await ctx.api.value.getProblemSets();
      needsRefetch = false;
    }
    return clientSidePaginate(allProblemSets, params, {
      searchFn: (item, q) => {
        const lower = q.toLowerCase();
        return item.title.toLowerCase().includes(lower)
          || (item.description?.toLowerCase().includes(lower) ?? false);
      },
    });
  },
  initialPageSize: 25,
});

// Column definitions
const columns: DataTableColumn<ProblemSet>[] = [
  { key: 'title', label: 'Title' },
  {
    key: 'description',
    label: 'Description',
    hideOnMobile: true,
    render: (value) => (value as string) || 'No description',
  },
  {
    key: 'problems_count',
    label: 'Problems',
    align: 'center',
    width: '100px',
    render: (value, row) => String(value ?? row.problems?.length ?? 0),
  },
  { key: 'is_public', label: 'Visibility', align: 'center', width: '120px', slot: 'cell-visibility' },
  { key: 'actions', label: 'Actions', slot: 'cell-actions', width: '160px' },
];

// Delete dialog state
const showDeleteDialog = ref(false);
const deleteTarget = ref<ProblemSet | null>(null);
const deleting = ref(false);

function confirmDelete(set: ProblemSet): void {
  deleteTarget.value = set;
  showDeleteDialog.value = true;
}

async function performDelete(): Promise<void> {
  if (!deleteTarget.value) return;

  deleting.value = true;
  try {
    await ctx.api.value.deleteProblemSet(deleteTarget.value.slug);
    allProblemSets = allProblemSets.filter(s => s.slug !== deleteTarget.value!.slug);
    showDeleteDialog.value = false;
    deleteTarget.value = null;
    await fetchTable();
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || 'Failed to delete problem set';
    log.error('Error deleting problem set', { error: err });
  } finally {
    deleting.value = false;
  }
}

onMounted(fetchTable);
</script>

<style scoped>
.filters-section {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.filter-group {
  flex: 1;
  min-width: 200px;
  max-width: 400px;
}

.search-input {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border, var(--color-bg-input));
  border-radius: var(--radius-base);
  background: var(--color-surface, var(--color-bg-hover));
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  transition: var(--transition-base);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

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

@media (max-width: 768px) {
  .actions-cell {
    flex-direction: column;
  }
}
</style>
