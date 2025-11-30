<template>
  <div class="admin-courses">
    <AdminNavBar />
    
    <div class="content-container">
      <div class="page-header">
        <h1>Course Management</h1>
        <button
          class="create-btn"
          @click="showCreateModal = true"
        >
          <span class="btn-icon">+</span>
          Create Course
        </button>
      </div>
      
      <!-- Loading State -->
      <div
        v-if="loading"
        class="loading-container"
      >
        <div class="loading-spinner" />
        <p>Loading courses...</p>
      </div>
      
      <!-- Courses Table -->
      <div
        v-else-if="courses.length > 0"
        class="courses-table-container"
      >
        <table class="courses-table">
          <thead>
            <tr>
              <th>Course ID</th>
              <th>Name</th>
              <th>Instructor</th>
              <th>Problem Sets</th>
              <th>Students</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="course in courses"
              :key="course.id"
            >
              <td class="course-id">
                {{ course.course_id }}
              </td>
              <td>{{ course.name }}</td>
              <td>{{ course.instructor_name }}</td>
              <td class="center">
                {{ course.problem_sets_count }}
              </td>
              <td class="center">
                {{ course.enrolled_students_count }}
              </td>
              <td>
                <span :class="['status-badge', course.is_active ? 'active' : 'inactive']">
                  {{ course.is_active ? 'Active' : 'Inactive' }}
                </span>
              </td>
              <td class="actions">
                <button
                  class="action-btn edit"
                  title="Edit"
                  @click="editCourse(course)"
                >
                  ✏️
                </button>
                <button
                  class="action-btn manage"
                  title="Manage Problem Sets"
                  @click="manageProblemSets(course)"
                >
                  📚
                </button>
                <button
                  class="action-btn view"
                  title="View Students"
                  @click="viewStudents(course)"
                >
                  👥
                </button>
                <button
                  class="action-btn delete"
                  title="Delete"
                  @click="deleteCourse(course)"
                >
                  🗑️
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- Empty State -->
      <div
        v-else
        class="empty-state"
      >
        <div class="empty-icon">
          🎓
        </div>
        <h3>No Courses Yet</h3>
        <p>Create your first course to get started.</p>
        <button
          class="create-btn"
          @click="showCreateModal = true"
        >
          Create Course
        </button>
      </div>
    </div>
    
    <!-- Create/Edit Course Modal -->
    <div
      v-if="showCreateModal || showEditModal"
      class="modal-overlay"
      @click.self="closeModals"
    >
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ showEditModal ? 'Edit Course' : 'Create Course' }}</h2>
          <button
            class="close-btn"
            @click="closeModals"
          >
            ×
          </button>
        </div>
        
        <form
          class="course-form"
          @submit.prevent="saveCourse"
        >
          <div class="form-group">
            <label for="course-id">Course ID *</label>
            <input
              id="course-id"
              v-model="courseForm.course_id"
              type="text"
              placeholder="e.g., CS101-FALL2024"
              :disabled="showEditModal"
              required
            >
            <small>Unique identifier for the course (cannot be changed after creation)</small>
          </div>
          
          <div class="form-group">
            <label for="course-name">Course Name *</label>
            <input
              id="course-name"
              v-model="courseForm.name"
              type="text"
              placeholder="e.g., Introduction to Computer Science"
              required
            >
          </div>

          <div class="form-group">
            <label for="instructor">Instructor *</label>
            <select
              id="instructor"
              v-model="courseForm.instructor_id"
              required
            >
              <option
                :value="null"
                disabled
              >
                Select an instructor...
              </option>
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

          <div class="form-group">
            <label for="course-description">Description</label>
            <textarea
              id="course-description"
              v-model="courseForm.description"
              rows="4"
              placeholder="Course description..."
            />
          </div>
          
          <div class="form-group checkbox-group">
            <label>
              <input
                v-model="courseForm.is_active"
                type="checkbox"
              >
              Course is active
            </label>
            <label>
              <input
                v-model="courseForm.enrollment_open"
                type="checkbox"
              >
              Enrollment is open
            </label>
          </div>
          
          <div class="modal-footer">
            <button
              type="button"
              class="cancel-btn"
              @click="closeModals"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="save-btn"
              :disabled="saving"
            >
              {{ saving ? 'Saving...' : (showEditModal ? 'Update' : 'Create') }}
            </button>
          </div>
        </form>
      </div>
    </div>
    
    <!-- Problem Sets Management Modal -->
    <AdminCourseProblemSetsModal
      v-if="selectedCourse"
      :visible="showProblemSetsModal"
      :course="selectedCourse"
      @close="showProblemSetsModal = false"
      @updated="fetchCourses"
    />
    
    <!-- Students Management Modal -->
    <AdminCourseStudentsModal
      v-if="selectedCourse"
      :visible="showStudentsModal"
      :course="selectedCourse"
      @close="showStudentsModal = false"
      @updated="fetchCourses"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref, Ref } from 'vue'
import axios, { AxiosError } from 'axios'
import AdminNavBar from './AdminNavBar.vue'
import AdminCourseProblemSetsModal from './AdminCourseProblemSetsModal.vue'
import AdminCourseStudentsModal from './AdminCourseStudentsModal.vue'
import { useNotification } from '@/composables/useNotification'
import { log } from '@/utils/logger'
import type { Course } from '@/types'

interface CourseForm {
  course_id: string;
  name: string;
  description: string;
  instructor_id: number | null;
  is_active: boolean;
  enrollment_open: boolean;
}

interface Instructor {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_staff: boolean;
}

export default defineComponent({
  name: 'AdminCourses',
  components: {
    AdminNavBar,
    AdminCourseProblemSetsModal,
    AdminCourseStudentsModal
  },
  setup() {
    const { notify } = useNotification()
    
    // Data
    const courses: Ref<Course[]> = ref([])
    const instructors: Ref<Instructor[]> = ref([])
    const loading = ref(true)
    const saving = ref(false)
    const showCreateModal = ref(false)
    const showEditModal = ref(false)
    const showProblemSetsModal = ref(false)
    const showStudentsModal = ref(false)
    const selectedCourse: Ref<Course | null> = ref(null)

    const courseForm: Ref<CourseForm> = ref({
      course_id: '',
      name: '',
      description: '',
      instructor_id: null,
      is_active: true,
      enrollment_open: true
    })
    
    // Methods
    const fetchCourses = async (): Promise<void> => {
      loading.value = true
      try {
        const response = await axios.get('/api/admin/courses/')
        courses.value = response.data
      } catch (error) {
        const axiosError = error as AxiosError
        notify.error('Error', 'Failed to load courses')
        log.error('Error fetching courses', { error: axiosError })
      } finally {
        loading.value = false
      }
    }

    const fetchInstructors = async (): Promise<void> => {
      try {
        const response = await axios.get('/api/admin/instructors/')
        instructors.value = response.data
      } catch (error) {
        const axiosError = error as AxiosError
        notify.error('Error', 'Failed to load instructors')
        log.error('Error fetching instructors', { error: axiosError })
      }
    }
    
    const saveCourse = async (): Promise<void> => {
      saving.value = true
      try {
        if (showEditModal.value) {
          // Update existing course
          await axios.put(`/api/admin/courses/${selectedCourse.value.course_id}/`, courseForm.value)
          notify.success('Success', 'Course updated successfully')
        } else {
          // Create new course
          await axios.post('/api/admin/courses/', courseForm.value)
          notify.success('Success', 'Course created successfully')
        }
        
        closeModals()
        await fetchCourses()
      } catch (error: unknown) {
        const axiosError = error as { response?: { data?: { error?: string } } }
        const errorMsg = axiosError.response?.data?.error || 'Failed to save course'
        notify.error('Error', errorMsg)
      } finally {
        saving.value = false
      }
    }
    
    const editCourse = (course: Course): void => {
      selectedCourse.value = course
      courseForm.value = {
        course_id: course.course_id,
        name: course.name,
        description: course.description || '',
        instructor_id: course.instructor_id,
        is_active: course.is_active,
        enrollment_open: course.enrollment_open
      }
      showEditModal.value = true
    }
    
    const deleteCourse = async (course: Course): Promise<void> => {
      if (!confirm(`Are you sure you want to delete "${course.name}"? This action cannot be undone.`)) {
        return
      }
      
      try {
        await axios.delete(`/api/admin/courses/${course.course_id}/`)
        notify.success('Success', 'Course deleted successfully')
        await fetchCourses()
      } catch (error) {
        const axiosError = error as AxiosError
        notify.error('Error', 'Failed to delete course')
        log.error('Error deleting course', { error: axiosError })
      }
    }
    
    const manageProblemSets = (course: Course): void => {
      selectedCourse.value = course
      showProblemSetsModal.value = true
    }
    
    const viewStudents = (course: Course): void => {
      selectedCourse.value = course
      showStudentsModal.value = true
    }
    
    const closeModals = (): void => {
      showCreateModal.value = false
      showEditModal.value = false
      showProblemSetsModal.value = false
      showStudentsModal.value = false
      selectedCourse.value = null
      courseForm.value = {
        course_id: '',
        name: '',
        description: '',
        instructor_id: null,
        is_active: true,
        enrollment_open: true
      }
    }
    
    // Lifecycle
    onMounted(() => {
      fetchCourses()
      fetchInstructors()
    })

    return {
      courses,
      instructors,
      loading,
      saving,
      showCreateModal,
      showEditModal,
      showProblemSetsModal,
      showStudentsModal,
      selectedCourse,
      courseForm,
      fetchCourses,
      fetchInstructors,
      saveCourse,
      editCourse,
      deleteCourse,
      manageProblemSets,
      viewStudents,
      closeModals
    }
  }
})
</script>

<style scoped>
.admin-courses {
  min-height: 100vh;
}

.content-container {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: 0 var(--spacing-xl) var(--spacing-xl);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
}

.page-header h1 {
  font-size: var(--font-size-xxl);
  color: var(--color-text-primary);
  margin: 0;
}

.create-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
  box-shadow: var(--shadow-colored);
}

.create-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-icon {
  font-size: var(--font-size-md);
}

/* Loading State */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
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

/* Table Styles */
.courses-table-container {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.courses-table {
  width: 100%;
  border-collapse: collapse;
}

.courses-table th {
  background-color: var(--color-bg-hover);
  padding: var(--spacing-lg) var(--spacing-xl);
  text-align: left;
  font-weight: 600;
  color: var(--color-text-secondary);
  border-bottom: 2px solid var(--color-bg-input);
}

.courses-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-input);
  color: var(--color-text-secondary);
}

.courses-table tr:hover {
  background-color: var(--color-bg-hover);
}

.course-id {
  font-family: monospace;
  font-weight: 500;
  color: var(--color-primary-gradient-start);
}

.center {
  text-align: center;
}

.status-badge {
  display: inline-block;
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.active {
  background-color: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.status-badge.inactive {
  background-color: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.actions {
  display: flex;
  gap: var(--spacing-sm);
}

.action-btn {
  padding: var(--spacing-sm);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: var(--transition-base);
  font-size: var(--font-size-base);
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.action-btn.edit:hover {
  border-color: var(--color-primary-gradient-start);
  background-color: rgba(102, 126, 234, 0.1);
}

.action-btn.manage:hover {
  border-color: var(--color-info);
  background-color: var(--color-info-bg);
}

.action-btn.view:hover {
  border-color: var(--color-success);
  background-color: var(--color-success-bg);
}

.action-btn.delete:hover {
  border-color: var(--color-error);
  background-color: var(--color-error-bg);
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

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--color-bg-panel);
  border-radius: calc(var(--radius-lg) + 4px);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
  border: 2px solid var(--color-bg-input);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 2px solid var(--color-bg-input);
  background: var(--color-bg-hover);
}

.modal-header h2 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
}

.close-btn {
  background: none;
  border: none;
  font-size: var(--font-size-xl);
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-xs);
  transition: var(--transition-base);
}

.close-btn:hover {
  background-color: var(--color-bg-input);
  color: var(--color-text-primary);
}

/* Form Styles */
.course-form {
  padding: var(--spacing-xl);
}

.form-group {
  margin-bottom: var(--spacing-xl);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
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

.checkbox-group {
  display: flex;
  gap: var(--spacing-xl);
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  font-weight: normal;
  color: var(--color-text-secondary);
}

.checkbox-group input[type="checkbox"] {
  width: auto;
  margin: 0;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-top: 2px solid var(--color-bg-input);
  background: var(--color-bg-hover);
}

.cancel-btn,
.save-btn {
  padding: var(--spacing-md) var(--spacing-xl);
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
}

.cancel-btn {
  background-color: var(--color-bg-panel);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.cancel-btn:hover {
  background-color: var(--color-bg-input);
  border-color: var(--color-bg-border);
  color: var(--color-text-primary);
}

.save-btn {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: none;
  box-shadow: var(--shadow-colored);
}

.save-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.save-btn:disabled {
  background: var(--color-bg-disabled);
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.7;
  box-shadow: none;
}
</style>