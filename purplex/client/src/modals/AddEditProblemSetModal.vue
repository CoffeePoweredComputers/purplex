<template>
  <Teleport to="body">
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="problem-set-modal-title"
      @click.self="closeModal"
    >
      <div
        ref="modalContentRef"
        class="modal-content large-modal"
        @keydown.esc="closeModal"
      >
        <div class="modal-header">
          <h2 id="problem-set-modal-title">
            {{ editMode ? 'Edit Problem Set' : 'Add New Problem Set' }}
          </h2>
          <button
            class="modal-close"
            @click="closeModal"
          >
            &times;
          </button>
        </div>

        <div
          v-if="!loading"
          class="modal-body"
        >
          <form @submit.prevent="submitForm">
            <div class="form-section">
              <div class="form-group">
                <label for="title">Title *</label>
                <input
                  id="title"
                  v-model="formData.title"
                  type="text"
                  class="form-input"
                  placeholder="Enter problem set title"
                  required
                >
              </div>

              <div class="form-group">
                <label for="description">Description</label>
                <textarea
                  id="description"
                  v-model="formData.description"
                  class="form-input"
                  placeholder="Enter description (optional)"
                  rows="3"
                />
              </div>

              <div class="form-group">
                <label for="visibility">Visibility</label>
                <button
                  type="button"
                  class="form-input toggle-button"
                  :class="{ 'active': formData.is_public }"
                  @click="formData.is_public = !formData.is_public"
                >
                  {{ formData.is_public ? 'Public' : 'Private' }}
                </button>
              </div>
            </div>

            <div class="form-section">
              <div
                class="section-header"
                @click="showProblemSelection = !showProblemSelection"
              >
                <h3>
                  <span class="toggle-icon">{{ showProblemSelection ? '▼' : '▶' }}</span>
                  Select Problems {{ editMode ? '' : '(Optional)' }}
                </h3>
                <span class="selection-count">{{ selectedProblems.length }} selected</span>
              </div>

              <div
                v-if="showProblemSelection"
                class="problems-selection"
              >
                <!-- Filters and Bulk Actions -->
                <div class="problems-controls">
                  <div class="filter-row">
                    <input
                      v-model="searchQuery"
                      type="text"
                      placeholder="Search problems..."
                      class="form-input search-input"
                    >
                    <select
                      v-model="difficultyFilter"
                      class="form-input filter-select"
                    >
                      <option value="">
                        All Difficulties
                      </option>
                      <option value="easy">
                        Easy
                      </option>
                      <option value="beginner">
                        Beginner
                      </option>
                      <option value="intermediate">
                        Intermediate
                      </option>
                      <option value="advanced">
                        Advanced
                      </option>
                    </select>
                    <select
                      v-model="typeFilter"
                      class="form-input filter-select"
                    >
                      <option value="">
                        All Types
                      </option>
                      <option value="eipl">
                        EiPL
                      </option>
                    </select>
                  </div>
                  <div class="bulk-actions">
                    <button
                      type="button"
                      class="bulk-btn"
                      @click="selectAll"
                    >
                      Select All
                    </button>
                    <button
                      type="button"
                      class="bulk-btn"
                      @click="selectNone"
                    >
                      Select None
                    </button>
                    <button
                      type="button"
                      class="bulk-btn"
                      @click="selectByDifficulty('beginner')"
                    >
                      All Beginner
                    </button>
                  </div>
                </div>


                <!-- Available Problems Table -->
                <div class="available-problems">
                  <h4>Available Problems ({{ filteredProblems.length }})</h4>
                  <div class="problems-table-container">
                    <table class="problems-table">
                      <thead>
                        <tr>
                          <th
                            class="col-title sortable"
                            @click="sortBy('title')"
                          >
                            Title
                            <span
                              v-if="sortField === 'title'"
                              class="sort-indicator"
                            >
                              {{ sortDirection === 'asc' ? '↑' : '↓' }}
                            </span>
                          </th>
                          <th
                            class="col-difficulty sortable"
                            @click="sortBy('difficulty')"
                          >
                            Difficulty
                            <span
                              v-if="sortField === 'difficulty'"
                              class="sort-indicator"
                            >
                              {{ sortDirection === 'asc' ? '↑' : '↓' }}
                            </span>
                          </th>
                          <th class="col-type">
                            Type
                          </th>
                          <th class="col-tests">
                            Tests
                          </th>
                          <th class="col-action">
                            Add/Remove
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          v-for="problem in paginatedProblems"
                          :key="problem.slug"
                          class="problem-row"
                          :class="{ selected: isSelected(problem.slug) }"
                        >
                          <td class="problem-title-cell">
                            <div class="problem-title">
                              {{ problem.title }}
                            </div>
                            <div
                              v-if="problem.description"
                              class="problem-description"
                            >
                              {{ truncateText(problem.description, 60) }}
                            </div>
                          </td>
                          <td>
                            <span
                              class="badge"
                              :class="difficultyClass(problem.difficulty)"
                            >
                              {{ problem.difficulty }}
                            </span>
                          </td>
                          <td>
                            <span class="type-badge">{{ getProblemTypeLabel(problem.problem_type) }}</span>
                          </td>
                          <td>
                            <span class="test-count">{{ problem.test_cases_count || 0 }}</span>
                          </td>
                          <td>
                            <button
                              type="button"
                              class="action-btn"
                              :class="{ 'remove-btn': isSelected(problem.slug), 'add-btn': !isSelected(problem.slug) }"
                              @click="toggleProblem(problem.slug)"
                            >
                              {{ isSelected(problem.slug) ? '−' : '+' }}
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <!-- Pagination -->
                  <div
                    v-if="totalPages > 1"
                    class="pagination"
                  >
                    <button
                      type="button"
                      :disabled="currentPage === 1"
                      class="page-btn"
                      @click="currentPage = Math.max(1, currentPage - 1)"
                    >
                      Previous
                    </button>
                    <span class="page-info">{{ currentPage }} of {{ totalPages }}</span>
                    <button
                      type="button"
                      :disabled="currentPage === totalPages"
                      class="page-btn"
                      @click="currentPage = Math.min(totalPages, currentPage + 1)"
                    >
                      Next
                    </button>
                  </div>
                </div>

                <!-- Selected Problems with Ordering -->
                <div
                  v-if="selectedProblems.length > 0"
                  class="selected-problems"
                >
                  <h4>Selected Problems ({{ selectedProblems.length }})</h4>
                  <div class="selected-list">
                    <div
                      v-for="(problemSlug, index) in selectedProblems"
                      :key="problemSlug"
                      class="selected-item"
                      draggable="true"
                      @dragstart="dragStart(index)"
                      @dragover.prevent
                      @drop="drop(index)"
                    >
                      <div class="order-number">
                        {{ index + 1 }}
                      </div>
                      <div class="drag-handle">
                        ⋮⋮
                      </div>
                      <div class="selected-content">
                        <div class="selected-title">
                          {{ getProblemBySlug(problemSlug)?.title }}
                        </div>
                        <div class="selected-meta">
                          <span
                            class="badge"
                            :class="difficultyClass(getProblemBySlug(problemSlug)?.difficulty)"
                          >
                            {{ getProblemBySlug(problemSlug)?.difficulty }}
                          </span>
                          <span class="type-badge">{{ getProblemTypeLabel(getProblemBySlug(problemSlug)?.problem_type) }}</span>
                        </div>
                      </div>
                      <button
                        type="button"
                        class="remove-selected-btn"
                        title="Remove from selection"
                        @click="removeProblem(problemSlug)"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                </div>

                <div class="selection-summary">
                  {{ selectedProblems.length }} problem{{ selectedProblems.length !== 1 ? 's' : '' }} selected
                  <span
                    v-if="selectedProblems.length > 0"
                    class="summary-meta"
                  >
                    • {{ getSelectedDifficultyBreakdown() }}
                  </span>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button
                type="button"
                class="action-button cancel-button"
                @click="closeModal"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="action-button save-button"
                :disabled="isSubmitting || !formData.title.trim()"
              >
                {{ isSubmitting ? (editMode ? 'Saving...' : 'Creating...') : (editMode ? 'Save Changes' : 'Create Problem Set') }}
              </button>
            </div>
          </form>
        </div>
        <div
          v-else
          class="loading-state"
        >
          Loading problem set details...
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { computed, onMounted, ref, toRef } from 'vue';
import axios from 'axios';
import { log } from '@/utils/logger';
import { useFocusTrap } from '@/composables/useFocusTrap';

export default {
  name: 'AddEditProblemSetModal',
  props: {
    editMode: {
      type: Boolean,
      default: false
    },
    problemSetData: {
      type: Object,
      default: null
    },
    problems: {
      type: Array,
      default: () => []
    },
    isVisible: {
      type: Boolean,
      default: true
    }
  },
  emits: ['close', 'problem-set-added', 'problem-set-updated', 'error'],
  setup(props, { emit }) {
    // Focus trap composable
    const { modalContentRef } = useFocusTrap(toRef(() => props.isVisible));
    const formData = ref({
      title: '',
      description: '',
      is_public: true
    });

    const selectedProblems = ref([]);
    const searchQuery = ref('');
    const difficultyFilter = ref('');
    const typeFilter = ref('');
    const sortField = ref('title');
    const sortDirection = ref('asc');
    const currentPage = ref(1);
    const itemsPerPage = ref(10);
    const isSubmitting = ref(false);
    const showProblemSelection = ref(false);
    const loading = ref(false);
    const draggedIndex = ref(null);

    const filteredProblems = computed(() => {
      let filtered = [...props.problems];

      // Apply search filter
      if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase();
        filtered = filtered.filter(problem =>
          problem.title.toLowerCase().includes(query) ||
          problem.difficulty.toLowerCase().includes(query) ||
          problem.problem_type.toLowerCase().includes(query) ||
          (problem.description && problem.description.toLowerCase().includes(query))
        );
      }

      // Apply difficulty filter
      if (difficultyFilter.value) {
        filtered = filtered.filter(problem =>
          problem.difficulty.toLowerCase() === difficultyFilter.value.toLowerCase()
        );
      }

      // Apply type filter
      if (typeFilter.value) {
        filtered = filtered.filter(problem =>
          problem.problem_type === typeFilter.value
        );
      }

      // Apply sorting
      filtered.sort((a, b) => {
        let aValue = a[sortField.value] || '';
        let bValue = b[sortField.value] || '';

        if (typeof aValue === 'string') {
          aValue = aValue.toLowerCase();
          bValue = bValue.toLowerCase();
        }

        let comparison = 0;
        if (aValue < bValue) {comparison = -1;}
        if (aValue > bValue) {comparison = 1;}

        return sortDirection.value === 'asc' ? comparison : -comparison;
      });

      return filtered;
    });

    const paginatedProblems = computed(() => {
      const start = (currentPage.value - 1) * itemsPerPage.value;
      const end = start + itemsPerPage.value;
      return filteredProblems.value.slice(start, end);
    });

    const totalPages = computed(() => {
      return Math.ceil(filteredProblems.value.length / itemsPerPage.value);
    });

    const closeModal = () => {
      emit('close');
    };

    const isSelected = (problemSlug) => {
      return selectedProblems.value.includes(problemSlug);
    };

    const toggleProblem = (problemSlug) => {
      const index = selectedProblems.value.indexOf(problemSlug);
      if (index > -1) {
        selectedProblems.value.splice(index, 1);
      } else {
        selectedProblems.value.push(problemSlug);
      }
    };


    const difficultyClass = (difficulty) => {
      switch(difficulty.toLowerCase()) {
        case 'easy':
        case 'beginner':
          return 'easy-badge';
        case 'medium':
        case 'intermediate':
          return 'medium-badge';
        case 'hard':
        case 'advanced':
          return 'hard-badge';
        default:
          return 'default-badge';
      }
    };

    const getProblemTypeLabel = (type) => {
      switch(type) {
        case 'eipl':
          return 'EiPL';
        default:
          return type || 'Unknown';
      }
    };

    // New methods for enhanced functionality
    const sortBy = (field) => {
      if (sortField.value === field) {
        sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
      } else {
        sortField.value = field;
        sortDirection.value = 'asc';
      }
      currentPage.value = 1; // Reset to first page
    };

    const selectAll = () => {
      const problemsToAdd = filteredProblems.value
        .filter(problem => !isSelected(problem.slug))
        .map(problem => problem.slug);
      selectedProblems.value = [...selectedProblems.value, ...problemsToAdd];
    };

    const selectNone = () => {
      selectedProblems.value = [];
    };

    const selectByDifficulty = (difficulty) => {
      const problemsToAdd = filteredProblems.value
        .filter(problem =>
          problem.difficulty.toLowerCase() === difficulty.toLowerCase() &&
          !isSelected(problem.slug)
        )
        .map(problem => problem.slug);
      selectedProblems.value = [...selectedProblems.value, ...problemsToAdd];
    };

    const getProblemBySlug = (slug) => {
      return props.problems.find(problem => problem.slug === slug);
    };

    const removeProblem = (problemSlug) => {
      const index = selectedProblems.value.indexOf(problemSlug);
      if (index > -1) {
        selectedProblems.value.splice(index, 1);
      }
    };

    const truncateText = (text, maxLength) => {
      if (!text) {return '';}
      return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    };

    const getSelectedDifficultyBreakdown = () => {
      const breakdown = {};
      selectedProblems.value.forEach(slug => {
        const problem = getProblemBySlug(slug);
        if (problem) {
          const difficulty = problem.difficulty;
          breakdown[difficulty] = (breakdown[difficulty] || 0) + 1;
        }
      });

      return Object.entries(breakdown)
        .map(([difficulty, count]) => `${count} ${difficulty}`)
        .join(', ');
    };

    // Drag and drop functionality
    const dragStart = (index) => {
      draggedIndex.value = index;
    };

    const drop = (targetIndex) => {
      if (draggedIndex.value === null || draggedIndex.value === targetIndex) {return;}

      const item = selectedProblems.value[draggedIndex.value];
      selectedProblems.value.splice(draggedIndex.value, 1);
      selectedProblems.value.splice(targetIndex, 0, item);

      draggedIndex.value = null;
    };

    const submitForm = async () => {
      if (isSubmitting.value || !formData.value.title.trim()) {return;}

      try {
        isSubmitting.value = true;

        if (props.editMode) {
          // Edit mode - use FormData for potential file uploads
          const data = new FormData();
          data.append('title', formData.value.title);
          data.append('description', formData.value.description || '');
          data.append('problem_slugs', JSON.stringify(selectedProblems.value));
          data.append('is_public', formData.value.is_public ? 'true' : 'false');

          const response = await axios.put(
            `/api/admin/problem-sets/${props.problemSetData.slug}/`,
            data,
            {
              headers: {
                'Content-Type': 'multipart/form-data'
              }
            }
          );

          emit('problem-set-updated', response.data);
        } else {
          // Add mode - use JSON
          const payload = {
            ...formData.value,
            problem_slugs: selectedProblems.value
          };

          log.debug('Sending create request with payload', { payload });
          const response = await axios.post('/api/admin/problem-sets/', payload);

          emit('problem-set-added', response.data);
        }

        closeModal();
      } catch (error) {
        log.error('Error saving problem set', { error, response: error.response });
        const errorMessage = error.response?.data?.detail ||
                           error.response?.data?.error ||
                           error.response?.data?.message ||
                           error.message ||
                           `Failed to ${props.editMode ? 'update' : 'create'} problem set. Please try again.`;
        emit('error', errorMessage);
      } finally {
        isSubmitting.value = false;
      }
    };

    // Load problem set data in edit mode
    const loadProblemSetData = async () => {
      if (!props.editMode || !props.problemSetData) {return;}

      try {
        loading.value = true;
        const response = await axios.get(`/api/admin/problem-sets/${props.problemSetData.slug}/`);
        const problemSet = response.data;

        // Populate form data
        formData.value = {
          title: problemSet.title,
          description: problemSet.description || '',
          is_public: problemSet.is_public
        };

        // Extract problem slugs from the problems_detail array
        selectedProblems.value = problemSet.problems_detail ?
          problemSet.problems_detail.map(pd => pd.problem.slug) : [];

        // Open problem selection if there are problems
        if (selectedProblems.value.length > 0) {
          showProblemSelection.value = true;
        }
      } catch (error) {
        log.error('Error loading problem set', { slug: props.problemSetData?.slug, error });
        emit('error', 'Failed to load problem set details');
        closeModal();
      } finally {
        loading.value = false;
      }
    };

    onMounted(() => {
      if (props.editMode) {
        loadProblemSetData();
      }
    });

    return {
      modalContentRef,
      formData,
      selectedProblems,
      searchQuery,
      difficultyFilter,
      typeFilter,
      sortField,
      sortDirection,
      currentPage,
      itemsPerPage,
      isSubmitting,
      showProblemSelection,
      loading,
      draggedIndex,
      filteredProblems,
      paginatedProblems,
      totalPages,
      closeModal,
      isSelected,
      toggleProblem,
      difficultyClass,
      getProblemTypeLabel,
      sortBy,
      selectAll,
      selectNone,
      selectByDifficulty,
      getProblemBySlug,
      removeProblem,
      truncateText,
      getSelectedDifficultyBreakdown,
      dragStart,
      drop,
      submitForm
    };
  }
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  border: 2px solid var(--color-bg-input);
  display: flex;
  flex-direction: column;
}

.modal-content.large-modal {
  max-width: 1100px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xl);
  border-bottom: 2px solid var(--color-bg-input);
}

.modal-header h2 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-base);
  transition: var(--transition-base);
}

.modal-close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.modal-body {
  padding: var(--spacing-xl);
  overflow-y: auto;
  flex: 1;
}

.loading-state {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-muted);
}

.form-section {
  margin-bottom: var(--spacing-xl);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  cursor: pointer;
  user-select: none;
  transition: var(--transition-base);
}

.section-header:hover {
  background: var(--color-bg-input);
}

.section-header h3 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.toggle-icon {
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
}

.selection-count {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.form-input {
  width: 100%;
  padding: var(--spacing-md);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-base);
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

.form-input::placeholder {
  color: var(--color-text-muted);
}

textarea.form-input {
  resize: vertical;
  min-height: 80px;
}

.toggle-button {
  cursor: pointer;
  text-align: left;
  font-weight: 500;
}

.toggle-button.active {
  background: var(--color-success-bg);
  color: var(--color-success);
  border-color: var(--color-success);
}

.problems-selection {
  margin-top: var(--spacing-md);
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
}

/* Enhanced Controls */
.problems-controls {
  margin-bottom: var(--spacing-lg);
}

.filter-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.filter-select {
  background: var(--color-bg-panel);
  font-size: var(--font-size-sm);
}

.search-input {
  background: var(--color-bg-panel);
}

.bulk-actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.bulk-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-base);
}

.bulk-btn:hover {
  background: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
}

.bulk-btn:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}



/* Available Problems Section */
.available-problems {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
}

.available-problems h4 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
}

.problems-table-container {
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-panel);
  max-height: 350px;
  overflow: auto; /* Changed from overflow-y to handle horizontal overflow */
  width: 100%;
}

.problems-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed; /* Critical: Fixed table layout for predictable column sizing */
  min-width: 500px; /* Minimum width to prevent cramping */
}

.problems-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-md);
  font-weight: 600;
  font-size: var(--font-size-sm);
  text-align: left;
  border-bottom: 2px solid var(--color-bg-input);
  position: sticky;
  top: 0;
  z-index: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Column Width Definitions */
.col-title {
  width: 50%;
  max-width: 50%;
  min-width: 200px;
}

.col-difficulty {
  width: 15%;
  max-width: 15%;
  min-width: 80px;
}

.col-type {
  width: 12%;
  max-width: 12%;
  min-width: 60px;
}

.col-tests {
  width: 10%;
  max-width: 10%;
  min-width: 50px;
}

.col-action {
  width: 100px;
  max-width: 100px;
  min-width: 100px;
}

.problems-table th.sortable {
  cursor: pointer;
  user-select: none;
  position: relative;
}

.problems-table th.sortable:hover {
  background: var(--color-bg-input);
}

.problems-table th.sortable:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: -2px;
}

.sort-indicator {
  margin-left: var(--spacing-xs);
  font-size: var(--font-size-xs);
  opacity: 0.7;
}

.problems-table td {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--color-bg-hover);
  vertical-align: middle;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.problem-row {
  transition: var(--transition-base);
}

.problem-row:hover {
  background: var(--color-bg-hover);
}

.problem-row.selected {
  background: rgba(99, 102, 241, 0.1);
}

.problem-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  flex-shrink: 0;
}

.problem-title-cell {
  overflow: hidden;
  padding-right: var(--spacing-sm);
  white-space: normal; /* Override table cell white-space for title column */
  max-height: 3.5em; /* Limit to ~2 lines */
}

.problem-title {
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2; /* Limit to 2 lines */
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}

.problem-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: var(--spacing-xs);
}

.type-badge {
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-info-bg);
  color: var(--color-info);
  border-radius: var(--radius-base);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.test-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.action-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-lg);
  font-weight: bold;
  cursor: pointer;
  transition: var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-btn {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.add-btn:hover {
  background: var(--color-success);
  color: var(--color-text-primary);
}

.remove-btn {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.remove-btn:hover {
  background: var(--color-error);
  color: var(--color-text-primary);
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--spacing-md);
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
}

.page-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-base);
}

.page-btn:hover:not(:disabled) {
  background: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

/* Selected Problems Section */
.selected-problems {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
  min-width: 0; /* Prevent overflow */
  overflow: hidden;
  /* Dynamic height with smart constraints */
  min-height: 120px; /* Minimum space for 1-2 items */
  max-height: min(50vh, 480px); /* Responsive to viewport, capped at reasonable size */
  margin-bottom: var(--spacing-xl);
}

.selected-problems h4 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
}

.selected-list {
  /* Allow natural growth up to container limits */
  max-height: calc(100% - 60px); /* Account for header space */
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  /* Smooth scrolling for better UX */
  scroll-behavior: smooth;
  /* Custom scrollbar styling */
  scrollbar-width: thin;
  scrollbar-color: var(--color-bg-input) transparent;
}

/* Webkit scrollbar styling for better cross-browser support */
.selected-list::-webkit-scrollbar {
  width: 6px;
}

.selected-list::-webkit-scrollbar-track {
  background: transparent;
}

.selected-list::-webkit-scrollbar-thumb {
  background: var(--color-bg-input);
  border-radius: var(--radius-base);
}

.selected-list::-webkit-scrollbar-thumb:hover {
  background: var(--color-bg-border);
}

.selected-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  cursor: move;
  transition: var(--transition-base);
  min-height: 64px;
  width: 100%;
}

.selected-item:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
}


.drag-handle {
  color: var(--color-text-secondary);
  cursor: grab;
  font-size: var(--font-size-base);
  user-select: none;
  padding: var(--spacing-sm);
  border-radius: var(--radius-base);
  transition: var(--transition-base);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(var(--color-text-muted), 0.1);
  border: 1px solid rgba(var(--color-text-muted), 0.2);
}

.drag-handle:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
  transform: scale(1.05);
}

.drag-handle:active {
  cursor: grabbing;
  background: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  transform: scale(0.95);
}

.selected-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 0; /* Allow flex children to shrink */
  overflow: hidden;
}

.selected-title {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.selected-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.order-number {
  background: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  padding: var(--spacing-xs);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: 700;
  min-width: 24px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.remove-selected-btn {
  width: 18px;
  height: 18px;
  border: none;
  border-radius: var(--radius-base);
  background: var(--color-error-bg);
  color: var(--color-error);
  font-size: var(--font-size-sm);
  font-weight: bold;
  cursor: pointer;
  transition: var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.remove-selected-btn:hover {
  background: var(--color-error);
  color: var(--color-text-primary);
}

/* Selection Summary */
.selection-summary {
  margin-top: var(--spacing-lg);
  text-align: center;
  color: var(--color-text-secondary);
  font-style: italic;
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-bg-input);
}

.summary-meta {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.badge {
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xl);
  font-weight: 600;
  font-size: var(--font-size-xs);
  display: inline-block;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.easy-badge {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.medium-badge {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.hard-badge {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.default-badge {
  background: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}


.modal-footer {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  padding: var(--spacing-xl);
  border-top: 2px solid var(--color-bg-input);
}

.action-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-xl);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-base);
  white-space: nowrap;
}

.action-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.save-button {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.save-button:hover:not(:disabled) {
  background: var(--color-success);
  color: var(--color-text-primary);
}

.cancel-button {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.cancel-button:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

/* Responsive Design */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: var(--spacing-md);
  }

  .modal-footer {
    flex-direction: column;
  }

  .action-button {
    width: 100%;
    justify-content: center;
  }

  /* Mobile adaptations for new features */
  .filter-row {
    grid-template-columns: 1fr;
    gap: var(--spacing-sm);
  }

  .bulk-actions {
    justify-content: center;
    flex-wrap: wrap;
  }

  .bulk-btn {
    font-size: var(--font-size-xs);
    padding: var(--spacing-xs) var(--spacing-sm);
  }

  .available-problems {
    width: 100%;
  }


  .available-problems,
  .selected-problems {
    min-width: 0;
    overflow: hidden;
  }

  .problems-table-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .problems-table {
    min-width: 550px;
    font-size: var(--font-size-sm);
  }

  .problems-table th,
  .problems-table td {
    padding: var(--spacing-sm);
  }

  /* Adjust column widths for mobile */
  .col-title {
    min-width: 200px;
  }

  .col-difficulty {
    min-width: 70px;
  }

  .col-type {
    min-width: 50px;
  }

  .col-tests {
    min-width: 40px;
  }

  .col-action {
    min-width: 60px;
  }

  .problem-title-cell {
    max-height: 2.5em;
  }

  .problem-title {
    font-size: var(--font-size-sm);
    -webkit-line-clamp: 1; /* Reduce to 1 line on mobile */
  }

  .problem-description {
    display: none; /* Hide descriptions on mobile to save space */
  }

  .selected-problems {
    max-height: 250px;
  }

  .selected-item {
    padding: var(--spacing-sm);
    min-height: 56px;
    gap: var(--spacing-sm);
  }

  .order-number {
    width: 32px;
    height: 32px;
    min-width: 32px;
    font-size: var(--font-size-sm);
  }

  .selected-title {
    font-size: var(--font-size-sm);
  }

  .remove-selected-btn {
    width: 28px;
    height: 28px;
  }

  .drag-handle {
    display: none; /* Hide drag handles on mobile */
  }

  .selected-info {
    gap: var(--spacing-sm);
  }

  .selected-title {
    font-size: var(--font-size-xs);
  }

  .order-number {
    font-size: var(--font-size-xs);
    min-width: 18px;
    padding: 2px var(--spacing-xs);
  }

  .remove-selected-btn {
    width: 20px;
    height: 20px;
    font-size: var(--font-size-sm);
  }

  /* Improve pagination on mobile */
  .pagination {
    padding: var(--spacing-sm);
    gap: var(--spacing-sm);
  }

  .page-btn {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: var(--font-size-xs);
  }

  /* Fix spacing for mobile */
  .problems-controls {
    margin-bottom: var(--spacing-md);
  }

  .selection-summary {
    padding: var(--spacing-sm);
    font-size: var(--font-size-sm);
  }

  .summary-meta {
    display: block;
    margin-top: var(--spacing-xs);
  }
}
</style>
