<template>
  <div v-if="enrollmentModal.visible" class="modal-overlay" @click.self="hideModal">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Join a Course</h3>
        <button class="close-btn" @click="hideModal">×</button>
      </div>
      
      <div class="enrollment-form">
        <label for="course-id">Course ID</label>
        <div class="input-group">
          <input 
            id="course-id"
            v-model="courseId" 
            placeholder="Enter Course ID (e.g., CS101-FALL2024)" 
            @keyup.enter="lookupCourse"
            :disabled="enrollmentModal.loading"
            class="course-input"
          />
          <button 
            @click="lookupCourse" 
            :disabled="!courseId || enrollmentModal.loading"
            class="lookup-btn"
          >
            {{ enrollmentModal.loading ? 'Looking up...' : 'Lookup Course' }}
          </button>
        </div>
      </div>
      
      <div v-if="enrollmentModal.coursePreview" class="course-preview">
        <h4>{{ enrollmentModal.coursePreview.name }}</h4>
        <p class="description">{{ enrollmentModal.coursePreview.description }}</p>
        <div class="course-meta">
          <div class="meta-item">
            <span class="label">Instructor:</span>
            <span class="value">{{ enrollmentModal.coursePreview.instructor }}</span>
          </div>
          <div class="meta-item">
            <span class="label">Problem Sets:</span>
            <span class="value">{{ enrollmentModal.coursePreview.problem_sets_count }}</span>
          </div>
          <div class="meta-item" v-if="enrollmentModal.coursePreview.enrollment_open">
            <span class="label">Status:</span>
            <span class="value status-open">Open for Enrollment</span>
          </div>
        </div>
        
        <div v-if="enrollmentModal.coursePreview.is_enrolled" class="already-enrolled">
          <p>✓ You are already enrolled in this course</p>
        </div>
        
        <button 
          v-else
          @click="enrollInCourse" 
          class="enroll-btn"
          :disabled="enrollmentModal.loading || !enrollmentModal.coursePreview.enrollment_open"
        >
          {{ enrollmentModal.loading ? 'Enrolling...' : 'Join Course' }}
        </button>
      </div>
      
      <div v-if="enrollmentModal.error" class="error-message">
        <p>{{ enrollmentModal.error }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue'
import { useStore } from 'vuex'
import { useRouter } from 'vue-router'

export default {
  name: 'CourseEnrollmentModal',
  setup() {
    const store = useStore()
    const router = useRouter()
    const courseId = ref('')
    
    const enrollmentModal = computed(() => store.state.courses.enrollmentModal)
    
    const hideModal = () => {
      store.dispatch('courses/hideEnrollmentModal')
      courseId.value = ''
    }
    
    const lookupCourse = async () => {
      if (!courseId.value.trim()) return
      
      try {
        await store.dispatch('courses/lookupCourse', courseId.value.trim())
      } catch (error) {
        // Error is handled in the store
      }
    }
    
    const enrollInCourse = async () => {
      if (!enrollmentModal.value.coursePreview) return
      
      try {
        await store.dispatch('courses/enrollInCourse', enrollmentModal.value.coursePreview.course_id)
        // Navigate to the course after successful enrollment
        router.push(`/courses/${enrollmentModal.value.coursePreview.course_id}`)
      } catch (error) {
        // Error is handled in the store
      }
    }
    
    return {
      courseId,
      enrollmentModal,
      hideModal,
      lookupCourse,
      enrollInCourse
    }
  }
}
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
  border-radius: calc(var(--radius-lg) + 4px);
  padding: 0;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
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
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 2px solid var(--color-bg-input);
  background: var(--color-bg-hover);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: var(--font-size-xl);
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
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

.enrollment-form {
  padding: var(--spacing-xl);
}

.enrollment-form label {
  display: block;
  margin-bottom: var(--spacing-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.input-group {
  display: flex;
  gap: var(--spacing-md);
}

.course-input {
  flex: 1;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-base);
  transition: var(--transition-fast);
}

.course-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.course-input:disabled {
  background-color: var(--color-bg-disabled);
  cursor: not-allowed;
  opacity: 0.7;
}

.lookup-btn {
  padding: var(--spacing-md) var(--spacing-lg);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
  white-space: nowrap;
  box-shadow: var(--shadow-colored);
}

.lookup-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.lookup-btn:disabled {
  background: var(--color-bg-disabled);
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.7;
  box-shadow: none;
}

.course-preview {
  padding: var(--spacing-xl);
  border-top: 2px solid var(--color-bg-input);
}

.course-preview h4 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
}

.description {
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-lg);
  line-height: 1.5;
}

.course-meta {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.meta-item .label {
  font-weight: 600;
  color: var(--color-text-muted);
  min-width: 100px;
}

.meta-item .value {
  color: var(--color-text-primary);
}

.status-open {
  color: var(--color-success);
  font-weight: 600;
}

.already-enrolled {
  background-color: var(--color-success-bg);
  border: 1px solid var(--color-success);
  border-radius: var(--radius-base);
  padding: var(--spacing-md);
  color: var(--color-success);
  text-align: center;
}

.enroll-btn {
  width: 100%;
  padding: var(--spacing-md);
  background: linear-gradient(135deg, var(--color-success) 0%, #0e9f6e 100%);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
  box-shadow: var(--shadow-colored);
}

.enroll-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4);
}

.enroll-btn:disabled {
  background: var(--color-bg-disabled);
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.7;
  box-shadow: none;
}

.error-message {
  padding: var(--spacing-xl);
  border-top: 2px solid var(--color-bg-input);
  background-color: var(--color-error-bg);
}

.error-message p {
  margin: 0;
  color: var(--color-error);
  text-align: center;
}

@media (max-width: 640px) {
  .modal-content {
    width: 95%;
    max-height: 90vh;
  }
  
  .input-group {
    flex-direction: column;
  }
  
  .lookup-btn {
    width: 100%;
  }
}
</style>