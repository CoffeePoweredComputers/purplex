/**
 * useSubmissions - Composable for unified submissions management.
 *
 * Provides shared state and logic for the SubmissionsPage component,
 * including pagination, filtering, debounced search, and role-aware API calls.
 *
 * Usage:
 *   const ctx = provideContentContext();
 *   const submissions = useSubmissions(ctx, courseId);
 */
import { computed, ref, watch, type ComputedRef, type Ref } from 'vue';
import type { ContentContext } from './useContentContext';
import type {
  PaginatedSubmissions,
  SubmissionFilters,
  SubmissionQueryParams,
  SubmissionSummary
} from '@/services/contentService';
import type { SubmissionDetailed } from '@/types';
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
  const { courseId, initialPageSize = 25 } = options;

  // Data
  const submissions = ref<SubmissionSummary[]>([]);
  const selectedSubmission = ref<SubmissionDetailed | null>(null);
  const filterOptions = ref<SubmissionFilters>({
    problem_sets: [],
    courses: [],
    statuses: ['complete', 'partial', 'incomplete']
  });

  // State
  const loading = ref(true);
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
  const statusFilter = ref('');
  const problemSetFilter = ref('');
  const courseFilter = ref('');

  // Modal
  const showViewModal = ref(false);

  // Debounce timer
  let searchTimeout: ReturnType<typeof setTimeout> | null = null;

  // Computed: Pagination range
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
    return !!(
      searchQuery.value ||
      statusFilter.value ||
      problemSetFilter.value ||
      courseFilter.value
    );
  });

  // Computed: Filter summary for display
  const filterSummary = computed(() => {
    const parts: string[] = [];
    if (searchQuery.value) {
      parts.push(`"${searchQuery.value}"`);
    }
    if (statusFilter.value) {
      parts.push(formatStatus(statusFilter.value));
    }
    if (problemSetFilter.value) {
      parts.push(getProblemSetTitle(problemSetFilter.value));
    }
    if (courseFilter.value) {
      const course = filterOptions.value.courses?.find(c => c.id === courseFilter.value);
      if (course) parts.push(course.name);
    }
    return parts.length > 0 ? `(filtered by ${parts.join(', ')})` : '';
  });

  // Fetch submissions
  async function fetchSubmissions(): Promise<void> {
    loading.value = true;
    error.value = null;

    try {
      const params: SubmissionQueryParams = {
        page: currentPage.value,
        page_size: pageSize.value,
      };

      if (searchQuery.value.trim()) {
        params.search = searchQuery.value.trim();
      }
      if (statusFilter.value) {
        params.status = statusFilter.value;
      }
      if (problemSetFilter.value) {
        params.problem_set = problemSetFilter.value;
      }

      // Role-specific parameters
      if (ctx.isAdmin.value) {
        // Admin can filter by course
        if (courseFilter.value) {
          params.course = courseFilter.value;
        }
      } else {
        // Instructor requires course_id
        const cid = courseId?.value;
        if (!cid) {
          throw new Error('Course ID is required for instructor submissions');
        }
        params.course_id = cid;
      }

      const response: PaginatedSubmissions = await ctx.api.value.getSubmissions(params);

      submissions.value = response.results;
      totalCount.value = response.count;
      totalPages.value = response.total_pages;
      currentPage.value = response.current_page;
      hasNext.value = !!response.next;
      hasPrevious.value = !!response.previous;

      // Update filter options from response
      if (response.filters) {
        filterOptions.value = response.filters;
      }

      log.info('Submissions loaded', {
        count: submissions.value.length,
        total: totalCount.value,
        role: ctx.role.value
      });
    } catch (err) {
      log.error('Failed to fetch submissions', err);
      const apiError = err as { error?: string; status?: number };

      if (apiError.status === 401) {
        error.value = 'Authentication required. Please log in again.';
      } else if (apiError.status === 403) {
        error.value = 'You do not have permission to view these submissions.';
      } else if (apiError.status === 404) {
        error.value = 'Course not found.';
      } else {
        error.value = apiError.error || 'Failed to load submissions. Please try again.';
      }
    } finally {
      loading.value = false;
    }
  }

  // Pagination actions
  function goToPage(page: number): void {
    if (page >= 1 && page <= totalPages.value && page !== currentPage.value) {
      currentPage.value = page;
      fetchSubmissions();
    }
  }

  function handlePageSizeChange(): void {
    currentPage.value = 1;
    fetchSubmissions();
  }

  // Filter actions
  function handleFilterChange(): void {
    currentPage.value = 1;
    fetchSubmissions();
  }

  function debouncedSearch(): void {
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }
    searchTimeout = setTimeout(() => {
      currentPage.value = 1;
      fetchSubmissions();
    }, 300);
  }

  function clearFilters(): void {
    searchQuery.value = '';
    statusFilter.value = '';
    problemSetFilter.value = '';
    courseFilter.value = '';
    currentPage.value = 1;
    fetchSubmissions();
  }

  function clearSearchFilter(): void {
    searchQuery.value = '';
    currentPage.value = 1;
    fetchSubmissions();
  }

  function clearStatusFilter(): void {
    statusFilter.value = '';
    currentPage.value = 1;
    fetchSubmissions();
  }

  function clearProblemSetFilter(): void {
    problemSetFilter.value = '';
    currentPage.value = 1;
    fetchSubmissions();
  }

  function clearCourseFilter(): void {
    courseFilter.value = '';
    currentPage.value = 1;
    fetchSubmissions();
  }

  // Submission detail view
  async function viewSubmission(id: number): Promise<void> {
    try {
      loading.value = true;
      const cid = courseId?.value;
      selectedSubmission.value = await ctx.api.value.getSubmission(id, cid);
      showViewModal.value = true;
    } catch (err) {
      log.error('Failed to load submission details', { error: err, id });
      error.value = 'Failed to load submission details. Please try again.';
    } finally {
      loading.value = false;
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
      if (searchQuery.value.trim()) params.search = searchQuery.value.trim();
      if (statusFilter.value) params.status = statusFilter.value;
      if (problemSetFilter.value) params.problem_set = problemSetFilter.value;
      if (courseFilter.value) params.course = courseFilter.value;

      const blob = await ctx.api.value.exportSubmissions(params);

      // Generate filename
      let filename = 'submissions_export';
      if (searchQuery.value) {
        filename += `_search-${searchQuery.value.replace(/[^a-zA-Z0-9]/g, '_')}`;
      }
      if (statusFilter.value) filename += `_status-${statusFilter.value}`;
      if (problemSetFilter.value) {
        filename += `_set-${problemSetFilter.value.replace(/[^a-zA-Z0-9]/g, '_')}`;
      }
      if (courseFilter.value) {
        filename += `_course-${courseFilter.value.replace(/[^a-zA-Z0-9]/g, '_')}`;
      }
      filename += `_${new Date().toISOString().split('T')[0]}.csv`;

      // Trigger download
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
      error.value = 'Failed to export CSV. Please try again.';
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
      error.value = 'Unable to download submission data.';
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
      error.value = 'Failed to download submission data. Please try again.';
    }
  }

  // Helper functions
  function getScoreClass(score: number): string {
    if (score >= 80) return 'score-high';
    if (score >= 50) return 'score-medium';
    return 'score-low';
  }

  function getStatusClass(status: string): string {
    switch (status.toLowerCase()) {
      case 'passed':
      case 'complete':
        return 'status-success';
      case 'partial':
        return 'status-warning';
      case 'failed':
      case 'incomplete':
        return 'status-error';
      case 'pending':
        return 'status-pending';
      default:
        return 'status-default';
    }
  }

  function getComprehensionClass(level: string | null): string {
    if (!level) return 'comprehension-not-evaluated';

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
    if (!level) return 'Not Evaluated';

    switch (level.toLowerCase()) {
      case 'high-level':
      case 'relational':
        return 'High-level';
      case 'low-level':
      case 'multi_structural':
      case 'multistructural':
        return 'Low-level';
      default:
        return 'Not Evaluated';
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
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toISOString();
  }

  function getProblemSetTitle(slug: string): string {
    const ps = filterOptions.value.problem_sets.find(p => p.slug === slug);
    return ps ? ps.title : slug;
  }

  // Watch for course ID changes (for instructor view)
  if (courseId) {
    watch(courseId, () => {
      currentPage.value = 1;
      pageSize.value = initialPageSize;
      searchQuery.value = '';
      statusFilter.value = '';
      problemSetFilter.value = '';
      courseFilter.value = '';
      fetchSubmissions();
    });
  }

  return {
    // Data
    submissions,
    selectedSubmission,
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
    statusFilter,
    problemSetFilter,
    courseFilter,
    hasFilters,
    filterSummary,

    // Actions
    fetchSubmissions,
    goToPage,
    handlePageSizeChange,
    handleFilterChange,
    debouncedSearch,
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
