<template>
  <ContentEditorLayout
    :show-header="false"
    :show-breadcrumb="false"
  >
    <!-- Filters Section -->
    <div class="filters-section" role="search" aria-label="Filter submissions">
      <div class="filter-group">
        <label for="search">Search</label>
        <input
          id="search"
          v-model="searchQuery"
          type="text"
          placeholder="Search by student or problem..."
          aria-label="Search submissions by student name or problem"
          @input="debouncedSearch"
        >
      </div>

      <div class="filter-group">
        <label for="status">Status</label>
        <select
          id="status"
          v-model="statusFilter"
          @change="handleFilterChange"
        >
          <option value="">All Statuses</option>
          <option value="complete">Complete</option>
          <option value="partial">Partial</option>
          <option value="incomplete">Incomplete</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="problem-set">Problem Set</label>
        <select
          id="problem-set"
          v-model="problemSetFilter"
          @change="handleFilterChange"
        >
          <option value="">All Problem Sets</option>
          <option
            v-for="ps in filterOptions.problem_sets"
            :key="ps.slug"
            :value="ps.slug"
          >
            {{ ps.title }}
          </option>
        </select>
      </div>

      <!-- Admin only: Course filter (when not in course drill-down mode) -->
      <div v-if="ctx.isAdmin.value && !isCourseScoped" class="filter-group">
        <label for="course">Course</label>
        <select
          id="course"
          v-model="courseFilter"
          @change="handleFilterChange"
        >
          <option value="">All Courses</option>
          <option
            v-for="course in filterOptions.courses"
            :key="course.id"
            :value="course.id"
          >
            {{ course.name }}
          </option>
        </select>
      </div>

      <div class="filter-actions">
        <Transition name="fade">
          <button
            v-if="hasFilters"
            class="clear-filters-btn"
            aria-label="Clear all filters"
            @click="clearFilters"
          >
            Clear Filters
          </button>
        </Transition>
        <!-- Admin only: Export button -->
        <button
          v-if="ctx.isAdmin.value"
          class="action-button export-button"
          :disabled="totalCount === 0"
          title="Export filtered submissions to CSV"
          @click="exportToCSV"
        >
          Export CSV ({{ totalCount }})
        </button>
      </div>
    </div>

    <!-- Active Filter Chips -->
    <Transition name="slide-fade">
      <div
        v-if="hasFilters"
        class="active-filters"
        role="region"
        aria-label="Active filters"
      >
        <span class="active-filters-label">Active filters:</span>
        <div class="filter-chips">
          <button
            v-if="searchQuery"
            class="filter-chip"
            :aria-label="`Remove search filter: ${searchQuery}`"
            @click="clearSearchFilter"
          >
            <span class="chip-label">Search:</span>
            <span class="chip-value">{{ searchQuery }}</span>
            <span class="chip-remove" aria-hidden="true">x</span>
          </button>
          <button
            v-if="statusFilter"
            class="filter-chip"
            :aria-label="`Remove status filter: ${formatStatus(statusFilter)}`"
            @click="clearStatusFilter"
          >
            <span class="chip-label">Status:</span>
            <span class="chip-value">{{ formatStatus(statusFilter) }}</span>
            <span class="chip-remove" aria-hidden="true">x</span>
          </button>
          <button
            v-if="problemSetFilter"
            class="filter-chip"
            :aria-label="`Remove problem set filter: ${getProblemSetTitle(problemSetFilter)}`"
            @click="clearProblemSetFilter"
          >
            <span class="chip-label">Problem Set:</span>
            <span class="chip-value">{{ getProblemSetTitle(problemSetFilter) }}</span>
            <span class="chip-remove" aria-hidden="true">x</span>
          </button>
          <button
            v-if="courseFilter && ctx.isAdmin.value"
            class="filter-chip"
            :aria-label="`Remove course filter`"
            @click="clearCourseFilter"
          >
            <span class="chip-label">Course:</span>
            <span class="chip-value">{{ getCourseName(courseFilter) }}</span>
            <span class="chip-remove" aria-hidden="true">x</span>
          </button>
        </div>
      </div>
    </Transition>

    <!-- Results Summary Bar -->
    <div
      v-if="!loading && !error"
      class="results-bar"
      role="status"
      aria-live="polite"
    >
      <span class="results-count">
        <template v-if="totalCount > 0">
          Showing {{ rangeStart }}-{{ rangeEnd }} of {{ totalCount }} submissions
        </template>
        <template v-else>
          No submissions found
        </template>
      </span>
      <span
        v-if="hasFilters && totalCount > 0"
        class="results-filter-summary"
      >
        {{ filterSummary }}
      </span>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner" />
      <p>Loading submissions...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state" role="alert">
      <div class="error-icon" aria-hidden="true">!!!</div>
      <span class="visually-hidden">Error:</span>
      <h3>Unable to Load Submissions</h3>
      <p>{{ error }}</p>
      <button class="retry-btn" aria-label="Retry loading submissions" @click="fetchSubmissions">
        Try Again
      </button>
    </div>

    <!-- Submissions Table -->
    <div v-else-if="submissions.length > 0" class="submissions-table-container">
      <table class="submissions-table">
        <thead>
          <tr>
            <th scope="col">Student</th>
            <th scope="col">Problem</th>
            <th scope="col">Problem Set</th>
            <!-- Admin: Show course column when not filtered to single course -->
            <th v-if="ctx.isAdmin.value && !isCourseScoped && !courseFilter" scope="col">
              Course
            </th>
            <th scope="col" class="center">Score</th>
            <!-- Admin: Show comprehension column -->
            <th v-if="ctx.isAdmin.value" scope="col" class="center">
              Comprehension
            </th>
            <th scope="col" class="center">Status</th>
            <th scope="col">Submitted</th>
            <!-- Admin: Show actions column -->
            <th v-if="ctx.isAdmin.value" scope="col" class="center">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="submission in submissions" :key="submission.id">
            <td class="student-cell">
              <div v-if="ctx.isAdmin.value" class="user-info">
                <div class="user-avatar-small">
                  {{ submission.user.charAt(0).toUpperCase() }}
                </div>
                <span class="username">{{ submission.user }}</span>
              </div>
              <span v-else>{{ submission.user }}</span>
            </td>
            <td class="problem-cell">{{ submission.problem }}</td>
            <td class="problem-set-cell">
              <span class="problem-set-tag">{{ submission.problem_set || '-' }}</span>
            </td>
            <td v-if="ctx.isAdmin.value && !isCourseScoped && !courseFilter" class="course-cell">
              <span class="course-tag">{{ submission.course || 'No Course' }}</span>
            </td>
            <td class="center">
              <span
                :class="['score-badge', getScoreClass(submission.score)]"
                role="status"
                :aria-label="`Score: ${submission.score}%`"
              >
                {{ submission.score }}%
              </span>
            </td>
            <td v-if="ctx.isAdmin.value" class="center">
              <span
                :class="['comprehension-badge', getComprehensionClass(submission.comprehension_level)]"
              >
                {{ formatComprehensionLevel(submission.comprehension_level) }}
              </span>
            </td>
            <td class="center">
              <span
                :class="['status-badge', getStatusClass(submission.status)]"
                role="status"
                :aria-label="`Status: ${formatStatus(submission.status)}`"
              >
                {{ formatStatus(submission.status) }}
              </span>
            </td>
            <td class="date-cell">
              {{ formatDate(submission.submitted_at) }}
            </td>
            <td v-if="ctx.isAdmin.value" class="actions-cell">
              <button
                class="action-button view-button"
                title="View Details"
                @click="viewSubmission(submission.id)"
              >
                View
              </button>
              <button
                class="action-button download-button"
                title="Download Data"
                @click="downloadSubmissionData(submission)"
              >
                Download
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <nav class="pagination" role="navigation" aria-label="Submissions pagination">
        <div class="pagination-left">
          <label for="page-size" class="page-size-label">Show:</label>
          <select
            id="page-size"
            v-model="pageSize"
            class="page-size-select"
            aria-label="Number of submissions per page"
            @change="handlePageSizeChange"
          >
            <option :value="10">10</option>
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
          <span class="page-size-suffix">per page</span>
        </div>

        <div class="pagination-center">
          <!-- Admin: Full page navigation -->
          <template v-if="ctx.isAdmin.value">
            <button
              class="pagination-btn"
              :disabled="!hasPrevious"
              title="First page"
              @click="goToPage(1)"
            >
              &laquo;
            </button>
            <button
              class="pagination-btn"
              :disabled="!hasPrevious"
              title="Previous page"
              @click="goToPage(currentPage - 1)"
            >
              &lsaquo;
            </button>

            <button
              v-for="page in pageNumbers"
              :key="page"
              class="pagination-btn page-number"
              :class="{ active: page === currentPage }"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>

            <button
              class="pagination-btn"
              :disabled="!hasNext"
              title="Next page"
              @click="goToPage(currentPage + 1)"
            >
              &rsaquo;
            </button>
            <button
              class="pagination-btn"
              :disabled="!hasNext"
              title="Last page"
              @click="goToPage(totalPages)"
            >
              &raquo;
            </button>
          </template>

          <!-- Instructor: Simple prev/next -->
          <template v-else>
            <button
              class="page-btn"
              :disabled="currentPage === 1"
              :aria-disabled="currentPage === 1 ? 'true' : undefined"
              aria-label="Go to previous page"
              @click="goToPage(currentPage - 1)"
            >
              Previous
            </button>
            <span class="page-info" aria-live="polite">
              Page {{ currentPage }} of {{ totalPages }}
            </span>
            <button
              class="page-btn"
              :disabled="currentPage === totalPages || totalPages === 0"
              :aria-disabled="currentPage === totalPages || totalPages === 0 ? 'true' : undefined"
              aria-label="Go to next page"
              @click="goToPage(currentPage + 1)"
            >
              Next
            </button>
          </template>
        </div>

        <div class="pagination-right">
          <span v-if="ctx.isAdmin.value" class="pagination-info">
            {{ rangeStart }}-{{ rangeEnd }} of {{ totalCount }}
          </span>
        </div>
      </nav>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <div class="empty-icon" aria-hidden="true">[ ]</div>
      <span class="visually-hidden">Information:</span>
      <h3>No Submissions Found</h3>
      <p v-if="hasFilters">
        Try adjusting your filters to see more results.
      </p>
      <p v-else>
        No students have submitted solutions yet.
      </p>
    </div>

    <!-- Admin only: View Submission Modal -->
    <ViewSubmissionModal
      v-if="ctx.isAdmin.value"
      :is-visible="showViewModal"
      :submission="selectedSubmission"
      @close="closeViewModal"
      @download="downloadSubmissionData"
    />
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import ViewSubmissionModal from '@/modals/ViewSubmissionModal.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { useSubmissions } from '@/composables/useSubmissions';

// Provide role-aware context
const ctx = provideContentContext();
const route = useRoute();

// Get courseId from route (for instructor mode or admin drill-down)
const courseId = computed(() => route.params.courseId as string | undefined);
const isCourseScoped = computed(() => !!courseId.value);

// Initialize submissions composable
const {
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
  getProblemSetTitle,
} = useSubmissions(ctx, { courseId });

// Helper for course name display
function getCourseName(courseIdValue: string): string {
  const course = filterOptions.value.courses?.find(c => c.id === courseIdValue);
  return course ? course.name : courseIdValue;
}

// Fetch on mount
onMounted(fetchSubmissions);
</script>

<style scoped>
/* Visually hidden utility for screen readers (WCAG) */
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Filters Section */
.filters-section {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 120px;
  flex: 0 1 auto;
}

.filter-group label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.filter-group input,
.filter-group select {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border, var(--color-bg-input));
  border-radius: var(--radius-base);
  background: var(--color-surface, var(--color-bg-hover));
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  height: 38px;
  transition: var(--transition-base);
}

.filter-group input {
  min-width: 180px;
}

.filter-group input:focus,
.filter-group select:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

.filter-group input:focus-visible,
.filter-group select:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

/* Filter Actions */
.filter-actions {
  display: flex;
  align-items: flex-end;
  height: 38px;
}

.clear-filters-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  background: transparent;
  border: 1px solid var(--color-border, var(--color-bg-input));
  border-radius: var(--radius-base);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-base);
  white-space: nowrap;
}

.clear-filters-btn:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-primary-gradient-start);
}

/* Active Filter Chips */
.active-filters {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
}

.active-filters-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid var(--color-primary-gradient-start);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-xs);
  color: var(--color-primary-gradient-start);
  cursor: pointer;
  transition: var(--transition-base);
}

.filter-chip:hover {
  background: rgba(102, 126, 234, 0.2);
}

.chip-label {
  font-weight: 600;
}

.chip-value {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-left: var(--spacing-xs);
  border-radius: 50%;
  background: var(--color-primary-gradient-start);
  color: white;
  font-size: 10px;
  font-weight: bold;
  line-height: 1;
}

/* Results Bar */
.results-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border, var(--color-bg-input));
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-lg);
}

.results-count {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.results-filter-summary {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-fade-enter-active {
  transition: all 0.2s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.15s ease-in;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-8px);
  opacity: 0;
}

/* Loading State */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--color-border, var(--color-bg-input));
  border-top-color: var(--color-primary-gradient-start);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: var(--spacing-lg);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State */
.error-state {
  text-align: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.error-icon {
  font-size: 2rem;
  margin-bottom: var(--spacing-lg);
  color: var(--color-error);
  font-weight: bold;
}

.error-state h3 {
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.error-state p {
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-lg);
}

.retry-btn {
  padding: var(--spacing-md) var(--spacing-xl);
  background: var(--color-primary-gradient-start);
  color: white;
  border: none;
  border-radius: var(--radius-base);
  cursor: pointer;
  font-weight: 600;
  transition: var(--transition-base);
}

.retry-btn:hover {
  background: var(--color-primary-gradient-end);
}

/* Table Container */
.submissions-table-container {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border, var(--color-bg-input));
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

/* Table */
.submissions-table {
  width: 100%;
  border-collapse: collapse;
}

.submissions-table th,
.submissions-table td {
  padding: var(--spacing-md) var(--spacing-lg);
  text-align: left;
  border-bottom: 1px solid var(--color-border, var(--color-bg-input));
}

.submissions-table th {
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: var(--color-bg-hover);
}

.submissions-table th.center,
.submissions-table td.center {
  text-align: center;
}

.submissions-table tbody tr:hover {
  background: var(--color-bg-hover);
}

.submissions-table tbody tr:last-child td {
  border-bottom: none;
}

/* Cell styles */
.student-cell {
  font-weight: 600;
  color: var(--color-text-primary);
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.user-avatar-small {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-circle);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-primary);
  font-weight: 600;
  font-size: var(--font-size-xs);
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}

.username {
  font-size: var(--font-size-sm);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.problem-cell {
  color: var(--color-text-primary);
}

.problem-set-cell,
.date-cell {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.problem-set-tag {
  display: inline-block;
  padding: 2px var(--spacing-xs);
  background: var(--color-info-bg);
  color: var(--color-info);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.course-tag {
  display: inline-block;
  padding: 2px var(--spacing-xs);
  background: var(--color-success-bg);
  color: var(--color-success);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

/* Badges */
.score-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.score-badge.score-high {
  background-color: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.score-badge.score-medium {
  background-color: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.score-badge.score-low {
  background-color: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.status-success {
  background-color: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.status-badge.status-warning {
  background-color: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.status-badge.status-error {
  background-color: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.status-badge.status-pending {
  background-color: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}

.comprehension-badge {
  display: inline-block;
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-base);
  font-weight: 500;
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  min-width: 80px;
  text-align: center;
}

.comprehension-badge.comprehension-high {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.comprehension-badge.comprehension-low {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.comprehension-badge.comprehension-not-evaluated {
  background: var(--color-bg-hover);
  color: var(--color-text-muted);
  border: 1px solid var(--color-bg-input);
}

/* Actions */
.actions-cell {
  text-align: center;
  white-space: nowrap;
}

.action-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-xs);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-base);
  margin-right: var(--spacing-xs);
}

.action-button:last-child {
  margin-right: 0;
}

.export-button {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-colored);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
}

.export-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.export-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.view-button {
  background: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}

.view-button:hover {
  background: var(--color-info);
  color: var(--color-text-primary);
}

.download-button {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.download-button:hover {
  background: var(--color-success);
  color: var(--color-text-primary);
}

/* Pagination */
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
  text-align: right;
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

/* Admin pagination buttons */
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
  color: var(--color-text-primary);
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-btn.active {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  font-weight: 600;
  box-shadow: var(--shadow-colored);
}

/* Instructor pagination buttons */
.page-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border, var(--color-bg-input));
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-base);
}

.page-btn:hover:not(:disabled) {
  background: var(--color-primary-gradient-start);
  color: white;
  border-color: var(--color-primary-gradient-start);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  padding: 0 var(--spacing-lg);
}

/* Empty State */
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
  .filters-section {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-group {
    width: 100%;
    min-width: unset;
  }

  .filter-group input {
    min-width: unset;
  }

  .filter-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .clear-filters-btn {
    width: 100%;
  }

  .active-filters {
    flex-direction: column;
    align-items: flex-start;
  }

  .results-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
  }

  .submissions-table th,
  .submissions-table td {
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: var(--font-size-sm);
  }

  /* Hide some columns on mobile */
  .submissions-table th:nth-child(3),
  .submissions-table td:nth-child(3) {
    display: none;
  }

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
