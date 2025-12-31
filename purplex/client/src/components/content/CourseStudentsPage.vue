<template>
  <ContentEditorLayout
    :page-title="pageTitle"
    :back-path="ctx.paths.courses.value"
    :back-label="ctx.isInstructor.value ? 'Back to My Courses' : 'Back to Courses'"
    :show-breadcrumb="true"
  >
    <template #header-actions>
      <router-link :to="ctx.paths.editCourse(courseId)" class="action-button secondary-button">
        Edit Course
      </router-link>
    </template>

    <!-- Summary Bar -->
    <div class="summary-bar">
      <p class="summary-text">
        <strong>{{ students.length }}</strong> students enrolled
      </p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner" />
      <p>Loading students...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <p class="error-message">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="students.length === 0" class="empty-state">
      <div class="empty-icon">&#x1F465;</div>
      <h3>No Students Enrolled</h3>
      <p>No students have enrolled in this course yet.</p>
    </div>

    <!-- Students Table -->
    <div v-else class="table-responsive">
      <table class="students-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Enrolled Date</th>
            <th>Progress</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="student in students" :key="student.id">
            <td>{{ getStudentName(student.user) }}</td>
            <td class="email">{{ student.user.email }}</td>
            <td>{{ formatDate(student.enrolled_at) }}</td>
            <td class="progress-cell">
              <div class="progress-info">
                <div class="progress-bar-mini">
                  <div
                    class="progress-fill"
                    :style="{ width: student.progress.completion_percentage + '%' }"
                  />
                </div>
                <span class="progress-text">
                  {{ student.progress.completed_problem_sets }} / {{ student.progress.total_problem_sets }}
                </span>
              </div>
            </td>
            <td>
              <button
                class="action-button remove-button"
                title="Remove from course"
                @click="confirmRemove(student)"
              >
                Remove
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Remove Confirmation Dialog -->
    <div v-if="showRemoveDialog" class="dialog-overlay">
      <div class="dialog">
        <h3>Remove Student?</h3>
        <p>
          Are you sure you want to remove "{{ removeTarget ? getStudentName(removeTarget.user) : '' }}" from this course?
        </p>
        <div class="dialog-actions">
          <button class="btn btn-secondary" @click="showRemoveDialog = false">
            Cancel
          </button>
          <button class="btn btn-danger" :disabled="removing" @click="performRemove">
            {{ removing ? 'Removing...' : 'Remove' }}
          </button>
        </div>
      </div>
    </div>
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { log } from '@/utils/logger';
import type { Course, CourseStudent } from '@/types';

// Router
const route = useRoute();

// Provide role-aware context
const ctx = provideContentContext();

// State
const course = ref<Course | null>(null);
const students = ref<CourseStudent[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const removing = ref(false);
const showRemoveDialog = ref(false);
const removeTarget = ref<CourseStudent | null>(null);

// Computed
const courseId = computed(() => route.params.courseId as string);
const pageTitle = computed(() => {
  if (course.value) {
    return `Students - ${course.value.name}`;
  }
  return 'Course Students';
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
    day: 'numeric'
  });
}

// Fetch course and students
async function fetchData(): Promise<void> {
  loading.value = true;
  error.value = null;

  try {
    // Fetch course info first
    course.value = await ctx.api.value.getCourse(courseId.value);
    // Then fetch students
    students.value = await ctx.api.value.getCourseStudents(courseId.value);
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || 'Failed to load students';
    log.error('Failed to load course students', { courseId: courseId.value, error: err });
  } finally {
    loading.value = false;
  }
}

// Remove handlers
function confirmRemove(student: CourseStudent): void {
  removeTarget.value = student;
  showRemoveDialog.value = true;
}

async function performRemove(): Promise<void> {
  if (!removeTarget.value) return;

  removing.value = true;
  try {
    await ctx.api.value.removeCourseStudent(courseId.value, removeTarget.value.id);
    students.value = students.value.filter(s => s.id !== removeTarget.value!.id);
    showRemoveDialog.value = false;
    removeTarget.value = null;
  } catch (err) {
    const apiError = err as { error?: string };
    error.value = apiError.error || 'Failed to remove student';
    log.error('Failed to remove student', { error: err });
  } finally {
    removing.value = false;
  }
}

// Watch for route changes
watch(
  () => route.params.courseId,
  () => {
    if (route.params.courseId) {
      fetchData();
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

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-bg-hover);
  border-top: 3px solid var(--color-primary-gradient-start);
  border-radius: var(--radius-circle);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error */
.error-container {
  padding: var(--spacing-xl);
  background: var(--color-error-bg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-error);
}

.error-message {
  color: var(--color-error-text);
  margin: 0;
  text-align: center;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
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

.students-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.students-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-lg) var(--spacing-xl);
  font-weight: 600;
  font-size: var(--font-size-sm);
  border-bottom: 2px solid var(--color-bg-input);
}

.students-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.students-table tr:hover {
  background: var(--color-bg-hover);
}

.students-table tr:last-child td {
  border-bottom: none;
}

.email {
  font-family: monospace;
  font-size: var(--font-size-sm);
}

/* Progress */
.progress-cell {
  width: 200px;
}

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

/* Dialog */
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
  .students-table th,
  .students-table td {
    padding: var(--spacing-md);
  }

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
