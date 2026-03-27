<template>
  <nav
    class="pagination"
    role="navigation"
    aria-label="Table pagination"
  >
    <div class="pagination-left">
      <label
        for="page-size"
        class="page-size-label"
      >{{ $t('common.pagination.show') }}</label>
      <select
        id="page-size"
        :value="pageSize"
        class="page-size-select"
        :aria-label="$t('common.pagination.itemsPerPage')"
        @change="handlePageSizeChange"
      >
        <option
          v-for="size in pageSizeOptions"
          :key="size"
          :value="size"
        >
          {{ size }}
        </option>
      </select>
      <span class="page-size-suffix">{{ $t('common.pagination.perPage') }}</span>
    </div>

    <div class="pagination-center">
      <button
        class="pagination-btn"
        :disabled="!hasPrevious"
        :title="$t('common.pagination.firstPage')"
        @click="$emit('go-to-page', 1)"
      >
        &laquo;
      </button>
      <button
        class="pagination-btn"
        :disabled="!hasPrevious"
        :title="$t('common.pagination.previousPage')"
        @click="$emit('go-to-page', currentPage - 1)"
      >
        &lsaquo;
      </button>

      <button
        v-for="page in pageNumbers"
        :key="page"
        class="pagination-btn page-number"
        :class="{ active: page === currentPage }"
        @click="$emit('go-to-page', page)"
      >
        {{ page }}
      </button>

      <button
        class="pagination-btn"
        :disabled="!hasNext"
        :title="$t('common.pagination.nextPage')"
        @click="$emit('go-to-page', currentPage + 1)"
      >
        &rsaquo;
      </button>
      <button
        class="pagination-btn"
        :disabled="!hasNext"
        :title="$t('common.pagination.lastPage')"
        @click="$emit('go-to-page', totalPages)"
      >
        &raquo;
      </button>
    </div>

    <div class="pagination-right">
      <span class="pagination-info">
        {{ $t('common.pagination.rangeOf', { start: rangeStart, end: rangeEnd, total: totalCount }) }}
      </span>
    </div>
  </nav>
</template>

<script setup lang="ts">
interface Props {
  currentPage: number;
  pageSize: number;
  totalPages: number;
  totalCount: number;
  hasNext: boolean;
  hasPrevious: boolean;
  pageNumbers: number[];
  rangeStart: number;
  rangeEnd: number;
  pageSizeOptions?: number[];
}

withDefaults(defineProps<Props>(), {
  pageSizeOptions: () => [10, 25, 50, 100],
});

const emit = defineEmits<{
  'go-to-page': [page: number];
  'page-size-change': [size: number];
}>();

function handlePageSizeChange(event: Event) {
  const target = event.target as HTMLSelectElement;
  emit('page-size-change', Number(target.value));
}
</script>

<style scoped>
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--color-border, var(--color-bg-input));
}

.pagination-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex: 1;
}

.pagination-center {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.pagination-right {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}

.pagination-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.page-size-label,
.page-size-suffix {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.page-size-select {
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--color-border, var(--color-bg-input));
  border-radius: var(--radius-base);
  background: var(--color-surface, var(--color-bg-hover));
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  cursor: pointer;
}

.pagination-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-base);
  min-width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pagination-btn:hover:not(:disabled) {
  border-color: var(--color-primary-gradient-start);
  background: var(--color-primary-gradient-start);
  color: var(--color-text-on-filled);
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-btn.active {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-on-filled);
  font-weight: 600;
  box-shadow: var(--shadow-colored);
}

/* Responsive */
@media (max-width: 768px) {
  .pagination {
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .pagination-left {
    order: 2;
    justify-content: center;
  }

  .pagination-center {
    order: 1;
    flex-wrap: wrap;
    justify-content: center;
  }

  .pagination-right {
    display: none;
  }
}
</style>
