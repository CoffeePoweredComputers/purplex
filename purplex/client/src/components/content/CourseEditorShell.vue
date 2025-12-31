<template>
  <ContentEditorLayout
    :back-path="ctx.paths.courses.value"
    :back-label="ctx.isInstructor.value ? 'Back to My Courses' : 'Back to Courses'"
    :show-header="false"
  >
    <div class="header rounded-lg border-default">
      <h2>{{ isEditing ? 'Edit Course' : 'Create New Course' }}</h2>
      <div class="actions">
        <button
          v-if="isEditing"
          class="btn btn-danger"
          @click="showDeleteDialog = true"
        >
          Delete
        </button>
        <button
          :disabled="saving || !canSave"
          class="btn btn-primary rounded-base"
          @click="handleSave"
        >
          {{ saving ? 'Saving...' : (isEditing ? 'Update Course' : 'Create Course') }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner" />
      <p>Loading course...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="loadError" class="error-container">
      <p class="error-message">{{ loadError }}</p>
      <router-link :to="ctx.paths.courses.value" class="btn btn-secondary">
        Back to Courses
      </router-link>
    </div>

    <!-- Course Form -->
    <form v-else class="course-form" @submit.prevent="handleSave">
      <div class="form-section rounded-lg border-default">
        <h3>Course Details</h3>

        <div class="form-group">
          <label for="course_id">Course ID *</label>
          <input
            id="course_id"
            v-model="formData.course_id"
            type="text"
            placeholder="e.g., CS101-FALL2024"
            :disabled="isEditing"
            required
          >
          <small>Unique identifier for the course{{ isEditing ? ' (cannot be changed)' : '' }}</small>
        </div>

        <div class="form-group">
          <label for="name">Course Name *</label>
          <input
            id="name"
            v-model="formData.name"
            type="text"
            placeholder="e.g., Introduction to Computer Science"
            required
          >
        </div>

        <div class="form-group">
          <label for="description">Description</label>
          <textarea
            id="description"
            v-model="formData.description"
            rows="4"
            placeholder="Brief description of the course..."
          />
        </div>

        <!-- Instructor selection (admin only) -->
        <div v-if="ctx.isAdmin.value" class="form-group">
          <label for="instructor">Instructor *</label>
          <select
            id="instructor"
            v-model="formData.instructor_id"
            required
          >
            <option :value="null" disabled>Select an instructor...</option>
            <option
              v-for="instructor in instructors"
              :key="instructor.id"
              :value="instructor.id"
            >
              {{ instructor.full_name }} ({{ instructor.username }})
            </option>
          </select>
          <small>Select the primary instructor for this course</small>
        </div>
      </div>

      <div class="form-section rounded-lg border-default">
        <h3>Course Settings</h3>

        <div class="checkbox-group">
          <label class="checkbox-label">
            <input v-model="formData.is_active" type="checkbox">
            <span>Course is active</span>
          </label>
          <small>Active courses are visible to enrolled students</small>
        </div>

        <div class="checkbox-group">
          <label class="checkbox-label">
            <input v-model="formData.enrollment_open" type="checkbox">
            <span>Enrollment is open</span>
          </label>
          <small>Allow new students to enroll in this course</small>
        </div>
      </div>
    </form>

    <!-- Delete Confirmation Dialog -->
    <div v-if="showDeleteDialog" class="dialog-overlay">
      <div class="dialog">
        <h3>Delete Course?</h3>
        <p>
          Are you sure you want to delete "{{ formData.name }}"?
          This action cannot be undone.
        </p>
        <div class="dialog-actions">
          <button class="btn btn-secondary" @click="showDeleteDialog = false">
            Cancel
          </button>
          <button class="btn btn-danger" :disabled="deleting" @click="handleDelete">
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { log } from '@/utils/logger';
import type { Instructor } from '@/types';

// Router
const route = useRoute();
const router = useRouter();

// Provide role-aware context
const ctx = provideContentContext();

// State
const loading = ref(false);
const loadError = ref<string | null>(null);
const saving = ref(false);
const deleting = ref(false);
const showDeleteDialog = ref(false);
const instructors = ref<Instructor[]>([]);

// Form data
const formData = reactive({
  course_id: '',
  name: '',
  description: '',
  instructor_id: null as number | null,
  is_active: true,
  enrollment_open: true,
});

// Computed
const courseIdFromRoute = computed(() => route.params.courseId as string | undefined);
const isEditing = computed(() => !!courseIdFromRoute.value);
const canSave = computed(() => {
  const hasId = formData.course_id.trim().length > 0;
  const hasName = formData.name.trim().length > 0;
  const hasInstructor = ctx.isInstructor.value || formData.instructor_id !== null;
  return hasId && hasName && hasInstructor;
});

// Reset form
function resetForm(): void {
  formData.course_id = '';
  formData.name = '';
  formData.description = '';
  formData.instructor_id = null;
  formData.is_active = true;
  formData.enrollment_open = true;
}

// Load course data
async function loadCourse(courseId: string): Promise<void> {
  loading.value = true;
  loadError.value = null;

  try {
    const course = await ctx.api.value.getCourse(courseId);
    formData.course_id = course.course_id;
    formData.name = course.name;
    formData.description = course.description || '';
    formData.instructor_id = course.instructor_id;
    formData.is_active = course.is_active;
    formData.enrollment_open = course.enrollment_open;
  } catch (err) {
    const apiError = err as { error?: string };
    loadError.value = apiError.error || `Failed to load course: ${courseId}`;
    log.error('Failed to load course', { courseId, error: err });
  } finally {
    loading.value = false;
  }
}

// Load instructors (admin only)
async function loadInstructors(): Promise<void> {
  if (!ctx.isAdmin.value) return;

  try {
    instructors.value = await ctx.api.value.getInstructors();
  } catch (err) {
    log.error('Failed to load instructors', { error: err });
  }
}

// Save handler
async function handleSave(): Promise<void> {
  if (!canSave.value) return;

  saving.value = true;
  try {
    const payload = { ...formData };

    if (isEditing.value) {
      await ctx.api.value.updateCourse(courseIdFromRoute.value!, payload);
    } else {
      await ctx.api.value.createCourse(payload);
    }

    // Navigate back to list
    router.push(ctx.paths.courses.value);
  } catch (err) {
    const apiError = err as { error?: string };
    loadError.value = apiError.error || 'Failed to save course';
    log.error('Failed to save course', { error: err });
  } finally {
    saving.value = false;
  }
}

// Delete handler
async function handleDelete(): Promise<void> {
  if (!courseIdFromRoute.value) return;

  deleting.value = true;
  try {
    await ctx.api.value.deleteCourse(courseIdFromRoute.value);
    showDeleteDialog.value = false;
    router.push(ctx.paths.courses.value);
  } catch (err) {
    const apiError = err as { error?: string };
    loadError.value = apiError.error || 'Failed to delete course';
    log.error('Failed to delete course', { error: err });
  } finally {
    deleting.value = false;
  }
}

// Watch for route changes
watch(
  () => route.params.courseId,
  (newId) => {
    if (newId) {
      loadCourse(newId as string);
    } else {
      resetForm();
    }
  },
  { immediate: true }
);

// Load instructors on mount
onMounted(loadInstructors);
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg) var(--spacing-xl);
  background: var(--color-bg-panel);
  margin-bottom: var(--spacing-xl);
}

.header h2 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
}

.actions {
  display: flex;
  gap: var(--spacing-md);
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
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
}

.error-message {
  color: var(--color-error);
  margin-bottom: var(--spacing-lg);
}

/* Form */
.course-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.form-section {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
}

.form-section h3 {
  margin: 0 0 var(--spacing-lg) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  border-bottom: 1px solid var(--color-bg-border);
  padding-bottom: var(--spacing-md);
}

.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.form-group input[type="text"],
.form-group textarea,
.form-group select {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  transition: var(--transition-fast);
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input:disabled {
  background-color: var(--color-bg-disabled);
  cursor: not-allowed;
  opacity: 0.7;
}

.form-group small {
  display: block;
  margin-top: var(--spacing-xs);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

/* Checkbox group */
.checkbox-group {
  margin-bottom: var(--spacing-lg);
}

.checkbox-group:last-child {
  margin-bottom: 0;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-group small {
  display: block;
  margin-top: var(--spacing-xs);
  margin-left: calc(18px + var(--spacing-sm));
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

/* Buttons */
.btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: var(--transition-base);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-colored);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.btn-secondary:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.btn-danger {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.btn-danger:hover:not(:disabled) {
  background: var(--color-error);
  color: var(--color-text-primary);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
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

/* Utility classes */
.rounded-lg {
  border-radius: var(--radius-lg);
}

.border-default {
  border: 2px solid var(--color-bg-input);
}

/* Responsive */
@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: var(--spacing-lg);
    text-align: center;
  }

  .actions {
    width: 100%;
    justify-content: center;
  }
}
</style>
