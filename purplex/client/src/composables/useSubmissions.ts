/**
 * useSubmissions - Composable for unified submissions management.
 *
 * Delegates pagination, search, and filter state management to useDataTable,
 * while keeping all domain-specific logic (filter summary, CSV export,
 * view modal, download, formatting helpers).
 */
import { computed, type ComputedRef, type Ref, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { ContentContext } from './useContentContext';
import { useDataTable } from './useDataTable';
import type {
  PaginatedSubmissions,
  SubmissionFilters,
  SubmissionQueryParams,
  SubmissionSummary
} from '@/services/contentService';
import type { SubmissionDetailed } from '@/types';
import type { DataTableQueryParams } from '@/types/datatable';
import { log } from '@/utils/logger';

export interface UseSubmissionsOptions {
  /** Course ID for instructor mode or admin drill-down (from route param) */
  courseId?: ComputedRef<string | undefined>;
  /** Initial page size */
  initialPageSize?: number;
}

export interface UseSubmissionsReturn {
  // Data
  submissions: Ref<SubmissionSummary[]>;
  selectedSubmission: Ref<SubmissionDetailed | null>;
  filterOptions: Ref<SubmissionFilters>;

  // State
  loading: Ref<boolean>;
  error: Ref<string | null>;

  // Pagination (delegated from useDataTable)
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
  statusFilter: Ref<string>;
  problemSetFilter: Ref<string>;
  courseFilter: Ref<string>;
  hasFilters: ComputedRef<boolean>;
  filterSummary: ComputedRef<string>;

  // Actions
  fetchSubmissions: () => Promise<void>;
  goToPage: (page: number) => void;
  handlePageSizeChange: () => void;
  handleFilterChange: () => void;
  debouncedSearch: () => void;
  clearFilters: () => void;
  clearSearchFilter: () => void;
  clearStatusFilter: () => void;
  clearProblemSetFilter: () => void;
  clearCourseFilter: () => void;
  viewSubmission: (id: number) => Promise<void>;
  closeViewModal: () => void;
  exportToCSV: () => Promise<void>;
  downloadSubmissionData: (submission: SubmissionSummary) => Promise<void>;

  // Modal state
  showViewModal: Ref<boolean>;

  // Helpers
  getScoreClass: (score: number) => string;
  getStatusClass: (status: string) => string;
  getComprehensionClass: (level: string | null) => string;
  formatStatus: (status: string) => string;
  formatComprehensionLevel: (level: string | null) => string;
  formatDate: (dateString: string) => string;
  formatISODate: (dateString: string | null) => string;
  getProblemSetTitle: (slug: string) => string;
}

export function useSubmissions(
  ctx: ContentContext,
  options: UseSubmissionsOptions = {}
): UseSubmissionsReturn {
  const { t } = useI18n();
  const { courseId, initialPageSize = 25 } = options;

  // Domain-specific filter refs (not part of useDataTable's generic filters)
  const statusFilter = ref('');
  const problemSetFilter = ref('');
  const courseFilter = ref('');

  // Domain-specific data
  const selectedSubmission = ref<SubmissionDetailed | null>(null);
  const showViewModal = ref(false);

  // Delegate pagination/search/error/loading to useDataTable
  const table = useDataTable<SubmissionSummary, SubmissionFilters>({
    fetchFn: async (params: DataTableQueryParams) => {
      const apiParams: SubmissionQueryParams = {
        page: params.page,
        page_size: params.page_size,
      };

      if (params.search) {apiParams.search = params.search;}
      if (statusFilter.value) {apiParams.status = statusFilter.value;}
      if (problemSetFilter.value) {apiParams.problem_set = problemSetFilter.value;}

      // Role-specific parameters
      if (ctx.isAdmin.value) {
        if (courseFilter.value) {apiParams.course = courseFilter.value;}
      } else {
        const cid = courseId?.value;
        if (!cid) {throw new Error('Course ID is required for instructor submissions');}
        apiParams.course_id = cid;
      }

      const response: PaginatedSubmissions = await ctx.api.value.getSubmissions(apiParams);
      return response;
    },
    initialPageSize,
  });

  // Expose items as 'submissions' for domain clarity
  const submissions = table.items;
  const filterOptions = computed(() =>
    table.filterOptions.value ?? { problem_sets: [], courses: [], statuses: ['complete', 'partial', 'incomplete'] }
  );

  // Domain-specific: has filters active (extends useDataTable's hasFilters with domain filters)
  const hasFilters = computed(() => {
    return !!(
      table.searchQuery.value ||
      statusFilter.value ||
      problemSetFilter.value ||
      courseFilter.value
    );
  });

  // Filter summary for display
  const filterSummary = computed(() => {
    const parts: string[] = [];
    if (table.searchQuery.value) {parts.push(`"${table.searchQuery.value}"`);}
    if (statusFilter.value) {parts.push(formatStatus(statusFilter.value));}
    if (problemSetFilter.value) {parts.push(getProblemSetTitle(problemSetFilter.value));}
    if (courseFilter.value) {
      const course = filterOptions.value.courses?.find((c: { id: string; name: string }) => c.id === courseFilter.value);
      if (course) {parts.push(course.name);}
    }
    return parts.length > 0 ? `(filtered by ${parts.join(', ')})` : '';
  });

  // Domain filter change — reset page and refetch
  function handleFilterChange(): void {
    table.currentPage.value = 1;
    table.fetch();
  }

  // Domain-specific page size change (v-model binding, no event arg)
  function handlePageSizeChange(): void {
    table.currentPage.value = 1;
    table.fetch();
  }

  // Clear filters
  function clearFilters(): void {
    statusFilter.value = '';
    problemSetFilter.value = '';
    courseFilter.value = '';
    table.clearAllFilters(); // resets searchQuery and fetches
  }

  function clearSearchFilter(): void {
    table.searchQuery.value = '';
    table.currentPage.value = 1;
    table.fetch();
  }

  function clearStatusFilter(): void {
    statusFilter.value = '';
    table.currentPage.value = 1;
    table.fetch();
  }

  function clearProblemSetFilter(): void {
    problemSetFilter.value = '';
    table.currentPage.value = 1;
    table.fetch();
  }

  function clearCourseFilter(): void {
    courseFilter.value = '';
    table.currentPage.value = 1;
    table.fetch();
  }

  // Submission detail view
  async function viewSubmission(id: number): Promise<void> {
    try {
      table.loading.value = true;
      const cid = courseId?.value;
      selectedSubmission.value = await ctx.api.value.getSubmission(id, cid);
      showViewModal.value = true;
    } catch (err) {
      log.error('Failed to load submission details', { error: err, id });
      table.error.value = t('admin.submissions.failedToLoadDetails');
    } finally {
      table.loading.value = false;
    }
  }

  function closeViewModal(): void {
    showViewModal.value = false;
    selectedSubmission.value = null;
  }

  // Export (admin only)
  async function exportToCSV(): Promise<void> {
    if (!ctx.isAdmin.value) {
      log.warn('Export attempted by non-admin user');
      return;
    }

    try {
      const params: SubmissionQueryParams = {};
      if (table.searchQuery.value.trim()) {params.search = table.searchQuery.value.trim();}
      if (statusFilter.value) {params.status = statusFilter.value;}
      if (problemSetFilter.value) {params.problem_set = problemSetFilter.value;}
      if (courseFilter.value) {params.course = courseFilter.value;}

      const blob = await ctx.api.value.exportSubmissions(params);

      let filename = 'submissions_export';
      if (table.searchQuery.value) {
        filename += `_search-${table.searchQuery.value.replace(/[^a-zA-Z0-9]/g, '_')}`;
      }
      if (statusFilter.value) {filename += `_status-${statusFilter.value}`;}
      if (problemSetFilter.value) {
        filename += `_set-${problemSetFilter.value.replace(/[^a-zA-Z0-9]/g, '_')}`;
      }
      if (courseFilter.value) {
        filename += `_course-${courseFilter.value.replace(/[^a-zA-Z0-9]/g, '_')}`;
      }
      filename += `_${new Date().toISOString().split('T')[0]}.csv`;

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      log.info('Export successful', { filename });
    } catch (err) {
      log.error('Export failed', err);
      table.error.value = t('admin.submissions.failedToExport');
    }
  }

  // Download individual submission (admin only)
  async function downloadSubmissionData(submission: SubmissionSummary): Promise<void> {
    if (!ctx.isAdmin.value) {
      log.warn('Download attempted by non-admin user');
      return;
    }

    if (!submission?.id) {
      log.error('Invalid submission for download', { submission });
      table.error.value = t('admin.submissions.unableToDownload');
      return;
    }

    try {
      const cid = courseId?.value;
      const fullSubmission = await ctx.api.value.getSubmission(submission.id, cid);

      const jsonContent = JSON.stringify(fullSubmission, null, 2);
      const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute(
        'download',
        `submission_${submission.id}_${submission.user}_${new Date().toISOString().split('T')[0]}.json`
      );
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      log.info('Submission downloaded', { id: submission.id });
    } catch (err) {
      log.error('Download failed', { error: err, id: submission.id });
      table.error.value = t('admin.submissions.failedToDownload');
    }
  }

  // Helper functions
  function getScoreClass(score: number): string {
    if (score >= 80) {return 'score-high';}
    if (score >= 50) {return 'score-medium';}
    return 'score-low';
  }

  function getStatusClass(status: string): string {
    switch (status.toLowerCase()) {
      case 'complete':
        return 'status-success';
      case 'partial':
        return 'status-warning';
      case 'incomplete':
        return 'status-error';
      case 'pending':
        return 'status-pending';
      default:
        return 'status-default';
    }
  }

  function getComprehensionClass(level: string | null): string {
    if (!level) {return 'comprehension-not-evaluated';}

    switch (level.toLowerCase()) {
      case 'high-level':
      case 'relational':
        return 'comprehension-high';
      case 'low-level':
      case 'multi_structural':
      case 'multistructural':
        return 'comprehension-low';
      default:
        return 'comprehension-not-evaluated';
    }
  }

  function formatStatus(status: string): string {
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  function formatComprehensionLevel(level: string | null): string {
    if (!level) {return t('admin.submissions.comprehension.notEvaluated');}

    switch (level.toLowerCase()) {
      case 'high-level':
      case 'relational':
        return t('admin.submissions.comprehension.highLevel');
      case 'low-level':
      case 'multi_structural':
      case 'multistructural':
        return t('admin.submissions.comprehension.lowLevel');
      default:
        return t('admin.submissions.comprehension.notEvaluated');
    }
  }

  function formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function formatISODate(dateString: string | null): string {
    if (!dateString) {return t('admin.submissions.unknownDate');}
    const date = new Date(dateString);
    return date.toISOString();
  }

  function getProblemSetTitle(slug: string): string {
    const ps = filterOptions.value.problem_sets.find((p: { slug: string; title: string }) => p.slug === slug);
    return ps ? ps.title : slug;
  }

  // Watch for course ID changes (for instructor view)
  if (courseId) {
    watch(courseId, () => {
      table.currentPage.value = 1;
      table.pageSize.value = initialPageSize;
      table.searchQuery.value = '';
      statusFilter.value = '';
      problemSetFilter.value = '';
      courseFilter.value = '';
      table.fetch();
    });
  }

  return {
    // Data
    submissions,
    selectedSubmission,
    filterOptions,

    // State (delegated)
    loading: table.loading,
    error: table.error,

    // Pagination (delegated)
    currentPage: table.currentPage,
    pageSize: table.pageSize,
    totalCount: table.totalCount,
    totalPages: table.totalPages,
    hasNext: table.hasNext,
    hasPrevious: table.hasPrevious,
    rangeStart: table.rangeStart,
    rangeEnd: table.rangeEnd,
    pageNumbers: table.pageNumbers,

    // Filters
    searchQuery: table.searchQuery,
    statusFilter,
    problemSetFilter,
    courseFilter,
    hasFilters,
    filterSummary,

    // Actions
    fetchSubmissions: table.fetch,
    goToPage: table.goToPage,
    handlePageSizeChange,
    handleFilterChange,
    debouncedSearch: table.debouncedSearch,
    clearFilters,
    clearSearchFilter,
    clearStatusFilter,
    clearProblemSetFilter,
    clearCourseFilter,
    viewSubmission,
    closeViewModal,
    exportToCSV,
    downloadSubmissionData,

    // Modal
    showViewModal,

    // Helpers
    getScoreClass,
    getStatusClass,
    getComprehensionClass,
    formatStatus,
    formatComprehensionLevel,
    formatDate,
    formatISODate,
    getProblemSetTitle,
  };
}
