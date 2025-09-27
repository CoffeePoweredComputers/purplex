<template>
  <div class="home-container">
    <!-- Course Enrollment Modal -->
    <CourseEnrollmentModal />
    
    <!-- Enrolled Courses Section -->
    <div
      v-if="enrolledCourses.length > 0"
      class="courses-section"
    >
      <div 
        v-for="enrollment in enrolledCourses" 
        :key="enrollment.course.course_id"
        class="course-section"
      >
        <div class="course-header">
          <h2 class="course-title">
            {{ enrollment.course.name }}
          </h2>
          <span class="progress-indicator">
            {{ enrollment.progress.completed_sets }} / {{ enrollment.progress.total_sets }} completed
          </span>
        </div>
        <hr class="course-divider">
        
        <!-- Reuse existing gallery grid for problem sets -->
        <div
          v-if="loading.courses"
          class="gallery-grid"
        >
          <!-- Skeleton cards -->
          <div
            v-for="n in 3"
            :key="`skeleton-${n}`"
            class="problem-set-card skeleton"
          >
            <div class="card-content">
              <div class="card-header">
                <div class="skeleton-title" />
              </div>
              <div class="progress-section">
                <div class="skeleton-progress-bar" />
                <div class="skeleton-progress-text" />
              </div>
            </div>
          </div>
        </div>
        
        <div
          v-else-if="enrollment.course.problem_sets && enrollment.course.problem_sets.length > 0"
          class="gallery-grid"
        >
          <div 
            v-for="psData in enrollment.course.problem_sets" 
            :key="psData.problem_set.slug" 
            class="problem-set-card"
            @click="navigateToProblemSet(enrollment.course.course_id, psData.problem_set.slug)"
          >
            <div class="card-content">
              <div class="card-header">
                <h3 class="card-title">
                  {{ psData.problem_set.title }}
                </h3>
              </div>

              <div class="progress-section">
                <div class="progress-bar-container">
                  <div class="progress-bar-background">
                    <div 
                      class="progress-bar-fill" 
                      :style="{ width: psData.progress.percentage + '%' }"
                    />
                  </div>
                  <span class="progress-text">
                    <template v-if="psData.progress.total_problems === 0">
                      No problems yet
                    </template>
                    <template v-else>
                      {{ psData.progress.completed_problems }} / 
                      {{ psData.progress.total_problems }} completed
                    </template>
                  </span>
                </div>
              </div>
            </div>
            <div class="card-hover-text">
              {{ psData.progress.percentage === 100 ? 'Review →' : 
                psData.progress.completed_problems > 0 ? 'Continue →' : 'Start →' }}
            </div>
          </div>
        </div>
        
        <div
          v-else
          class="empty-state"
        >
          <p>No problem sets available in this course yet.</p>
        </div>
      </div>
    </div>
    
    
    <!-- Empty State -->
    <div
      v-if="!loading.courses && enrolledCourses.length === 0"
      class="empty-state-container"
    >
      <div class="empty-state-content">
        <div class="empty-icon">
          🎓
        </div>
        <h3>Welcome to Purplex!</h3>
        <p>Get started by joining a course to access problem sets.</p>
        <button
          class="add-course-btn"
          @click="showEnrollmentModal"
        >
          <span class="btn-icon">+</span>
          Join a Course
        </button>
      </div>
    </div>
    
    <!-- Add Course Button (floating) -->
    <button 
      v-if="enrolledCourses.length > 0"
      class="add-course-btn floating" 
      title="Join a Course"
      @click="showEnrollmentModal"
    >
      <span class="btn-icon">+</span>
    </button>
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, onMounted } from 'vue'
import { useStore } from 'vuex'
import { useRouter } from 'vue-router'
import CourseEnrollmentModal from '../modals/CourseEnrollmentModal.vue'

export default defineComponent({
  name: 'Home',
  components: {
    CourseEnrollmentModal
  },
  setup() {
    const store = useStore()
    const router = useRouter()
    
    // Computed properties
    const enrolledCourses = computed(() => store.state.courses.enrolledCourses)
    const loading = computed(() => store.state.courses.loading)
    const progressData = computed(() => store.state.courses.courseProgress)
    
    // Methods
    const showEnrollmentModal = (): void => {
      store.dispatch('courses/showEnrollmentModal')
    }
    
    const navigateToProblemSet = (courseId: string, problemSetSlug: string): void => {
      router.push(`/courses/${courseId}/problem-set/${problemSetSlug}`)
    }
    
    
    // Lifecycle
    onMounted(async () => {
      // Initialize courses data
      await store.dispatch('courses/initializeCourses')
    })
    
    return {
      enrolledCourses,
      loading,
      showEnrollmentModal,
      navigateToProblemSet
    }
  }
})
</script>

<style scoped>
.home-container {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: var(--spacing-xl);
  padding-bottom: 100px; /* Space for floating button */
}

.courses-section {
  margin-bottom: var(--spacing-xxl);
}

.course-section {
  margin-bottom: var(--spacing-xxl);
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.course-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.progress-indicator {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  font-weight: 500;
}

.course-divider {
  border: none;
  border-top: 2px solid var(--color-bg-input);
  margin-bottom: var(--spacing-xl);
}


.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-xl);
}

.problem-set-card {
  background: var(--color-bg-panel);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-lg);
  padding: 0;
  cursor: pointer;
  transition: var(--transition-base);
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-base);
}

.problem-set-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary-gradient-start);
}

.card-content {
  padding: var(--spacing-xl);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-lg);
}

.card-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  flex: 1;
}


.progress-section {
  margin-top: var(--spacing-lg);
}

.progress-bar-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.progress-bar-background {
  width: 100%;
  height: 8px;
  background-color: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-success) 0%, #0e9f6e 100%);
  transition: width 0.3s ease;
  border-radius: var(--radius-xs);
}

.progress-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}


.card-hover-text {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  padding: var(--spacing-md);
  text-align: center;
  font-weight: 600;
  transform: translateY(100%);
  transition: transform 0.3s ease;
}

.problem-set-card:hover .card-hover-text {
  transform: translateY(0);
}

/* Skeleton Loading */
.skeleton .skeleton-title {
  height: 24px;
  background-color: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  width: 70%;
  animation: pulse 2s infinite;
}

.skeleton .skeleton-progress-bar {
  height: 8px;
  background-color: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  margin-bottom: var(--spacing-sm);
  animation: pulse 2s infinite;
}

.skeleton .skeleton-progress-text {
  height: 16px;
  background-color: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  width: 40%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* Empty States */
.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-muted);
}

.empty-state-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

.empty-state-content {
  text-align: center;
  max-width: 400px;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: var(--spacing-lg);
}

.empty-state-content h3 {
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.empty-state-content p {
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-xl);
}

/* Add Course Button */
.add-course-btn {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-base);
  padding: var(--spacing-md) var(--spacing-xl);
  font-size: var(--font-size-base);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  box-shadow: var(--shadow-colored);
}

.add-course-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.add-course-btn.floating {
  position: fixed;
  bottom: var(--spacing-xl);
  right: var(--spacing-xl);
  width: 56px;
  height: 56px;
  padding: 0;
  border-radius: var(--radius-circle);
  box-shadow: var(--shadow-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.btn-icon {
  font-size: var(--font-size-xl);
  font-weight: 300;
}


/* Responsive Design */
@media (max-width: 768px) {
  .home-container {
    padding: var(--spacing-lg);
  }
  
  .gallery-grid {
    grid-template-columns: 1fr;
  }
  
  .course-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }
  
  .add-course-btn.floating {
    bottom: var(--spacing-lg);
    right: var(--spacing-lg);
  }
}
</style>