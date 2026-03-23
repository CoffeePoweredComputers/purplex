<template>
  <ContentEditorLayout
    :page-title="ctx.getPageTitle('Courses').value"
    :back-path="ctx.basePath.value"
    :back-label="ctx.isInstructor.value ? $t('admin.contentLayout.backToDashboard') : $t('admin.contentLayout.backToAdmin')"
    :show-breadcrumb="false"
  >
    <template #header-actions>
      <router-link :to="ctx.paths.newCourse.value" class="action-button add-button">
        {{ $t('admin.courses.createCourse') }}
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
      :item-label="$t('admin.courses.itemLabel')"
      row-key="id"
      :empty-title="$t('admin.courses.noCourses')"
      :empty-message="ctx.isInstructor.value
        ? $t('admin.courses.emptyInstructor')
        : $t('admin.courses.emptyAdmin')"
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
              :placeholder="$t('admin.courses.searchPlaceholder')"
              class="search-input"
              @input="debouncedSearch"
            >
          </div>
        </div>
      </template>

      <!-- Course ID with monospace styling -->
      <template #cell-course-id="{ value }">
        <span class="course-id">{{ value }}</span>
      </template>

      <!-- Status badge -->
      <template #cell-status="{ item }">
        <StatusBadge
          :value="item.is_active ? $t('common.active') : $t('common.inactive')"
          :variant="item.is_active ? 'success' : 'error'"
        />
      </template>

      <!-- Actions (icon buttons) -->
      <template #cell-actions="{ item }">
        <div class="actions-cell">
          <router-link
            :to="ctx.paths.editCourse(item.course_id)"
            class="icon-button"
            :title="$t('admin.courses.editCourse')"
          >
            <span class="icon">&#x270E;</span>
          </router-link>
          <router-link
            :to="ctx.paths.courseProblemSets(item.course_id)"
            class="icon-button"
            :title="$t('admin.courses.manageProblemSets')"
          >
            <span class="icon">&#x1F4DA;</span>
          </router-link>
          <router-link
            :to="ctx.paths.courseStudents(item.course_id)"
            class="icon-button"
            :title="$t('admin.courses.viewStudents')"
          >
            <span class="icon">&#x1F465;</span>
          </router-link>
          <button
            class="icon-button delete"
            :title="$t('admin.courses.deleteCourse')"
            @click="confirmDelete(item)"
          >
            <span class="icon">&#x1F5D1;</span>
          </button>
        </div>
      </template>

      <!-- Empty state action -->
      <template #empty-actions>
        <router-link :to="ctx.paths.newCourse.value" class="action-button add-button">
          {{ $t('admin.courses.createCourse') }}
        </router-link>
      </template>
    </DataTable>

    <!-- Delete Confirmation Dialog -->
    <ConfirmDialog
      :visible="showDeleteDialog"
      :title="$t('admin.courses.deleteConfirm')"
      :message="$t('admin.courses.deleteConfirmMessage', { name: deleteTarget?.name })"
      :confirm-label="$t('common.delete')"
      :loading="deleting"
      @confirm="performDelete"
      @cancel="showDeleteDialog = false"
    />
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import ContentEditorLayout from './ContentEditorLayout.vue';
import DataTable from '@/components/ui/DataTable.vue';
import StatusBadge from '@/components/ui/StatusBadge.vue';
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { useDataTable } from '@/composables/useDataTable';
import { clientSidePaginate } from '@/utils/clientSidePaginate';
import { log } from '@/utils/logger';
import type { Course } from '@/types';
import type { DataTableColumn } from '@/types/datatable';

const { t } = useI18n();
const ctx = provideContentContext();

// Cached data for client-side pagination
let allCourses: Course[] = [];
let needsRefetch = true;

const {
  items, loading, error, currentPage, pageSize, totalCount,
  totalPages, hasNext, hasPrevious, rangeStart, rangeEnd,
  pageNumbers, searchQuery, debouncedSearch, goToPage,
  handlePageSizeChange, fetch: fetchTable, refresh,
} = useDataTable<Course>({
  fetchFn: async (params) => {
    if (needsRefetch) {
      allCourses = await ctx.api.value.getCourses();
      needsRefetch = false;
    }
    return clientSidePaginate(allCourses, params, {
      searchFn: (item, q) => {
        const lower = q.toLowerCase();
        return item.name.toLowerCase().includes(lower)
          || item.course_id.toLowerCase().includes(lower);
      },
    });
  },
  initialPageSize: 25,
});

// Column definitions — conditionally include Instructor for admins
const columns = computed<DataTableColumn<Course>[]>(() => {
  const cols: DataTableColumn<Course>[] = [
    { key: 'course_id', label: t('admin.courses.columnCourseId'), slot: 'cell-course-id', width: '120px' },
    { key: 'name', label: t('admin.courses.columnName') },
  ];

  if (ctx.isAdmin.value) {
    cols.push({
      key: 'instructor_name',
      label: t('admin.courses.columnInstructor'),
      hideOnMobile: true,
      render: (value) => (value as string) || t('admin.courses.notAssigned'),
    });
  }

  cols.push(
    { key: 'problem_sets_count', label: t('admin.courses.columnProblemSets'), align: 'center', width: '120px',
      render: (value) => String(value ?? 0) },
    { key: 'enrolled_students_count', label: t('admin.courses.columnStudents'), align: 'center', width: '100px',
      render: (value) => String(value ?? 0) },
    { key: 'is_active', label: t('admin.courses.columnStatus'), align: 'center', width: '110px', slot: 'cell-status' },
    { key: 'actions', label: t('admin.courses.columnActions'), slot: 'cell-actions', width: '170px' },
  );

  return cols;
});

// Delete dialog state
const showDeleteDialog = ref(false);
const deleteTarget = ref<Course | null>(null);
const deleting = ref(false);

function confirmDelete(course: Course): void {
  deleteTarget.value = course;
  showDeleteDialog.value = true;
}

async function performDelete(): Promise<void> {
  if (!deleteTarget.value) return;

  deleting.value = true;
  try {
    await ctx.api.value.deleteCourse(deleteTarget.value.course_id);
    allCourses = allCourses.filter(c => c.course_id !== deleteTarget.value!.course_id);
    showDeleteDialog.value = false;
    deleteTarget.value = null;
    await fetchTable();
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || t('admin.courseEditor.failedToDeleteCourse');
    log.error('Error deleting course', { error: err });
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

.course-id {
  font-family: monospace;
  font-weight: 500;
  color: var(--color-primary-gradient-start);
}

.actions-cell {
  display: flex;
  gap: var(--spacing-sm);
}

.action-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
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
  color: var(--color-text-on-filled);
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

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-base);
  text-decoration: none;
  color: var(--color-text-primary);
}

.icon-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-input);
}

.icon-button.delete:hover {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.icon {
  font-size: 16px;
  line-height: 1;
}

@media (max-width: 768px) {
  .actions-cell {
    flex-wrap: wrap;
  }
}
</style>
