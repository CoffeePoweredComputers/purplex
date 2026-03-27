<template>
  <ContentEditorLayout
    :page-title="pageTitle"
    :back-path="ctx.paths.courses.value"
    :back-label="ctx.isInstructor.value ? $t('admin.contentLayout.backToMyCourses') : $t('admin.contentLayout.backToCourses')"
    :show-breadcrumb="true"
  >
    <template #header-actions>
      <router-link
        :to="ctx.paths.editCourse(courseId)"
        class="action-button secondary-button"
      >
        {{ $t('admin.courses.editCourse') }}
      </router-link>
    </template>

    <!-- Summary Bar -->
    <div class="summary-bar">
      <p class="summary-text">
        {{ $t('admin.courseStudents.studentsEnrolled', { count: totalCount }) }}
      </p>
    </div>

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
      :item-label="$t('admin.courseStudents.itemLabel')"
      row-key="id"
      :empty-title="$t('admin.courseStudents.noStudents')"
      :empty-message="$t('admin.courseStudents.noStudentsMessage')"
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
              :placeholder="$t('admin.courseStudents.searchPlaceholder')"
              class="search-input"
              @input="debouncedSearch"
            >
          </div>
        </div>
      </template>

      <!-- Email with monospace -->
      <template #cell-email="{ item }">
        <span class="email">{{ item.user.email }}</span>
      </template>

      <!-- Progress bar -->
      <template #cell-progress="{ item }">
        <div class="progress-info">
          <div class="progress-bar-mini">
            <div
              class="progress-fill"
              :style="{ width: item.progress.completion_percentage + '%' }"
            />
          </div>
          <span class="progress-text">
            {{ item.progress.completed_problem_sets }} / {{ item.progress.total_problem_sets }}
          </span>
        </div>
      </template>

      <!-- Remove action -->
      <template #cell-actions="{ item }">
        <button
          class="action-button remove-button"
          :title="$t('admin.courseStudents.removeFromCourse')"
          @click="confirmRemove(item)"
        >
          {{ $t('common.remove') }}
        </button>
      </template>
    </DataTable>

    <!-- Remove Confirmation Dialog -->
    <ConfirmDialog
      :visible="showRemoveDialog"
      :title="$t('admin.courseStudents.removeStudent')"
      :message="$t('admin.courseStudents.removeConfirmMessage', { name: removeTarget ? getStudentName(removeTarget.user) : '' })"
      :confirm-label="$t('common.remove')"
      :loading="removing"
      @confirm="performRemove"
      @cancel="showRemoveDialog = false"
    />
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import DataTable from '@/components/ui/DataTable.vue';
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { useDataTable } from '@/composables/useDataTable';
import { clientSidePaginate } from '@/utils/clientSidePaginate';
import { log } from '@/utils/logger';
import type { Course, CourseStudent } from '@/types';
import type { DataTableColumn } from '@/types/datatable';

const { t } = useI18n();
const route = useRoute();
const ctx = provideContentContext();

// Course info (fetched separately from table data)
const course = ref<Course | null>(null);

const courseId = computed(() => route.params.courseId as string);
const pageTitle = computed(() => {
  if (course.value) {return t('admin.courseStudents.studentsDash', { name: course.value.name });}
  return t('admin.courseStudents.title');
});

// Cached data for client-side pagination
let allStudents: CourseStudent[] = [];
let needsRefetch = true;

const {
  items, loading, error, currentPage, pageSize, totalCount,
  totalPages, hasNext, hasPrevious, rangeStart, rangeEnd,
  pageNumbers, searchQuery, debouncedSearch, goToPage,
  handlePageSizeChange, fetch: fetchTable, refresh,
} = useDataTable<CourseStudent>({
  fetchFn: async (params) => {
    if (needsRefetch) {
      // Fetch course info + students in parallel
      const [courseData, students] = await Promise.all([
        ctx.api.value.getCourse(courseId.value),
        ctx.api.value.getCourseStudents(courseId.value),
      ]);
      course.value = courseData;
      allStudents = students;
      needsRefetch = false;
    }
    return clientSidePaginate(allStudents, params, {
      searchFn: (item, q) => {
        const lower = q.toLowerCase();
        const name = getStudentName(item.user).toLowerCase();
        return name.includes(lower) || item.user.email.toLowerCase().includes(lower);
      },
    });
  },
  initialPageSize: 25,
});

// Helpers
function getStudentName(user: CourseStudent['user']): string {
  if (user.first_name || user.last_name) {
    return `${user.first_name || ''} ${user.last_name || ''}`.trim();
  }
  return user.username;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// Column definitions
const columns = computed<DataTableColumn<CourseStudent>[]>(() => [
  {
    key: 'user',
    label: t('admin.courseStudents.columnName'),
    render: (_value, row) => getStudentName(row.user),
  },
  { key: 'user.email', label: t('admin.courseStudents.columnEmail'), hideOnMobile: true, slot: 'cell-email' },
  {
    key: 'enrolled_at',
    label: t('admin.courseStudents.columnEnrolled'),
    hideOnMobile: true,
    render: (value) => formatDate(value as string),
  },
  { key: 'progress', label: t('admin.courseStudents.columnProgress'), slot: 'cell-progress', width: '200px' },
  { key: 'actions', label: t('admin.courseStudents.columnActions'), slot: 'cell-actions', width: '100px' },
]);

// Remove dialog state
const showRemoveDialog = ref(false);
const removeTarget = ref<CourseStudent | null>(null);
const removing = ref(false);

function confirmRemove(student: CourseStudent): void {
  removeTarget.value = student;
  showRemoveDialog.value = true;
}

async function performRemove(): Promise<void> {
  if (!removeTarget.value) {return;}

  removing.value = true;
  try {
    await ctx.api.value.removeCourseStudent(courseId.value, removeTarget.value.user.id);
    allStudents = allStudents.filter(s => s.id !== removeTarget.value!.id);
    showRemoveDialog.value = false;
    removeTarget.value = null;
    await fetchTable();
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || t('admin.courseStudents.failedToRemove');
    log.error('Failed to remove student', { error: err });
  } finally {
    removing.value = false;
  }
}

// Watch for route changes — refetch when courseId changes
watch(
  () => route.params.courseId,
  () => {
    if (route.params.courseId) {
      needsRefetch = true;
      refresh();
    }
  },
  { immediate: true }
);
</script>

<style scoped>
/* Summary Bar */
.summary-bar {
  background-color: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg) var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  border: 2px solid var(--color-bg-input);
}

.summary-text {
  margin: 0;
  color: var(--color-text-secondary);
}

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

.email {
  font-family: monospace;
  font-size: var(--font-size-sm);
}

/* Progress */
.progress-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.progress-bar-mini {
  flex: 1;
  height: 6px;
  background-color: var(--color-bg-input);
  border-radius: var(--radius-xs);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-success) 0%, #0e9f6e 100%);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  white-space: nowrap;
}

/* Action Buttons */
.action-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-base);
  text-decoration: none;
}

.secondary-button {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.secondary-button:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.remove-button {
  background-color: transparent;
  border: 1px solid var(--color-bg-border);
  color: var(--color-text-muted);
  padding: var(--spacing-xs) var(--spacing-md);
}

.remove-button:hover {
  color: var(--color-error);
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

@media (max-width: 768px) {
  .progress-info {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
  }

  .progress-bar-mini {
    width: 100%;
  }
}
</style>
