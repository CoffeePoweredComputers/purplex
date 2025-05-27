<template>
  <div class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>{{ editMode ? 'Edit Problem' : 'Add New Problem' }}</h2>
        <button class="modal-close" @click="closeModal">&times;</button>
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
                   <option value="">Select Problem Type</option>
                   <option value="eipl">Explain in Plain Language (EiPL)</option>
                   <option value="function_redefinition">Function Redefinition</option>
            </select>
          </div>

          <div class="form-group">
            <label for="problemName">Problem Title</label>
            <input 
                   type="text" 
                   id="problemName" 
                   v-model="problem.name" 
                   class="form-input"
                   required
                   >
          </div>

            <div class="form-group">
              <label for="problemDifficulty">Difficulty</label>
              <select 
                     id="problemDifficulty" 
                     v-model="problem.difficulty" 
                     class="form-input"
                     required
                     >
                     <option value="">Select Difficulty</option>
                     <option value="easy">Easy</option>
                     <option value="beginner">Beginner</option>
                     <option value="intermediate">Intermediate</option>
                     <option value="advanced">Advanced</option>
              </select>
            </div>

            <div class="form-group">
              <label for="problemCategory">Category</label>
              <input 
                     type="text" 
                     id="problemCategory" 
                     v-model="problem.category" 
                     class="form-input"
                     required
                     >
            </div>

              <div class="form-group">
                <label for="problemDescription">Description</label>
                <textarea 
                       id="problemDescription" 
                       v-model="problem.description" 
                       class="form-textarea"
                       rows="4"
                       required
                       ></textarea>
              </div>

              <!-- Fields specific to Function Redefinition -->
              <div v-if="problem.problem_type === 'function_redefinition'">
                <div class="form-group">
                  <label for="functionName">Function Name</label>
                  <input 
                         type="text" 
                         id="functionName" 
                         v-model="problem.function_name" 
                         class="form-input"
                         placeholder="e.g., calculate_sum"
                         required
                         >
                </div>

                <div class="form-group">
                  <label for="functionSignature">Function Signature</label>
                  <input 
                         type="text" 
                         id="functionSignature" 
                         v-model="problem.function_signature" 
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
                         ></textarea>
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
                         ></textarea>
                </div>

                <div class="form-group">
                  <label for="expectedExplanation">Expected Explanation (Reference)</label>
                  <textarea 
                         id="expectedExplanation" 
                         v-model="problem.expected_explanation" 
                         class="form-textarea"
                         rows="4"
                         placeholder="What this code should do..."
                         ></textarea>
                </div>
              </div>

              <div class="form-group">
                <label>Problem Sets</label>
                <div class="checkbox-group">
                  <div 
                     v-for="problemSet in problemSets" 
                     :key="problemSet.slug || problemSet.id"
                     class="checkbox-item"
                     >
                     <input 
                     type="checkbox" 
                     :id="`ps-${problemSet.slug || problemSet.id}`"
                     :value="problemSet.slug || problemSet.id"
                     v-model="problem.problemSets"
                     >
                     <label :for="`ps-${problemSet.slug || problemSet.id}`">{{ problemSet.title || problemSet.name }}</label>
                  </div>
                </div>
              </div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="action-button cancel-button" @click="closeModal">
          Cancel
        </button>
        <button 
                              type="button" 
                              class="action-button submit-button" 
                              @click="submitProblem"
                              :disabled="isSubmitting"
                              >
                              {{ submitButtonText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
  import axios from 'axios';

  export default {
    name: 'AddProblemModal',
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
        isSubmitting: false
      };
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
    methods: {
      initializeProblem() {
        if (this.editMode && this.problemData) {
          const problemSets = this.problemData.problem_sets || [];
          return {
            name: this.problemData.title || '',
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

      async submitProblem() {
        if (this.isSubmitting) return;

        try {
          this.isSubmitting = true;
          
          // Prepare the data based on problem type
          const problemData = {
            title: this.problem.name,
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
          console.error(`Error ${action}ing problem:`, error);
        } finally {
          this.isSubmitting = false;
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
    },
    computed: {
      submitButtonText() {
        if (this.isSubmitting) {
          return this.editMode ? 'Updating...' : 'Adding...';
        }
        return this.editMode ? 'Update Problem' : 'Add Problem';
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
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  border: 2px solid var(--color-bg-input);
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

.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-primary);
  font-weight: 600;
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

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  max-height: 150px;
  overflow-y: auto;
  padding: var(--spacing-sm);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.checkbox-item input[type="checkbox"] {
  margin: 0;
}

.checkbox-item label {
  margin: 0;
  font-weight: normal;
  cursor: pointer;
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
}

.action-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}

.submit-button {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  box-shadow: var(--shadow-colored);
}

.submit-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
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
