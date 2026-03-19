<template>
  <ContentEditorLayout
    :page-title="ctx.getPageTitle('Problems').value"
    :show-breadcrumb="false"
  >
    <template #header-actions>
      <button class="action-button add-button" @click="createNewProblem">
        {{ $t('admin.problems.addNew') }}
      </button>
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
      :item-label="$t('admin.problems.itemLabel')"
      row-key="slug"
      :empty-title="$t('admin.problems.noProblems')"
      :empty-message="ctx.isInstructor.value
        ? $t('admin.problems.emptyInstructor')
        : $t('admin.problems.emptyAdmin')"
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
              :placeholder="$t('admin.problems.searchByTitle')"
              class="search-input"
              @input="debouncedSearch"
            >
          </div>
        </div>
      </template>

      <!-- Type badge -->
      <template #cell-type="{ item }">
        <StatusBadge
          :value="item.problem_type"
          :variant="getTypeVariant(item.problem_type)"
          :label="getProblemTypeLabel(item.problem_type)"
        />
      </template>

      <!-- Difficulty badge -->
      <template #cell-difficulty="{ item }">
        <StatusBadge
          :value="item.difficulty"
          :variant="getDifficultyVariant(item.difficulty)"
        />
      </template>

      <!-- Actions -->
      <template #cell-actions="{ item }">
        <div class="actions-cell">
          <button class="action-button edit-button" @click="editProblem(item.slug)">
            {{ $t('common.edit') }}
          </button>
          <button class="action-button delete-button" @click="confirmDelete(item)">
            {{ $t('common.delete') }}
          </button>
        </div>
      </template>
    </DataTable>
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import DataTable from '@/components/ui/DataTable.vue';
import StatusBadge from '@/components/ui/StatusBadge.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { useDataTable } from '@/composables/useDataTable';
import { clientSidePaginate } from '@/utils/clientSidePaginate';
import { useNotification } from '@/composables/useNotification';
import { log } from '@/utils/logger';
import type { ProblemDetailed } from '@/types';
import type { DataTableColumn, BadgeVariant } from '@/types/datatable';

const { t } = useI18n();
const ctx = provideContentContext();
const router = useRouter();
const { notify } = useNotification();

// Cached data for client-side pagination
let allProblems: ProblemDetailed[] = [];
let needsRefetch = true;

const {
  items, loading, error, currentPage, pageSize, totalCount,
  totalPages, hasNext, hasPrevious, rangeStart, rangeEnd,
  pageNumbers, searchQuery, debouncedSearch, goToPage,
  handlePageSizeChange, fetch: fetchTable, refresh,
} = useDataTable<ProblemDetailed>({
  fetchFn: async (params) => {
    if (needsRefetch) {
      allProblems = await ctx.api.value.getProblems();
      needsRefetch = false;
    }
    return clientSidePaginate(allProblems, params, {
      searchFn: (item, q) => item.title.toLowerCase().includes(q.toLowerCase()),
    });
  },
  initialPageSize: 25,
});

// Problem type labels
const problemTypeLabels: Record<string, string> = {
  mcq: 'MCQ',
  eipl: 'EiPL',
  prompt: 'Prompt',
  debug_fix: 'Debug & Fix',
  probeable_code: 'Probeable (Code)',
  probeable_spec: 'Probeable (Spec)',
  refute: 'Refute',
};

function getProblemTypeLabel(type: string): string {
  return problemTypeLabels[type] || type || t('common.unknown');
}

function getTypeVariant(type: string): BadgeVariant {
  switch (type) {
    case 'eipl': return 'info';
    case 'mcq': return 'success';
    case 'prompt': return 'warning';
    default: return 'default';
  }
}

function getDifficultyVariant(difficulty: string): BadgeVariant {
  switch (difficulty?.toLowerCase()) {
    case 'easy':
    case 'beginner':
      return 'success';
    case 'intermediate':
      return 'warning';
    case 'advanced':
    case 'hard':
      return 'error';
    default:
      return 'default';
  }
}

function getProblemSetNames(problem: ProblemDetailed): string {
  const sets = (problem as ProblemDetailed & { problem_sets?: Array<{ title?: string }> }).problem_sets;
  if (!sets || sets.length === 0) return t('admin.problems.noProblemSets');
  return sets.map(ps => ps.title || t('common.unknown')).join(', ');
}

// Column definitions
const columns = computed<DataTableColumn<ProblemDetailed>[]>(() => [
  { key: 'problem_type', label: t('admin.problems.columnType'), width: '130px', slot: 'cell-type' },
  { key: 'title', label: t('admin.problems.columnTitle') },
  { key: 'difficulty', label: t('admin.problems.columnDifficulty'), width: '140px', slot: 'cell-difficulty' },
  {
    key: 'problem_sets',
    label: t('admin.problems.columnProblemSets'),
    hideOnMobile: true,
    render: (_value, row) => getProblemSetNames(row),
  },
  { key: 'actions', label: t('admin.problems.columnActions'), slot: 'cell-actions', width: '160px' },
]);

// Navigation
function createNewProblem(): void {
  router.push(ctx.paths.newProblem.value);
}

function editProblem(slug: string): void {
  router.push(ctx.paths.editProblem(slug));
}

// Delete handling
function confirmDelete(problem: ProblemDetailed): void {
  if (confirm(t('admin.problems.deleteConfirmMessage', { title: problem.title }))) {
    deleteProblem(problem);
  }
}

async function deleteProblem(problem: ProblemDetailed): Promise<void> {
  try {
    await ctx.api.value.deleteProblem(problem.slug);
    allProblems = allProblems.filter(p => p.slug !== problem.slug);
    await fetchTable();
    notify.success(t('admin.problems.deleteSuccess'), t('admin.problems.deleteSuccessMessage', { title: problem.title }));
  } catch (err) {
    const apiError = err as { error?: string };
    if (apiError.error?.includes('submission')) {
      notify.error(
        t('admin.problems.deleteHasSubmissions', { title: problem.title }),
        t('admin.problems.deleteHasSubmissionsHint')
      );
    } else {
      notify.error(t('admin.problems.deleteFailed'), apiError.error || t('admin.problems.deleteFailedMessage'));
    }
    log.error('Error deleting problem', { error: err });
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
}

.add-button {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  box-shadow: var(--shadow-colored);
}

.add-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--color-primary-shadow);
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
