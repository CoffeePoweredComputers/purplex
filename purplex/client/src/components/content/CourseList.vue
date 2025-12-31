<template>
  <ContentEditorLayout
    :page-title="ctx.getPageTitle('Courses').value"
    :back-path="ctx.basePath.value"
    :back-label="ctx.isInstructor.value ? 'Back to Dashboard' : 'Back to Admin'"
    :show-breadcrumb="false"
  >
    <template #header-actions>
      <router-link :to="ctx.paths.newCourse.value" class="action-button add-button">
        Create Course
      </router-link>
    </template>

    <!-- Status Messages -->
    <div class="status-container">
      <div v-if="loading" class="loading-indicator">
        Loading courses...
      </div>
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>

    <!-- Courses Table -->
    <div v-if="!loading && !error" class="table-responsive">
      <table class="courses-table">
        <thead>
          <tr>
            <th>Course ID</th>
            <th>Name</th>
            <th v-if="ctx.isAdmin.value">Instructor</th>
            <th class="center">Problem Sets</th>
            <th class="center">Students</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="course in courses" :key="course.id">
            <td class="course-id">{{ course.course_id }}</td>
            <td>{{ course.name }}</td>
            <td v-if="ctx.isAdmin.value">{{ course.instructor_name || 'Not assigned' }}</td>
            <td class="center">{{ course.problem_sets_count || 0 }}</td>
            <td class="center">{{ course.enrolled_students_count || 0 }}</td>
            <td>
              <span :class="['status-badge', course.is_active ? 'active' : 'inactive']">
                {{ course.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td class="actions-cell">
              <router-link
                :to="ctx.paths.editCourse(course.course_id)"
                class="action-button icon-button"
                title="Edit Course"
              >
                <span class="icon">&#x270E;</span>
              </router-link>
              <router-link
                :to="ctx.paths.courseProblemSets(course.course_id)"
                class="action-button icon-button"
                title="Manage Problem Sets"
              >
                <span class="icon">&#x1F4DA;</span>
              </router-link>
              <router-link
                :to="ctx.paths.courseStudents(course.course_id)"
                class="action-button icon-button"
                title="View Students"
              >
                <span class="icon">&#x1F465;</span>
              </router-link>
              <button
                class="action-button icon-button delete"
                title="Delete Course"
                @click="confirmDelete(course)"
              >
                <span class="icon">&#x1F5D1;</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="courses.length === 0" class="empty-state">
        <div class="empty-icon">&#x1F393;</div>
        <h3>No Courses Yet</h3>
        <p>
          {{ ctx.isInstructor.value
            ? "You haven't created any courses yet. Create your first one!"
            : "No courses found. Create your first one!"
          }}
        </p>
        <router-link :to="ctx.paths.newCourse.value" class="action-button add-button">
          Create Course
        </router-link>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <div v-if="showDeleteDialog" class="dialog-overlay">
      <div class="dialog">
        <h3>Delete Course?</h3>
        <p>
          Are you sure you want to delete "{{ deleteTarget?.name }}"?
          This action cannot be undone.
        </p>
        <div class="dialog-actions">
          <button class="btn btn-secondary" @click="showDeleteDialog = false">
            Cancel
          </button>
          <button class="btn btn-danger" :disabled="deleting" @click="performDelete">
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import ContentEditorLayout from './ContentEditorLayout.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { log } from '@/utils/logger';
import type { Course } from '@/types';

// Provide role-aware context (page-level components must provide, not inject)
const ctx = provideContentContext();

// State
const courses = ref<Course[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const deleting = ref(false);

// Delete dialog state
const showDeleteDialog = ref(false);
const deleteTarget = ref<Course | null>(null);

// Fetch courses
async function fetchCourses(): Promise<void> {
  try {
    loading.value = true;
    error.value = null;
    courses.value = await ctx.api.value.getCourses();
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || 'Failed to load courses';
    log.error('Failed to fetch courses', { error: err });
  } finally {
    loading.value = false;
  }
}

// Delete handlers
function confirmDelete(course: Course): void {
  deleteTarget.value = course;
  showDeleteDialog.value = true;
}

async function performDelete(): Promise<void> {
  if (!deleteTarget.value) return;

  deleting.value = true;
  try {
    await ctx.api.value.deleteCourse(deleteTarget.value.course_id);
    courses.value = courses.value.filter(c => c.course_id !== deleteTarget.value!.course_id);
    showDeleteDialog.value = false;
    deleteTarget.value = null;
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || 'Failed to delete course';
    log.error('Error deleting course', { error: err });
  } finally {
    deleting.value = false;
  }
}

// Load on mount
onMounted(fetchCourses);
</script>

<style scoped>
/* Status messages */
.status-container {
  margin-bottom: var(--spacing-xl);
}

.loading-indicator {
  padding: var(--spacing-xl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
  text-align: center;
  box-shadow: var(--shadow-md);
}

.error-message {
  padding: var(--spacing-xl);
  background: var(--color-error-bg);
  border-radius: var(--radius-lg);
  color: var(--color-error-text);
  text-align: center;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-error);
}

/* Table */
.table-responsive {
  overflow-x: auto;
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 2px solid transparent;
  transition: var(--transition-base);
}

.table-responsive:hover {
  border-color: var(--color-bg-input);
}

.courses-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.courses-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-lg) var(--spacing-xl);
  font-weight: 600;
  font-size: var(--font-size-base);
  border-bottom: 2px solid var(--color-bg-input);
}

.courses-table th.center {
  text-align: center;
}

.courses-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.courses-table td.center {
  text-align: center;
}

.courses-table tr:hover {
  background: var(--color-bg-hover);
}

.courses-table tr:last-child td {
  border-bottom: none;
}

.course-id {
  font-family: monospace;
  font-weight: 500;
  color: var(--color-primary-gradient-start);
}

/* Status badge */
.status-badge {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-weight: 600;
  font-size: var(--font-size-xs);
  display: inline-block;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.active {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.status-badge.inactive {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

/* Actions */
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
}

.add-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.add-button::before {
  content: "+";
  font-size: 18px;
  font-weight: bold;
}

.icon-button {
  width: 36px;
  height: 36px;
  padding: 0;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
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

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--spacing-xxl);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: var(--spacing-lg);
}

.empty-state h3 {
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.empty-state p {
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-xl);
}

/* Delete Dialog */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  max-width: 400px;
  width: 90%;
  box-shadow: var(--shadow-lg);
}

.dialog h3 {
  margin: 0 0 var(--spacing-lg) 0;
  color: var(--color-text-primary);
}

.dialog p {
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-lg);
}

.dialog-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  margin-top: var(--spacing-lg);
}

/* Buttons */
.btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: var(--transition-base);
}

.btn-secondary {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.btn-danger {
  background: var(--color-error);
  color: var(--color-text-primary);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 768px) {
  .courses-table {
    font-size: var(--font-size-sm);
  }

  .courses-table th,
  .courses-table td {
    padding: var(--spacing-md);
  }

  .actions-cell {
    flex-wrap: wrap;
  }
}
</style>
