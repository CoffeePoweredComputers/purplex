<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="course-students-modal-title"
      @click.self="closeModal"
    >
      <div
        ref="modalContentRef"
        class="modal-content"
        @keydown.esc="closeModal"
      >
        <div class="modal-header">
          <h2 id="course-students-modal-title">
            Students in {{ course.name }}
          </h2>
          <button
            class="close-btn"
            @click="closeModal"
          >
            ×
          </button>
        </div>

        <div class="modal-body">
          <div class="summary-bar">
            <p class="summary-text">
              <strong>{{ students.length }}</strong> students enrolled
            </p>
          </div>

          <div
            v-if="loading"
            class="loading-container"
          >
            <div class="loading-spinner" />
            <p>Loading students...</p>
          </div>

          <div
            v-else-if="students.length === 0"
            class="empty-state"
          >
            <p>No students enrolled in this course yet.</p>
          </div>

          <table
            v-else
            class="students-table"
          >
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
              <tr
                v-for="student in students"
                :key="student.user.id"
              >
                <td>
                  {{ getStudentName(student.user) }}
                </td>
                <td class="email">
                  {{ student.user.email }}
                </td>
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
                    class="remove-btn"
                    title="Remove from course"
                    @click="removeStudent(student)"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="modal-footer">
          <button
            class="close-modal-btn"
            @click="closeModal"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script lang="ts">
import { defineComponent, type PropType, ref, toRef, watch } from 'vue'
import axios, { type AxiosError } from 'axios'
import { useNotification } from '@/composables/useNotification'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { log } from '@/utils/logger'
import type { Course } from '@/types'

interface User {
  id: number
  email: string
  username: string
  first_name?: string
  last_name?: string
}

interface StudentProgress {
  completion_percentage: number
  completed_problem_sets: number
  total_problem_sets: number
}

interface CourseStudent {
  user: User
  enrolled_at: string
  progress: StudentProgress
}

interface APIErrorResponse {
  error?: string
}

export default defineComponent({
  name: 'AdminCourseStudentsModal',
  props: {
    visible: {
      type: Boolean,
      required: true
    },
    course: {
      type: Object as PropType<Course>,
      required: true
    }
  },
  emits: ['close', 'updated'] as const,
  setup(props, { emit }) {
    const { notify } = useNotification()

    // Focus trap composable
    const { modalContentRef } = useFocusTrap(toRef(() => props.visible))

    const closeModal = (): void => {
      emit('close')
    }

    // Data
    const students = ref<CourseStudent[]>([])
    const loading = ref<boolean>(false)

    // Methods
    const fetchStudents = async (): Promise<void> => {
      loading.value = true
      try {
        const response = await axios.get<CourseStudent[]>(`/api/admin/courses/${props.course.course_id}/students/`)
        students.value = response.data
      } catch (error) {
        notify.error('Error', 'Failed to load students')
        log.error('Error fetching students', { error, courseId: props.course.course_id })
      } finally {
        loading.value = false
      }
    }

    const removeStudent = async (student: CourseStudent): Promise<void> => {
      const studentName = getStudentName(student.user)
      if (!confirm(`Remove ${studentName} from this course?`)) {
        return
      }

      try {
        await axios.delete(`/api/admin/courses/${props.course.course_id}/students/${student.user.id}/`)

        // Remove from list
        const index = students.value.findIndex(s => s.user.id === student.user.id)
        if (index > -1) {
          students.value.splice(index, 1)
        }

        notify.success('Success', 'Student removed from course')
        emit('updated')
      } catch (error) {
        const axiosError = error as AxiosError<APIErrorResponse>
        const errorMsg = axiosError.response?.data?.error || 'Failed to remove student'
        notify.error('Error', errorMsg)
      }
    }

    const getStudentName = (user: User): string => {
      if (user.first_name || user.last_name) {
        return `${user.first_name || ''} ${user.last_name || ''}`.trim()
      }
      return user.username
    }

    const formatDate = (dateString: string): string => {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    // Watch for modal visibility changes
    watch(() => props.visible, (newVal: boolean) => {
      if (newVal) {
        setTimeout(() => {
          fetchStudents()
        }, 50) // Small delay to ensure modal is rendered
      }
    })

    return {
      modalContentRef,
      closeModal,
      students,
      loading,
      fetchStudents,
      removeStudent,
      getStudentName,
      formatDate
    }
  }
})
</script>

<style scoped>
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
  border-radius: var(--radius-lg);
  max-width: 800px;
  width: 90%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  border: 2px solid var(--color-bg-input);
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
  transition: var(--transition-fast);
}

.close-btn:hover {
  background-color: var(--color-bg-input);
  color: var(--color-text-primary);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xl);
}

.summary-bar {
  background-color: var(--color-bg-hover);
  border-radius: var(--radius-base);
  padding: var(--spacing-md) var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.summary-text {
  margin: 0;
  color: var(--color-text-secondary);
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

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--spacing-xxl);
  color: var(--color-text-muted);
}

/* Students Table */
.students-table {
  width: 100%;
  border-collapse: collapse;
}

.students-table th {
  background-color: var(--color-bg-hover);
  padding: var(--spacing-md) var(--spacing-lg);
  text-align: left;
  font-weight: 600;
  color: var(--color-text-secondary);
  border-bottom: 2px solid var(--color-bg-input);
  font-size: var(--font-size-sm);
}

.students-table td {
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-input);
  color: var(--color-text-secondary);
}

.students-table tr:hover {
  background-color: var(--color-bg-hover);
  transition: background-color 0.15s ease;
}

.email {
  font-family: monospace;
  font-size: var(--font-size-sm);
}

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

.remove-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  background-color: transparent;
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-sm);
}

.remove-btn:hover {
  color: var(--color-error);
  border-color: var(--color-error);
}

/* Modal Footer */
.modal-footer {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-top: 2px solid var(--color-bg-input);
  background: var(--color-bg-hover);
  display: flex;
  justify-content: flex-end;
}

.close-modal-btn {
  padding: var(--spacing-md) var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-fast);
}

.close-modal-btn:hover {
  opacity: 0.9;
}

/* Responsive */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    max-height: 90vh;
  }

  .students-table {
    font-size: var(--font-size-sm);
  }

  .students-table th,
  .students-table td {
    padding: var(--spacing-sm) var(--spacing-md);
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
