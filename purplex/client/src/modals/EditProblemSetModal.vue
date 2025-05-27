<template>
  <div class="modal-overlay" @click="closeModal">
    <div class="modal-content large-modal" @click.stop>
      <div class="modal-header">
        <h2>Edit Problem Set</h2>
        <button class="modal-close" @click="closeModal">&times;</button>
      </div>
      <div class="modal-body" v-if="problemSet">
        <form @submit.prevent="updateProblemSet">
          <div class="form-section">
            <div class="form-group">
              <label for="title">Title</label>
              <input 
                type="text" 
                id="title"
                v-model="editedProblemSet.title" 
                class="form-input"
                required
              >
            </div>
            <div class="form-group">
              <label for="description">Description</label>
              <textarea 
                id="description"
                v-model="editedProblemSet.description" 
                class="form-input"
                rows="3"
              ></textarea>
            </div>
            <div class="form-group">
              <label for="is_public">Visibility</label>
              <button 
                type="button" 
                class="form-input toggle-button"
                :class="{ 'active': problemSet.is_public }"
                @click="problemSet.is_public = !problemSet.is_public"
              >
                {{ problemSet.is_public ? 'Public' : 'Private' }}
              </button>
            </div>
          </div>

          <div class="form-section">
            <h3>Select Problems</h3>
            <div class="problems-selection">
              <div class="problems-filter">
                <input 
                  type="text" 
                  v-model="searchQuery"
                  placeholder="Search problems..."
                  class="form-input search-input"
                >
              </div>
              <div class="problems-list">
                <div 
                  v-for="problem in filteredProblems" 
                  :key="problem.slug"
                  class="problem-item"
                  :class="{ selected: isSelected(problem.slug) }"
                  @click="toggleProblem(problem.slug)"
                >
                  <div class="problem-checkbox">
                    <input 
                      type="checkbox" 
                      :checked="isSelected(problem.slug)"
                      @click.stop
                      @change="toggleProblem(problem.slug)"
                    >
                  </div>
                  <div class="problem-info">
                    <div class="problem-title">{{ problem.title }}</div>
                    <div class="problem-meta">
                      <span class="badge" :class="difficultyClass(problem.difficulty)">
                        {{ problem.difficulty }}
                      </span>
                      <span class="problem-type">{{ problem.problem_type }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="selection-summary">
                {{ selectedProblems.length }} problem{{ selectedProblems.length !== 1 ? 's' : '' }} selected
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" class="action-button cancel-button" @click="closeModal">
              Cancel
            </button>
            <button 
              type="submit" 
              class="action-button save-button"
              :disabled="isSubmitting || !editedProblemSet.title.trim()"
            >
              {{ isSubmitting ? 'Saving...' : 'Save Changes' }}
            </button>
          </div>
        </form>
      </div>
      <div class="loading-state" v-else>
        Loading problem set details...
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'EditProblemSetModal',
  props: {
    problemSetSlug: {
      type: String,
      required: true
    },
    problems: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      problemSet: null,
      editedProblemSet: {
        title: '',
        description: ''
      },
      selectedProblems: [],
      searchQuery: '',
      isSubmitting: false,
      loading: true
    };
  },
  computed: {
    filteredProblems() {
      if (!this.searchQuery) {
        return this.problems;
      }
      const query = this.searchQuery.toLowerCase();
      return this.problems.filter(problem => 
        problem.title.toLowerCase().includes(query) ||
        problem.difficulty.toLowerCase().includes(query) ||
        problem.problem_type.toLowerCase().includes(query)
      );
    }
  },
  async mounted() {
    await this.fetchProblemSet();
    // Add ESC key listener
    document.addEventListener('keydown', this.handleEscape);
  },
  beforeUnmount() {
    // Remove ESC key listener
    document.removeEventListener('keydown', this.handleEscape);
  },
  methods: {
    async fetchProblemSet() {
      try {
        this.loading = true;
        const response = await axios.get(`/api/admin/problem-sets/${this.problemSetSlug}/`);
        this.problemSet = response.data;
        this.editedProblemSet = {
          title: this.problemSet.title,
          description: this.problemSet.description
        };
        // Extract problem slugs from the problems_detail array
        this.selectedProblems = this.problemSet.problems_detail.map(pd => pd.problem.slug);
        this.loading = false;
      } catch (error) {
        console.error('Error fetching problem set:', error);
        this.$emit('error', 'Failed to load problem set details');
        this.closeModal();
      }
    },

    closeModal() {
      this.$emit('close');
    },

    isSelected(problemSlug) {
      return this.selectedProblems.includes(problemSlug);
    },

    toggleProblem(problemSlug) {
      const index = this.selectedProblems.indexOf(problemSlug);
      if (index > -1) {
        this.selectedProblems.splice(index, 1);
      } else {
        this.selectedProblems.push(problemSlug);
      }
    },

    difficultyClass(difficulty) {
      switch(difficulty.toLowerCase()) {
        case 'easy':
          return 'easy-badge';
        case 'medium':
          return 'medium-badge';
        case 'hard':
          return 'hard-badge';
        default:
          return 'default-badge';
      }
    },

    async updateProblemSet() {
      if (this.isSubmitting || !this.editedProblemSet.title.trim()) return;
      
      try {
        this.isSubmitting = true;
        
        const formData = new FormData();
        formData.append('title', this.editedProblemSet.title);
        formData.append('description', this.editedProblemSet.description || '');
        formData.append('problem_slugs', JSON.stringify(this.selectedProblems));
        formData.append('is_public', this.problemSet.is_public ? 'true' : 'false');
        
        const response = await axios.put(`/api/admin/problem-sets/${this.problemSetSlug}/`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        
        this.$emit('problem-set-updated', response.data);
        this.closeModal();
      } catch (error) {
        const errorMessage = error.response?.data?.detail || error.response?.data?.error || 'Failed to update problem set';
        this.$emit('error', errorMessage);
        console.error('Error updating problem set:', error);
      } finally {
        this.isSubmitting = false;
      }
    },

    handleEscape(event) {
      if (event.key === 'Escape') {
        this.closeModal();
      }
    }
  }
}
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
  max-width: 900px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  border: 2px solid var(--color-bg-input);
  display: flex;
  flex-direction: column;
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

.form-section {
  margin-bottom: var(--spacing-xl);
}

.form-section h3 {
  margin: 0 0 var(--spacing-lg) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
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

.problems-selection {
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
}

.problems-filter {
  margin-bottom: var(--spacing-lg);
}

.search-input {
  background: var(--color-bg-panel);
}

.problems-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-panel);
}

.problem-item {
  display: flex;
  align-items: center;
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--color-bg-input);
  cursor: pointer;
  transition: var(--transition-base);
}

.problem-item:last-child {
  border-bottom: none;
}

.problem-item:hover {
  background: var(--color-bg-hover);
}

.problem-item.selected {
  background: var(--color-bg-input);
}

.problem-checkbox {
  margin-right: var(--spacing-md);
}

.problem-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.problem-info {
  flex: 1;
}

.problem-title {
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.problem-meta {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
}

.problem-type {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
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

.medium-badge, .default-badge {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.hard-badge {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.selection-summary {
  margin-top: var(--spacing-md);
  text-align: center;
  color: var(--color-text-secondary);
  font-style: italic;
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

.loading-state {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-muted);
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
}
</style>
