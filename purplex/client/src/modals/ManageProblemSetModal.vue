<template>
  <div class="modal-overlay" @click="closeModal">
    <div class="modal-content large-modal" @click.stop>
      <div class="modal-header">
        <h2>Manage Problem Sets</h2>
        <button class="modal-close" @click="closeModal">&times;</button>
      </div>
      <div class="modal-body">
        <div class="problem-sets-section">
          <div class="section-header">
            <h3>Add New Problem Set</h3>
          </div>
          <form @submit.prevent="submitNewProblemSet" class="add-set-form">
            <div class="form-row">
              <input 
                type="text" 
                v-model="newProblemSet.title" 
                placeholder="Problem Set Name"
                class="form-input"
                required
              >
              <input 
                type="text" 
                v-model="newProblemSet.description" 
                placeholder="Description"
                class="form-input"
              >
              <button 
                type="submit" 
                class="action-button add-set-button"
                :disabled="isSubmitting || !newProblemSet.title.trim()"
              >
                {{ isSubmitting ? 'Adding...' : 'Add Set' }}
              </button>
            </div>
          </form>
        </div>
        
        <div class="problem-sets-list">
          <h3>Existing Problem Sets</h3>
          <div class="sets-table-container" v-if="problemSets.length > 0">
            <table class="sets-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Problems Count</th>
                  <th>Actions</th>
                  <th>Visibility</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="problemSet in problemSets" :key="problemSet.slug || problemSet.id">
                  <td>{{ problemSet.title }}</td>
                  <td>{{ problemSet.description || 'No description' }}</td>
                  <td>{{ getProblemSetCount(problemSet) }}</td>
                  <td class="actions-cell">
                    <button 
                      class="action-button edit-button" 
                      @click="editProblemSet(problemSet.slug || problemSet.id)"
                    >
                      Edit
                    </button>
                    <button 
                      class="action-button delete-button" 
                      @click="confirmDeleteProblemSet(problemSet)"
                      :disabled="isDeleting === (problemSet.slug || problemSet.id)"
                    >
                      {{ isDeleting === (problemSet.slug || problemSet.id) ? 'Deleting...' : 'Delete' }}
                    </button>
                  </td>
                  <td>
                    <span>{{ problemSet.is_public ? 'Public' : 'Private' }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-state">
            <p>No problem sets found. Create your first problem set above.</p>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="action-button cancel-button" @click="closeModal">
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'ManageProblemSetModal',
  props: {
    problemSets: {
      type: Array,
      default: () => []
    },
    problems: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      newProblemSet: {
        title: '',
        description: ''
      },
      isSubmitting: false,
      isDeleting: null
    };
  },
  methods: {
    closeModal() {
      this.resetForm();
      this.$emit('close');
    },

    resetForm() {
      this.newProblemSet = {
        title: '',
        description: ''
      };
      this.isSubmitting = false;
      this.isDeleting = null;
    },

    getProblemSetCount(problemSet) {
      // Use the problems_count property if available
      if (typeof problemSet.problems_count === 'number') {
        return problemSet.problems_count;
      }
      
      // Fallback: count problems that have this problem set in their problem_sets array
      const problemSetSlug = problemSet.slug;
      return this.problems.filter(problem => 
        problem.problem_sets && 
        problem.problem_sets.some(ps => ps.slug === problemSetSlug || ps.title === problemSet.title)
      ).length;
    },

    async submitNewProblemSet() {
      if (this.isSubmitting || !this.newProblemSet.title.trim()) return;
      
      try {
        this.isSubmitting = true;
        // Create FormData to support file upload if needed later
        const formData = new FormData();
        formData.append('title', this.newProblemSet.title);
        formData.append('description', this.newProblemSet.description || '');
        // Set is_public to false by default for new problem sets
        formData.append('is_public', 'false');
        // Add empty problem_slugs array for problem assignment
        formData.append('problem_slugs', JSON.stringify([]));
        
        const response = await axios.post('/api/admin/problem-sets/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        
        console.log('Problem set created:', response.data);
        this.$emit('problem-set-added', response.data);
        this.newProblemSet = { title: '', description: '' };
      } catch (error) {
        const errorMessage = error.response?.data?.detail || error.response?.data?.error || 'Failed to add problem set. Please try again.';
        this.$emit('error', errorMessage);
        console.error('Error adding problem set:', error);
      } finally {
        this.isSubmitting = false;
      }
    },

    editProblemSet(problemSetSlug) {
      // Emit event to parent component to handle editing
      this.$emit('edit-problem-set', problemSetSlug);
    },

    confirmDeleteProblemSet(problemSet) {
      const problemCount = this.getProblemSetCount(problemSet);
      const name = problemSet.title;
      
      let message = `Are you sure you want to delete the problem set "${name}"?`;
      if (problemCount > 0) {
        message += `\n\nThis problem set contains ${problemCount} problem(s). The problems will not be deleted, but they will be removed from this set.`;
      }
      message += '\n\nThis action cannot be undone.';
      
      if (confirm(message)) {
        this.deleteProblemSet(problemSet);
      }
    },

    async deleteProblemSet(problemSet) {
      if (this.isDeleting) return;
      
      const slug = problemSet.slug;
      const id = problemSet.id;
      
      try {
        this.isDeleting = slug || id;
        await axios.delete(`/api/admin/problem-sets/${slug}/`);
        
        // Don't update local state - let parent handle everything
        // Emit both identifiers for maximum safety
        this.$emit('problem-set-deleted', { 
          slug: slug, 
          id: id,
          problemSet: problemSet // Include full object for reference
        });
      } catch (error) {
        this.$emit('error', `Failed to delete problem set: ${error.response?.data?.detail || error.message || 'Please try again.'}`);
        console.error('Error deleting problem set:', error);
      } finally {
        this.isDeleting = null;
      }
    },

    handleEscape(event) {
      if (event.key === 'Escape') {
        this.closeModal();
      }
    }
  },
  mounted() {
    // Add ESC key listener
    document.addEventListener('keydown', this.handleEscape);
  },
  beforeUnmount() {
    // Remove ESC key listener
    document.removeEventListener('keydown', this.handleEscape);
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
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  border: 2px solid var(--color-bg-input);
}

.large-modal {
  max-width: 800px;
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
}

.modal-footer {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  padding: var(--spacing-xl);
  border-top: 2px solid var(--color-bg-input);
}

.problem-sets-section {
  margin-bottom: var(--spacing-xl);
}

.section-header {
  margin-bottom: var(--spacing-lg);
}

.section-header h3 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
}

.add-set-form {
  background: var(--color-bg-hover);
  padding: var(--spacing-lg);
  border-radius: var(--radius-base);
  border: 2px solid var(--color-bg-input);
}

.form-row {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-end;
}

.form-row .form-input {
  flex: 1;
}

.form-input {
  padding: var(--spacing-md);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-panel);
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

.problem-sets-list h3 {
  margin: 0 0 var(--spacing-lg) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
}

.sets-table-container {
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  border: 2px solid var(--color-bg-input);
  overflow: hidden;
}

.sets-table {
  width: 100%;
  border-collapse: collapse;
}

.sets-table th {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  padding: var(--spacing-md) var(--spacing-lg);
  font-weight: 600;
  font-size: var(--font-size-sm);
  text-align: left;
}

.sets-table td {
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-input);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.sets-table tr:last-child td {
  border-bottom: none;
}

.sets-table tr:hover {
  background: var(--color-bg-input);
}

.actions-cell {
  display: flex;
  gap: var(--spacing-md);
}

.action-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-base);
  white-space: nowrap;
}

.action-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}

.add-set-button {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.add-set-button:hover:not(:disabled) {
  background: var(--color-success);
  color: var(--color-text-primary);
}

.edit-button {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.edit-button:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.delete-button {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.delete-button:hover:not(:disabled) {
  background: var(--color-error);
  color: var(--color-text-primary);
  transform: translateY(-1px);
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

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-muted);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  border: 2px solid var(--color-bg-input);
}

.empty-state p {
  margin: 0;
  font-style: italic;
}

/* Responsive Design */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: var(--spacing-md);
  }

  .form-row {
    flex-direction: column;
  }

  .form-row .form-input {
    margin-bottom: var(--spacing-sm);
  }

  .modal-footer {
    flex-direction: column;
  }

  .action-button {
    width: 100%;
    justify-content: center;
  }

  .actions-cell {
    flex-direction: column;
  }

  .sets-table {
    font-size: var(--font-size-sm);
  }

  .sets-table th,
  .sets-table td {
    padding: var(--spacing-sm) var(--spacing-md);
  }
}
</style>
