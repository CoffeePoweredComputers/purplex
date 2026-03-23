<template>
  <ContentEditorLayout
    :show-header="false"
    :show-breadcrumb="false"
  >
    <DataTable
      :columns="columns"
      :items="submissions"
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
      :item-label="$t('admin.submissions.itemLabel')"
      row-key="id"
      :empty-title="$t('admin.submissions.noSubmissions')"
      :empty-message="hasFilters
        ? $t('admin.submissions.emptyFiltered')
        : $t('admin.submissions.emptyDefault')"
      @go-to-page="goToPage"
      @page-size-change="handlePageSizeChange"
      @retry="fetchSubmissions"
    >
      <!-- Filters -->
      <template #filters>
        <div class="filters-section" role="search" :aria-label="$t('admin.submissions.filterSubmissions')">
          <div class="filter-group">
            <label for="search">{{ $t('common.search') }}</label>
            <input
              id="search"
              v-model="searchQuery"
              type="text"
              :placeholder="$t('admin.submissions.searchPlaceholder')"
              :aria-label="$t('admin.submissions.searchAriaLabel')"
              @input="debouncedSearch"
            >
          </div>

          <div class="filter-group">
            <label for="status">{{ $t('common.status') }}</label>
            <select
              id="status"
              v-model="statusFilter"
              @change="handleFilterChange"
            >
              <option value="">{{ $t('admin.submissions.allStatuses') }}</option>
              <option value="complete">{{ $t('admin.submissions.complete') }}</option>
              <option value="partial">{{ $t('admin.submissions.partial') }}</option>
              <option value="incomplete">{{ $t('admin.submissions.incomplete') }}</option>
            </select>
          </div>

          <div class="filter-group">
            <label for="problem-set">{{ $t('admin.submissions.chipProblemSet').replace(':', '') }}</label>
            <select
              id="problem-set"
              v-model="problemSetFilter"
              @change="handleFilterChange"
            >
              <option value="">{{ $t('admin.submissions.allProblemSets') }}</option>
              <option
                v-for="ps in filterOptions.problem_sets"
                :key="ps.slug"
                :value="ps.slug"
              >
                {{ ps.title }}
              </option>
            </select>
          </div>

          <!-- Admin only: Course filter -->
          <div v-if="ctx.isAdmin.value && !isCourseScoped" class="filter-group">
            <label for="course">{{ $t('admin.submissions.chipCourse').replace(':', '') }}</label>
            <select
              id="course"
              v-model="courseFilter"
              @change="handleFilterChange"
            >
              <option value="">{{ $t('admin.submissions.allCourses') }}</option>
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
                :aria-label="$t('admin.submissions.clearAllFilters')"
                @click="clearFilters"
              >
                {{ $t('admin.submissions.clearFilters') }}
              </button>
            </Transition>
            <button
              v-if="ctx.isAdmin.value"
              class="action-button export-button"
              :disabled="totalCount === 0"
              :title="$t('admin.submissions.exportTitle')"
              @click="exportToCSV"
            >
              {{ $t('admin.submissions.exportCsv', { count: totalCount }) }}
            </button>
          </div>
        </div>

        <!-- Active Filter Chips -->
        <Transition name="slide-fade">
          <div
            v-if="hasFilters"
            class="active-filters"
            role="region"
            :aria-label="$t('admin.submissions.activeFiltersRegion')"
          >
            <span class="active-filters-label">{{ $t('admin.submissions.activeFilters') }}</span>
            <div class="filter-chips">
              <button
                v-if="searchQuery"
                class="filter-chip"
                :aria-label="$t('admin.submissions.removeSearchFilter', { query: searchQuery })"
                @click="clearSearchFilter"
              >
                <span class="chip-label">{{ $t('admin.submissions.chipSearch') }}</span>
                <span class="chip-value">{{ searchQuery }}</span>
                <!-- eslint-disable-next-line @intlify/vue-i18n/no-raw-text -->
                <span class="chip-remove" aria-hidden="true">x</span>
              </button>
              <button
                v-if="statusFilter"
                class="filter-chip"
                :aria-label="$t('admin.submissions.removeStatusFilter', { status: formatStatus(statusFilter) })"
                @click="clearStatusFilter"
              >
                <span class="chip-label">{{ $t('admin.submissions.chipStatus') }}</span>
                <span class="chip-value">{{ formatStatus(statusFilter) }}</span>
                <!-- eslint-disable-next-line @intlify/vue-i18n/no-raw-text -->
                <span class="chip-remove" aria-hidden="true">x</span>
              </button>
              <button
                v-if="problemSetFilter"
                class="filter-chip"
                :aria-label="$t('admin.submissions.removeProblemSetFilter', { title: getProblemSetTitle(problemSetFilter) })"
                @click="clearProblemSetFilter"
              >
                <span class="chip-label">{{ $t('admin.submissions.chipProblemSet') }}</span>
                <span class="chip-value">{{ getProblemSetTitle(problemSetFilter) }}</span>
                <!-- eslint-disable-next-line @intlify/vue-i18n/no-raw-text -->
                <span class="chip-remove" aria-hidden="true">x</span>
              </button>
              <button
                v-if="courseFilter && ctx.isAdmin.value"
                class="filter-chip"
                :aria-label="$t('admin.submissions.removeCourseFilter')"
                @click="clearCourseFilter"
              >
                <span class="chip-label">{{ $t('admin.submissions.chipCourse') }}</span>
                <span class="chip-value">{{ getCourseName(courseFilter) }}</span>
                <!-- eslint-disable-next-line @intlify/vue-i18n/no-raw-text -->
                <span class="chip-remove" aria-hidden="true">x</span>
              </button>
            </div>
          </div>
        </Transition>
      </template>

      <!-- Results actions (filter summary) -->
      <template #results-actions>
        <span
          v-if="hasFilters && totalCount > 0"
          class="results-filter-summary"
        >
          {{ filterSummary }}
        </span>
      </template>

      <!-- Student cell -->
      <template #cell-student="{ item }">
        <div v-if="ctx.isAdmin.value" class="user-info">
          <div class="user-avatar-small">
            {{ item.user.charAt(0).toUpperCase() }}
          </div>
          <span class="username">{{ item.user }}</span>
        </div>
        <span v-else>{{ item.user }}</span>
      </template>

      <!-- Problem set cell -->
      <template #cell-problem-set="{ item }">
        <span class="problem-set-tag">{{ item.problem_set || '-' }}</span>
      </template>

      <!-- Course cell (admin only) -->
      <template #cell-course="{ item }">
        <span class="course-tag">{{ item.course || $t('admin.submissions.noCourse') }}</span>
      </template>

      <!-- Score badge -->
      <template #cell-score="{ item }">
        <span
          :class="['score-badge', getScoreClass(item.score)]"
          role="status"
          :aria-label="`Score: ${item.score}%`"
        >
          {{ item.score }}%
        </span>
      </template>

      <!-- Comprehension level (admin only) -->
      <template #cell-comprehension="{ item }">
        <span
          :class="['comprehension-badge', getComprehensionClass(item.comprehension_level)]"
        >
          {{ formatComprehensionLevel(item.comprehension_level) }}
        </span>
      </template>

      <!-- Status badge -->
      <template #cell-status="{ item }">
        <span
          :class="['status-badge', getStatusClass(item.status)]"
          role="status"
          :aria-label="`Status: ${formatStatus(item.status)}`"
        >
          {{ formatStatus(item.status) }}
        </span>
      </template>

      <!-- Submission type badge (instructors + admins) -->
      <template #cell-type="{ item }">
        <span class="type-badge">{{ formatSubmissionType(item.submission_type) }}</span>
      </template>

      <!-- Actions (admin: View + Download, instructor: View only) -->
      <template #cell-actions="{ item }">
        <div class="actions-cell">
          <button
            class="action-button view-button"
            :title="$t('admin.submissions.viewDetails')"
            @click="viewSubmission(item.id)"
          >
            {{ $t('admin.submissions.view') }}
          </button>
          <button
            v-if="ctx.isAdmin.value"
            class="action-button download-button"
            :title="$t('admin.submissions.downloadData')"
            @click="downloadSubmissionData(item)"
          >
            {{ $t('admin.submissions.download') }}
          </button>
        </div>
      </template>
    </DataTable>

    <!-- View Submission Modal (admin + instructor) -->
    <ViewSubmissionModal
      :is-visible="showViewModal"
      :submission="selectedSubmission"
      @close="closeViewModal"
      @download="downloadSubmissionData"
    />
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import DataTable from '@/components/ui/DataTable.vue';
import ViewSubmissionModal from '@/modals/ViewSubmissionModal.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { useSubmissions } from '@/composables/useSubmissions';
import type { DataTableColumn } from '@/types/datatable';
import type { SubmissionSummary } from '@/services/contentService';

const { t } = useI18n();

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

// Column definitions — built dynamically based on admin/instructor role and filters
const columns = computed<DataTableColumn<SubmissionSummary>[]>(() => {
  const cols: DataTableColumn<SubmissionSummary>[] = [
    { key: 'user', label: t('admin.submissions.columnStudent'), slot: 'cell-student' },
    { key: 'problem', label: t('admin.submissions.columnProblem') },
    { key: 'problem_set', label: t('admin.submissions.columnProblemSet'), hideOnMobile: true, slot: 'cell-problem-set' },
  ];

  // Admin: Show course column when not filtered to single course
  if (ctx.isAdmin.value && !isCourseScoped.value && !courseFilter.value) {
    cols.push({ key: 'course', label: t('admin.submissions.columnCourse'), hideOnMobile: true, slot: 'cell-course' });
  }

  // Submission type column (instructor + admin)
  if (ctx.isInstructor.value || ctx.isAdmin.value) {
    cols.push({ key: 'submission_type', label: t('admin.submissions.columnType'), align: 'center', hideOnMobile: true, width: '110px', slot: 'cell-type' });
  }

  cols.push({ key: 'score', label: t('admin.submissions.columnScore'), align: 'center', width: '100px', slot: 'cell-score' });

  // Admin: comprehension column
  if (ctx.isAdmin.value) {
    cols.push({ key: 'comprehension_level', label: t('admin.submissions.columnComprehension'), align: 'center', hideOnMobile: true, slot: 'cell-comprehension' });
  }

  cols.push(
    { key: 'status', label: t('admin.submissions.columnStatus'), align: 'center', width: '110px', slot: 'cell-status' },
    {
      key: 'submitted_at',
      label: t('admin.submissions.columnSubmitted'),
      hideOnMobile: true,
      render: (value) => formatDate(value as string),
    },
  );

  // Actions column (admin + instructor)
  if (ctx.isAdmin.value || ctx.isInstructor.value) {
    cols.push({
      key: 'actions',
      label: t('admin.submissions.columnActions'),
      align: 'center',
      slot: 'cell-actions',
      width: ctx.isAdmin.value ? '160px' : '80px',
    });
  }

  return cols;
});

// Helper for submission type display
function formatSubmissionType(type: string): string {
  const typeMap: Record<string, string> = {
    eipl: 'EiPL',
    mcq: 'MCQ',
    prompt: 'Prompt',
    refute: 'Refute',
    debug_fix: 'Debug Fix',
    probeable_code: 'Probeable',
    probeable_spec: 'Probe Spec',
    direct_code: 'Code',
    function_redef: 'Func Redef',
  };
  return typeMap[type] || type;
}

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
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
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
  gap: var(--spacing-sm);
  height: 38px;
}

.clear-filters-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  background: transparent;
  border: 1px solid var(--color-bg-input);
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
  background: var(--color-primary-overlay);
  border: 1px solid var(--color-primary-gradient-start);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-xs);
  color: var(--color-primary-gradient-start);
  cursor: pointer;
  transition: var(--transition-base);
}

.filter-chip:hover {
  background: var(--color-primary-overlay);
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
  color: var(--color-text-on-filled);
  font-size: 10px;
  font-weight: bold;
  line-height: 1;
}

/* Results summary */
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

/* Cell styles */
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
  color: var(--color-text-on-filled);
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

/* Type badge */
.type-badge {
  display: inline-block;
  padding: 2px var(--spacing-xs);
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
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
  color: var(--color-text-on-filled);
  box-shadow: var(--shadow-colored);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
}

.export-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--color-primary-glow);
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
  color: var(--color-text-on-filled);
}

.download-button {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.download-button:hover {
  background: var(--color-success);
  color: var(--color-text-on-filled);
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
}
</style>
