<template>
  <div class="instructor-dashboard">
    <InstructorNavBar />

    <div class="content-container">
      <!-- Loading State -->
      <div
        v-if="loading"
        class="loading-container"
      >
        <div class="loading-spinner" />
        <p>Loading your courses...</p>
      </div>

      <!-- Error State -->
      <div
        v-else-if="error"
        class="error-state"
        role="alert"
      >
        <div class="error-icon" aria-hidden="true">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <span class="visually-hidden">Error:</span>
        <h3>Unable to Load Courses</h3>
        <p>{{ error }}</p>
        <button
          class="retry-btn"
          aria-label="Retry loading courses"
          @click="fetchCourses"
        >
          Try Again
        </button>
      </div>

      <!-- Courses List -->
      <div
        v-else
        class="courses-list"
      >
        <router-link
          v-for="course in courses"
          :key="course.id"
          :to="`/instructor/courses/${course.course_id}`"
          :class="['course-card', course.is_active ? 'active' : 'inactive']"
          :aria-label="`Open ${course.name}`"
        >
          <div class="card-main">
            <h3 class="course-title">{{ course.name }}</h3>

            <div class="card-meta">
              <span class="course-code">{{ course.course_id }}</span>
              <span class="meta-separator" aria-hidden="true">·</span>
              <span
                :class="['status-indicator', course.is_active ? 'active' : 'inactive']"
                role="status"
              >
                {{ course.is_active ? 'Active' : 'Inactive' }}
              </span>
              <span class="meta-separator" aria-hidden="true">·</span>
              <span class="student-count">{{ course.enrolled_students_count }} students</span>
              <template v-if="course.my_role">
                <span class="meta-separator" aria-hidden="true">·</span>
                <span :class="['role-badge', `role-${course.my_role}`]">
                  {{ course.my_role === 'primary' ? 'Primary' : 'TA' }}
                </span>
              </template>
            </div>
          </div>

          <!-- Hover arrow that grows from right -->
          <div class="hover-arrow" aria-hidden="true">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <line x1="5" y1="12" x2="19" y2="12"/>
              <polyline points="12 5 19 12 12 19"/>
            </svg>
          </div>
        </router-link>

        <!-- Add Course / Create Form -->
        <div
          :class="[
            'course-card',
            'add-course-card',
            { 'form-expanded': isFormExpanded }
          ]"
        >
          <!-- Collapsed State: Plus Button -->
          <button
            v-if="!isFormExpanded"
            class="add-card-trigger"
            aria-label="Create a new course"
            @click="toggleForm"
          >
            <div class="add-card-content">
              <div class="add-icon" aria-hidden="true">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
              </div>
              <span class="add-text">Create Course</span>
            </div>
          </button>

          <!-- Expanded State: Creation Form -->
          <form
            v-else
            class="inline-course-form"
            @submit.prevent="handleCreateCourse"
          >
            <div class="form-header">
              <h3>Create New Course</h3>
              <button
                type="button"
                class="close-form-btn"
                aria-label="Cancel course creation"
                @click="toggleForm"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <div class="form-body">
              <div class="form-row">
                <div class="form-field">
                  <label for="new-course-name">Course Name *</label>
                  <input
                    id="new-course-name"
                    v-model="formData.name"
                    type="text"
                    placeholder="e.g., Introduction to Computer Science"
                    :disabled="isCreating"
                    required
                  >
                </div>
              </div>

              <div class="form-row">
                <div class="form-field">
                  <label for="new-course-id">Course ID *</label>
                  <input
                    id="new-course-id"
                    :value="formData.course_id"
                    type="text"
                    placeholder="e.g., CS101-FALL2024"
                    :disabled="isCreating"
                    required
                    @input="handleCourseIdInput"
                  >
                  <small>Unique identifier (no spaces, auto-uppercased)</small>
                </div>
              </div>

              <div class="form-row">
                <label class="toggle-label">
                  <input
                    v-model="formData.is_active"
                    type="checkbox"
                    class="toggle-checkbox"
                    :disabled="isCreating"
                  >
                  <span class="toggle-text">Active</span>
                  <span class="toggle-hint">
                    {{ formData.is_active ? 'Visible to students' : 'Hidden from students' }}
                  </span>
                </label>
              </div>

              <!-- Error message -->
              <div v-if="formError" class="form-error" role="alert">
                {{ formError }}
              </div>
            </div>

            <div class="form-actions">
              <button
                type="button"
                class="btn-cancel"
                :disabled="isCreating"
                @click="toggleForm"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="btn-create"
                :disabled="!isFormValid || isCreating"
              >
                {{ isCreating ? 'Creating...' : 'Create Course' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive, computed } from 'vue';
import axios from 'axios';
import InstructorNavBar from './InstructorNavBar.vue';
import { log } from '../../utils/logger';
import { instructorContentService } from '@/services/contentService';

interface Course {
  id: number;
  course_id: string;
  name: string;
  description?: string;
  is_active: boolean;
  problem_sets_count: number;
  enrolled_students_count: number;
  my_role?: 'primary' | 'ta';
}

const courses = ref<Course[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Course creation form state
const isFormExpanded = ref(false);
const formData = reactive({
  course_id: '',
  name: '',
  is_active: true,
});
const isCreating = ref(false);
const formError = ref<string | null>(null);

const isFormValid = computed(() => {
  return formData.course_id.trim().length > 0 && formData.name.trim().length > 0;
});

async function fetchCourses() {
  loading.value = true;
  error.value = null;

  try {
    // FERPA: This endpoint only returns courses for the authenticated instructor
    const response = await axios.get('/api/instructor/courses/');
    courses.value = response.data;
    log.info('Loaded instructor courses', { count: courses.value.length });
  } catch (err: unknown) {
    log.error('Failed to fetch instructor courses', err);
    if (axios.isAxiosError(err) && err.response?.status === 403) {
      error.value = 'You do not have permission to view instructor courses.';
    } else {
      error.value = 'Failed to load courses. Please try again.';
    }
  } finally {
    loading.value = false;
  }
}

function toggleForm(): void {
  isFormExpanded.value = !isFormExpanded.value;
  if (!isFormExpanded.value) {
    resetForm();
  }
}

function resetForm(): void {
  formData.course_id = '';
  formData.name = '';
  formData.is_active = true;
  formError.value = null;
}

async function handleCreateCourse(): Promise<void> {
  if (!isFormValid.value || isCreating.value) return;

  isCreating.value = true;
  formError.value = null;

  try {
    const newCourse = await instructorContentService.createCourse({
      course_id: formData.course_id.trim(),
      name: formData.name.trim(),
      description: '',
      is_active: formData.is_active,
      enrollment_open: true,
    });

    courses.value.push({
      ...newCourse,
      enrolled_students_count: newCourse.enrolled_students_count ?? 0,
      problem_sets_count: newCourse.problem_sets_count ?? 0,
    });

    log.info('Created course', { course_id: newCourse.course_id });

    isFormExpanded.value = false;
    resetForm();
  } catch (err) {
    const apiError = err as { error?: string };
    formError.value = apiError.error || 'Failed to create course';
    log.error('Failed to create course', err);
  } finally {
    isCreating.value = false;
  }
}

function handleCourseIdInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  formData.course_id = input.value.toUpperCase().replace(/\s+/g, '-');
}

onMounted(() => {
  fetchCourses();
});
</script>

<style scoped>
/* Visually hidden utility for screen readers (WCAG 1.1.1) */
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

.instructor-dashboard {
  min-height: 100vh;
  background: var(--color-background, var(--color-bg-main));
}

.content-container {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: 0 var(--spacing-xl);
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
  border: 4px solid var(--color-border, var(--color-bg-border));
  border-top-color: var(--color-primary);
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
}

.error-icon {
  color: var(--color-error);
  margin-bottom: var(--spacing-lg);
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
  background: var(--color-admin);
  color: white;
  border: none;
  border-radius: var(--radius-base);
  cursor: pointer;
  font-weight: 600;
  transition: var(--transition-base);
}

.retry-btn:hover {
  background: var(--color-admin-hover);
}

.retry-btn:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

/* Courses List */
.courses-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.course-card {
  position: relative;
  display: flex;
  align-items: stretch;
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border, var(--color-bg-border));
  border-radius: var(--radius-lg);
  transition: var(--transition-base);
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}

.course-card:hover,
.course-card:focus-visible {
  transform: translateY(-2px);
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.25);
}

.course-card:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

/* Hover arrow that grows from right */
.hover-arrow {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 0;
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  overflow: hidden;
  transition: width 0.25s ease;
}

.hover-arrow svg {
  opacity: 0;
  transition: opacity 0.15s ease 0.1s;
}

.course-card:hover .hover-arrow,
.course-card:focus-visible .hover-arrow {
  width: 56px;
}

.course-card:hover .hover-arrow svg,
.course-card:focus-visible .hover-arrow svg {
  opacity: 1;
}

.card-main {
  flex: 1;
  padding: var(--spacing-lg) var(--spacing-xl);
  min-width: 0;
}

.course-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Card Meta Line */
.card-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  flex-wrap: wrap;
}

.course-code {
  font-family: var(--font-mono, 'Monaco', 'Menlo', monospace);
  background: var(--color-bg-hover);
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-sm);
}

.meta-separator {
  color: var(--color-text-tertiary);
  opacity: 0.5;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-weight: 500;
}

.status-indicator.active {
  color: var(--color-success);
}

.status-indicator.inactive {
  color: var(--color-text-muted);
}

.status-indicator::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.student-count {
  color: var(--color-text-secondary);
}

.role-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.role-primary {
  background: rgba(102, 126, 234, 0.15);
  color: var(--color-primary-gradient-start);
}

.role-ta {
  background: rgba(76, 175, 80, 0.15);
  color: var(--color-success);
}

/* Add Course Card - Ghost/Shadow style */
.add-course-card {
  border: 2px dashed var(--color-border, var(--color-bg-border));
  background: transparent;
  min-height: 80px;
}

.add-course-card:hover,
.add-course-card:focus-visible {
  border-color: var(--color-primary-gradient-start);
  border-style: solid;
  background: rgba(102, 126, 234, 0.05);
}

.add-course-card .hover-arrow {
  display: none;
}

.add-card-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) var(--spacing-xl);
  width: 100%;
}

.add-icon {
  color: var(--color-text-muted);
  transition: var(--transition-base);
}

.add-course-card:hover .add-icon,
.add-course-card:focus-visible .add-icon {
  color: var(--color-primary-gradient-start);
}

.add-text {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-muted);
  transition: var(--transition-base);
}

.add-course-card:hover .add-text,
.add-course-card:focus-visible .add-text {
  color: var(--color-primary-gradient-start);
}

/* Expandable Form Card */
.add-course-card.form-expanded {
  border-style: solid;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
  min-height: auto;
  cursor: default;
  transform: none;
}

.add-course-card.form-expanded:hover {
  transform: none;
  box-shadow: none;
}

.add-card-trigger {
  width: 100%;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
}

/* Inline Course Form */
.inline-course-form {
  padding: var(--spacing-lg) var(--spacing-xl);
  width: 100%;
  animation: expandForm 0.25s ease-out;
}

@keyframes expandForm {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-bg-border);
}

.form-header h3 {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.close-form-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-sm);
  transition: var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-form-btn:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.form-row {
  display: flex;
  flex-direction: column;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-field label {
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.form-field input[type="text"] {
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  transition: var(--transition-fast);
}

.form-field input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-field input:disabled {
  background-color: var(--color-bg-disabled);
  cursor: not-allowed;
  opacity: 0.7;
}

.form-field small {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

/* Toggle styling */
.toggle-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}

.toggle-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  flex-shrink: 0;
}

.toggle-text {
  font-weight: 500;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.toggle-hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  padding-left: var(--spacing-sm);
  border-left: 1px solid var(--color-bg-border);
}

/* Form error */
.form-error {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-error-bg);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-base);
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

/* Form actions */
.form-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-bg-border);
}

.btn-cancel {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
}

.btn-cancel:hover:not(:disabled) {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.btn-create {
  padding: var(--spacing-sm) var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-admin) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
  box-shadow: var(--shadow-colored);
}

.btn-create:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
}

.btn-create:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .content-container {
    padding: 0 var(--spacing-md);
  }

  .card-main {
    padding: var(--spacing-md) var(--spacing-lg);
  }

  .course-card:hover .hover-arrow {
    width: 44px;
  }

  .inline-course-form {
    padding: var(--spacing-md) var(--spacing-lg);
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-cancel,
  .btn-create {
    width: 100%;
  }
}
</style>
