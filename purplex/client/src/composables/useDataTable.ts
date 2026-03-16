/**
 * useDataTable - Generic composable for paginated data tables.
 *
 * Provides shared state and logic for paginated tables including:
 * - Pagination state and navigation
 * - Debounced search
 * - Filter management
 * - Loading/error states
 *
 * Usage:
 *   const { items, loading, currentPage, goToPage, ... } = useDataTable({
 *     fetchFn: (params) => api.getUsers(params),
 *     initialPageSize: 25,
 *   });
 */
import { computed, onUnmounted, ref, type ComputedRef, type Ref } from 'vue';
import { useI18n } from 'vue-i18n';
import type {
  DataTableQueryParams,
  PaginatedResponseWithFilters,
  UseDataTableOptions,
} from '@/types/datatable';
import { log } from '@/utils/logger';

export interface UseDataTableReturn<T, F = Record<string, unknown>> {
  // Data
  items: Ref<T[]>;
  filterOptions: Ref<F | null>;

  // State
  loading: Ref<boolean>;
  error: Ref<string | null>;

  // Pagination
  currentPage: Ref<number>;
  pageSize: Ref<number>;
  totalCount: Ref<number>;
  totalPages: Ref<number>;
  hasNext: Ref<boolean>;
  hasPrevious: Ref<boolean>;
  rangeStart: ComputedRef<number>;
  rangeEnd: ComputedRef<number>;
  pageNumbers: ComputedRef<number[]>;

  // Filters
  searchQuery: Ref<string>;
  filters: Ref<Record<string, string>>;
  hasFilters: ComputedRef<boolean>;

  // Actions
  fetch: () => Promise<void>;
  goToPage: (page: number) => void;
  handlePageSizeChange: (size: number) => void;
  setFilter: (key: string, value: string) => void;
  clearFilter: (key: string) => void;
  clearAllFilters: () => void;
  debouncedSearch: () => void;
  refresh: () => Promise<void>;
}

export function useDataTable<T, F = Record<string, unknown>>(
  options: UseDataTableOptions<T, F>
): UseDataTableReturn<T, F> {
  const { t } = useI18n();
  const { fetchFn, initialPageSize = 25, debounceMs = 300, filterKeys = [] } = options;

  // Data
  const items = ref<T[]>([]) as Ref<T[]>;
  const filterOptions = ref<F | null>(null) as Ref<F | null>;

  // State
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Pagination
  const currentPage = ref(1);
  const pageSize = ref(initialPageSize);
  const totalCount = ref(0);
  const totalPages = ref(0);
  const hasNext = ref(false);
  const hasPrevious = ref(false);

  // Filters
  const searchQuery = ref('');
  const filters = ref<Record<string, string>>({});

  // Debounce timer
  let searchTimeout: ReturnType<typeof setTimeout> | null = null;

  // Computed: Pagination range for display
  const rangeStart = computed(() => {
    if (totalCount.value === 0) return 0;
    return (currentPage.value - 1) * pageSize.value + 1;
  });

  const rangeEnd = computed(() => {
    const end = currentPage.value * pageSize.value;
    return Math.min(end, totalCount.value);
  });

  // Computed: Page numbers for pagination (shows up to 5 pages)
  const pageNumbers = computed(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    const half = Math.floor(maxVisible / 2);

    let start = Math.max(1, currentPage.value - half);
    const end = Math.min(totalPages.value, start + maxVisible - 1);

    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    return pages;
  });

  // Computed: Has any filters active
  const hasFilters = computed(() => {
    if (searchQuery.value.trim()) return true;
    return Object.values(filters.value).some((v) => v && v.trim());
  });

  // Build query params
  function buildParams(): DataTableQueryParams {
    const params: DataTableQueryParams = {
      page: currentPage.value,
      page_size: pageSize.value,
    };

    if (searchQuery.value.trim()) {
      params.search = searchQuery.value.trim();
    }

    // Add all active filters
    for (const [key, value] of Object.entries(filters.value)) {
      if (value && value.trim()) {
        params[key] = value;
      }
    }

    return params;
  }

  // Fetch data
  async function fetch(): Promise<void> {
    loading.value = true;
    error.value = null;

    try {
      const params = buildParams();
      const response: PaginatedResponseWithFilters<T, F> = await fetchFn(params);

      items.value = response.results;
      totalCount.value = response.count;
      totalPages.value = response.total_pages;
      currentPage.value = response.current_page;
      hasNext.value = !!response.next;
      hasPrevious.value = !!response.previous;

      // Update filter options if provided
      if (response.filters) {
        filterOptions.value = response.filters;
      }

      log.debug('DataTable fetched', {
        count: items.value.length,
        total: totalCount.value,
        page: currentPage.value,
      });
    } catch (err) {
      log.error('DataTable fetch failed', err);
      const apiError = err as { error?: string; message?: string; status?: number };

      if (apiError.status === 401) {
        error.value = t('common.errors.authRequired');
      } else if (apiError.status === 403) {
        error.value = t('common.errors.noPermission');
      } else {
        error.value = apiError.error || apiError.message || t('common.errors.failedToLoadData');
      }
    } finally {
      loading.value = false;
    }
  }

  // Pagination actions
  function goToPage(page: number): void {
    if (page >= 1 && page <= totalPages.value && page !== currentPage.value) {
      currentPage.value = page;
      fetch();
    }
  }

  function handlePageSizeChange(size: number): void {
    pageSize.value = size;
    currentPage.value = 1;
    fetch();
  }

  // Filter actions
  function setFilter(key: string, value: string): void {
    filters.value = { ...filters.value, [key]: value };
    currentPage.value = 1;
    fetch();
  }

  function clearFilter(key: string): void {
    const newFilters = { ...filters.value };
    delete newFilters[key];
    filters.value = newFilters;
    currentPage.value = 1;
    fetch();
  }

  function clearAllFilters(): void {
    searchQuery.value = '';
    filters.value = {};
    currentPage.value = 1;
    fetch();
  }

  function debouncedSearch(): void {
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }
    searchTimeout = setTimeout(() => {
      currentPage.value = 1;
      fetch();
    }, debounceMs);
  }

  async function refresh(): Promise<void> {
    await fetch();
  }

  // Clean up debounce timer when the component using this composable unmounts
  onUnmounted(() => {
    if (searchTimeout) {
      clearTimeout(searchTimeout);
      searchTimeout = null;
    }
  });

  return {
    // Data
    items,
    filterOptions,

    // State
    loading,
    error,

    // Pagination
    currentPage,
    pageSize,
    totalCount,
    totalPages,
    hasNext,
    hasPrevious,
    rangeStart,
    rangeEnd,
    pageNumbers,

    // Filters
    searchQuery,
    filters,
    hasFilters,

    // Actions
    fetch,
    goToPage,
    handlePageSizeChange,
    setFilter,
    clearFilter,
    clearAllFilters,
    debouncedSearch,
    refresh,
  };
}
