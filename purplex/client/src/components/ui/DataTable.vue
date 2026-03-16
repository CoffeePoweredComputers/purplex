<template>
  <div class="data-table-container">
    <!-- Filters slot -->
    <slot name="filters" />

    <!-- Results summary bar -->
    <div v-if="!loading && !error && totalCount > 0" class="results-bar" aria-live="polite">
      <span class="results-count">
        {{ $t('common.dataTable.showing', { start: rangeStart, end: rangeEnd, total: totalCount, label: effectiveItemLabel }) }}
      </span>
      <slot name="results-actions" />
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-container">
      <AsyncLoader />
      <p class="loading-text">{{ $t('common.dataTable.loading', { label: effectiveItemLabel }) }}</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <div class="error-icon" aria-hidden="true">!</div>
      <h3>{{ $t('common.dataTable.errorTitle') }}</h3>
      <p>{{ error }}</p>
      <button class="retry-button" @click="$emit('retry')">
        {{ $t('common.dataTable.tryAgain') }}
      </button>
    </div>

    <!-- Table with data -->
    <template v-else-if="items.length > 0">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th
                v-for="col in columns"
                :key="col.key"
                :class="[
                  col.align ? `text-${col.align}` : '',
                  { 'hide-mobile': col.hideOnMobile }
                ]"
                :style="col.width ? { width: col.width } : {}"
                scope="col"
              >
                {{ col.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="getRowKey(item, index)">
              <td
                v-for="col in columns"
                :key="col.key"
                :class="[
                  col.align ? `text-${col.align}` : '',
                  { 'hide-mobile': col.hideOnMobile }
                ]"
              >
                <!-- Named slot for custom cell content -->
                <slot
                  v-if="col.slot"
                  :name="col.slot"
                  :item="item"
                  :value="getNestedValue(item, col.key)"
                  :column="col"
                />
                <!-- Custom render function -->
                <template v-else-if="col.render">
                  {{ col.render(getNestedValue(item, col.key), item) }}
                </template>
                <!-- Default rendering -->
                <template v-else>
                  {{ getNestedValue(item, col.key) ?? '-' }}
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <DataTablePagination
        v-if="showPagination && totalPages > 1"
        :current-page="currentPage"
        :page-size="pageSize"
        :total-pages="totalPages"
        :total-count="totalCount"
        :has-next="hasNext"
        :has-previous="hasPrevious"
        :page-numbers="pageNumbers"
        :range-start="rangeStart"
        :range-end="rangeEnd"
        :page-size-options="pageSizeOptions"
        @go-to-page="$emit('go-to-page', $event)"
        @page-size-change="$emit('page-size-change', $event)"
      />
    </template>

    <!-- Empty state -->
    <div v-else class="empty-state">
      <div class="empty-icon" aria-hidden="true">[ ]</div>
      <h3>{{ effectiveEmptyTitle }}</h3>
      <p>{{ effectiveEmptyMessage }}</p>
      <slot name="empty-actions" />
    </div>
  </div>
</template>

<script setup lang="ts" generic="T">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import AsyncLoader from './AsyncLoader.vue';
import DataTablePagination from './DataTablePagination.vue';
import type { DataTableColumn } from '@/types/datatable';

const { t } = useI18n();

interface Props {
  /** Column definitions */
  columns: DataTableColumn<T>[];
  /** Data items to display */
  items: T[];
  /** Loading state */
  loading: boolean;
  /** Error message (if any) */
  error: string | null;
  /** Total number of items across all pages */
  totalCount: number;
  /** Current page number (1-indexed) */
  currentPage: number;
  /** Number of items per page */
  pageSize: number;
  /** Total number of pages */
  totalPages: number;
  /** Whether there is a next page */
  hasNext: boolean;
  /** Whether there is a previous page */
  hasPrevious: boolean;
  /** Visible page numbers for pagination */
  pageNumbers: number[];
  /** Start of current page range (1-indexed) */
  rangeStart: number;
  /** End of current page range */
  rangeEnd: number;
  /** Label for items (e.g., "users", "problems") */
  itemLabel?: string;
  /** Title shown when table is empty */
  emptyTitle?: string;
  /** Message shown when table is empty */
  emptyMessage?: string;
  /** Property key to use for row :key (or function) */
  rowKey?: string | ((item: T, index: number) => string | number);
  /** Whether to show pagination controls */
  showPagination?: boolean;
  /** Available page size options */
  pageSizeOptions?: number[];
}

const props = withDefaults(defineProps<Props>(), {
  itemLabel: '',
  emptyTitle: '',
  emptyMessage: '',
  rowKey: 'id',
  showPagination: true,
  pageSizeOptions: () => [10, 25, 50, 100],
});

/** Computed fallbacks: use provided prop or fall back to i18n default */
const effectiveItemLabel = computed(() => props.itemLabel || t('common.dataTable.defaultItemLabel'));
const effectiveEmptyTitle = computed(() => props.emptyTitle || t('common.dataTable.defaultEmptyTitle'));
const effectiveEmptyMessage = computed(() => props.emptyMessage || t('common.dataTable.defaultEmptyMessage'));

defineEmits<{
  'go-to-page': [page: number];
  'page-size-change': [size: number];
  retry: [];
}>();

/**
 * Get a nested value from an object using dot notation.
 * e.g., getNestedValue(obj, 'user.email')
 */
function getNestedValue(obj: T, path: string): unknown {
  return path.split('.').reduce((acc: unknown, part: string) => {
    if (acc && typeof acc === 'object' && part in acc) {
      return (acc as Record<string, unknown>)[part];
    }
    return undefined;
  }, obj);
}

/**
 * Get the unique key for a row.
 */
function getRowKey(item: T, index: number): string | number {
  if (typeof props.rowKey === 'function') {
    return props.rowKey(item, index);
  }
  const value = getNestedValue(item, props.rowKey);
  return (value as string | number) ?? index;
}
</script>

<style scoped>
.data-table-container {
  width: 100%;
}

.results-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) 0;
  margin-bottom: var(--spacing-md);
}

.results-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.loading-text {
  margin-top: var(--spacing-md);
  color: var(--color-text-muted);
}

.error-state {
  text-align: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-lg);
}

.error-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto var(--spacing-md);
  border-radius: var(--radius-circle);
  background: var(--color-error-bg);
  color: var(--color-error);
  font-size: var(--font-size-xl);
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-state h3 {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.error-state p {
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-lg);
}

.retry-button {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  border: none;
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
}

.retry-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-colored);
}

.table-wrapper {
  overflow-x: auto;
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 2px solid transparent;
  transition: var(--transition-base);
}

.table-wrapper:hover {
  border-color: var(--color-bg-input);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.data-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-lg) var(--spacing-xl);
  font-weight: 600;
  font-size: var(--font-size-base);
  border-bottom: 2px solid var(--color-bg-input);
}

.data-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.data-table tr:hover {
  background: var(--color-bg-hover);
}

.data-table tr:last-child td {
  border-bottom: none;
}

/* Text alignment */
.text-left { text-align: left; }
.text-center { text-align: center; }
.text-right { text-align: right; }

/* Empty state */
.empty-state {
  text-align: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border: 1px dashed var(--color-border, var(--color-bg-input));
  border-radius: var(--radius-lg);
}

.empty-icon {
  font-size: 2rem;
  margin-bottom: var(--spacing-lg);
  color: var(--color-text-secondary);
}

.empty-state h3 {
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.empty-state p {
  color: var(--color-text-secondary);
}

/* Responsive */
@media (max-width: 768px) {
  .data-table th,
  .data-table td {
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: var(--font-size-sm);
  }

  .hide-mobile {
    display: none;
  }

  .results-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
  }
}
</style>
