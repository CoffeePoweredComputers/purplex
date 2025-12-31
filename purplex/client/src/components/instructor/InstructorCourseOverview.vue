<template>
  <div class="instructor-overview">
    <InstructorNavBar />

    <div class="content-container">
      <!-- Loading State -->
      <div
        v-if="loading"
        class="loading-container"
      >
        <div class="loading-spinner" />
        <p>Loading course overview...</p>
      </div>

      <!-- Error State -->
      <div
        v-else-if="error"
        class="error-state"
        role="alert"
      >
        <div class="error-icon" aria-hidden="true">
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </div>
        <span class="visually-hidden">Error:</span>
        <h3>Unable to Load Course</h3>
        <p>{{ error }}</p>
        <router-link
          to="/instructor"
          class="back-btn"
        >
          Back to My Courses
        </router-link>
      </div>

      <!-- Course Content -->
      <template v-else-if="overview">
        <!-- Unified Course Card -->
        <div class="course-card">
          <!-- Header Section -->
          <header class="course-header">
            <div class="header-identity">
              <h1>{{ overview.course_name }}</h1>
              <span class="course-code">Course ID: {{ overview.course_id }}</span>
            </div>
            <div class="header-stats">
              <div class="header-stat">
                <span class="stat-value">{{ overview.total_students }}</span>
                <span class="stat-label">students</span>
              </div>
              <div class="header-stat">
                <span class="stat-value">{{ overview.avg_score }}%</span>
                <span class="stat-label">avg score</span>
              </div>
            </div>
          </header>

          <div class="card-divider" />

          <!-- Journey Timeline -->
          <div
            v-if="overview.problem_set_stats.length === 0"
            class="empty-journey"
          >
            <p>No problem sets assigned to this course yet.</p>
          </div>

          <div
            v-else
            class="journey-timeline"
          >
            <div
              v-for="(ps, index) in overview.problem_set_stats"
              :key="ps.problem_set_slug"
              class="journey-item"
              :class="{
                'selected': selectedProblemSetSlug === ps.problem_set_slug,
                'dimmed': selectedProblemSetSlug && selectedProblemSetSlug !== ps.problem_set_slug
              }"
              role="button"
              tabindex="0"
              :aria-pressed="selectedProblemSetSlug === ps.problem_set_slug"
              :aria-label="`Filter by ${ps.problem_set_title}`"
              @click="toggleProblemSetSelection(ps.problem_set_slug)"
              @keydown.enter="toggleProblemSetSelection(ps.problem_set_slug)"
              @keydown.space.prevent="toggleProblemSetSelection(ps.problem_set_slug)"
            >
              <div class="journey-marker">
                <span class="marker-number">{{ index + 1 }}</span>
                <div
                  v-if="index < overview.problem_set_stats.length - 1"
                  class="marker-line"
                />
              </div>
              <div class="journey-content">
                <div class="journey-header">
                  <h3 class="ps-title">{{ ps.problem_set_title }}</h3>
                  <div class="header-right">
                    <span
                      v-if="ps.due_date"
                      :class="['due-badge', getDueDateClass(ps.due_date)]"
                    >
                      {{ formatDueDate(ps.due_date) }}
                    </span>
                    <span v-else class="due-badge no-due">No due date</span>
                    <span
                      :class="['completion-badge', getCompletionClass(ps.avg_completion)]"
                    >
                      {{ Math.round(ps.avg_completion) }}%
                    </span>
                    <button
                      class="download-btn"
                      :title="`Download scores for ${ps.problem_set_title}`"
                      @click.stop="downloadProblemSetScores(ps.problem_set_slug, ps.problem_set_title)"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="7 10 12 15 17 10" />
                        <line x1="12" y1="15" x2="12" y2="3" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div
                  v-if="ps.due_date && getDueDateDetail(ps.due_date)"
                  class="due-detail"
                  :class="getDueDateClass(ps.due_date)"
                >
                  {{ getDueDateDetail(ps.due_date) }}
                </div>
                <div class="journey-progress">
                  <div
                    class="progress-track"
                    role="progressbar"
                    :aria-valuenow="ps.avg_completion"
                    aria-valuemin="0"
                    aria-valuemax="100"
                  >
                    <div
                      class="progress-fill"
                      :class="getCompletionClass(ps.avg_completion)"
                      :style="{ width: `${ps.avg_completion}%` }"
                    />
                    <div
                      class="progress-marker"
                      :style="{ left: `${ps.avg_completion}%` }"
                    />
                  </div>
                </div>
                <div class="journey-stats">
                  <span class="stat-item">
                    {{ ps.students_completed }} of {{ overview.total_students }} finished
                  </span>
                  <span class="stat-separator">·</span>
                  <span class="stat-item">
                    avg score {{ ps.avg_score }}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="card-divider" />

          <!-- Filter Indicator (when problem set is selected) -->
          <div
            v-if="selectedProblemSetSlug"
            class="filter-indicator"
          >
            <span class="filter-text">
              Showing: <strong>{{ displayedMetrics?.title }}</strong>
            </span>
            <button
              class="clear-filter-btn"
              @click="clearSelection"
            >
              Clear filter
            </button>
          </div>

          <!-- Metrics Row: Activity + Snapshot -->
          <div class="metrics-row">
            <!-- Activity Chart -->
            <div class="metrics-section activity-section">
              <div class="activity-content">
                <!-- Placeholder state when nothing selected -->
                <template v-if="!selectedProblemSetSlug">
                  <div class="activity-placeholder">
                    <div class="chart-bars muted">
                      <div
                        v-for="i in 7"
                        :key="i"
                        class="chart-bar-container"
                      >
                        <div
                          class="chart-bar placeholder-bar"
                          :style="{ height: `${15 + (i % 3) * 10}%` }"
                        />
                        <span class="chart-label">{{ ['M', 'T', 'W', 'T', 'F', 'S', 'S'][i - 1] }}</span>
                      </div>
                    </div>
                    <p class="activity-summary muted-text">~ submissions this week</p>
                  </div>
                </template>

                <!-- Loading state for problem set activity -->
                <template v-else-if="loadingActivity">
                  <div class="activity-loading">
                    <div class="loading-spinner small" />
                    <span>Loading activity...</span>
                  </div>
                </template>

                <!-- Activity chart for selected problem set -->
                <template v-else-if="displayedMetrics?.activity_by_day.length">
                  <div class="activity-chart">
                    <!-- SVG Area + Line overlay (hidden when all values are zero) -->
                    <svg
                      v-if="hasActivityData(displayedMetrics.activity_by_day)"
                      class="chart-area-overlay"
                      viewBox="0 0 100 100"
                      preserveAspectRatio="none"
                    >
                      <defs>
                        <linearGradient
                          id="areaGradient"
                          x1="0%"
                          y1="0%"
                          x2="0%"
                          y2="100%"
                        >
                          <stop
                            offset="0%"
                            stop-color="var(--color-admin)"
                            stop-opacity="0.25"
                          />
                          <stop
                            offset="100%"
                            stop-color="var(--color-admin)"
                            stop-opacity="0.02"
                          />
                        </linearGradient>
                      </defs>
                      <!-- Area fill -->
                      <path
                        :d="getAreaPath(displayedMetrics.activity_by_day)"
                        fill="url(#areaGradient)"
                      />
                      <!-- Line connecting tops -->
                      <path
                        :d="getLinePath(displayedMetrics.activity_by_day)"
                        fill="none"
                        stroke="var(--color-admin)"
                        stroke-width="2.5"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        class="chart-line"
                      />
                    </svg>
                    <!-- Bars with data points overlay -->
                    <div class="chart-bars">
                      <div
                        v-for="day in displayedMetrics.activity_by_day"
                        :key="day.date"
                        class="chart-bar-container"
                      >
                        <div
                          class="chart-bar"
                          :style="{ height: `${getBarHeight(day.count)}%` }"
                          :title="`${day.count} submissions on ${formatDate(day.date)}`"
                        />
                        <div
                          v-if="day.count > 0"
                          class="chart-point"
                          :style="{ bottom: `${getBarHeight(day.count)}%` }"
                        />
                        <span class="chart-label">{{ getDayLabel(day.date) }}</span>
                      </div>
                    </div>
                  </div>
                  <p class="activity-summary">
                    {{ displayedMetrics.recent_submissions }} submissions this week
                  </p>
                </template>

                <!-- Empty state -->
                <div
                  v-else
                  class="activity-empty"
                >
                  <p>No submissions in the last 7 days</p>
                </div>
              </div>
              <h3 class="section-label bottom-label">Activity (7 days)</h3>
            </div>

            <!-- Class Snapshot -->
            <div class="metrics-section snapshot-section">
              <h3 class="section-label">
                {{ selectedProblemSetSlug ? 'Problem Set Snapshot' : 'Select a Problem Set' }}
              </h3>

              <!-- Placeholder state when nothing selected -->
              <template v-if="!selectedProblemSetSlug">
                <div class="snapshot-placeholder">
                  <p class="placeholder-hint">Click a problem set above to see detailed metrics</p>
                  <div class="snapshot-metrics muted">
                    <div class="snapshot-item">
                      <span class="snapshot-value placeholder">~</span>
                      <span class="snapshot-label">Avg Progress</span>
                    </div>
                    <div class="snapshot-item">
                      <span class="snapshot-value placeholder">~</span>
                      <span class="snapshot-label">Avg Score</span>
                    </div>
                  </div>
                  <div class="snapshot-distribution muted">
                    <div class="distribution-item completed">
                      <span class="dist-count">~</span>
                      <span class="dist-label">Completed</span>
                    </div>
                    <div class="distribution-item in-progress">
                      <span class="dist-count">~</span>
                      <span class="dist-label">In progress</span>
                    </div>
                    <div class="distribution-item not-started">
                      <span class="dist-count">~</span>
                      <span class="dist-label">Not started</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Actual metrics when problem set is selected -->
              <template v-else>
                <div class="snapshot-metrics">
                  <div class="snapshot-item">
                    <span class="snapshot-value">{{ displayedMetrics?.completion_rate }}%</span>
                    <span class="snapshot-label">Avg Progress</span>
                  </div>
                  <div class="snapshot-item">
                    <span class="snapshot-value">{{ displayedMetrics?.avg_score }}%</span>
                    <span class="snapshot-label">Avg Score</span>
                  </div>
                </div>
                <div class="snapshot-distribution">
                  <div class="distribution-item completed">
                    <span class="dist-count">{{ displayedMetrics?.student_distribution.completed_all }}</span>
                    <span class="dist-label">Completed</span>
                  </div>
                  <div class="distribution-item in-progress">
                    <span class="dist-count">{{ displayedMetrics?.student_distribution.in_progress }}</span>
                    <span class="dist-label">In progress</span>
                  </div>
                  <div class="distribution-item not-started">
                    <span class="dist-count">{{ displayedMetrics?.student_distribution.not_started }}</span>
                    <span class="dist-label">Not started</span>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import axios from 'axios';
import InstructorNavBar from './InstructorNavBar.vue';
import { log } from '../../utils/logger';

interface ProblemSetStat {
  problem_set_slug: string;
  problem_set_title: string;
  due_date: string | null;
  avg_completion: number;
  avg_score: number;
  students_completed: number;
  students_started: number;
  completion_rate: number;
}

interface ActivityDay {
  date: string;
  count: number;
}

interface StudentDistribution {
  completed_all: number;
  in_progress: number;
  not_started: number;
}

interface CourseOverview {
  course_id: string;
  course_name: string;
  total_students: number;
  total_attempts: number;
  avg_score: number;
  completion_rate: number;
  avg_time_per_problem_seconds: number;
  recent_submissions_7days: number;
  problem_set_stats: ProblemSetStat[];
  activity_by_day: ActivityDay[];
  student_distribution: StudentDistribution;
}

const route = useRoute();
const courseId = computed(() => route.params.courseId as string);

const overview = ref<CourseOverview | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

// Problem set selection state
const selectedProblemSetSlug = ref<string | null>(null);
const problemSetActivity = ref<{ activity_by_day: ActivityDay[]; recent_submissions_7days: number } | null>(null);
const loadingActivity = ref(false);

// Computed: metrics to display (course-wide or per-problem-set)
const displayedMetrics = computed(() => {
  if (!selectedProblemSetSlug.value || !overview.value) {
    // Course-wide (default)
    return {
      mode: 'course' as const,
      title: null,
      completion_rate: overview.value?.completion_rate || 0,
      avg_score: overview.value?.avg_score || 0,
      student_distribution: overview.value?.student_distribution || { completed_all: 0, in_progress: 0, not_started: 0 },
      activity_by_day: overview.value?.activity_by_day || [],
      recent_submissions: overview.value?.recent_submissions_7days || 0,
    };
  }

  // Per-problem-set
  const ps = overview.value.problem_set_stats.find(
    p => p.problem_set_slug === selectedProblemSetSlug.value
  );
  if (!ps) return null;

  return {
    mode: 'problem_set' as const,
    title: ps.problem_set_title,
    completion_rate: Math.round(ps.avg_completion),
    avg_score: ps.avg_score,
    student_distribution: {
      completed_all: ps.students_completed,
      in_progress: ps.students_started - ps.students_completed,
      not_started: overview.value.total_students - ps.students_started,
    },
    activity_by_day: problemSetActivity.value?.activity_by_day || [],
    recent_submissions: problemSetActivity.value?.recent_submissions_7days || 0,
  };
});

// Calculate max submissions for bar chart scaling (uses displayedMetrics for correct scaling)
const maxSubmissions = computed(() => {
  const activityData = displayedMetrics.value?.activity_by_day;
  if (!activityData || activityData.length === 0) return 1;
  return Math.max(...activityData.map(d => d.count), 1);
});

function getBarHeight(count: number): number {
  return (count / maxSubmissions.value) * 100;
}

// Generate SVG path for the line connecting bar tops
function getLinePath(data: ActivityDay[]): string {
  if (data.length === 0) return '';
  if (data.length === 1) {
    // Single point - just a dot, no line needed
    const y = 100 - getBarHeight(data[0].count) * 0.85 - 5;
    return `M 50 ${y}`;
  }

  const numPoints = data.length;
  const points = data.map((day, index) => {
    const x = (index / (numPoints - 1)) * 100;
    const y = 100 - getBarHeight(day.count) * 0.85 - 5;
    return { x, y };
  });

  // Create smooth curve using quadratic bezier
  let path = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev.x + curr.x) / 2;
    path += ` Q ${prev.x + (curr.x - prev.x) * 0.5} ${prev.y}, ${cpx} ${(prev.y + curr.y) / 2}`;
    if (i === points.length - 1) {
      path += ` T ${curr.x} ${curr.y}`;
    }
  }
  return path;
}

// Generate SVG path for the area fill under the line
function getAreaPath(data: ActivityDay[]): string {
  if (data.length === 0) return '';
  if (data.length === 1) {
    // Single point - small area around the point
    const y = 100 - getBarHeight(data[0].count) * 0.85 - 5;
    return `M 0 100 L 50 100 L 50 ${y} L 50 100 L 100 100 Z`;
  }

  const numPoints = data.length;
  const points = data.map((day, index) => {
    const x = (index / (numPoints - 1)) * 100;
    const y = 100 - getBarHeight(day.count) * 0.85 - 5;
    return { x, y };
  });

  // Start from bottom left
  let path = `M 0 100 L ${points[0].x} 100 L ${points[0].x} ${points[0].y}`;

  // Draw the top curve (same as line path)
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev.x + curr.x) / 2;
    path += ` Q ${prev.x + (curr.x - prev.x) * 0.5} ${prev.y}, ${cpx} ${(prev.y + curr.y) / 2}`;
    if (i === points.length - 1) {
      path += ` T ${curr.x} ${curr.y}`;
    }
  }

  // Close path back to bottom
  path += ` L ${points[points.length - 1].x} 100 L 100 100 Z`;
  return path;
}

// Check if there's any meaningful activity data (at least one non-zero value)
function hasActivityData(data: ActivityDay[]): boolean {
  return data.some(day => day.count > 0);
}

function getCompletionClass(completion: number): string {
  if (completion >= 75) return 'high';
  if (completion >= 40) return 'medium';
  return 'low';
}

// Due date helper functions
function getDueDateClass(dueDateStr: string): string {
  const due = new Date(dueDateStr);
  const now = new Date();
  const diffMs = due.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return 'overdue';
  if (diffDays === 0) return 'due-today';
  if (diffDays === 1) return 'due-tomorrow';
  if (diffDays <= 7) return 'due-soon';
  return 'due-later';
}

function formatDueDate(dueDateStr: string): string {
  const due = new Date(dueDateStr);
  const now = new Date();
  const diffMs = due.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return 'OVERDUE';
  if (diffDays === 0) return 'Due today';
  if (diffDays === 1) return 'Due tomorrow';
  return `Due ${due.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
}

function getDueDateDetail(dueDateStr: string): string {
  const due = new Date(dueDateStr);
  const now = new Date();
  const diffMs = due.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return `by ${Math.abs(diffDays)} day${Math.abs(diffDays) === 1 ? '' : 's'}`;
  if (diffDays === 0) return '';
  if (diffDays <= 7) return `in ${diffDays} day${diffDays === 1 ? '' : 's'}`;
  return '';
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getDayLabel(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { weekday: 'short' }).charAt(0);
}

// Problem set selection handlers
function toggleProblemSetSelection(slug: string) {
  if (selectedProblemSetSlug.value === slug) {
    selectedProblemSetSlug.value = null; // Deselect
  } else {
    selectedProblemSetSlug.value = slug; // Select
  }
}

function clearSelection() {
  selectedProblemSetSlug.value = null;
}

// Download problem set scores as CSV
async function downloadProblemSetScores(slug: string, title: string) {
  try {
    const response = await axios.get(
      `/api/instructor/courses/${courseId.value}/problem-sets/${slug}/export/`,
      { responseType: 'blob' }
    );

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    const filename = `${courseId.value}_${slug}_scores_${new Date().toISOString().split('T')[0]}.csv`;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    log.info('Downloaded problem set scores', { slug, courseId: courseId.value });
  } catch (err) {
    log.error('Failed to download problem set scores', err);
  }
}

// Fetch activity data for a specific problem set
async function fetchProblemSetActivity(slug: string) {
  loadingActivity.value = true;
  try {
    const response = await axios.get(
      `/api/instructor/courses/${courseId.value}/problem-sets/${slug}/activity/`
    );
    problemSetActivity.value = response.data;
    log.info('Loaded problem set activity', { slug, courseId: courseId.value });
  } catch (err) {
    log.error('Failed to fetch problem set activity', err);
    problemSetActivity.value = null;
  } finally {
    loadingActivity.value = false;
  }
}

// Watch selection changes to fetch per-problem-set activity
watch(selectedProblemSetSlug, async (newSlug) => {
  if (newSlug) {
    await fetchProblemSetActivity(newSlug);
  } else {
    problemSetActivity.value = null;
  }
});

async function fetchOverview() {
  loading.value = true;
  error.value = null;

  try {
    // Use the analytics endpoint which returns overview data
    const response = await axios.get(`/api/instructor/courses/${courseId.value}/analytics/`);
    overview.value = response.data;

    log.info('Loaded instructor course overview', {
      courseId: courseId.value,
      students: overview.value?.total_students,
    });
  } catch (err: unknown) {
    log.error('Failed to fetch course overview', err);
    if (axios.isAxiosError(err)) {
      if (err.response?.status === 404) {
        error.value = 'Course not found.';
      } else if (err.response?.status === 403) {
        error.value = 'You do not have permission to view this course.';
      } else {
        error.value = 'Failed to load course data. Please try again.';
      }
    } else {
      error.value = 'An unexpected error occurred.';
    }
  } finally {
    loading.value = false;
  }
}

watch(courseId, () => {
  fetchOverview();
});

onMounted(() => {
  fetchOverview();
});
</script>

<style scoped>
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

.instructor-overview {
  min-height: 100vh;
  background: var(--color-background);
}

.content-container {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: 0 var(--spacing-xl) var(--spacing-xxl);
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
  border: 4px solid var(--color-bg-border);
  border-top-color: var(--color-admin);
  border-right-color: var(--color-primary-gradient-end, #8b5cf6);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: var(--spacing-lg);
  box-shadow: 0 0 15px rgba(99, 102, 241, 0.2);
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
  margin-bottom: var(--spacing-lg);
  color: var(--color-warning);
}

.error-state h3 {
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.error-state p {
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-lg);
}

.back-btn {
  display: inline-block;
  padding: var(--spacing-md) var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-admin), var(--color-primary-gradient-end, #8b5cf6));
  color: white;
  text-decoration: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  transition: var(--transition-base);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.back-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

/* Unified Course Card */
.course-card {
  background: var(--color-bg-panel);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-base);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xxl);
}

.card-divider {
  height: 1px;
  background: var(--color-bg-border);
  margin: var(--spacing-xl) 0;
}

/* Course Header */
.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-identity {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.course-code {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-border);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  margin-top: var(--spacing-sm);
  width: fit-content;
}

.course-header h1 {
  font-size: var(--font-size-xxl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.header-stats {
  display: flex;
  gap: var(--spacing-xxl);
}

.header-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stat-value {
  font-size: var(--font-size-xxl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-transform: lowercase;
}

/* Journey Timeline */
.empty-journey {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-secondary);
}

.journey-timeline {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.journey-item {
  display: flex;
  gap: var(--spacing-lg);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md) var(--spacing-lg);
  position: relative;
  /* At-rest card appearance - clearly clickable */
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(99, 102, 241, 0.15);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.journey-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary-gradient-start);
}

.journey-item.selected {
  background: rgba(99, 102, 241, 0.08);
  border-color: var(--color-admin);
  box-shadow: var(--shadow-lg);
}

.journey-item.dimmed {
  opacity: 0.5;
}

.journey-item.dimmed:hover {
  opacity: 0.75;
}

.journey-item:focus-visible {
  outline: 2px solid var(--color-admin);
  outline-offset: 2px;
}

.journey-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 32px;
  flex-shrink: 0;
}

.marker-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--color-admin), var(--color-primary-gradient-end, #8b5cf6));
  color: white;
  font-weight: 600;
  font-size: var(--font-size-sm);
  border-radius: 50%;
  box-shadow: 0 3px 8px rgba(99, 102, 241, 0.4);
}

.marker-line {
  flex: 1;
  width: 2px;
  background: linear-gradient(to bottom, var(--color-admin), var(--color-bg-border));
  margin-top: var(--spacing-sm);
  min-height: 40px;
}

.journey-content {
  flex: 1;
  padding: var(--spacing-md) 0;
}

.journey-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.ps-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

/* Due date badges */
.due-badge {
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
  white-space: nowrap;
}

.due-badge.no-due {
  color: var(--color-text-tertiary);
  background: transparent;
}

.due-badge.due-later {
  color: var(--color-text-secondary);
  background: rgba(255, 255, 255, 0.05);
}

.due-badge.due-soon {
  color: var(--color-warning);
  background: rgba(245, 158, 11, 0.15);
}

.due-badge.due-tomorrow {
  color: var(--color-warning);
  background: rgba(245, 158, 11, 0.2);
  font-weight: 600;
}

.due-badge.due-today {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.15);
  font-weight: 600;
}

.due-badge.overdue {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.2);
  font-weight: 700;
}

/* Due date detail line */
.due-detail {
  font-size: var(--font-size-xs);
  margin-bottom: var(--spacing-sm);
}

.due-detail.due-soon,
.due-detail.due-tomorrow {
  color: var(--color-warning);
}

.due-detail.due-today,
.due-detail.overdue {
  color: var(--color-error);
}

.completion-badge {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-sm);
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.completion-badge.high {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.1));
  color: var(--color-success);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.completion-badge.medium {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.1));
  color: var(--color-warning);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.completion-badge.low {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(239, 68, 68, 0.1));
  color: var(--color-error);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Download button */
.download-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: var(--radius-base);
  color: var(--color-admin);
  cursor: pointer;
  transition: var(--transition-base);
  opacity: 0.7;
}

.download-btn:hover {
  background: rgba(99, 102, 241, 0.2);
  border-color: var(--color-admin);
  opacity: 1;
  transform: translateY(-1px);
}

.download-btn:active {
  transform: translateY(0);
}

.download-btn svg {
  flex-shrink: 0;
}

/* Journey Progress Bar */
.journey-progress {
  margin-bottom: var(--spacing-md);
}

.progress-track {
  position: relative;
  height: 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-base);
  overflow: visible;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.2);
}

.progress-fill {
  height: 100%;
  border-radius: var(--radius-base);
  transition: width 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}

.progress-fill.high {
  background: linear-gradient(90deg, var(--color-success), #34d399);
}

.progress-fill.medium {
  background: linear-gradient(90deg, var(--color-warning), #fbbf24);
}

.progress-fill.low {
  background: linear-gradient(90deg, var(--color-error), #f87171);
}

.progress-marker {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 16px;
  height: 16px;
  background: linear-gradient(135deg, var(--color-admin), var(--color-primary-gradient-end, #8b5cf6));
  border: 3px solid var(--color-bg-panel);
  border-radius: 50%;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.4);
}

.journey-stats {
  display: flex;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.stat-separator {
  color: var(--color-text-tertiary);
}

/* Filter Indicator */
.filter-indicator {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1));
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-lg);
}

.filter-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.filter-text strong {
  color: var(--color-text-primary);
}

.clear-filter-btn {
  background: transparent;
  border: 1px solid var(--color-admin);
  color: var(--color-admin);
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: 500;
  transition: var(--transition-base);
}

.clear-filter-btn:hover {
  background: var(--color-admin);
  color: white;
}

/* Activity Loading/Empty States */
.activity-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.loading-spinner.small {
  width: 20px;
  height: 20px;
  border-width: 2px;
}

.activity-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* Metrics Row */
.metrics-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-xl);
  align-items: end;
}

.metrics-section {
  padding: var(--spacing-md) 0;
}

/* Activity section floats to bottom */
.activity-section {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.activity-content {
  margin-top: auto;
}

.section-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--spacing-lg);
}

.section-label.bottom-label {
  margin-bottom: 0;
  margin-top: var(--spacing-sm);
  text-align: center;
}

/* Activity Chart */
.activity-chart {
  position: relative;
  margin-bottom: var(--spacing-md);
}

/* SVG overlay for area + line */
.chart-area-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 80px;
  pointer-events: none;
  z-index: 1;
}

.chart-line {
  filter: drop-shadow(0 1px 2px rgba(99, 102, 241, 0.3));
}

.chart-bars {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 80px;
  gap: var(--spacing-sm);
  position: relative;
}

.chart-bar-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  height: 100%;
  position: relative;
}

.chart-bar {
  width: 100%;
  max-width: 20px;
  background: linear-gradient(
    to top,
    rgba(99, 102, 241, 0.4),
    rgba(139, 92, 246, 0.2)
  );
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  min-height: 4px;
  margin-top: auto;
  transition: all 0.3s ease;
  opacity: 0.6;
}

.chart-bar-container:hover .chart-bar {
  opacity: 1;
  background: linear-gradient(
    to top,
    var(--color-admin),
    var(--color-primary-gradient-end, #8b5cf6)
  );
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
}

/* Data point dots at bar tops */
.chart-point {
  position: absolute;
  left: 50%;
  transform: translate(-50%, 50%);
  width: 8px;
  height: 8px;
  background: var(--color-bg-panel);
  border: 2px solid var(--color-admin);
  border-radius: 50%;
  z-index: 2;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.chart-bar-container:hover .chart-point {
  transform: translate(-50%, 50%) scale(1.3);
  background: var(--color-admin);
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.5);
}

.chart-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-sm);
}

.activity-summary {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-align: center;
  margin-top: var(--spacing-xs);
}

/* Snapshot Card */
.snapshot-metrics {
  display: flex;
  justify-content: space-around;
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-border);
}

.snapshot-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.snapshot-value {
  font-size: var(--font-size-xxl);
  font-weight: 700;
  background: linear-gradient(135deg, var(--color-admin), var(--color-primary-gradient-end, #8b5cf6));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.snapshot-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.snapshot-distribution {
  display: flex;
  justify-content: space-around;
}

.distribution-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-base);
  transition: var(--transition-base);
}

.distribution-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.dist-count {
  font-size: var(--font-size-xl);
  font-weight: 700;
}

.distribution-item.completed .dist-count {
  color: var(--color-success);
}

.distribution-item.in-progress .dist-count {
  color: var(--color-warning);
}

.distribution-item.not-started .dist-count {
  color: var(--color-text-tertiary);
}

.dist-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

/* Snapshot Placeholder State */
.snapshot-placeholder {
  text-align: center;
}

.placeholder-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-lg);
  font-style: italic;
}

.snapshot-metrics.muted,
.snapshot-distribution.muted {
  opacity: 0.4;
}

.snapshot-value.placeholder {
  background: none;
  -webkit-background-clip: unset;
  -webkit-text-fill-color: var(--color-text-tertiary);
  background-clip: unset;
  color: var(--color-text-tertiary);
}

.muted .dist-count {
  color: var(--color-text-tertiary) !important;
}

/* Activity Placeholder State */
.activity-placeholder {
  margin-bottom: var(--spacing-md);
}

.chart-bars.muted {
  opacity: 0.3;
}

.chart-bar.placeholder-bar {
  background: var(--color-bg-border);
}

.muted-text {
  color: var(--color-text-tertiary);
  font-style: italic;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .content-container {
    padding: 0 var(--spacing-md) var(--spacing-xl);
  }

  .course-card {
    padding: var(--spacing-lg);
  }

  .course-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-lg);
  }

  .header-stats {
    width: 100%;
    justify-content: space-around;
  }

  .course-header h1 {
    font-size: var(--font-size-xl);
  }

  .metrics-row {
    grid-template-columns: 1fr;
  }

  .journey-item {
    gap: var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .journey-marker {
    width: 24px;
  }

  .marker-number {
    width: 24px;
    height: 24px;
    font-size: var(--font-size-xs);
  }

  .filter-indicator {
    flex-direction: column;
    gap: var(--spacing-sm);
    text-align: center;
  }
}
</style>
