<template>
  <div class="home-container">
    <!-- Course Enrollment Modal -->
    <CourseEnrollmentModal />

    <!-- Main Content Area -->
    <main>
      <!-- Enrolled Courses Section -->
      <div
        v-if="enrolledCourses.length > 0"
        class="courses-section"
      >
        <section
          v-for="enrollment in enrolledCourses"
          :key="enrollment.course.course_id"
          class="course-section"
          :aria-labelledby="`course-title-${enrollment.course.course_id}`"
          :aria-describedby="`course-progress-${enrollment.course.course_id}`"
        >
          <div class="course-header">
            <h2
              :id="`course-title-${enrollment.course.course_id}`"
              class="course-title"
            >
              {{ enrollment.course.name }}
            </h2>
            <span
              :id="`course-progress-${enrollment.course.course_id}`"
              class="progress-indicator"
              role="status"
              :aria-label="t('problems.home.aria.courseProgress', { completed: enrollment.progress.completed_sets, total: enrollment.progress.total_sets })"
            >
              {{ t('problems.home.completed', { completed: enrollment.progress.completed_sets, total: enrollment.progress.total_sets }) }}
            </span>
          </div>
          <hr
            class="course-divider"
            aria-hidden="true"
          >

          <!-- Reuse existing gallery grid for problem sets -->
          <div
            v-if="loading.courses"
            class="gallery-grid"
            role="status"
            :aria-label="t('problems.home.aria.loadingProblemSets')"
          >
            <!-- Skeleton cards -->
            <div
              v-for="n in 3"
              :key="`skeleton-${n}`"
              class="problem-set-card skeleton"
              aria-hidden="true"
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

          <nav
            v-else-if="enrollment.course.problem_sets && enrollment.course.problem_sets.length > 0"
            class="gallery-grid"
            :aria-label="`${enrollment.course.name}`"
          >
            <button
              v-for="psData in enrollment.course.problem_sets"
              :key="psData.problem_set.slug"
              class="problem-set-card"
              :aria-label="t('problems.home.aria.problemSetProgress', { title: psData.problem_set.title, completed: psData.progress.completed_problems, total: psData.progress.total_problems })"
              @click="navigateToProblemSet(enrollment.course.course_id, psData.problem_set.slug)"
            >
              <div class="card-content">
                <div class="card-header">
                  <h3 class="card-title">
                    {{ psData.problem_set.title }}
                  </h3>
                  <span
                    v-if="psData.due_date"
                    :class="['due-badge', getDueDateClass(psData)]"
                  >
                    {{ isLocked(psData) ? t('problems.home.closedBadge') : formatDueDate(psData.due_date) }}
                  </span>
                </div>

                <div class="progress-section">
                  <div class="progress-bar-container">
                    <div
                      class="progress-bar-background"
                      role="progressbar"
                      :aria-valuenow="psData.progress.percentage"
                      aria-valuemin="0"
                      aria-valuemax="100"
                      :aria-label="t('problems.home.aria.progressPercent', { percent: psData.progress.percentage })"
                      aria-live="polite"
                    >
                      <div
                        class="progress-bar-fill"
                        :style="{ width: psData.progress.percentage + '%' }"
                      />
                    </div>
                    <span
                      class="progress-text"
                      aria-live="polite"
                    >
                      <template v-if="psData.progress.total_problems === 0">
                        {{ $t('problems.home.noProblems') }}
                      </template>
                      <template v-else>
                        {{ t('problems.home.completed', { completed: psData.progress.completed_problems, total: psData.progress.total_problems }) }}
                      </template>
                    </span>
                  </div>
                </div>
              </div>
              <span
                class="card-hover-text"
                aria-hidden="true"
              >
                {{ psData.progress.percentage === 100 ? t('problems.home.reviewAction') :
                  psData.progress.completed_problems > 0 ? t('problems.home.continueAction') : t('problems.home.startAction') }}
              </span>
            </button>
          </nav>

          <div
            v-else
            class="empty-state"
            role="status"
          >
            <p>{{ $t('problems.home.noSetsAvailable') }}</p>
          </div>
        </section>
      </div>

      <!-- Empty State -->
      <div
        v-if="!loading.courses && enrolledCourses.length === 0"
        class="empty-state-container"
      >
        <div class="empty-state-content">
          <div
            class="empty-icon"
            aria-hidden="true"
          >
            🎓
          </div>
          <h1>{{ $t('problems.home.welcome') }}</h1>
          <p>{{ $t('problems.home.welcomeMessage') }}</p>
          <button
            class="add-course-btn"
            :aria-label="$t('aria.joinCourse')"
            @click="showEnrollmentModal"
          >
            <span
              class="btn-icon"
              aria-hidden="true"
            >+</span>
            {{ $t('problems.home.joinCourse') }}
          </button>
        </div>
      </div>
    </main>

    <!-- Add Course Button (floating) -->
    <button
      v-if="enrolledCourses.length > 0"
      class="add-course-btn floating"
      :aria-label="$t('problems.home.joinCourse')"
      @click="showEnrollmentModal"
    >
      <span
        class="btn-icon"
        aria-hidden="true"
      >+</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import CourseEnrollmentModal from '../modals/CourseEnrollmentModal.vue'
import { waitForAuthState } from '../utils/auth-state'

const store = useStore()
const router = useRouter()
const { t, locale } = useI18n()

// Computed properties
const enrolledCourses = computed(() => store.state.courses.enrolledCourses)
const loading = computed(() => store.state.courses.loading)

function showEnrollmentModal(): void {
  store.dispatch('courses/showEnrollmentModal')
}

function navigateToProblemSet(courseId: string, problemSetSlug: string): void {
  router.push(`/courses/${courseId}/problem-set/${problemSetSlug}`)
}

// Due date helpers
function formatDueDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays < 0) {
    return t('problems.dueDate.pastDue')
  } else if (diffDays === 0) {
    return t('problems.dueDate.today')
  } else if (diffDays === 1) {
    return t('problems.dueDate.tomorrow')
  } else if (diffDays <= 7) {
    return t('problems.dueDate.inDays', { days: diffDays })
  } else {
    return t('problems.dueDate.onDate', { date: date.toLocaleDateString(locale.value, { month: 'short', day: 'numeric' }) })
  }
}

function getDueDateClass(psData: { due_date?: string; deadline_type?: string }): string {
  if (!psData.due_date) {
    return ''
  }

  const date = new Date(psData.due_date)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays < 0) {
    return psData.deadline_type === 'hard' ? 'due-locked' : 'due-past'
  } else if (diffDays <= 2) {
    return 'due-urgent'
  } else if (diffDays <= 7) {
    return 'due-soon'
  }
  return 'due-normal'
}

function isLocked(psData: { due_date?: string; deadline_type?: string }): boolean {
  if (!psData.due_date || psData.deadline_type !== 'hard') {
    return false
  }
  return new Date(psData.due_date) < new Date()
}

// Lifecycle
onMounted(async () => {
  // Wait for auth state to be determined first
  await waitForAuthState()
  // Initialize courses data
  await store.dispatch('courses/initializeCourses')
})
</script>

<style scoped>
.home-container {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: var(--spacing-xl);
  padding-bottom: 100px; /* Space for floating button */
}

main {
  /* Remove any default main element styling */
  display: block;
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
  text-align: left;
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
  text-align: left;
  width: 100%;
  font-family: inherit;
}

.problem-set-card:hover {
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary-gradient-start);
}

.problem-set-card:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.problem-set-card:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.problem-set-card:focus:not(:focus-visible) {
  outline: none;
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

/* Due date badges */
.due-badge {
  font-size: var(--font-size-xs);
  font-weight: 500;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

.due-badge.due-normal {
  background-color: var(--color-bg-hover);
  color: var(--color-text-muted);
}

.due-badge.due-soon {
  background-color: var(--color-warning-overlay);
  color: var(--color-warning);
}

.due-badge.due-urgent {
  background-color: var(--color-error-overlay);
  color: var(--color-error);
}

.due-badge.due-past {
  background-color: var(--color-error-overlay);
  color: var(--color-text-muted);
  text-decoration: line-through;
}

.due-badge.due-locked {
  background-color: var(--color-overlay-medium);
  color: var(--color-text-muted);
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
  background: linear-gradient(90deg, var(--color-success) 0%, var(--color-success-dark) 100%);
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
  background: var(--color-primary-glow);
  backdrop-filter: blur(8px);
  color: var(--color-primary-gradient-start);
  padding: var(--spacing-lg) var(--spacing-md) var(--spacing-md);
  text-align: center;
  font-weight: 600;
  transform: translateY(100%);
  transition: transform 0.3s ease;
  will-change: transform;
  backface-visibility: hidden;
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

.empty-state-content h1 {
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
  color: var(--color-text-on-filled);
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
  box-shadow: 0 6px 20px var(--color-primary-glow);
}

.add-course-btn:focus {
  outline: 2px solid var(--color-text-primary);
  outline-offset: 2px;
}

.add-course-btn:focus-visible {
  outline: 2px solid var(--color-text-primary);
  outline-offset: 2px;
}

.add-course-btn:focus:not(:focus-visible) {
  outline: none;
}

.add-course-btn.floating {
  position: fixed;
  bottom: calc(60px + var(--spacing-xl)); /* Account for footer height */
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
@media (width <= 768px) {
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
