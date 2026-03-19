<template>
  <div class="course-detail">
    <div
      v-if="loading"
      class="loading-container"
    >
      <div class="loading-spinner" />
      <p>{{ $t('problems.courseDetail.loadingCourse') }}</p>
    </div>

    <div
      v-else-if="course"
      class="course-content"
    >
      <!-- Course Header -->
      <div class="course-header">
        <router-link
          to="/home"
          class="back-link"
        >
          <span class="back-arrow">←</span>
          {{ $t('problems.courseDetail.backToCourses') }}
        </router-link>

        <div class="course-info">
          <h1>{{ course.name }}</h1>
          <p class="course-id">
            {{ $t('problems.courseDetail.courseIdLabel') }} {{ course.course_id }}
          </p>
          <p
            v-if="course.description"
            class="course-description"
          >
            {{ course.description }}
          </p>

          <div class="course-meta">
            <div class="meta-item">
              <span class="label">{{ $t('problems.courseDetail.instructorLabel') }}</span>
              <span v-if="course.instructors?.length" class="value">
                {{ course.instructors.filter(i => i.role === 'primary').map(i => i.full_name).join(', ') }}
              </span>
              <span v-else class="value">{{ $t('problems.courseDetail.unknownInstructor') }}</span>
            </div>
            <div class="meta-item">
              <span class="label">{{ $t('problems.courseDetail.problemSetsLabel') }}</span>
              <span class="value">{{ course.problem_sets.length }}</span>
            </div>
            <div class="meta-item">
              <span class="label">{{ $t('problems.courseDetail.studentsEnrolledLabel') }}</span>
              <span class="value">{{ course.enrolled_students_count }}</span>
            </div>
          </div>
        </div>
      </div>

      <hr class="divider">

      <!-- Problem Sets -->
      <div class="problem-sets-section">
        <h2>{{ $t('problems.courseDetail.problemSetsHeading') }}</h2>

        <div
          v-if="course.problem_sets.length === 0"
          class="empty-state"
        >
          <p>{{ $t('problems.courseDetail.noProblemSets') }}</p>
        </div>

        <div
          v-else
          class="problem-sets-grid"
        >
          <div
            v-for="psData in course.problem_sets"
            :key="psData.problem_set.slug"
            class="problem-set-card"
            @click="navigateToProblemSet(psData.problem_set.slug)"
          >
            <div class="card-content">
              <div class="card-header">
                <h3>{{ psData.problem_set.title }}</h3>
                <div class="badges">
                  <span
                    v-if="psData.due_date"
                    :class="['due-badge', getDueDateClass(psData)]"
                  >
                    {{ isLocked(psData) ? '🔒 ' + $t('problems.courseDetail.closed') : formatDueDate(psData.due_date) }}
                  </span>
                  <span
                    v-if="psData.is_required"
                    class="required-badge"
                  >{{ $t('problems.courseDetail.required') }}</span>
                </div>
              </div>

              <p
                v-if="psData.problem_set.description"
                class="card-description"
              >
                {{ psData.problem_set.description }}
              </p>

              <div class="card-footer">
                <span class="problems-count">
                  {{ $t('problems.courseDetail.problemsCount', { count: psData.problem_set.problems_count }) }}
                </span>
                <span class="order-badge">
                  #{{ psData.order + 1 }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      v-else
      class="error-container"
    >
      <h2>{{ $t('problems.courseDetail.courseNotFound') }}</h2>
      <p>{{ $t('problems.courseDetail.courseNotFoundMessage') }}</p>
      <router-link
        to="/home"
        class="home-link"
      >
        {{ $t('problems.courseDetail.goBackToCourses') }}
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { useI18n } from 'vue-i18n'
import axios, { AxiosError } from 'axios'
import { log } from '@/utils/logger'
import type { Course } from '@/types'
import { waitForAuthState } from '@/utils/auth-state'

const route = useRoute()
const router = useRouter()
const store = useStore()
const { t } = useI18n()

const course = ref<Course | null>(null)
const loading = ref(true)
const courseId = computed(() => route.params.courseId as string)

async function fetchCourseDetails(): Promise<void> {
  loading.value = true
  try {
    const response = await axios.get(`/api/courses/${courseId.value}/`)
    course.value = response.data

    // Update current course in store
    store.commit('courses/SET_CURRENT_COURSE', response.data)
  } catch (error) {
    const axiosError = error as AxiosError
    log.error('Failed to fetch course details', { courseId: courseId.value, error: axiosError })
    course.value = null
  } finally {
    loading.value = false
  }
}

function navigateToProblemSet(problemSetSlug: string): void {
  router.push({
    name: 'CourseProblemSet',
    params: {
      courseId: courseId.value,
      slug: problemSetSlug
    }
  })
}

// Due date helpers
function formatDueDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays < 0) {
    return t('common.dueDate.pastDue')
  } else if (diffDays === 0) {
    return t('common.dueDate.dueToday')
  } else if (diffDays === 1) {
    return t('common.dueDate.dueTomorrow')
  } else if (diffDays <= 7) {
    return t('common.dueDate.dueInDays', { days: diffDays })
  } else {
    return t('common.dueDate.dueOn', { date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) })
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

onMounted(async () => {
  // Wait for auth state to be determined first
  await waitForAuthState()
  fetchCourseDetails()
})
</script>

<style scoped>
.course-detail {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: var(--spacing-xl);
}

/* Loading State */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
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

/* Course Header */
.course-header {
  margin-bottom: var(--spacing-xl);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--color-primary-gradient-start);
  text-decoration: none;
  font-weight: 600;
  margin-bottom: var(--spacing-lg);
  transition: var(--transition-base);
}

.back-link:hover {
  color: var(--color-primary-gradient-end);
  transform: translateX(-2px);
}

.back-arrow {
  font-size: var(--font-size-md);
}

.course-info h1 {
  font-size: 2.5rem;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.course-id {
  font-family: monospace;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-lg);
}

.course-description {
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--spacing-xl);
}

.course-meta {
  display: flex;
  gap: var(--spacing-xl);
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  gap: var(--spacing-sm);
}

.meta-item .label {
  font-weight: 600;
  color: var(--color-text-muted);
}

.meta-item .value {
  color: var(--color-text-primary);
}

.divider {
  border: none;
  border-top: 2px solid var(--color-bg-input);
  margin: var(--spacing-xl) 0;
}

/* Problem Sets Section */
.problem-sets-section h2 {
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xl);
}

.problem-sets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: var(--spacing-xl);
}

.problem-set-card {
  background: var(--color-bg-panel);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-lg);
  padding: 0;
  cursor: pointer;
  transition: var(--transition-base);
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

.card-header h3 {
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
  margin: 0;
  flex: 1;
}

.badges {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  flex-shrink: 0;
}

.required-badge {
  background-color: var(--color-error-bg);
  color: var(--color-error);
  font-size: var(--font-size-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-weight: 600;
  white-space: nowrap;
  border: 1px solid var(--color-error);
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

.card-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: 1.5;
  margin-bottom: var(--spacing-lg);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-sm);
}

.problems-count {
  color: var(--color-text-muted);
}

.order-badge {
  background-color: var(--color-bg-hover);
  color: var(--color-text-muted);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-weight: 600;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--spacing-xxl);
  background-color: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
  border: 2px solid var(--color-bg-border);
}

/* Error State */
.error-container {
  text-align: center;
  padding: var(--spacing-xxl);
}

.error-container h2 {
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-lg);
}

.error-container p {
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-xl);
}

.home-link {
  display: inline-block;
  padding: var(--spacing-md) var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  text-decoration: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  transition: var(--transition-base);
  box-shadow: var(--shadow-colored);
}

.home-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--color-primary-glow);
}

/* Responsive Design */
@media (max-width: 768px) {
  .course-detail {
    padding: var(--spacing-lg);
  }

  .course-info h1 {
    font-size: var(--font-size-xxl);
  }

  .course-meta {
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .problem-sets-grid {
    grid-template-columns: 1fr;
  }
}
</style>
