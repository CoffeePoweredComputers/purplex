<template>
  <div
    class="modal-overlay"
    @click="closeModal"
  >
    <div
      class="modal-content"
      @click.stop
    >
      <div class="modal-header">
        <h2>{{ editMode ? 'Edit Problem' : 'Add New Problem' }}</h2>
        <button
          class="modal-close"
          @click="closeModal"
        >
          &times;
        </button>
      </div>
      <div class="modal-body">
        <form @submit.prevent="submitProblem">
          <!-- Problem Type Selection -->
          <div class="form-group">
            <label for="problemType">Problem Type</label>
            <select 
              id="problemType" 
              v-model="problem.problem_type" 
              class="form-input"
              required
              @change="handleProblemTypeChange"
            >
              <option value="">
                Select Problem Type
              </option>
              <option value="eipl">
                Explain in Plain Language (EiPL)
              </option>
              <option value="function_redefinition">
                Function Redefinition
              </option>
            </select>
          </div>

          <div class="form-group">
            <label for="problemName">Problem Title</label>
            <input 
              id="problemName" 
              type="text" 
              :value="problem.title"
              class="form-input"
              :class="{ error: errors.title && touched.title }"
              placeholder="Enter a descriptive problem title"
              required
              @input="onFieldInput('title', $event.target.value)"
              @blur="onFieldBlur('title')"
            >
            <span
              v-if="errors.title && touched.title"
              class="error-message"
            >{{ errors.title }}</span>
          </div>

          <div class="form-group">
            <label for="problemDifficulty">Difficulty</label>
            <select 
              id="problemDifficulty" 
              v-model="problem.difficulty" 
              class="form-input"
              required
            >
              <option value="">
                Select Difficulty
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
          </div>

          <div class="form-group">
            <label for="problemCategory">Category</label>
            <input 
              id="problemCategory" 
              v-model="problem.category" 
              type="text" 
              class="form-input"
              required
            >
          </div>

          <div class="form-group">
            <label for="problemDescription">Description</label>
            <textarea 
              id="problemDescription" 
              :value="problem.description"
              class="form-textarea"
              :class="{ error: errors.description && touched.description }"
              rows="4"
              placeholder="Provide a clear description of what the problem asks students to do"
              required
              @input="onFieldInput('description', $event.target.value)"
              @blur="onFieldBlur('description')"
            />
            <span
              v-if="errors.description && touched.description"
              class="error-message"
            >{{ errors.description }}</span>
          </div>

          <!-- Fields specific to Function Redefinition -->
          <div v-if="problem.problem_type === 'function_redefinition'">
            <div class="form-group">
              <label for="functionName">Function Name</label>
              <input 
                id="functionName" 
                v-model="problem.function_name" 
                type="text" 
                class="form-input"
                placeholder="e.g., calculate_sum"
                required
              >
            </div>

            <div class="form-group">
              <label for="functionSignature">Function Signature</label>
              <input 
                id="functionSignature" 
                v-model="problem.function_signature" 
                type="text" 
                class="form-input"
                placeholder="e.g., def calculate_sum(a: int, b: int) -> int:"
                required
              >
            </div>

            <div class="form-group">
              <label for="referenceSolution">Reference Solution</label>
              <textarea 
                id="referenceSolution" 
                v-model="problem.reference_solution" 
                class="form-textarea code-font"
                rows="6"
                placeholder="def calculate_sum(a, b):&#10;    return a + b"
                required
              />
            </div>
          </div>

          <!-- Fields specific to EiPL -->
          <div v-if="problem.problem_type === 'eipl'">
            <div class="form-group">
              <label for="codeSnippet">Code Snippet</label>
              <textarea 
                id="codeSnippet" 
                v-model="problem.code_snippet" 
                class="form-textarea code-font"
                rows="8"
                placeholder="# Enter the code snippet students will explain"
                required
              />
            </div>

            <div class="form-group">
              <label for="expectedExplanation">Expected Explanation (Reference)</label>
              <textarea 
                id="expectedExplanation" 
                v-model="problem.expected_explanation" 
                class="form-textarea"
                rows="4"
                placeholder="What this code should do..."
              />
            </div>
          </div>

          <!-- Problem Sets Selection -->
          <div class="form-group">
            <div
              class="section-header"
              @click="showProblemSetSelection = !showProblemSetSelection"
            >
              <label class="section-label">
                <span class="toggle-icon">{{ showProblemSetSelection ? '▼' : '▶' }}</span>
                Problem Sets
              </label>
              <span class="selection-count">{{ problem.problemSets.length }} selected</span>
            </div>
                
            <div
              v-if="showProblemSetSelection"
              class="problem-sets-selection"
            >
              <!-- Search and filters -->
              <div class="selection-controls">
                <input 
                  v-model="problemSetSearch" 
                  type="text"
                  placeholder="Search problem sets..."
                  class="form-input search-input"
                >
                <div class="bulk-actions">
                  <button
                    type="button"
                    class="bulk-btn"
                    @click="selectAllProblemSets"
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    class="bulk-btn"
                    @click="clearAllProblemSets"
                  >
                    Clear All
                  </button>
                </div>
              </div>

              <!-- Problem Sets Table -->
              <div class="problem-sets-table-container">
                <table class="problem-sets-table">
                  <thead>
                    <tr>
                      <th class="col-title">
                        Problem Set
                      </th>
                      <th class="col-visibility">
                        Visibility
                      </th>
                      <th class="col-problems">
                        Problems
                      </th>
                      <th class="col-action">
                        Add/Remove
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                      v-for="problemSet in filteredProblemSets" 
                      :key="problemSet.slug || problemSet.id"
                      class="problem-set-row"
                      :class="{ selected: isProblemSetSelected(problemSet.slug || problemSet.id) }"
                    >
                      <td class="problem-set-title-cell">
                        <div class="problem-set-title">
                          {{ problemSet.title }}
                        </div>
                        <div
                          v-if="problemSet.description"
                          class="problem-set-description"
                        >
                          {{ truncateText(problemSet.description, 60) }}
                        </div>
                      </td>
                      <td>
                        <span
                          class="visibility-badge"
                          :class="{ 'public': problemSet.is_public, 'private': !problemSet.is_public }"
                        >
                          {{ problemSet.is_public ? 'Public' : 'Private' }}
                        </span>
                      </td>
                      <td>
                        <span class="problems-count">{{ problemSet.problems_count || 0 }}</span>
                      </td>
                      <td>
                        <button 
                          type="button"
                          class="action-btn"
                          :class="{ 'remove-btn': isProblemSetSelected(problemSet.slug || problemSet.id), 'add-btn': !isProblemSetSelected(problemSet.slug || problemSet.id) }"
                          @click="toggleProblemSet(problemSet.slug || problemSet.id)"
                        >
                          {{ isProblemSetSelected(problemSet.slug || problemSet.id) ? '−' : '+' }}
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Selected Problem Sets Summary -->
              <div
                v-if="problem.problemSets.length > 0"
                class="selected-summary"
              >
                <h4>Selected Problem Sets ({{ problem.problemSets.length }})</h4>
                <div class="selected-items">
                  <div 
                    v-for="problemSetId in problem.problemSets" 
                    :key="problemSetId"
                    class="selected-item"
                  >
                    <span class="selected-title">{{ getProblemSetById(problemSetId)?.title }}</span>
                    <button 
                      type="button"
                      class="remove-selected-btn"
                      title="Remove from selection"
                      @click="removeProblemSet(problemSetId)"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </form>
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
          type="button" 
          class="action-button submit-button" 
          :disabled="isSubmitting || !isFormValid"
          @click="submitProblem"
        >
          {{ submitButtonText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
  import axios from 'axios';
  import { log } from '@/utils/logger';

  export default {
    name: 'AddEditProblemModal',
    props: {
      problemSets: {
        type: Array,
        default: () => []
      },
      editMode: {
        type: Boolean,
        default: false
      },
      problemData: {
        type: Object,
        default: null
      }
    },
    data() {
      return {
        problem: this.initializeProblem(),
        isSubmitting: false,
        showProblemSetSelection: false,
        problemSetSearch: '',
        errors: {},
        touched: {}
      };
    },
    computed: {
      submitButtonText() {
        if (this.isSubmitting) {
          return this.editMode ? 'Updating...' : 'Adding...';
        }
        return this.editMode ? 'Update Problem' : 'Add Problem';
      },

      filteredProblemSets() {
        if (!this.problemSetSearch) {return this.problemSets;}
        
        const query = this.problemSetSearch.toLowerCase();
        return this.problemSets.filter(problemSet => {
          const title = (problemSet.title || '').toLowerCase();
          const description = (problemSet.description || '').toLowerCase();
          return title.includes(query) || description.includes(query);
        });
      },

      isFormValid() {
        return Object.keys(this.errors).length === 0 && 
               this.problem.title.trim() && 
               this.problem.problem_type && 
               this.problem.difficulty && 
               this.problem.description.trim();
      }
    },
    watch: {
      problemData: {
        handler(newVal) {
          if (this.editMode && newVal) {
            this.problem = this.initializeProblem();
          }
        },
        immediate: true
      }
    },
    mounted() {
      // Add ESC key listener
      document.addEventListener('keydown', this.handleEscape);
    },
    beforeUnmount() {
      // Remove ESC key listener
      document.removeEventListener('keydown', this.handleEscape);
    },
    methods: {
      initializeProblem() {
        if (this.editMode && this.problemData) {
          const problemSets = this.problemData.problem_sets || [];
          return {
            title: this.problemData.title || '',
            problem_type: this.problemData.problem_type || '',
            difficulty: this.problemData.difficulty || '',
            category: this.problemData.categories && this.problemData.categories.length > 0 
              ? this.problemData.categories[0].name 
              : '',
            description: this.problemData.description || '',
            problemSets: problemSets.map(ps => ps.slug || ps.id),
            // Function Redefinition fields
            function_name: this.problemData.function_name || '',
            function_signature: this.problemData.function_signature || '',
            reference_solution: this.problemData.reference_solution || '',
            // EiPL fields - if problem_type is eipl, reference_solution contains the code snippet
            code_snippet: this.problemData.problem_type === 'eipl' 
              ? this.problemData.reference_solution || '' 
              : '',
            expected_explanation: this.problemData.problem_type === 'eipl' 
              ? this.problemData.hints || '' 
              : ''
          };
        }
        return {
          title: '',
          problem_type: '',
          difficulty: '',
          category: '',
          description: '',
          problemSets: [],
          function_name: '',
          function_signature: '',
          reference_solution: '',
          code_snippet: '',
          expected_explanation: ''
        };
      },
      
      closeModal() {
        this.resetForm();
        this.$emit('close');
      },

      resetForm() {
        this.problem = {
          name: '',
          problem_type: '',
          difficulty: '',
          category: '',
          description: '',
          problemSets: [],
          function_name: '',
          function_signature: '',
          reference_solution: '',
          code_snippet: '',
          expected_explanation: ''
        };
        this.isSubmitting = false;
      },

      handleProblemTypeChange() {
        // Clear type-specific fields when switching problem types
        if (this.problem.problem_type === 'eipl') {
          this.problem.function_name = '';
          this.problem.function_signature = '';
          this.problem.reference_solution = '';
        } else if (this.problem.problem_type === 'function_redefinition') {
          this.problem.code_snippet = '';
          this.problem.expected_explanation = '';
        }
      },

      // Problem Set Selection Methods
      isProblemSetSelected(problemSetId) {
        return this.problem.problemSets.includes(problemSetId);
      },

      toggleProblemSet(problemSetId) {
        const index = this.problem.problemSets.indexOf(problemSetId);
        if (index > -1) {
          this.problem.problemSets.splice(index, 1);
        } else {
          this.problem.problemSets.push(problemSetId);
        }
      },

      removeProblemSet(problemSetId) {
        const index = this.problem.problemSets.indexOf(problemSetId);
        if (index > -1) {
          this.problem.problemSets.splice(index, 1);
        }
      },

      selectAllProblemSets() {
        const allIds = this.filteredProblemSets.map(ps => ps.slug || ps.id);
        this.problem.problemSets = [...new Set([...this.problem.problemSets, ...allIds])];
      },

      clearAllProblemSets() {
        this.problem.problemSets = [];
      },

      getProblemSetById(problemSetId) {
        return this.problemSets.find(ps => (ps.slug || ps.id) === problemSetId);
      },

      truncateText(text, maxLength) {
        if (!text) {return '';}
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
      },

      // Validation methods
      validateField(fieldName, value) {
        const errors = { ...this.errors };
        
        switch (fieldName) {
          case 'name':
            if (!value.trim()) {
              errors.title = 'Problem title is required';
            } else if (value.trim().length < 3) {
              errors.title = 'Problem title must be at least 3 characters';
            } else {
              delete errors.title;
            }
            break;
            
          case 'description':
            if (!value.trim()) {
              errors.description = 'Description is required';
            } else if (value.trim().length < 10) {
              errors.description = 'Description must be at least 10 characters';
            } else {
              delete errors.description;
            }
            break;
            
          case 'function_name':
            if (this.problem.problem_type === 'function_redefinition' && !value.trim()) {
              errors.function_name = 'Function name is required';
            } else {
              delete errors.function_name;
            }
            break;
            
          case 'reference_solution':
            if (this.problem.problem_type === 'function_redefinition' && !value.trim()) {
              errors.reference_solution = 'Reference solution is required';
            } else {
              delete errors.reference_solution;
            }
            break;
            
          case 'code_snippet':
            if (this.problem.problem_type === 'eipl' && !value.trim()) {
              errors.code_snippet = 'Code snippet is required';
            } else {
              delete errors.code_snippet;
            }
            break;
        }
        
        this.errors = errors;
      },

      onFieldBlur(fieldName) {
        this.touched[fieldName] = true;
        this.validateField(fieldName, this.problem[fieldName]);
      },

      onFieldInput(fieldName, value) {
        this.problem[fieldName] = value;
        if (this.touched[fieldName]) {
          this.validateField(fieldName, value);
        }
      },

      async submitProblem() {
        if (this.isSubmitting) {return;}

        try {
          this.isSubmitting = true;
          
          // Prepare the data based on problem type
          const problemData = {
            title: this.problem.title,
            problem_type: this.problem.problem_type,
            difficulty: this.problem.difficulty,
            category: this.problem.category,
            description: this.problem.description,
            problem_sets: this.problem.problemSets
          };

          // Add type-specific fields
          if (this.problem.problem_type === 'function_redefinition') {
            problemData.function_name = this.problem.function_name;
            problemData.function_signature = this.problem.function_signature;
            problemData.reference_solution = this.problem.reference_solution;
          } else if (this.problem.problem_type === 'eipl') {
            // For EiPL, we might store the code snippet in the reference_solution field
            // and the expected explanation in the description or a new field
            problemData.reference_solution = this.problem.code_snippet;
            // You might want to add a new field to the model for expected_explanation
            problemData.hints = this.problem.expected_explanation;
          }

          let response;
          if (this.editMode) {
            response = await axios.put(`/api/admin/problems/${this.problemData.slug}/`, problemData);
            this.$emit('problem-updated', response.data);
          } else {
            response = await axios.post('/api/admin/problems/', problemData);
            this.$emit('problem-added', response.data);
          }
          this.closeModal();
        } catch (error) {
          const action = this.editMode ? 'update' : 'add';
          this.$emit('error', `Failed to ${action} problem. Please try again.`);
          log.error(`Error ${action}ing problem`, { action, error });
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

.modal-footer {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  padding: var(--spacing-xl);
  border-top: 2px solid var(--color-bg-input);
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
  background: var(--color-bg-panel);
}

.form-input::placeholder {
  color: var(--color-text-muted);
}

.form-input.error {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.error-message {
  color: var(--color-error);
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-xs);
  display: block;
}

.form-textarea {
  width: 100%;
  padding: var(--spacing-md);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  resize: vertical;
  min-height: 100px;
  transition: var(--transition-base);
}

.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

.form-textarea.error {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

/* Problem Sets Selection */
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
  margin-bottom: var(--spacing-sm);
}

.section-header:hover {
  background: var(--color-bg-input);
}

.section-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
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

.problem-sets-selection {
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
}

.selection-controls {
  margin-bottom: var(--spacing-lg);
}

.search-input {
  margin-bottom: var(--spacing-md);
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

.problem-sets-table-container {
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-panel);
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: var(--spacing-lg);
}

.problem-sets-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.problem-sets-table th {
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
}

.col-title {
  width: 50%;
}

.col-visibility {
  width: 20%;
}

.col-problems {
  width: 15%;
}

.col-action {
  width: 15%;
}

.problem-sets-table td {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--color-bg-hover);
  vertical-align: middle;
}

.problem-set-row {
  transition: var(--transition-base);
}

.problem-set-row:hover {
  background: var(--color-bg-hover);
}

.problem-set-row.selected {
  background: rgba(99, 102, 241, 0.1);
}

.problem-set-title-cell {
  overflow: hidden;
}

.problem-set-title {
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
  line-height: 1.3;
}

.problem-set-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  line-height: 1.2;
}

.visibility-badge {
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-base);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.visibility-badge.public {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.visibility-badge.private {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.problems-count {
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

.selected-summary {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
}

.selected-summary h4 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
}

.selected-items {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.selected-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  transition: var(--transition-base);
}

.selected-item:hover {
  background: var(--color-bg-input);
}

.selected-title {
  font-weight: 500;
  color: var(--color-text-primary);
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

.submit-button {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.submit-button:hover:not(:disabled) {
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

.code-font {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
  font-size: 13px;
  line-height: 1.5;
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
