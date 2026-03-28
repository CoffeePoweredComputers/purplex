<template>
  <div class="instructor-students">
    <InstructorNavBar :course-name="courseName" />

    <div class="content-container">
      <!-- Loading State -->
      <div
        v-if="loading"
        class="loading-container"
      >
        <div class="loading-spinner" />
        <p>{{ $t('admin.courseStudents.loadingStudents') }}</p>
      </div>

      <!-- Error State -->
      <div
        v-else-if="error"
        class="error-state"
        role="alert"
      >
        <div
          class="error-icon"
          aria-hidden="true"
        >
          ⚠️
        </div>
        <span class="visually-hidden">{{ $t('admin.courseStudents.errorLabel') }}</span>
        <h3>{{ $t('admin.courseStudents.unableToLoadStudents') }}</h3>
        <p>{{ error }}</p>
        <button
          class="retry-btn"
          :aria-label="$t('admin.courseStudents.retryAriaLabel')"
          @click="fetchStudents"
        >
          {{ $t('admin.courseStudents.tryAgain') }}
        </button>
      </div>

      <!-- Students Table -->
      <template v-else-if="students.length > 0">
        <!-- Controls -->
        <div class="controls-container">
          <div class="search-container">
            <input
              id="student-search"
              v-model="searchQuery"
              type="text"
              :placeholder="$t('admin.courseStudents.searchPlaceholder')"
              class="search-input"
              :aria-label="$t('admin.courseStudents.searchAriaLabel')"
            >
          </div>
          <span class="results-count">
            {{ $t('admin.courseStudents.studentsEnrolled', { count: filteredStudents.length }) }}
          </span>
        </div>

        <div class="table-responsive">
          <table class="students-table">
            <thead>
              <tr>
                <th class="sticky-col">
                  {{ $t('admin.courseStudents.studentHeader') }}
                </th>
                <th
                  v-for="ps in problemSets"
                  :key="ps.id"
                  class="center problem-set-header"
                  :title="ps.title"
                >
                  {{ ps.title }}
                </th>
                <th class="center">
                  {{ $t('admin.courseStudents.overallHeader') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="student in filteredStudents"
                :key="student.user_id"
              >
                <td class="sticky-col student-cell">
                  <div class="student-name">
                    {{ student.username }}
                  </div>
                  <div class="student-email">
                    {{ student.email }}
                  </div>
                </td>
                <td
                  v-for="ps in problemSets"
                  :key="ps.id"
                  class="center progress-cell"
                >
                  <div
                    v-if="getStudentProblemSetProgress(student, ps.id)"
                    class="progress-indicator"
                    :class="getProgressColorClass(getStudentProblemSetProgress(student, ps.id)?.completion_percentage || 0)"
                    :title="`${getStudentProblemSetProgress(student, ps.id)?.completed_problems || 0}/${getStudentProblemSetProgress(student, ps.id)?.total_problems || 0} problems`"
                  >
                    {{ getStudentProblemSetProgress(student, ps.id)?.completion_percentage || 0 }}%
                  </div>
                  <div
                    v-else
                    class="progress-indicator progress-none"
                    :title="$t('admin.courseStudents.notStartedTitle')"
                  >
                    —
                  </div>
                </td>
                <td class="center progress-cell">
                  <div
                    class="progress-indicator overall"
                    :class="getProgressColorClass(student.progress_percentage)"
                    :title="`${student.problems_completed}/${student.total_problems} problems completed`"
                  >
                    {{ student.progress_percentage }}%
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- No results from filter -->
          <div
            v-if="filteredStudents.length === 0 && searchQuery"
            class="no-filter-results"
          >
            <p>{{ $t('admin.courseStudents.noSearchResults', { query: searchQuery }) }}</p>
          </div>
        </div>
      </template>

      <!-- Empty State -->
      <div
        v-else
        class="empty-state"
      >
        <div
          class="empty-icon"
          aria-hidden="true"
        >
          👥
        </div>
        <span class="visually-hidden">{{ $t('admin.courseStudents.informationLabel') }}</span>
        <h3>{{ $t('admin.courseStudents.noStudents') }}</h3>
        <p>{{ $t('admin.courseStudents.noStudentsMessage') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import axios from 'axios';
import InstructorNavBar from './InstructorNavBar.vue';
import { log } from '../../utils/logger';

interface ProblemSetProgress {
  problem_set_id: number;
  problem_set_title: string;
  problem_set_slug: string;
  completed_problems: number;
  total_problems: number;
  completion_percentage: number;
  average_score: number;
  is_completed: boolean;
}

interface ProblemSet {
  id: number;
  title: string;
  slug: string;
  order: number;
}

interface Student {
  user_id: number;
  username: string;
  email: string;
  progress_percentage: number;
  problems_completed: number;
  total_problems: number;
  enrolled_at: string;
  problem_set_progress: ProblemSetProgress[];
}

const route = useRoute();
const { t } = useI18n();
const courseId = computed(() => route.params.courseId as string);

const students = ref<Student[]>([]);
const problemSets = ref<ProblemSet[]>([]);
const courseName = ref<string>('');
const loading = ref(true);
const error = ref<string | null>(null);
const searchQuery = ref('');

// Computed property for filtered students
const filteredStudents = computed(() => {
  if (!searchQuery.value.trim()) {
    return students.value;
  }

  const query = searchQuery.value.toLowerCase().trim();
  return students.value.filter((student) => {
    const usernameMatch = student.username.toLowerCase().includes(query);
    const emailMatch = student.email.toLowerCase().includes(query);
    return usernameMatch || emailMatch;
  });
});

function getProgressColorClass(progress: number): string {
  if (progress >= 80) {
    return 'progress-high';
  }
  if (progress >= 50) {
    return 'progress-medium';
  }
  return 'progress-low';
}

function getStudentProblemSetProgress(
  student: Student,
  problemSetId: number
): ProblemSetProgress | undefined {
  return student.problem_set_progress.find(
    (psp) => psp.problem_set_id === problemSetId
  );
}

async function fetchStudents() {
  loading.value = true;
  error.value = null;

  try {
    // FERPA: This endpoint only returns students enrolled in the instructor's course
    const [studentsRes, courseRes] = await Promise.all([
      axios.get(`/api/instructor/courses/${courseId.value}/students/`),
      axios.get(`/api/instructor/courses/${courseId.value}/`),
    ]);

    // New API returns { problem_sets: [...], students: [...] }
    problemSets.value = studentsRes.data.problem_sets;
    students.value = studentsRes.data.students;
    courseName.value = courseRes.data.name;

    log.info('Loaded instructor course students', {
      courseId: courseId.value,
      studentCount: students.value.length,
      problemSetCount: problemSets.value.length,
    });
  } catch (err: unknown) {
    log.error('Failed to fetch students', err);
    if (axios.isAxiosError(err)) {
      if (err.response?.status === 404) {
        error.value = t('admin.courseStudents.courseNotFound');
      } else if (err.response?.status === 403) {
        error.value = t('admin.courseStudents.noPermissionStudents');
      } else {
        error.value = t('admin.courseStudents.failedToLoadStudentsRetry');
      }
    } else {
      error.value = t('common.errors.unexpectedError');
    }
  } finally {
    loading.value = false;
  }
}

// Watch for route changes
watch(courseId, () => {
  searchQuery.value = '';
  fetchStudents();
});

onMounted(() => {
  fetchStudents();
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
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}

.instructor-students {
  min-height: 100vh;
  background: var(--color-background);
}

.content-container {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: 0 var(--spacing-xl) var(--spacing-xxl);
}

/* Loading State (matches admin) */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
  box-shadow: var(--shadow-md);
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--color-bg-input);
  border-top-color: var(--color-primary-gradient-start);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: var(--spacing-lg);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State (matches admin) */
.error-state {
  text-align: center;
  padding: var(--spacing-xxl);
  background: var(--color-error-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-error);
}

.error-icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-lg);
}

.error-state h3 {
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.error-state p {
  color: var(--color-error-text);
  margin-bottom: var(--spacing-lg);
}

.retry-btn {
  padding: var(--spacing-md) var(--spacing-xl);
  background: var(--color-admin);
  color: var(--color-text-on-filled);
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

/* Controls Container (matches AdminSubmissions) */
.controls-container {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
}

.search-container {
  position: relative;
}

.search-input {
  width: 300px;
  padding: var(--spacing-md);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-base);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 3px var(--color-primary-overlay);
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.results-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: 500;
}

/* Table Container (matches admin .table-responsive) */
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

/* Table (matches admin tables) */
.students-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.students-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  padding: var(--spacing-lg);
  font-weight: 600;
  font-size: var(--font-size-xs);
  border-bottom: 2px solid var(--color-bg-input);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.students-table td {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.students-table th.center,
.students-table td.center {
  text-align: center;
}

.students-table tbody tr:hover {
  background: var(--color-bg-hover);
}

.students-table tbody tr:last-child td {
  border-bottom: none;
}

/* Sticky first column for horizontal scroll */
.sticky-col {
  position: sticky;
  left: 0;
  z-index: 1;
  background: var(--color-bg-panel);
}

.students-table thead .sticky-col {
  background: var(--color-bg-hover);
  z-index: 2;
}

.students-table tbody tr:hover .sticky-col {
  background: var(--color-bg-hover);
}

/* Problem set header */
.problem-set-header {
  min-width: 100px;
  max-width: 140px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Student cell */
.student-cell {
  min-width: 180px;
}

.student-name {
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
}

.student-email {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

/* Progress cell */
.progress-cell {
  padding: var(--spacing-md) var(--spacing-sm) !important;
}

/* Progress indicator (compact percentage display) */
.progress-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-base);
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: default;
}

.progress-indicator.progress-high {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.progress-indicator.progress-medium {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.progress-indicator.progress-low {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.progress-indicator.progress-none {
  background: var(--color-bg-input);
  color: var(--color-text-muted);
}

.progress-indicator.overall {
  font-weight: 700;
  min-width: 56px;
}

/* No filter results */
.no-filter-results {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-secondary);
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border: 2px dashed var(--color-bg-input);
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
  color: var(--color-text-secondary);
}

/* Mobile responsive */
@media (width <= 768px) {
  .content-container {
    padding: 0 var(--spacing-md) var(--spacing-xl);
  }

  .controls-container {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input {
    width: 100%;
  }

  .results-count {
    text-align: center;
  }

  .students-table {
    font-size: var(--font-size-sm);
  }

  .students-table th,
  .students-table td {
    padding: var(--spacing-sm);
  }

  .problem-set-header {
    min-width: 80px;
    max-width: 100px;
    font-size: 10px;
  }

  .student-cell {
    min-width: 140px;
  }

  .student-email {
    display: none;
  }

  .progress-indicator {
    min-width: 40px;
    padding: 2px var(--spacing-xs);
    font-size: 10px;
  }
}
</style>
