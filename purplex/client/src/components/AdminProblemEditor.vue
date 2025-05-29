<template>
  <div class="admin-problem-editor">
    <!-- Breadcrumb navigation -->
    <nav class="breadcrumb">
      <router-link to="/admin/problems" class="breadcrumb-link">
        ← Back to Problems
      </router-link>
    </nav>
    
    <div class="header">
      <h2>{{ isEditing ? 'Edit Problem' : 'Create New Problem' }}</h2>
      <div class="actions">
        <button @click="saveProblem" :disabled="!canSave || ui.loading" class="btn btn-primary">
          {{ ui.loading ? 'Saving...' : 'Save Problem' }}
        </button>
      </div>
    </div>

    <form @submit.prevent="saveProblem" class="problem-form">
      <!-- Basic Information -->
      <div class="form-section">
        <h3>Basic Information</h3>
        <div class="form-group">
          <label for="title">Title *</label>
          <input
            id="title"
            v-model="form.title"
            type="text"
            required
            placeholder="e.g., Anagram Checker"
          />
        </div>

        <div class="form-group">
          <label for="difficulty">Difficulty</label>
          <select id="difficulty" v-model="form.difficulty">
            <option value="easy">Easy</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        <div class="form-group">
          <label for="categories">Categories</label>
          <div class="category-selector">
            <div
              v-for="category in categories"
              :key="category.id"
              class="category-option"
              :class="{ active: form.category_ids && form.category_ids.includes(category.id) }"
              @click="toggleCategory(category.id)"
            >
              <span class="category-color" :style="{ backgroundColor: category.color }"></span>
              {{ category.name }}
            </div>
            
            <!-- Morphing Category Bean -->
            <div 
              ref="categoryShell"
              class="category-shell" 
              :class="{ 
                expanded: showAddCategory,
                transitioning: isTransitioning
              }"
              @click.stop="handleShellClick"
            >
                <!-- Button Content (collapsed state) -->
                <div 
                  class="add-category-content"
                  :class="{ visible: !showAddCategory }"
                >
                  <span class="add-icon">+</span>
                  <span class="add-text">Add Category</span>
                </div>
                
                <!-- Form Content (expanded state) -->
                <div 
                  class="bean-form-content"
                  :class="{ visible: showAddCategory }"
                >
                  <!-- Input Segment -->
                  <div class="form-segment input-segment">
                    <input 
                      ref="nameInput"
                      v-model="newCategory.name"
                      placeholder="Category name"
                      class="bean-input"
                      @keyup.enter="createCategory"
                      @keyup.escape="collapseBean"
                    />
                  </div>
                  
                  <!-- Color Segment -->
                  <div class="form-segment color-segment">
                    <div 
                      ref="colorTrigger"
                      class="color-preview-btn"
                      @click="toggleColorPicker"
                      :style="{ backgroundColor: newCategory.color }"
                    ></div>
                  </div>
                  
                  <!-- Action Segment -->
                  <div class="form-segment action-segment">
                    <button 
                      @click="createCategory"
                      :disabled="!newCategory.name.trim() || creatingCategory"
                      class="bean-submit-btn"
                      :class="{ loading: creatingCategory, disabled: !newCategory.name.trim() }"
                      :title="creatingCategory ? 'Creating...' : 'Create Category'"
                    >
                      {{ creatingCategory ? '⋯' : '✓' }}
                    </button>
                  </div>
                </div>
              </div>
            
            <!-- Error message -->
            <transition name="error-slide">
              <div v-if="categoryError" class="bean-error">
                {{ categoryError }}
              </div>
            </transition>
          </div>
        </div>


        <div class="form-group">
          <label for="tags">Tags (comma-separated)</label>
          <input
            id="tags"
            :value="tagsDisplay" @input="updateTags"
            type="text"
            placeholder="e.g., strings, sorting, hash-map"
          />
        </div>
      </div>

      <!-- Problem Description -->
      <div class="form-section">
        <h3>Problem Description</h3>
        <div class="form-group">
          <label for="description">Description (Markdown supported)</label>
          <textarea
            id="description"
            v-model="form.description"
            placeholder="Write your problem description here..."
            rows="10"
          ></textarea>
        </div>
      </div>

      <!-- Function Details -->
      <div class="form-section">
        <h3>Function Details</h3>
        <div class="form-row">
          <div class="form-group">
            <label for="function_name">Function Name *</label>
            <input
              id="function_name"
              v-model="form.function_name"
              type="text"
              required
              pattern="[a-zA-Z_][a-zA-Z0-9_]*"
              placeholder="e.g., is_anagram"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="function_signature">Function Signature</label>
          <input
            id="function_signature"
            v-model="form.function_signature"
            type="text"
            placeholder="e.g., def is_anagram(str1: str, str2: str) -> bool:"
          />
        </div>

        <div class="form-group">
          <label for="reference_solution">Reference Solution *</label>
          <div class="code-editor">
            <textarea
              id="reference_solution"
              v-model="form.reference_solution"
              class="code-textarea"
              placeholder="def your_function():&#10;    # Your solution here&#10;    pass"
              rows="8"
            ></textarea>
          </div>
        </div>

        <div class="form-group">
          <label for="hints">Hints (optional)</label>
          <textarea
            id="hints"
            v-model="form.hints"
            rows="3"
            placeholder="Provide helpful hints for students..."
          ></textarea>
        </div>
      </div>

      <!-- Test Cases -->
      <div class="form-section">
        <h3>Test Cases</h3>
        
        <!-- Test Results Summary -->
        <div v-if="ui.testResults" class="test-results-summary">
          <div class="results-summary-content">
            <span class="results-text">
              {{ ui.testResults.passed }}/{{ ui.testResults.total }} tests passed
            </span>
            <span v-if="ui.testResults.passed === ui.testResults.total" class="success-icon">✓</span>
            <span v-else class="failure-icon">✗</span>
          </div>
        </div>
        
        <div class="test-cases-actions">
          <div class="action-group">
            <button type="button" @click="addTestCase" class="btn btn-secondary">
              Add Test Case
            </button>
            <button
              type="button"
              @click="generateTestCases"
              :disabled="ui.loading || !canGenerateTestCases"
              class="btn btn-secondary"
              :title="canGenerateTestCasesReason || 'Generate one test case using AI'"
            >
              {{ ui.loading ? 'Generating...' : 'Add Test Case with AI' }}
            </button>
          </div>
          
          <button 
            @click="testProblem" 
            :disabled="!canTest || ui.loading" 
            class="btn btn-primary test-solution-btn"
            :title="canTestReason || 'Test your reference solution against all test cases'"
          >
            {{ ui.loading ? 'Testing...' : 'Test Reference Solution' }}
          </button>
        </div>

        <div class="test-cases-list">
          <div
            v-for="(testCase, index) in form.test_cases"
            :key="index"
            class="test-case"
            :class="{ 'test-case-error': testCase.error }"
          >
            <div class="test-case-header">
              <div class="test-case-title">
                <span class="test-case-number">Test {{ index + 1 }}</span>
                <div v-if="ui.testResults && ui.testResults.results && ui.testResults.results[index]" class="test-status">
                  <span v-if="ui.testResults.results[index].passed" class="status-passed">✓ Passed</span>
                  <span v-else class="status-failed">✗ Failed</span>
                </div>
              </div>
              <div class="test-case-options">
                <label>
                  <input type="checkbox" v-model="testCase.is_sample" />
                  Sample
                </label>
                <label>
                  <input type="checkbox" v-model="testCase.is_hidden" />
                  Hidden
                </label>
                <button type="button" @click="removeTestCase(index)" class="btn-remove">
                  ×
                </button>
              </div>
            </div>

            <div class="test-case-content">
              <div class="form-group">
                <label>Inputs (JSON array)</label>
                <input
                  :value="getTestCaseInputsDisplay(testCase)"
                  @input="updateTestCaseInputs(testCase, $event.target.value)"
                  type="text"
                  placeholder='["arg1", "arg2"]'
                />
              </div>

              <div class="form-group">
                <label>Expected Output (JSON)</label>
                <input
                  :value="getTestCaseExpectedDisplay(testCase)"
                  @input="updateTestCaseExpected(testCase, $event.target.value)"
                  type="text"
                  placeholder="true"
                />
              </div>

              <div class="form-group">
                <label>Description (optional)</label>
                <input
                  v-model="testCase.description"
                  type="text"
                  placeholder="Brief description of this test case"
                />
              </div>

              <div v-if="testCase.error" class="test-case-error-message">
                {{ testCase.error }}
              </div>
              
              <!-- Test Failure Details -->
              <div v-if="ui.testResults && ui.testResults.results && ui.testResults.results[index] && !ui.testResults.results[index].passed" 
                   class="test-failure-details">
                <div class="failure-content">
                  <button 
                    @click="toggleFailureDetails(index)"
                    class="failure-toggle"
                    :class="{ expanded: testCase.showFailureDetails }"
                  >
                    <span class="toggle-icon">{{ testCase.showFailureDetails ? '▼' : '▶' }}</span>
                    View Failure Details
                  </button>
                  
                  <div v-if="testCase.showFailureDetails" class="failure-details">
                    <div class="detail-item">
                      <strong>Expected:</strong> {{ JSON.stringify(ui.testResults.results[index].expected_output) }}
                    </div>
                    <div class="detail-item">
                      <strong>Got:</strong> {{ JSON.stringify(ui.testResults.results[index].actual_output) }}
                    </div>
                    <div v-if="ui.testResults.results[index].error" class="detail-item error-detail">
                      <strong>Error:</strong> {{ ui.testResults.results[index].error }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>


      <!-- Settings -->
      <div class="form-section">
        <h3>Settings</h3>
        <div class="form-row">
          <div class="form-group">
            <label for="memory_limit">Memory Limit (MB)</label>
            <input
              id="memory_limit"
              v-model.number="form.memory_limit"
              type="number"
              min="32"
              max="1024"
            />
          </div>

          <div class="form-group">
            <label>
              <input type="checkbox" v-model="form.is_active" />
              Active (visible to students)
            </label>
          </div>
        </div>
      </div>
    </form>
    
    <!-- Color picker popup (teleported to body) -->
    <Teleport to="body">
      <div 
        v-if="showColorPicker" 
        class="color-picker-overlay"
        @click="closeColorPicker"
      >
        <div 
          class="color-picker-popup"
          :class="{ 'popup-below': popupDirection === 'below' }"
          :style="popupStyle"
          @click.stop
        >
          <div class="popup-content">
            <div class="color-grid">
              <div 
                v-for="color in $options.colorOptions" 
                :key="color.value"
                class="color-option"
                :class="{ active: newCategory.color === color.value }"
                :style="{ backgroundColor: color.value }"
                @click="selectColor(color.value)"
                :title="color.name"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Notification toast integration -->
    <NotificationToast />
  </div>
</template>

<script>
import NotificationToast from './NotificationToast.vue'
import { problemService } from '../services/problemService'

// Color options as static constant
const COLOR_OPTIONS = [
  { value: '#3b82f6', name: 'Blue' },
  { value: '#ef4444', name: 'Red' },
  { value: '#10b981', name: 'Green' },
  { value: '#f59e0b', name: 'Orange' },
  { value: '#8b5cf6', name: 'Purple' },
  { value: '#06b6d4', name: 'Cyan' },
  { value: '#84cc16', name: 'Lime' },
  { value: '#f97316', name: 'Orange Red' }
];

export default {
  name: 'AdminProblemEditor',
  components: {
    NotificationToast
  },
  // Static options
  colorOptions: COLOR_OPTIONS,
  props: {
    problemSlug: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      // Single form state
      form: {
        title: '',
        description: '',
        difficulty: 'beginner',
        category_ids: [],
        function_name: '',
        function_signature: '',
        reference_solution: '',
        hints: '',
        memory_limit: 128,
        tags: [],
        is_active: true,
        test_cases: []
      },
      
      // Single UI state
      ui: {
        loading: false,
        error: null,
        testResults: null
      },
      
      // External data
      categories: [],
      
      // Category creation
      showAddCategory: false,
      isTransitioning: false,
      creatingCategory: false,
      categoryError: null,
      newCategory: {
        name: '',
        color: '#3b82f6',
        description: ''
      },
      
      // Color picker
      showColorPicker: false,
      popupPosition: {
        top: '0px',
        left: '0px'
      },
      popupDirection: 'below',
      
      // Click outside handler
      clickOutsideHandler: null
    }
  },
  computed: {
    // Get the slug from route params if not provided as prop
    currentProblemSlug() {
      return this.problemSlug || this.$route.params.slug || null;
    },
    isEditing() {
      return Boolean(this.currentProblemSlug)
    },
    validationErrors() {
      const errors = [];
      if (!this.form.title?.trim()) errors.push('Title is required');
      if (!this.form.function_name?.trim()) errors.push('Function name is required');
      if (!this.form.reference_solution?.trim()) errors.push('Reference solution is required');
      if (this.form.test_cases.length === 0) errors.push('At least one test case required');
      if (this.form.test_cases.some(tc => tc.error)) errors.push('Fix test case errors');
      return errors;
    },
    canSave() {
      return !this.ui.loading && 
             this.validationErrors.length === 0 &&
             (this.form.title.trim().length > 0 || 
              this.form.description.trim().length > 0 ||
              this.form.test_cases.length > 0);
    },
    canTest() {
      return !this.ui.loading &&
             this.form.function_name.trim().length > 0 &&
             this.form.reference_solution.trim().length > 0 &&
             this.form.test_cases.length > 0 &&
             this.form.test_cases.every(tc => !tc.error);
    },
    canTestReason() {
      if (this.ui.loading) return "Currently loading...";
      if (!this.form.function_name?.trim()) return "Function name required";
      if (!this.form.reference_solution?.trim()) return "Reference solution required";
      if (this.form.test_cases.length === 0) return "Add at least one test case";
      if (this.form.test_cases.some(tc => tc.error)) return "Fix test case errors first";
      return null; // Can test
    },
    canGenerateTestCases() {
      return !this.ui.loading &&
             this.form.function_name.trim().length > 0 &&
             this.form.reference_solution.trim().length > 0;
    },
    canGenerateTestCasesReason() {
      if (this.ui.loading) return "Currently loading...";
      if (!this.form.function_name?.trim()) return "Function name required for AI generation";
      if (!this.form.reference_solution?.trim()) return "Reference solution required for AI generation";
      return null; // Can generate
    },
    tagsDisplay() {
      return this.form.tags.join(', ')
    },
    popupStyle() {
      return {
        position: 'fixed',
        top: this.popupPosition.top,
        left: this.popupPosition.left,
        zIndex: 1001
      };
    }
  },
  async mounted() {
    try {
      await Promise.all([
        this.loadCategories(),
        // Don't call loadProblem here as the watcher will handle it
        !this.isEditing ? Promise.resolve(this.addTestCase()) : Promise.resolve()
      ]);
    } catch (error) {
      this.$toast?.error?.('Failed to load data') || console.error('Failed to load data');
    }
  },
  
  // Add watcher for route changes
  watch: {
    '$route'(to, from) {
      // If we're switching to edit mode or changing problem slug
      if (to.params.slug && to.params.slug !== from.params.slug) {
        this.loadProblem();
      }
    },
    
    currentProblemSlug: {
      immediate: true,
      async handler(newSlug, oldSlug) {
        if (newSlug && newSlug !== oldSlug) {
          // Ensure categories are loaded before loading the problem
          if (this.categories.length === 0) {
            await this.loadCategories();
          }
          await this.loadProblem();
        }
      }
    }
  },
  
  beforeUnmount() {
    // Clear any pending operations
    this.ui.loading = false;
    
    // Remove click outside listener
    if (this.clickOutsideHandler) {
      document.removeEventListener('click', this.clickOutsideHandler, true);
    }
  },
  methods: {
    async executeAction(actionName, actionFn, successMsg = null) {
      if (this.ui.loading) return;
      
      this.ui.loading = true;
      this.ui.error = null;
      
      try {
        const result = await actionFn();
        if (successMsg) {
          this.$toast?.success?.(successMsg) || console.log(successMsg);
        }
        return result;
      } catch (error) {
        console.error(`Error in ${actionName}:`, error);
        
        // Better error message extraction
        let errorMsg = `Failed to ${actionName}`;
        if (error.error) {
          errorMsg = error.error;
        } else if (error.message) {
          errorMsg = error.message;
        } else if (error.response && error.response.data) {
          errorMsg = error.response.data.error || error.response.data.message || errorMsg;
        }
        
        // Add status code if available
        if (error.status) {
          errorMsg += ` (Status: ${error.status})`;
        }
        
        this.ui.error = errorMsg;
        this.$toast?.error?.(errorMsg) || console.error(errorMsg);
        throw error;
      } finally {
        this.ui.loading = false;
      }
    },

    async loadCategories() {
      await this.executeAction('load categories', async () => {
        this.categories = await problemService.loadCategories();
      });
    },
    
    async loadProblem() {
      if (!this.currentProblemSlug) {
        return;
      }
      
      await this.executeAction('load problem', async () => {
        const loadedProblem = await problemService.loadProblem(this.currentProblemSlug);
        
        // Add error tracking and failure details to test cases
        if (loadedProblem.test_cases) {
          loadedProblem.test_cases = loadedProblem.test_cases.map(tc => ({
            ...tc,
            error: null,
            showFailureDetails: false
          }));
        }
        
        // Extract category IDs from categories objects
        if (loadedProblem.categories && Array.isArray(loadedProblem.categories)) {
          loadedProblem.category_ids = loadedProblem.categories.map(cat => cat.id);
        } else if (!loadedProblem.category_ids) {
          loadedProblem.category_ids = [];
        }
        
        // Ensure tags is an array
        if (!loadedProblem.tags) {
          loadedProblem.tags = [];
        }
        
        this.form = loadedProblem;
      });
    },
    
    toggleCategory(categoryId) {
      // Ensure category_ids is always an array
      if (!this.form.category_ids) {
        this.form.category_ids = [];
      }
      
      const index = this.form.category_ids.indexOf(categoryId)
      if (index > -1) {
        this.form.category_ids.splice(index, 1)
      } else {
        this.form.category_ids.push(categoryId)
      }
    },
    
    handleShellClick() {
      if (!this.showAddCategory && !this.isTransitioning) {
        this.expandBean();
      }
    },
    
    expandBean() {
      if (this.isTransitioning) return;
      
      this.isTransitioning = true;
      this.categoryError = null;
      
      // Progressive reveal: width expands slowly, revealing sections one by one
      setTimeout(() => {
        this.showAddCategory = true;
      }, 150); // Let width start expanding first, then reveal form content
      
      setTimeout(() => {
        if (this.$refs.nameInput) {
          this.$refs.nameInput.focus();
        }
        this.isTransitioning = false;
      }, 600); // Longer total duration for slower reveal
      
      // Add click outside listener immediately (no delay)
      this.$nextTick(() => {
        this.clickOutsideHandler = (event) => {
          const categoryShell = this.$refs.categoryShell;
          
          if (event.target && 
              categoryShell && 
              !categoryShell.contains(event.target)) {
            this.collapseBean();
          }
        };
        
        document.addEventListener('click', this.clickOutsideHandler, true);
      });
    },
    
    collapseBean() {
      if (this.isTransitioning) return;
      
      this.isTransitioning = true;
      this.showColorPicker = false;
      
      // First, hide the form content (reverse of expand)
      // This creates visual symmetry with the expand animation
      setTimeout(() => {
        this.showAddCategory = false;
      }, 200); // Give content time to fade out first
      
      // Then complete the transition
      setTimeout(() => {
        this.isTransitioning = false;
      }, 400); // Match CSS transition duration
      
      // Reset form data
      this.newCategory = {
        name: '',
        color: '#3b82f6',
        description: ''
      };
      this.categoryError = null;
      
      // Remove click outside listener
      if (this.clickOutsideHandler) {
        document.removeEventListener('click', this.clickOutsideHandler, true);
        this.clickOutsideHandler = null;
      }
    },
    
    toggleColorPicker() {
      if (!this.showColorPicker) {
        this.calculatePopupPosition();
      }
      this.showColorPicker = !this.showColorPicker;
    },

    calculatePopupPosition() {
      this.$nextTick(() => {
        if (this.$refs.colorTrigger) {
          const rect = this.$refs.colorTrigger.getBoundingClientRect();
          const popupWidth = 128; // 4 colors * 24px + gaps + padding
          const popupHeight = 90; // 2 rows * 24px + gaps + padding
          const gap = 1; // Gap between button and popup
          
          let top, left;
          
          // Determine if popup should appear above or below
          const spaceAbove = rect.top;
          const spaceBelow = window.innerHeight - rect.bottom;
          
          if (spaceAbove >= popupHeight + gap) {
            // Show above
            this.popupDirection = 'above';
            top = rect.top - popupHeight - gap;
          } else {
            // Show below
            this.popupDirection = 'below';
            top = rect.bottom + gap;
          }
          
          // Center horizontally on the trigger
          left = rect.left + (rect.width / 2) - (popupWidth / 2);
          
          // Adjust horizontal position if off-screen
          if (left < 10) {
            left = 10;
          } else if (left + popupWidth > window.innerWidth - 10) {
            left = window.innerWidth - popupWidth - 10;
          }
          
          this.popupPosition = {
            top: `${top}px`,
            left: `${left}px`
          };
        }
      });
    },
    
    closeColorPicker() {
      this.showColorPicker = false;
    },
    
    selectColor(colorValue) {
      this.newCategory.color = colorValue;
      this.showColorPicker = false; // Auto-close after selection
    },
    
    async createCategory() {
      if (!this.newCategory.name.trim()) {
        this.categoryError = 'Category name is required';
        return;
      }
      
      this.creatingCategory = true;
      this.categoryError = null;
      
      try {
        await this.executeAction('create category', async () => {
          const categoryData = {
            name: this.newCategory.name.trim(),
            color: this.newCategory.color,
            description: this.newCategory.description || `Category for ${this.newCategory.name.trim()} problems`
          };
          
          const newCategory = await problemService.createCategory(categoryData);
          
          // Add to local categories list
          this.categories.push(newCategory);
          
          // Auto-select the new category
          this.form.category_ids.push(newCategory.id);
          
          // Reset form
          this.collapseBean();
          
          return newCategory;
        }, `Category "${this.newCategory.name}" created successfully`);
      } catch (error) {
        this.categoryError = error.error || 'Failed to create category';
      } finally {
        this.creatingCategory = false;
      }
    },
    
    addTestCase() {
      this.form.test_cases.push({
        inputs: [],
        expected_output: null,
        description: '',
        is_hidden: false,
        is_sample: false,
        order: this.form.test_cases.length,
        error: null,
        showFailureDetails: false
      })
    },
    
    removeTestCase(index) {
      this.form.test_cases.splice(index, 1)
    },
    
    getTestCaseInputsDisplay(testCase) {
      return JSON.stringify(testCase.inputs || []);
    },
    
    getTestCaseExpectedDisplay(testCase) {
      return JSON.stringify(testCase.expected_output ?? '');
    },
    
    updateTestCaseInputs(testCase, value) {
      try {
        const parsed = JSON.parse(value);
        if (!Array.isArray(parsed)) {
          throw new Error('Must be an array');
        }
        testCase.inputs = parsed;
        testCase.error = null;
      } catch (e) {
        testCase.error = 'Invalid JSON array for inputs';
      }
    },
    
    updateTestCaseExpected(testCase, value) {
      try {
        testCase.expected_output = JSON.parse(value);
        testCase.error = null;
      } catch (e) {
        testCase.error = 'Invalid JSON for expected output';
      }
    },
    
    async testProblem() {
      if (!this.canTest) {
        // Show specific reason instead of generic warning
        const reason = this.canTestReason || 'Cannot test problem in current state';
        this.$toast?.warning?.(reason) || console.warn(reason);
        return;
      }
      
      await this.executeAction('test problem', async () => {
        const testData = {
          title: this.form.title,
          description: this.form.description,
          function_name: this.form.function_name,
          reference_solution: this.form.reference_solution,
          test_cases: this.form.test_cases.filter(tc => !tc.error).map(tc => ({
            inputs: tc.inputs,
            expected_output: tc.expected_output,
            description: tc.description || '',
            is_hidden: tc.is_hidden,
            is_sample: tc.is_sample,
            order: tc.order
          }))
        };
        
        // Debug: Log the data being sent
        console.log('Testing with data:', testData);
        
        this.ui.testResults = await problemService.testProblem(testData);
        
        const passed = this.ui.testResults.passed;
        const total = this.ui.testResults.total;
        
        if (this.ui.testResults.success && passed === total) {
          return 'All tests passed! ✓';
        } else {
          return `${passed}/${total} tests passed`;
        }
      });
    },
    
    async generateTestCases() {
      if (!this.canGenerateTestCases) {
        const reason = this.canGenerateTestCasesReason || 'Cannot generate test cases in current state';
        this.$toast?.warning?.(reason) || console.warn(reason);
        return;
      }
      
      await this.executeAction('generate test cases', async () => {
        console.log('Starting AI test case generation...');
        
        const requestData = {
          description: this.form.description || '',
          function_name: this.form.function_name,
          function_signature: this.form.function_signature || '',
          reference_solution: this.form.reference_solution
        };
        
        console.log('AI Generation request data:', requestData);
        
        const response = await problemService.generateTestCases(requestData);
        
        console.log('AI Generation response:', response);
        
        if (!response.test_cases || !Array.isArray(response.test_cases)) {
          throw new Error('Invalid response format: expected test_cases array');
        }
        
        response.test_cases.forEach(tc => {
          this.form.test_cases.push({
            ...tc,
            order: this.form.test_cases.length,
            error: null,
            showFailureDetails: false
          });
        });
        
        const count = response.test_cases.length;
        return count === 1 ? 'Generated 1 test case' : `Generated ${count} test cases`;
      });
    },
    
    async saveProblem() {
      if (!this.canSave) {
        this.$toast?.error?.('Please fix validation errors before saving') || console.error('Cannot save - validation errors');
        return;
      }
      
      await this.executeAction('save problem', async () => {
        const problemData = {
          title: this.form.title,
          description: this.form.description,
          difficulty: this.form.difficulty,
          problem_type: this.form.problem_type,
          category_ids: this.form.category_ids,
          function_name: this.form.function_name,
          function_signature: this.form.function_signature,
          reference_solution: this.form.reference_solution,
          hints: this.form.hints || '',
          memory_limit: this.form.memory_limit,
          tags: this.form.tags,
          is_active: this.form.is_active,
          test_cases: this.form.test_cases.filter(tc => !tc.error).map(tc => ({
            inputs: tc.inputs,
            expected_output: tc.expected_output,
            description: tc.description || '',
            is_hidden: tc.is_hidden,
            is_sample: tc.is_sample,
            order: tc.order
          }))
        };
        
        let savedProblem;
        
        if (this.isEditing) {
          savedProblem = await problemService.updateProblem(this.currentProblemSlug, problemData);
        } else {
          savedProblem = await problemService.createProblem(problemData);
          // Navigate to edit mode for the new problem
          await this.$router.push(`/admin/problems/${savedProblem.slug}/edit`);
        }
        
        // Update local state with saved data
        this.form = savedProblem;
        
        return this.isEditing ? 'Problem updated successfully' : 'Problem created successfully';
      });
    },
    
    
    /**
     * Update tags from input
     */
    updateTags(event) {
      const value = event.target.value;
      this.form.tags = value.split(',').map(tag => tag.trim()).filter(tag => tag);
    },
    
    /**
     * Toggle failure details for a specific test case
     */
    toggleFailureDetails(index) {
      if (this.form.test_cases[index]) {
        this.form.test_cases[index].showFailureDetails = !this.form.test_cases[index].showFailureDetails;
      }
    }
  }
}
</script>

<style scoped>
/* Main Container */
.admin-problem-editor {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: var(--spacing-lg);
  min-height: 100vh;
}

/* Navigation */
.breadcrumb {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-md) 0;
  border-bottom: 2px solid var(--color-bg-border);
}

.breadcrumb-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--color-text-muted);
  text-decoration: none;
  font-weight: 500;
  transition: var(--transition-fast);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-xs);
}

.breadcrumb-link:hover {
  color: var(--color-primary-gradient-start);
  background: var(--color-bg-hover);
}

/* Header Section */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xxl);
  padding: var(--spacing-xl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-base);
  border: 2px solid var(--color-bg-border);
}

.header h2 {
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
  font-weight: 600;
  margin: 0;
}

.actions {
  display: flex;
  gap: var(--spacing-md);
}

/* Button Styling */
.btn {
  padding: var(--spacing-md) var(--spacing-lg);
  border: 2px solid transparent;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-base);
  cursor: pointer;
  transition: var(--transition-base);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  text-decoration: none;
  outline: none;
}

.btn:focus {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-colored);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: var(--color-bg-panel);
  color: var(--color-text-secondary);
  border-color: var(--color-bg-border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

/* Form Sections */
.problem-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xxl);
}

.form-section {
  background: var(--color-bg-panel);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-base);
  transition: var(--transition-fast);
}

.form-section:hover {
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-colored);
}

.form-section h3 {
  margin: 0 0 var(--spacing-xl) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-border);
}

/* Form Groups */
.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-fast);
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  border-color: var(--color-primary-gradient-start);
  outline: none;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input::placeholder,
.form-group textarea::placeholder {
  color: var(--color-text-muted);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-lg);
}

/* Category Selector */
.category-selector {
  --bean-height: 42px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-md);
  margin-top: var(--spacing-sm);
}

.category-option {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-md);
  height: var(--bean-height);
  min-height: var(--bean-height);
  max-height: var(--bean-height);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-xl);
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-sm);
  font-weight: 500;
  box-sizing: border-box;
  flex-shrink: 0;
}

.category-option:hover {
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  transform: translateY(-1px);
}

.category-option.active {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-colored);
}

.category-color {
  width: 14px;
  height: 14px;
  border-radius: var(--radius-circle);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

/* Morphing Category Bean System with Dynamic Sizing */
.category-shell {
  --button-padding: var(--spacing-md);
  --button-min-width: 140px;
  --form-width: clamp(320px, 50vw, 450px);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-md);
  width: fit-content;
  min-width: var(--button-min-width);
  height: var(--bean-height);
  min-height: var(--bean-height);
  max-height: var(--bean-height);
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-xl);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transform-origin: left center;
  transition: all 0.6s cubic-bezier(0.23, 1, 0.320, 1);
  box-shadow: none;
  flex-shrink: 0;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  box-sizing: border-box;
}

.category-shell:hover:not(.expanded) {
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  transform: translateY(-1px);
}

.category-shell.expanded {
  width: var(--form-width);
  min-width: var(--form-width);
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
  box-shadow: var(--shadow-lg);
  cursor: default;
  padding: 0;
  gap: 0;
}

.category-shell.transitioning {
  pointer-events: none;
}

/* Transitioning state - width expands slowly revealing sections */
.category-shell.transitioning:not(.expanded) {
  width: var(--form-width);
  min-width: var(--form-width);
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
  box-shadow: var(--shadow-lg);
  cursor: default;
  /* Maintain button content layout during initial expansion */
  padding: var(--spacing-xs) var(--spacing-md);
  gap: var(--spacing-sm);
}

/* Button Content (collapsed state) - Dynamic Width */
.add-category-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity 0.4s ease;
  color: var(--color-primary-gradient-start);
  font-weight: 500;
  pointer-events: none;
  justify-content: center;
  box-sizing: border-box;
}

.add-category-content.visible {
  opacity: 1;
  pointer-events: auto;
}

.add-icon {
  font-weight: bold;
  font-size: var(--font-size-sm);
  flex-shrink: 0;
}

.add-text {
  white-space: nowrap;
  font-size: var(--font-size-xs);
  flex-shrink: 0;
}

/* Form Content (expanded state) */
.bean-form-content {
  display: flex;
  align-items: center;
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity 0.4s ease 0.15s; /* Progressive reveal after width expansion starts */
  pointer-events: none;
}

.bean-form-content.visible {
  opacity: 1;
  pointer-events: auto;
}

/* Form Segments */
.form-segment {
  display: flex;
  align-items: center;
  height: 100%;
}

.input-segment {
  flex: 1;
  padding: 0 var(--button-padding);
  min-width: 0;
  overflow: hidden;
}

.bean-input {
  width: 100%;
  border: none;
  background: transparent;
  color: var(--color-text-primary);
  outline: none;
  padding: var(--spacing-xs) 0;
  font-size: var(--font-size-sm);
  font-weight: 500;
  line-height: 1.2;
}

.bean-input::placeholder {
  color: var(--color-text-muted);
}

.color-segment {
  width: 48px;
  min-width: 48px;
  justify-content: center;
  border-left: 1px solid var(--color-bg-border);
  border-right: 1px solid var(--color-bg-border);
  background: var(--color-bg-hover);
  flex-shrink: 0;
}

.color-preview-btn {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-circle);
  border: 2px solid var(--color-bg-border);
  cursor: pointer;
  transition: var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.color-preview-btn:hover {
  transform: scale(1.1);
  border-color: var(--color-text-primary);
  box-shadow: var(--shadow-md);
}

.action-segment {
  width: 44px;
  min-width: 44px;
  justify-content: center;
  background: var(--color-bg-hover);
  flex-shrink: 0;
}

.bean-submit-btn {
  background: transparent;
  border: none;
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: var(--transition-fast);
  padding: var(--spacing-xs);
  border-radius: var(--radius-base);
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bean-submit-btn:hover:not(.disabled) {
  background: var(--color-success);
  transform: scale(1.05);
  color: var(--color-text-primary);
}

.bean-submit-btn.disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.5;
}

.bean-error {
  color: var(--color-error-text);
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-sm);
  padding: var(--spacing-md);
  background: var(--color-error-bg);
  border-radius: var(--radius-base);
  border-left: 4px solid var(--color-error);
  max-width: var(--form-width);
}

/* Color Picker Popup - Enhanced */
.color-picker-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.2);
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.color-picker-popup {
  background: var(--color-bg-panel);
  border: 2px solid var(--color-primary-gradient-start);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  animation: popupFadeIn 0.2s ease-out;
}

.popup-content {
  padding: var(--spacing-md);
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-sm);
}

.color-option {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-circle);
  cursor: pointer;
  border: 3px solid transparent;
  transition: var(--transition-fast);
}

.color-option:hover {
  transform: scale(1.15);
  border-color: var(--color-text-primary);
  box-shadow: var(--shadow-md);
}

.color-option.active {
  border-color: var(--color-text-primary);
  transform: scale(1.1);
  box-shadow: var(--shadow-base);
}

/* Test Cases - Improved */

.test-results-summary {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-panel);
  border: 2px solid var(--color-success);
  border-radius: var(--radius-base);
}

.results-summary-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  font-weight: 600;
  color: var(--color-text-primary);
}

.success-icon {
  color: var(--color-success);
  font-size: var(--font-size-lg);
  font-weight: bold;
}

.failure-icon {
  color: var(--color-error);
  font-size: var(--font-size-lg);
  font-weight: bold;
}

.test-cases-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
}

.action-group {
  display: flex;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.test-solution-btn {
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.test-cases-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.test-case {
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-hover);
  transition: var(--transition-fast);
  overflow: hidden;
}

.test-case:hover {
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-colored);
}

.test-case-error {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.test-case-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-panel);
  border-bottom: 2px solid var(--color-bg-border);
}

.test-case-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.test-status {
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.status-passed {
  color: var(--color-success);
  background: rgba(16, 185, 129, 0.1);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-success);
}

.status-failed {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.1);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-error);
}

.test-case-number {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.test-case-options {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.test-case-options label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
}

.test-case-options label:hover {
  color: var(--color-text-primary);
}

.btn-remove {
  background: var(--color-error-bg);
  border: 2px solid var(--color-error);
  color: var(--color-error);
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-circle);
  transition: var(--transition-fast);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-remove:hover {
  background: var(--color-error);
  color: var(--color-text-primary);
  transform: scale(1.1);
}

.test-case-content {
  padding: var(--spacing-lg);
}

.test-case-error-message {
  color: var(--color-error-text);
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-error-bg);
  border-radius: var(--radius-base);
  border-left: 3px solid var(--color-error);
}

/* Test Failure Details */
.test-failure-details {
  margin-top: var(--spacing-md);
  border-top: 1px solid var(--color-bg-border);
  padding-top: var(--spacing-md);
}

.failure-content {
  background: var(--color-error-bg);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-base);
  overflow: hidden;
}

.failure-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: transparent;
  border: none;
  color: var(--color-error-text);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-fast);
  text-align: left;
}

.failure-toggle:hover {
  background: rgba(239, 68, 68, 0.1);
}

.toggle-icon {
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
  color: var(--color-error);
}

.failure-toggle.expanded .toggle-icon {
  transform: rotate(0deg);
}

.failure-details {
  padding: var(--spacing-md);
  border-top: 1px solid var(--color-error);
  background: rgba(239, 68, 68, 0.05);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
  font-size: var(--font-size-sm);
}

.detail-item {
  margin-bottom: var(--spacing-sm);
  line-height: 1.5;
}

.detail-item:last-child {
  margin-bottom: 0;
}

.error-detail {
  color: var(--color-error-text);
  font-weight: 500;
}


/* Code Editor */
.code-editor {
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  overflow: hidden;
  transition: var(--transition-fast);
}

.code-editor:focus-within {
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.code-textarea {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
  font-size: var(--font-size-sm);
  line-height: 1.5;
  resize: vertical;
  min-height: 200px;
}


/* Error Message Transition */
.error-slide-enter-active,
.error-slide-leave-active {
  transition: all 0.3s ease;
}

.error-slide-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.error-slide-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}


@keyframes popupFadeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .admin-problem-editor {
    padding: var(--spacing-md);
  }
  
  .header {
    flex-direction: column;
    gap: var(--spacing-lg);
    text-align: center;
  }
  
  .actions {
    width: 100%;
    justify-content: center;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .category-shell {
    max-width: 100%;
    width: 100%;
  }
  
  .input-segment {
    min-width: 150px;
  }
  
  .test-cases-actions {
    flex-direction: column;
    gap: var(--spacing-lg);
  }
  
  .action-group {
    justify-content: center;
  }
  
  .test-solution-btn {
    width: 100%;
    order: -1; /* Put test button first on mobile */
  }
  
  .btn {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .form-section {
    padding: var(--spacing-lg);
  }
  
  .category-selector {
    flex-direction: column;
    align-items: stretch;
  }
  
  .category-option {
    justify-content: center;
  }
}
</style>
