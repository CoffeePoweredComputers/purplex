<template>
  <ContentEditorLayout
    :show-breadcrumb="false"
    :show-header="false"
  >
    <!-- Current Problem Sets Section -->
    <div class="section">
      <div class="section-header">
        <h3>{{ $t('admin.courseProblemSets.currentProblemSets') }}</h3>
        <span class="count-badge">{{ currentProblemSets.length }}</span>
      </div>

      <div
        v-if="loading.current"
        class="loading-container"
      >
        <div class="loading-spinner" />
        <p>{{ $t('admin.courseProblemSets.loading') }}</p>
      </div>

      <div
        v-else-if="currentProblemSets.length === 0"
        class="empty-state"
      >
        <p>{{ $t('admin.courseProblemSets.noProblemSets') }}</p>
      </div>

      <div
        v-else
        class="table-responsive"
      >
        <table class="problem-sets-table">
          <thead>
            <tr>
              <th>{{ $t('admin.courseProblemSets.columnOrder') }}</th>
              <th>{{ $t('admin.courseProblemSets.columnProblemSet') }}</th>
              <th class="center">
                {{ $t('admin.courseProblemSets.columnProblems') }}
              </th>
              <th class="center">
                {{ $t('admin.courseProblemSets.columnRequired') }}
              </th>
              <th>{{ $t('admin.courseProblemSets.columnDueDate') }}</th>
              <th>{{ $t('admin.courseProblemSets.columnDeadline') }}</th>
              <th>{{ $t('admin.courseProblemSets.columnActions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, index) in currentProblemSets"
              :key="item.id"
            >
              <td class="order-cell">
                <div class="order-controls">
                  <button
                    :disabled="index === 0"
                    class="order-btn"
                    :title="$t('admin.courseProblemSets.moveUp')"
                    @click="moveUp(index)"
                  >
                    &#x2191;
                  </button>
                  <span class="order-number">{{ item.order + 1 }}</span>
                  <button
                    :disabled="index === currentProblemSets.length - 1"
                    class="order-btn"
                    :title="$t('admin.courseProblemSets.moveDown')"
                    @click="moveDown(index)"
                  >
                    &#x2193;
                  </button>
                </div>
              </td>
              <td>{{ item.problem_set.title }}</td>
              <td class="center">
                {{ item.problem_set.problems_count }}
              </td>
              <td class="center">
                <input
                  v-model="item.is_required"
                  type="checkbox"
                  class="required-checkbox"
                  @change="updateRequired(item)"
                >
              </td>
              <td class="due-date-cell">
                <input
                  :ref="(el) => setDateInputRef(item.id, el)"
                  type="datetime-local"
                  class="due-date-input"
                  @blur="saveDueDate(item)"
                  @keydown.enter="($event.target as HTMLInputElement).blur()"
                >
                <button
                  v-if="item.due_date"
                  class="clear-date-btn"
                  :title="$t('admin.courseProblemSets.clearDueDate')"
                  @click="clearDueDate(item)"
                >
                  ✕
                </button>
              </td>
              <td class="deadline-cell">
                <select
                  v-model="item.deadline_type"
                  class="deadline-select"
                  :disabled="!item.due_date"
                  :title="!item.due_date ? $t('admin.courseProblemSets.setDueDateFirst') : ''"
                  @change="updateDeadlineType(item)"
                >
                  <option value="none">
                    {{ $t('admin.courseProblemSets.none') }}
                  </option>
                  <option value="soft">
                    {{ $t('admin.courseProblemSets.soft') }}
                  </option>
                  <option value="hard">
                    {{ $t('admin.courseProblemSets.hard') }}
                  </option>
                </select>
              </td>
              <td>
                <button
                  class="action-button remove-button"
                  :title="$t('admin.courseProblemSets.removeFromCourse')"
                  @click="confirmRemove(item)"
                >
                  {{ $t('common.remove') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <hr class="divider">

    <!-- Available Problem Sets Section -->
    <div class="section">
      <div class="section-header">
        <h3>{{ $t('admin.courseProblemSets.addProblemSets') }}</h3>
        <span class="count-badge">{{ $t('admin.courseProblemSets.available', { count: availableProblemSets.length }) }}</span>
      </div>

      <div
        v-if="loading.available"
        class="loading-container"
      >
        <div class="loading-spinner" />
        <p>{{ $t('admin.courseProblemSets.loadingAvailable') }}</p>
      </div>

      <div
        v-else-if="availableProblemSets.length === 0"
        class="empty-state"
      >
        <p>{{ $t('admin.courseProblemSets.allAdded') }}</p>
      </div>

      <div
        v-else
        class="available-grid"
      >
        <div
          v-for="ps in availableProblemSets"
          :key="ps.slug"
          class="available-item"
        >
          <div class="item-info">
            <h4>{{ ps.title }}</h4>
            <p class="description">
              {{ ps.description || $t('admin.courseProblemSets.noDescription') }}
            </p>
            <span class="problems-count">{{ $t('admin.courseProblemSets.problemsCount', { count: ps.problems_count || 0 }) }}</span>
          </div>
          <button
            class="action-button add-button"
            :disabled="loading.adding"
            @click="addProblemSet(ps)"
          >
            {{ $t('common.add') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Remove Confirmation Dialog -->
    <div
      v-if="showRemoveDialog"
      class="dialog-overlay"
    >
      <div class="dialog">
        <h3>{{ $t('admin.courseProblemSets.removeProblemSet') }}</h3>
        <p>
          {{ $t('admin.courseProblemSets.removeConfirmMessage', { title: removeTarget?.problem_set.title }) }}
        </p>
        <div class="dialog-actions">
          <button
            class="btn btn-secondary"
            @click="showRemoveDialog = false"
          >
            {{ $t('common.cancel') }}
          </button>
          <button
            class="btn btn-danger"
            :disabled="removing"
            @click="performRemove"
          >
            {{ removing ? $t('admin.courseProblemSets.removing') : $t('common.remove') }}
          </button>
        </div>
      </div>
    </div>
  </ContentEditorLayout>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import ContentEditorLayout from './ContentEditorLayout.vue';
import { provideContentContext } from '@/composables/useContentContext';
import { log } from '@/utils/logger';
import type { Course, CourseProblemSet, ProblemSet } from '@/types';

// Router
const route = useRoute();
const { t } = useI18n();

// Provide role-aware context
const ctx = provideContentContext();

// State
const course = ref<Course | null>(null);
const currentProblemSets = ref<CourseProblemSet[]>([]);
const availableProblemSets = ref<ProblemSet[]>([]);
const loading = reactive({
  current: true,
  available: true,
  adding: false
});
const removing = ref(false);
const showRemoveDialog = ref(false);
const removeTarget = ref<CourseProblemSet | null>(null);

// Due date input refs - store references to each input by item ID
const dateInputRefs = new Map<number, HTMLInputElement>();

function setDateInputRef(itemId: number, el: unknown): void {
  if (el instanceof HTMLInputElement) {
    dateInputRefs.set(itemId, el);
  }
}

// Computed
const courseId = computed(() => route.params.courseId as string);
const _pageTitle = computed(() => {
  if (course.value) {
    return t('admin.courseProblemSets.problemSetsDash', { name: course.value.name });
  }
  return t('admin.courseProblemSets.title');
});

// Fetch data
async function fetchCourse(): Promise<void> {
  try {
    course.value = await ctx.api.value.getCourse(courseId.value);
  } catch (err) {
    log.error('Failed to load course', { courseId: courseId.value, error: err });
  }
}

async function fetchCurrentProblemSets(): Promise<void> {
  loading.current = true;
  try {
    currentProblemSets.value = await ctx.api.value.getCourseProblemSets(courseId.value);
    // Initialize date inputs after data loads and DOM updates
    initializeDateInputs();
  } catch (err) {
    log.error('Failed to load current problem sets', { error: err });
  } finally {
    loading.current = false;
  }
}

async function fetchAvailableProblemSets(): Promise<void> {
  loading.available = true;
  try {
    availableProblemSets.value = await ctx.api.value.getAvailableProblemSetsForCourse(courseId.value);
  } catch (err) {
    log.error('Failed to load available problem sets', { error: err });
  } finally {
    loading.available = false;
  }
}

// Add problem set
async function addProblemSet(problemSet: ProblemSet): Promise<void> {
  loading.adding = true;
  try {
    const newItem = await ctx.api.value.addCourseProblemSet(courseId.value, {
      problem_set_slug: problemSet.slug,
      is_required: false
    });

    // Add to current list
    currentProblemSets.value.push(newItem);

    // Remove from available list
    availableProblemSets.value = availableProblemSets.value.filter(ps => ps.slug !== problemSet.slug);
  } catch (err) {
    log.error('Failed to add problem set', { error: err });
  } finally {
    loading.adding = false;
  }
}

// Update required status
async function updateRequired(item: CourseProblemSet): Promise<void> {
  try {
    await ctx.api.value.updateCourseProblemSet(courseId.value, item.id, {
      is_required: item.is_required
    });
  } catch (err) {
    // Revert on error
    item.is_required = !item.is_required;
    log.error('Failed to update required status', { error: err });
  }
}

// Update deadline type
async function updateDeadlineType(item: CourseProblemSet): Promise<void> {
  const previousType = item.deadline_type;
  try {
    await ctx.api.value.updateCourseProblemSet(courseId.value, item.id, {
      deadline_type: item.deadline_type
    });
    log.info('Updated deadline type', { problemSet: item.problem_set.slug, deadlineType: item.deadline_type });
  } catch (err) {
    // Revert on error
    item.deadline_type = previousType;
    log.error('Failed to update deadline type', { error: err });
  }
}

// Remove handlers
function confirmRemove(item: CourseProblemSet): void {
  removeTarget.value = item;
  showRemoveDialog.value = true;
}

async function performRemove(): Promise<void> {
  if (!removeTarget.value) {
    return;
  }

  removing.value = true;
  log.debug('[performRemove] Removing:', courseId.value, removeTarget.value.id);
  try {
    await ctx.api.value.removeCourseProblemSet(courseId.value, removeTarget.value.id);
    log.debug('[performRemove] Success!');

    // Move to available list
    const removedItem = removeTarget.value;
    availableProblemSets.value.push({
      slug: removedItem.problem_set.slug,
      title: removedItem.problem_set.title,
      problems_count: removedItem.problem_set.problems_count,
      is_public: true, // Default
    } as ProblemSet);
    availableProblemSets.value.sort((a, b) => a.title.localeCompare(b.title));

    // Remove from current list
    currentProblemSets.value = currentProblemSets.value.filter(ps => ps.id !== removeTarget.value!.id);

    showRemoveDialog.value = false;
    removeTarget.value = null;
  } catch (err) {
    log.error('[performRemove] Error:', err);
    log.error('Failed to remove problem set', { error: err });
  } finally {
    removing.value = false;
  }
}

// Reorder functions
async function moveUp(index: number): Promise<void> {
  if (index === 0) {return;}

  const items = [...currentProblemSets.value];
  const current = items[index];
  const previous = items[index - 1];

  // Swap orders
  const tempOrder = current.order;
  current.order = previous.order;
  previous.order = tempOrder;

  // Swap in array
  items[index] = previous;
  items[index - 1] = current;
  currentProblemSets.value = items;

  // Update on server
  try {
    await ctx.api.value.updateCourseProblemSet(courseId.value, current.id, { order: current.order });
    await ctx.api.value.updateCourseProblemSet(courseId.value, previous.id, { order: previous.order });
  } catch (err) {
    // Revert on error
    fetchCurrentProblemSets();
    log.error('Failed to reorder', { error: err });
  }
}

async function moveDown(index: number): Promise<void> {
  if (index === currentProblemSets.value.length - 1) {return;}

  const items = [...currentProblemSets.value];
  const current = items[index];
  const next = items[index + 1];

  // Swap orders
  const tempOrder = current.order;
  current.order = next.order;
  next.order = tempOrder;

  // Swap in array
  items[index] = next;
  items[index + 1] = current;
  currentProblemSets.value = items;

  // Update on server
  try {
    await ctx.api.value.updateCourseProblemSet(courseId.value, current.id, { order: current.order });
    await ctx.api.value.updateCourseProblemSet(courseId.value, next.id, { order: next.order });
  } catch (err) {
    // Revert on error
    fetchCurrentProblemSets();
    log.error('Failed to reorder', { error: err });
  }
}

// Due date helpers
function formatDateForInput(isoDate: string | null | undefined): string {
  if (!isoDate) {
    return '';
  }
  // Convert ISO to datetime-local format in LOCAL time
  const date = new Date(isoDate);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

async function initializeDateInputs(): Promise<void> {
  // Wait for DOM to update, then set initial values
  await nextTick();
  currentProblemSets.value.forEach(item => {
    const input = dateInputRefs.get(item.id);
    if (input) {
      input.value = formatDateForInput(item.due_date);
    }
  });
}

async function saveDueDate(item: CourseProblemSet): Promise<void> {
  log.debug('[saveDueDate] Called for item:', item.id);
  const input = dateInputRefs.get(item.id);
  if (!input) {
    log.debug('[saveDueDate] No input ref found for item:', item.id);
    return;
  }

  const inputValue = input.value;
  const newDate = inputValue ? new Date(inputValue).toISOString() : null;

  // Skip if unchanged
  const currentFormatted = formatDateForInput(item.due_date);
  log.debug('[saveDueDate] inputValue:', inputValue, 'currentFormatted:', currentFormatted);
  if (inputValue === currentFormatted) {
    log.debug('[saveDueDate] Skipping - unchanged');
    return;
  }

  log.debug('[saveDueDate] Saving newDate:', newDate);
  try {
    await ctx.api.value.updateCourseProblemSet(courseId.value, item.id, {
      due_date: newDate
    });
    item.due_date = newDate;
    log.debug('[saveDueDate] Success!');
    log.info('Updated due date', { problemSet: item.problem_set?.slug, dueDate: newDate });
  } catch (err) {
    log.error('[saveDueDate] Error:', err);
    log.error('Failed to update due date', { error: err });
    // Reset input to previous value
    input.value = formatDateForInput(item.due_date);
  }
}

async function clearDueDate(item: CourseProblemSet): Promise<void> {
  try {
    await ctx.api.value.updateCourseProblemSet(courseId.value, item.id, {
      due_date: null
    });
    item.due_date = null;
    // Also clear the input
    const input = dateInputRefs.get(item.id);
    if (input) {
      input.value = '';
    }
    log.info('Cleared due date', { problemSet: item.problem_set?.slug });
  } catch (err) {
    log.error('Failed to clear due date', { error: err });
  }
}

// Watch for route changes
watch(
  () => route.params.courseId,
  () => {
    if (route.params.courseId) {
      fetchCourse();
      fetchCurrentProblemSets();
      fetchAvailableProblemSets();
    }
  },
  { immediate: true }
);
</script>

<style scoped>
/* Section */
.section {
  margin-bottom: var(--spacing-xl);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.section-header h3 {
  margin: 0;
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.count-badge {
  background: var(--color-bg-hover);
  color: var(--color-text-muted);
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
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

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-muted);
  background-color: var(--color-bg-panel);
  border-radius: var(--radius-lg);
}

/* Table */
.table-responsive {
  overflow-x: auto;
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.problem-sets-table {
  width: 100%;
  border-collapse: collapse;
}

.problem-sets-table th {
  background-color: var(--color-bg-section);
  padding: var(--spacing-lg) var(--spacing-xl);
  text-align: left;
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  border-bottom: 2px solid var(--color-bg-input);
}

.problem-sets-table th.center {
  text-align: center;
}

.problem-sets-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.problem-sets-table td.center {
  text-align: center;
}

.problem-sets-table tr:hover {
  background-color: var(--color-bg-hover);
}

.problem-sets-table tr:last-child td {
  border-bottom: none;
}

/* Order Controls */
.order-cell {
  width: 120px;
}

.order-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.order-number {
  width: 28px;
  text-align: center;
  font-weight: 600;
}

.order-btn {
  padding: var(--spacing-xs) var(--spacing-sm);
  background-color: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-sm);
}

.order-btn:hover:not(:disabled) {
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.order-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.required-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

/* Due Date */
.due-date-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.due-date-input {
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  min-width: 180px;
}

.due-date-input:focus {
  border-color: var(--color-primary-gradient-start);
  outline: none;
}

.clear-date-btn {
  background: transparent;
  border: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  padding: var(--spacing-xs);
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
}

.clear-date-btn:hover {
  color: var(--color-error);
  background: var(--color-error-bg);
}

/* Deadline Type */
.deadline-cell {
  min-width: 100px;
}

.deadline-select {
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  min-width: 90px;
}

.deadline-select:focus {
  border-color: var(--color-primary-gradient-start);
  outline: none;
}

.deadline-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Divider */
.divider {
  border: none;
  border-top: 2px solid var(--color-bg-input);
  margin: var(--spacing-xl) 0;
}

/* Available Grid */
.available-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-lg);
}

.available-item {
  background-color: var(--color-bg-panel);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: var(--spacing-lg);
  transition: var(--transition-fast);
}

.available-item:hover {
  border-color: var(--color-primary-gradient-start);
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-info h4 {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.description {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--spacing-sm) 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.problems-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* Action Buttons */
.action-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-base);
  text-decoration: none;
  white-space: nowrap;
}

.secondary-button {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.secondary-button:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.add-button {
  background-color: var(--color-success);
  color: var(--color-text-on-filled);
}

.add-button:hover:not(:disabled) {
  opacity: 0.9;
}

.add-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.remove-button {
  background-color: transparent;
  border: 1px solid var(--color-bg-border);
  color: var(--color-text-muted);
  padding: var(--spacing-xs) var(--spacing-md);
}

.remove-button:hover {
  color: var(--color-error);
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

/* Dialog */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-backdrop);
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

/* Buttons */
.btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: var(--transition-base);
}

.btn-secondary {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.btn-danger {
  background: var(--color-error);
  color: var(--color-text-on-filled);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 768px) {
  .available-grid {
    grid-template-columns: 1fr;
  }

  .problem-sets-table th,
  .problem-sets-table td {
    padding: var(--spacing-md);
  }
}
</style>
