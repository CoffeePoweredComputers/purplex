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
          
          <!-- Editor toolbar -->
          <div class="editor-toolbar">
            <div class="toolbar-left">
              <!-- Zoom controls -->
              <div class="zoom-controls">
                <button
                  type="button"
                  @click="decreaseFontSize"
                  :disabled="editorFontSize <= 12"
                  class="zoom-btn"
                  title="Decrease font size"
                >
                  <span class="zoom-icon">−</span>
                </button>
                <span class="zoom-display">{{ Math.round((editorFontSize / 14) * 100) }}%</span>
                <button
                  type="button"
                  @click="increaseFontSize"
                  :disabled="editorFontSize >= 24"
                  class="zoom-btn"
                  title="Increase font size"
                >
                  <span class="zoom-icon">+</span>
                </button>
              </div>

              <!-- Theme selector -->
              <div class="theme-selector">
                <select v-model="editorTheme" @change="updateTheme" class="theme-dropdown">
                  <option value="monokai">Monokai</option>
                  <option value="github">GitHub</option>
                  <option value="clouds_midnight">Clouds Midnight</option>
                  <option value="chrome">Chrome</option>
                  <option value="solarized_dark">Solarized Dark</option>
                  <option value="solarized_light">Solarized Light</option>
                  <option value="dracula">Dracula</option>
                  <option value="tomorrow_night">Tomorrow Night</option>
                </select>
              </div>
            </div>

          </div>

          <!-- Editor component -->
          <div class="code-editor">
            <Editor
              ref="editor"
              :value="String(form.reference_solution || '')"
              @update:value="updateReferenceSolution($event)"
              :height="'300px'"
              :width="'100%'"
              :theme="editorTheme"
              :showGutter="true"
              :mode="'python'"
              :lang="'python'"
            />
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
        
        <!-- Simplified Actions Bar -->
        <div class="test-actions">
          <div class="left-actions">
            <button type="button" @click="addTestCase" class="btn-secondary">
              + Add Test
            </button>
            <button
              type="button"
              @click="generateTestCases"
              :disabled="ui.loading || !canGenerateTestCases"
              class="btn-secondary"
              :title="canGenerateTestCasesReason || 'Generate one test case using AI'"
            >
              {{ ui.loading ? 'Generating...' : '+ AI Generate' }}
            </button>
          </div>
          
          <button 
            @click="testProblem" 
            :disabled="!canTest || ui.loading" 
            class="btn-primary"
            :title="canTestReason || 'Test your reference solution against all test cases'"
          >
            {{ ui.loading ? 'Testing...' : 'Test All Cases' }}
          </button>
        </div>

        <!-- Simplified Test Cases List -->
        <div class="test-cases-list">
          <div
            v-for="(testCase, index) in form.test_cases"
            :key="index"
            class="test-case"
            :class="{ 
              error: testCase.error, 
              passed: isTestPassed(index), 
              failed: isTestFailed(index) 
            }"
          >
            <!-- Single row with everything -->
            <div class="test-case-row" :style="{ '--param-count': getParameterCount() }">
              <span class="test-number">{{ index + 1 }}</span>
              
              <!-- Dynamic parameter fields based on function signature -->
              <div v-if="functionParameters.length > 0" class="smart-parameters">
                <div 
                  v-for="(param, paramIndex) in functionParameters" 
                  :key="paramIndex" 
                  class="smart-param-field"
                >
                  <div class="param-input-container">
                    <input 
                      :value="getParameterValue(testCase, paramIndex)"
                      @input="updateParameterValue(testCase, paramIndex, $event.target.value)"
                      :placeholder="getParameterPlaceholder(param.type)" 
                      class="param-input" 
                      :class="{ 'param-error': getParameterError(testCase, paramIndex) }"
                    />
                    <div 
                      class="param-type-badge" 
                      :class="getParameterTypeClass(testCase, paramIndex)"
                      :title="getParameterTypeInfo(testCase, paramIndex)"
                    >
                      {{ getParameterDetectedType(testCase, paramIndex) }}
                    </div>
                  </div>
                  <div class="param-label">
                    <span class="param-name">{{ param.name }}</span>
                    <span class="param-expected-type">: {{ param.type }}</span>
                  </div>
                </div>
              </div>
              
              <!-- Fallback to single input if no function signature -->
              <input 
                v-else
                :value="getTestCaseInputsDisplay(testCase)"
                @input="updateTestCaseInputs(testCase, $event.target.value)"
                placeholder="Inputs: [1, 2]" 
                class="inputs-field" 
              />
              
              <!-- Expected output field -->
              <div class="output-field-container">
                <div class="output-input-container">
                  <input 
                    :value="getTestCaseExpectedDisplay(testCase)"
                    @input="updateTestCaseExpected(testCase, $event.target.value)"
                    :placeholder="getOutputPlaceholder()" 
                    class="output-field" 
                    :class="{ 'param-error': testCase.expectedOutputError }"
                  />
                  <div 
                    class="param-type-badge" 
                    :class="getOutputTypeClass(testCase)"
                    :title="getOutputTypeInfo(testCase)"
                  >
                    {{ getOutputDetectedType(testCase) }}
                  </div>
                </div>
                <div class="param-label">
                  <span class="param-name">output</span>
                  <span class="param-expected-type">: {{ getReturnType() }}</span>
                </div>
              </div>
              
              <!-- Status and actions -->
              <span v-if="ui.testResults" class="status-badge" :class="getStatusClass(index)">
                {{ getStatusText(index) }}
              </span>
              <button @click="removeTestCase(index)" class="remove-btn">×</button>
            </div>
            
            <!-- Error message directly below if exists -->
            <div v-if="testCase.error" class="error-msg">{{ testCase.error }}</div>
            
            <!-- Failure details directly below if failed -->
            <div v-if="isTestFailed(index)" class="failure-msg">
              Expected: {{ JSON.stringify(ui.testResults.results[index].expected_output) }} | 
              Got: {{ JSON.stringify(ui.testResults.results[index].actual_output) }}
              <span v-if="ui.testResults.results[index].error"> | Error: {{ ui.testResults.results[index].error }}</span>
            </div>
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
import Editor from '@/features/editor/Editor.vue'
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
    NotificationToast,
    Editor
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
        problem_type: 'eipl',
        category_ids: [],
        function_name: '',
        function_signature: '',
        reference_solution: '',
        hints: '',
        tags: [],
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
      
      // Function signature parsing
      functionParameters: [],
      returnType: 'Any',
      
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
      clickOutsideHandler: null,
      
      // Editor settings
      editorFontSize: 14,
      editorTheme: 'monokai'
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
      const title = (this.form.title || '').toString().trim();
      const functionName = (this.form.function_name || '').toString().trim();
      const referenceSolution = (this.form.reference_solution || '').toString().trim();
      
      if (!title) errors.push('Title is required');
      if (!functionName) errors.push('Function name is required');
      if (!referenceSolution) errors.push('Reference solution is required');
      if (this.form.test_cases.length === 0) errors.push('At least one test case required');
      if (this.form.test_cases.some(tc => tc.error)) errors.push('Fix test case errors');
      return errors;
    },
    canSave() {
      const title = (this.form.title || '').toString().trim();
      const description = (this.form.description || '').toString().trim();
      
      return !this.ui.loading && 
             this.validationErrors.length === 0 &&
             (title.length > 0 || 
              description.length > 0 ||
              this.form.test_cases.length > 0);
    },
    canTest() {
      const functionName = (this.form.function_name || '').toString().trim();
      const referenceSolution = (this.form.reference_solution || '').toString().trim();
      
      return !this.ui.loading &&
             functionName.length > 0 &&
             referenceSolution.length > 0 &&
             this.form.test_cases.length > 0 &&
             this.form.test_cases.every(tc => !tc.error);
    },
    canTestReason() {
      const functionName = (this.form.function_name || '').toString().trim();
      const referenceSolution = (this.form.reference_solution || '').toString().trim();
      
      if (this.ui.loading) return "Currently loading...";
      if (!functionName) return "Function name required";
      if (!referenceSolution) return "Reference solution required";
      if (this.form.test_cases.length === 0) return "Add at least one test case";
      if (this.form.test_cases.some(tc => tc.error)) return "Fix test case errors first";
      return null; // Can test
    },
    canGenerateTestCases() {
      const functionName = (this.form.function_name || '').toString().trim();
      const referenceSolution = (this.form.reference_solution || '').toString().trim();
      
      return !this.ui.loading &&
             functionName.length > 0 &&
             referenceSolution.length > 0;
    },
    canGenerateTestCasesReason() {
      const functionName = (this.form.function_name || '').toString().trim();
      const referenceSolution = (this.form.reference_solution || '').toString().trim();
      
      if (this.ui.loading) return "Currently loading...";
      if (!functionName) return "Function name required for AI generation";
      if (!referenceSolution) return "Reference solution required for AI generation";
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
    },
    currentTheme() {
      // Return the theme name directly as the Editor component handles the mapping
      return this.editorTheme;
    }
  },
  async mounted() {
    // Configure ACE editor base path
    if (window.ace) {
      window.ace.config.set('basePath', 'https://cdn.jsdelivr.net/npm/ace-builds@1.15.0/src-noconflict/');
    }
    
    try {
      await Promise.all([
        this.loadCategories(),
        // Don't call loadProblem here as the watcher will handle it
        !this.isEditing ? Promise.resolve(this.addTestCase()) : Promise.resolve()
      ]);
      
      // Parse function signature if available
      this.parseFunctionSignature();
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
    },
    
    // Watch function signature changes
    'form.function_signature'() {
      this.parseFunctionSignature();
      // Re-convert existing test case inputs when signature changes
      this.$nextTick(() => {
        this.convertInputsToSmartParameters();
      });
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

    /**
     * Normalize problem data to ensure proper types
     */
    normalizeProblemData(problemData) {
      // Extract category IDs from categories objects
      if (problemData.categories && Array.isArray(problemData.categories)) {
        problemData.category_ids = problemData.categories.map(cat => cat.id);
      } else if (!problemData.category_ids) {
        problemData.category_ids = [];
      }
      
      // Ensure tags is an array
      if (!problemData.tags) {
        problemData.tags = [];
      }
      
      // Ensure problem_type has a default value
      if (!problemData.problem_type) {
        problemData.problem_type = 'eipl';
      }
      
      // DEBUG: Log reference solution details
      console.log('=== DEBUGGING REFERENCE SOLUTION ===');
      console.log('Original problemData.reference_solution:', problemData.reference_solution);
      console.log('Type:', typeof problemData.reference_solution);
      console.log('Is object?', typeof problemData.reference_solution === 'object');
      console.log('JSON stringify:', JSON.stringify(problemData.reference_solution));
      
      // Ensure reference_solution is always a string
      if (problemData.reference_solution && typeof problemData.reference_solution !== 'string') {
        console.log('Converting reference_solution from object to string');
        console.log('Object value:', problemData.reference_solution);
        problemData.reference_solution = String(problemData.reference_solution);
        console.log('After conversion:', problemData.reference_solution);
      } else {
        console.log('Reference solution is already a string:', problemData.reference_solution);
      }
      
      console.log('Final reference_solution:', problemData.reference_solution);
      console.log('=== END DEBUGGING ===');
      
      // Add error tracking to test cases and convert to smart parameter format
      if (problemData.test_cases) {
        problemData.test_cases = problemData.test_cases.map(tc => ({
          ...tc,
          error: null,
          // Initialize smart parameter arrays
          parameterValues: [],
          parameterErrors: [],
          parameterDetectedTypes: [],
          expectedOutputError: null,
          expectedOutputDetectedType: 'Any'
        }));
      }
      
      return problemData;
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
        this.form = this.normalizeProblemData(loadedProblem);
        
        // Parse function signature first to get parameter info
        this.parseFunctionSignature();
        
        // Convert existing inputs to smart parameter format
        this.convertInputsToSmartParameters();
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
          const colorPicker = document.querySelector('.color-picker-popup');
          const colorOverlay = document.querySelector('.color-picker-overlay');
          
          if (event.target && 
              categoryShell && 
              !categoryShell.contains(event.target) &&
              (!colorPicker || !colorPicker.contains(event.target)) &&
              (!colorOverlay || !colorOverlay.contains(event.target))) {
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
      const newTestCase = {
        inputs: [],
        expected_output: null,
        description: '',
        order: this.form.test_cases.length,
        error: null,
        // Smart parameter tracking
        parameterValues: [],
        parameterErrors: [],
        parameterDetectedTypes: [],
        expectedOutputError: null,
        expectedOutputDetectedType: 'Any'
      };
      
      // Initialize parameter arrays based on current function signature
      for (let i = 0; i < this.functionParameters.length; i++) {
        newTestCase.parameterValues.push('');
        newTestCase.parameterErrors.push(null);
        newTestCase.parameterDetectedTypes.push('Any');
      }
      
      this.form.test_cases.push(newTestCase);
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
        // Parse and set the value
        testCase.expected_output = this.parseValueForBackend(value);
        
        // Detect and validate type for expected output
        if (!value.trim()) {
          testCase.expectedOutputDetectedType = 'Any';
          testCase.expectedOutputError = null;
        } else {
          const detectedType = this.autoDetectType(value);
          testCase.expectedOutputDetectedType = detectedType;
          
          // Get expected return type
          const expectedType = this.simplifyType(this.returnType);
          
          // Validate type match
          if (expectedType !== 'Any' && detectedType !== 'invalid' && !this.typesMatch(detectedType, expectedType)) {
            testCase.expectedOutputError = `Expected ${expectedType}, got ${detectedType}`;
          } else if (detectedType === 'invalid') {
            testCase.expectedOutputError = 'Invalid input format';
          } else {
            testCase.expectedOutputError = null;
          }
        }
        
        testCase.error = null;
      } catch (e) {
        testCase.error = 'Invalid input for expected output';
        testCase.expectedOutputError = 'Parse error';
      }
    },
    
    
    async testProblem() {
      if (!this.canTest) {
        // Show specific reason instead of generic warning
        const reason = this.canTestReason || 'Cannot test problem in current state';
        this.$toast?.warning?.(reason) || console.warn(reason);
        return;
      }
      
      // Validate test cases for errors
      for (let i = 0; i < this.form.test_cases.length; i++) {
        if (this.form.test_cases[i].error) {
          this.$toast?.error?.(`Please fix errors in test case ${i + 1}`) || console.error(`Test case ${i + 1} has errors`);
          return;
        }
      }
      
      await this.executeAction('test problem', async () => {
        // Ensure all test cases have updated inputs from smart parameters
        this.form.test_cases.forEach(testCase => {
          this.updateInputsFromParameters(testCase);
        });
        
        const testData = {
          title: this.form.title,
          description: this.form.description,
          function_name: this.form.function_name,
          reference_solution: this.getApiSafeString(this.form.reference_solution, 'reference_solution'),
          test_cases: this.form.test_cases.filter(tc => {
            // Debug: Log what we're filtering
            console.log('Filtering test case:', tc, 'Has error:', tc.error, 'Has inputs:', tc.inputs);
            return !tc.error;
          }).map(tc => ({
            inputs: tc.inputs || [],
            expected_output: tc.expected_output,
            description: tc.description || '',
            order: tc.order
          }))
        };
        
        // Debug: Log the data being sent
        console.log('Testing with data:', testData);
        
        // Check if we have any test cases to test
        if (!testData.test_cases || testData.test_cases.length === 0) {
          throw new Error('No valid test cases found. Please add test cases with inputs and expected outputs.');
        }
        
        this.ui.testResults = await problemService.testProblem(testData);
        
        // Debug: Log the test results received
        console.log('Test results received:', this.ui.testResults);
        console.log('Test results structure:', {
          success: this.ui.testResults.success,
          passed: this.ui.testResults.passed,
          total: this.ui.testResults.total,
          results: this.ui.testResults.results
        });
        
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
          reference_solution: this.getApiSafeString(this.form.reference_solution, 'reference_solution')
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
            error: null
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
        console.log('Form test cases before filtering:', this.form.test_cases);
        
        const problemData = {
          title: this.getApiSafeString(this.form.title),
          description: this.getApiSafeString(this.form.description),
          difficulty: this.form.difficulty,
          problem_type: this.form.problem_type,
          category_ids: Array.isArray(this.form.category_ids) ? this.form.category_ids : [],
          function_name: this.getApiSafeString(this.form.function_name),
          function_signature: this.getApiSafeString(this.form.function_signature),
          reference_solution: this.getApiSafeString(this.form.reference_solution, 'reference_solution'),
          hints: this.getApiSafeString(this.form.hints),
          tags: Array.isArray(this.form.tags) ? this.form.tags : [],
          test_cases: this.form.test_cases.filter(tc => {
            // Debug logging
            console.log('Validating test case:', tc);
            
            // Filter out test cases with errors or missing required fields
            if (tc.error) {
              console.log('Filtered out due to error:', tc.error);
              return false;
            }
            if (!Array.isArray(tc.inputs)) {
              console.log('Filtered out due to invalid inputs:', tc.inputs);
              return false;
            }
            if (tc.expected_output === null || tc.expected_output === undefined) {
              console.log('Filtered out due to missing expected_output:', tc.expected_output);
              return false;
            }
            console.log('Test case is valid');
            return true;
          }).map(tc => ({
            inputs: tc.inputs,
            expected_output: tc.expected_output,
            description: tc.description || '',
            order: Number(tc.order) || 0
          }))
        };
        
        console.log('Problem data test cases after filtering:', problemData.test_cases);
        
        // Additional validation
        if (!problemData.title) {
          throw new Error('Title is required');
        }
        if (!problemData.function_name) {
          throw new Error('Function name is required');
        }
        if (!problemData.reference_solution) {
          throw new Error('Reference solution is required');
        }
        if (problemData.test_cases.length === 0) {
          throw new Error('At least one valid test case is required. Please check that all test cases have inputs and expected output.');
        }
        
        // Validate test cases individually
        problemData.test_cases.forEach((tc, index) => {
          if (!Array.isArray(tc.inputs)) {
            throw new Error(`Test case ${index + 1}: inputs must be an array`);
          }
          if (tc.expected_output === null || tc.expected_output === undefined) {
            throw new Error(`Test case ${index + 1}: expected output is required`);
          }
        });
        
        console.log('Sending problem data:', problemData);
        
        let savedProblem;
        
        if (this.isEditing) {
          savedProblem = await problemService.updateProblem(this.currentProblemSlug, problemData);
        } else {
          savedProblem = await problemService.createProblem(problemData);
          // Navigate to edit mode for the new problem
          await this.$router.push(`/admin/problems/${savedProblem.slug}/edit`);
        }
        
        // Update local state with saved data
        this.form = this.normalizeProblemData(savedProblem);
        
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
     * Increase editor font size
     */
    increaseFontSize() {
      if (this.editorFontSize < 24) {
        this.editorFontSize += 2;
        this.updateEditorFontSize();
      }
    },
    
    /**
     * Decrease editor font size
     */
    decreaseFontSize() {
      if (this.editorFontSize > 12) {
        this.editorFontSize -= 2;
        this.updateEditorFontSize();
      }
    },
    
    /**
     * Update editor font size
     */
    updateEditorFontSize() {
      if (this.$refs.editor && this.$refs.editor.editor) {
        this.$refs.editor.editor.setFontSize(this.editorFontSize);
      }
    },
    
    /**
     * Update editor theme
     */
    updateTheme() {
      // Theme updates automatically through the reactive prop binding
    },
    
    /**
     * Check if test case passed
     */
    isTestPassed(index) {
      return this.ui.testResults && 
             this.ui.testResults.results && 
             this.ui.testResults.results[index] && 
             this.ui.testResults.results[index].passed;
    },
    
    /**
     * Check if test case failed
     */
    isTestFailed(index) {
      return this.ui.testResults && 
             this.ui.testResults.results && 
             this.ui.testResults.results[index] && 
             !this.ui.testResults.results[index].passed;
    },
    
    /**
     * Get status class for test case
     */
    getStatusClass(index) {
      if (this.isTestPassed(index)) return 'passed';
      if (this.isTestFailed(index)) return 'failed';
      return '';
    },
    
    /**
     * Get status text for test case
     */
    getStatusText(index) {
      if (this.isTestPassed(index)) return '✓';
      if (this.isTestFailed(index)) return '✗';
      return '';
    },
    
    // === Function Signature Parsing ===
    
    /**
     * Parse function signature to extract parameters and return type
     */
    parseFunctionSignature() {
      if (!this.form.function_signature) {
        this.functionParameters = [];
        this.returnType = 'Any';
        return;
      }
      
      const signature = this.form.function_signature.trim();
      
      // Parse function signature pattern: def func_name(param1: type1, param2: type2) -> return_type:
      const regex = /def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*(.+?))?:/;
      const match = signature.match(regex);
      
      if (!match) {
        this.functionParameters = [];
        this.returnType = 'Any';
        return;
      }
      
      const [_, functionName, paramsStr, returnTypeStr] = match;
      
      // Parse parameters
      this.functionParameters = this.parseParameters(paramsStr || '');
      this.returnType = returnTypeStr?.trim() || 'Any';
      
      // Initialize parameter data in existing test cases
      this.initializeParameterData();
    },
    
    /**
     * Parse parameter string into parameter objects
     */
    parseParameters(paramsStr) {
      if (!paramsStr.trim()) return [];
      
      const params = [];
      
      // Handle typed parameters: param: type
      const paramRegex = /(\w+)\s*:\s*([^,]+)/g;
      let match;
      
      while ((match = paramRegex.exec(paramsStr)) !== null) {
        params.push({
          name: match[1],
          type: match[2].trim(),
          simplifiedType: this.simplifyType(match[2].trim())
        });
      }
      
      // Handle untyped parameters if no typed ones found
      if (params.length === 0) {
        const simpleParams = paramsStr.split(',').map(p => p.trim()).filter(p => p);
        simpleParams.forEach(param => {
          params.push({
            name: param,
            type: 'Any',
            simplifiedType: 'Any'
          });
        });
      }
      
      return params;
    },
    
    /**
     * Simplify complex types for placeholder generation
     */
    simplifyType(typeStr) {
      const lower = typeStr.toLowerCase();
      if (lower.includes('list') || lower.includes('[]')) return 'list';
      if (lower.includes('dict') || lower.includes('{}')) return 'dict';
      if (lower.includes('tuple')) return 'tuple';
      if (lower.includes('set')) return 'set';
      if (lower.includes('bool')) return 'bool';
      if (lower.includes('int')) return 'int';
      if (lower.includes('float')) return 'float';
      if (lower.includes('str')) return 'str';
      return 'Any';
    },
    
    /**
     * Convert existing inputs arrays to smart parameter format
     */
    convertInputsToSmartParameters() {
      if (!this.form.test_cases || this.functionParameters.length === 0) {
        return;
      }
      
      this.form.test_cases.forEach(testCase => {
        // Convert inputs array to parameterValues
        if (testCase.inputs && Array.isArray(testCase.inputs)) {
          testCase.parameterValues = [];
          testCase.parameterErrors = [];
          testCase.parameterDetectedTypes = [];
          
          // Convert each input value to string format for the UI
          testCase.inputs.forEach((value, index) => {
            if (index < this.functionParameters.length) {
              // Convert value to string representation
              const stringValue = this.formatValueForInput(value);
              testCase.parameterValues[index] = stringValue;
              
              // Detect and validate the type
              this.detectParameterType(testCase, index, stringValue);
            }
          });
          
          // Fill remaining parameters with empty values
          while (testCase.parameterValues.length < this.functionParameters.length) {
            testCase.parameterValues.push('');
            testCase.parameterErrors.push(null);
            testCase.parameterDetectedTypes.push('Any');
          }
        }
        
        // Convert expected_output for type detection
        if (testCase.expected_output !== null && testCase.expected_output !== undefined) {
          const outputString = this.formatValueForInput(testCase.expected_output);
          const detectedType = this.autoDetectType(outputString);
          testCase.expectedOutputDetectedType = detectedType;
          
          // Validate against return type
          const expectedType = this.simplifyType(this.returnType);
          if (expectedType !== 'Any' && detectedType !== 'invalid' && !this.typesMatch(detectedType, expectedType)) {
            testCase.expectedOutputError = `Expected ${expectedType}, got ${detectedType}`;
          } else {
            testCase.expectedOutputError = null;
          }
        }
      });
    },
    
    /**
     * Format a JavaScript value for input display (reverse of parseValueForBackend)
     */
    formatValueForInput(value) {
      if (value === null || value === undefined) return 'None';
      if (typeof value === 'boolean') return value ? 'True' : 'False';
      if (typeof value === 'string') return value; // Don't add quotes for display
      if (Array.isArray(value) || typeof value === 'object') {
        return JSON.stringify(value);
      }
      return String(value);
    },
    
    /**
     * Initialize parameter data for existing test cases
     */
    initializeParameterData() {
      this.form.test_cases.forEach(testCase => {
        // Initialize parameter values array if not exists
        if (!testCase.parameterValues) {
          testCase.parameterValues = [];
        }
        
        // Initialize parameter errors array if not exists  
        if (!testCase.parameterErrors) {
          testCase.parameterErrors = [];
        }
        
        // Initialize parameter detected types array if not exists
        if (!testCase.parameterDetectedTypes) {
          testCase.parameterDetectedTypes = [];
        }
        
        // Ensure arrays have correct length
        while (testCase.parameterValues.length < this.functionParameters.length) {
          testCase.parameterValues.push('');
          testCase.parameterErrors.push(null);
          testCase.parameterDetectedTypes.push('Any');
        }
        
        // Initialize expected output error tracking
        if (!testCase.expectedOutputError) {
          testCase.expectedOutputError = null;
        }
        
        if (!testCase.expectedOutputDetectedType) {
          testCase.expectedOutputDetectedType = 'Any';
        }
      });
    },
    
    // === Parameter Input Methods ===
    
    /**
     * Get parameter count for grid layout
     */
    getParameterCount() {
      return this.functionParameters.length || 1;
    },
    
    /**
     * Get parameter value for a specific test case and parameter index
     */
    getParameterValue(testCase, paramIndex) {
      if (!testCase.parameterValues || paramIndex >= testCase.parameterValues.length) {
        return '';
      }
      return testCase.parameterValues[paramIndex] || '';
    },
    
    /**
     * Update parameter value and perform type detection
     */
    updateParameterValue(testCase, paramIndex, value) {
      // Ensure arrays exist
      if (!testCase.parameterValues) testCase.parameterValues = [];
      if (!testCase.parameterErrors) testCase.parameterErrors = [];
      if (!testCase.parameterDetectedTypes) testCase.parameterDetectedTypes = [];
      
      // Ensure arrays are long enough
      while (testCase.parameterValues.length <= paramIndex) {
        testCase.parameterValues.push('');
        testCase.parameterErrors.push(null);
        testCase.parameterDetectedTypes.push('Any');
      }
      
      // Update value
      testCase.parameterValues[paramIndex] = value;
      
      // Detect and validate type
      this.detectParameterType(testCase, paramIndex, value);
      
      // Update the inputs array for backend compatibility
      this.updateInputsFromParameters(testCase);
    },
    
    /**
     * Detect parameter type and validate against expected type
     */
    detectParameterType(testCase, paramIndex, value) {
      if (!value.trim()) {
        testCase.parameterDetectedTypes[paramIndex] = 'Any';
        testCase.parameterErrors[paramIndex] = null;
        return;
      }
      
      const detectedType = this.autoDetectType(value);
      testCase.parameterDetectedTypes[paramIndex] = detectedType;
      
      // Get expected type
      const expectedType = this.functionParameters[paramIndex]?.simplifiedType || 'Any';
      
      // Validate type match
      if (expectedType !== 'Any' && detectedType !== 'invalid' && !this.typesMatch(detectedType, expectedType)) {
        testCase.parameterErrors[paramIndex] = `Expected ${expectedType}, got ${detectedType}`;
      } else if (detectedType === 'invalid') {
        testCase.parameterErrors[paramIndex] = 'Invalid input format';
      } else {
        testCase.parameterErrors[paramIndex] = null;
      }
    },
    
    /**
     * Auto-detect type from input string
     */
    autoDetectType(value) {
      const trimmed = value.trim();
      
      // None/null
      if (/^(None|null|none)$/i.test(trimmed)) return 'None';
      
      // Boolean
      if (/^(true|false|True|False)$/i.test(trimmed)) return 'bool';
      
      // Integer
      if (/^-?\d+$/.test(trimmed)) return 'int';
      
      // Float
      if (/^-?\d*\.\d+$/.test(trimmed)) return 'float';
      
      // List
      if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
        try {
          JSON.parse(trimmed);
          return 'list';
        } catch {
          return 'invalid';
        }
      }
      
      // Dict
      if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
        try {
          JSON.parse(trimmed);
          return 'dict';
        } catch {
          return 'invalid';
        }
      }
      
      // Tuple (represented as array in JSON)
      if (trimmed.startsWith('(') && trimmed.endsWith(')')) {
        try {
          const arrayStr = trimmed.replace(/^\(/, '[').replace(/\)$/, ']');
          JSON.parse(arrayStr);
          return 'tuple';
        } catch {
          return 'invalid';
        }
      }
      
      // String (quoted or unquoted)
      if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
          (trimmed.startsWith("'") && trimmed.endsWith("'")) ||
          /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(trimmed)) {
        return 'str';
      }
      
      return 'str'; // Default to string for other inputs
    },
    
    /**
     * Check if detected type matches expected type
     */
    typesMatch(detected, expected) {
      if (expected === 'Any') return true;
      if (detected === expected) return true;
      
      // Allow int to match float
      if (expected === 'float' && detected === 'int') return true;
      
      return false;
    },
    
    /**
     * Update the inputs array from parameter values (for backend compatibility)
     */
    updateInputsFromParameters(testCase) {
      if (!testCase.parameterValues || this.functionParameters.length === 0) {
        return;
      }
      
      const inputs = testCase.parameterValues.map(value => {
        if (!value.trim()) return null;
        return this.parseValueForBackend(value);
      });
      
      testCase.inputs = inputs;
    },
    
    /**
     * Parse value string to actual JavaScript value for backend
     */
    parseValueForBackend(value) {
      const trimmed = value.trim();
      
      if (!trimmed) return null;
      if (/^(None|null|none)$/i.test(trimmed)) return null;
      if (/^(true|True)$/i.test(trimmed)) return true;
      if (/^(false|False)$/i.test(trimmed)) return false;
      if (/^-?\d+$/.test(trimmed)) return parseInt(trimmed);
      if (/^-?\d*\.\d+$/.test(trimmed)) return parseFloat(trimmed);
      
      // Try to parse JSON for collections
      if ((trimmed.startsWith('[') && trimmed.endsWith(']')) ||
          (trimmed.startsWith('{') && trimmed.endsWith('}'))) {
        try {
          return JSON.parse(trimmed);
        } catch {
          return trimmed;
        }
      }
      
      // Handle tuple notation
      if (trimmed.startsWith('(') && trimmed.endsWith(')')) {
        try {
          const arrayStr = trimmed.replace(/^\(/, '[').replace(/\)$/, ']');
          return JSON.parse(arrayStr);
        } catch {
          return trimmed;
        }
      }
      
      // Remove quotes from strings
      if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
          (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
        return trimmed.slice(1, -1);
      }
      
      return trimmed;
    },
    
    /**
     * Get parameter error for a specific test case and parameter index
     */
    getParameterError(testCase, paramIndex) {
      if (!testCase.parameterErrors || paramIndex >= testCase.parameterErrors.length) {
        return null;
      }
      return testCase.parameterErrors[paramIndex];
    },
    
    /**
     * Get detected type for a parameter
     */
    getParameterDetectedType(testCase, paramIndex) {
      if (!testCase.parameterDetectedTypes || paramIndex >= testCase.parameterDetectedTypes.length) {
        return 'Any';
      }
      return testCase.parameterDetectedTypes[paramIndex] || 'Any';
    },
    
    /**
     * Get CSS class for parameter type badge
     */
    getParameterTypeClass(testCase, paramIndex) {
      const detectedType = this.getParameterDetectedType(testCase, paramIndex);
      const hasError = this.getParameterError(testCase, paramIndex);
      
      if (hasError) return 'type-error';
      
      if (['int', 'float'].includes(detectedType)) return 'type-number';
      if (detectedType === 'str') return 'type-string';
      if (detectedType === 'bool') return 'type-boolean';
      if (['list', 'dict', 'tuple', 'set'].includes(detectedType)) return 'type-collection';
      if (detectedType === 'None') return 'type-none';
      if (detectedType === 'invalid') return 'type-invalid';
      
      return 'type-any';
    },
    
    /**
     * Get type info tooltip
     */
    getParameterTypeInfo(testCase, paramIndex) {
      const detectedType = this.getParameterDetectedType(testCase, paramIndex);
      const expectedType = this.functionParameters[paramIndex]?.type || 'Any';
      const error = this.getParameterError(testCase, paramIndex);
      
      if (error) return error;
      return `Detected: ${detectedType} | Expected: ${expectedType}`;
    },
    
    /**
     * Get placeholder for parameter input
     */
    getParameterPlaceholder(type) {
      const simplified = this.simplifyType(type);
      const placeholders = {
        'int': '42',
        'float': '3.14',
        'str': '"hello"',
        'bool': 'true',
        'list': '[1, 2, 3]',
        'dict': '{"key": "value"}',
        'tuple': '(1, 2, 3)',
        'set': '{1, 2, 3}',
        'None': 'None'
      };
      return placeholders[simplified] || 'value';
    },
    
    // === Output Field Methods ===
    
    /**
     * Get return type for output field
     */
    getReturnType() {
      return this.returnType;
    },
    
    /**
     * Get placeholder for output field
     */
    getOutputPlaceholder() {
      return this.getParameterPlaceholder(this.returnType);
    },
    
    /**
     * Get detected type for output
     */
    getOutputDetectedType(testCase) {
      return testCase.expectedOutputDetectedType || 'Any';
    },
    
    /**
     * Get CSS class for output type badge
     */
    getOutputTypeClass(testCase) {
      const detectedType = this.getOutputDetectedType(testCase);
      const hasError = testCase.expectedOutputError;
      
      if (hasError) return 'type-error';
      
      if (['int', 'float'].includes(detectedType)) return 'type-number';
      if (detectedType === 'str') return 'type-string';
      if (detectedType === 'bool') return 'type-boolean';
      if (['list', 'dict', 'tuple', 'set'].includes(detectedType)) return 'type-collection';
      if (detectedType === 'None') return 'type-none';
      if (detectedType === 'invalid') return 'type-invalid';
      
      return 'type-any';
    },
    
    /**
     * Get type info tooltip for output
     */
    getOutputTypeInfo(testCase) {
      const detectedType = this.getOutputDetectedType(testCase);
      const expectedType = this.getReturnType();
      const error = testCase.expectedOutputError;
      
      if (error) return error;
      return `Detected: ${detectedType} | Expected: ${expectedType}`;
    },
    
    /**
     * Update reference solution ensuring it's always a string
     */
    updateReferenceSolution(value) {
      // Debug: Log what the editor is sending
      console.log('Editor value received:', value, 'Type:', typeof value);
      
      // Handle different types of values from the editor
      let stringValue = '';
      
      if (typeof value === 'string') {
        stringValue = value;
      } else if (value && typeof value === 'object') {
        // Check if it's an event object with target.value
        if (value.target && typeof value.target.value === 'string') {
          stringValue = value.target.value;
        }
        // Check if it has a value property
        else if (value.value && typeof value.value === 'string') {
          stringValue = value.value;
        }
        // Check if it has a text property
        else if (value.text && typeof value.text === 'string') {
          stringValue = value.text;
        }
        // If it's an empty object, don't update at all
        else if (Object.keys(value).length === 0) {
          console.log('Received empty object, ignoring update');
          return; // Don't update at all
        }
        // Last resort - try JSON stringify for non-empty objects
        else {
          try {
            stringValue = JSON.stringify(value);
          } catch {
            stringValue = '';
          }
        }
      } else {
        stringValue = String(value || '');
      }
      
      this.form.reference_solution = stringValue;
      console.log('Stored as:', this.form.reference_solution);
    },
    
    /**
     * Get the actual string value from the ACE editor
     */
    getEditorValue() {
      if (this.$refs.editor && this.$refs.editor.editor) {
        try {
          const editorValue = this.$refs.editor.editor.getValue();
          console.log('Direct editor value:', editorValue);
          return editorValue || '';
        } catch (error) {
          console.warn('Could not get editor value:', error);
        }
      }
      return this.form.reference_solution || '';
    },
    
    /**
     * Helper method to safely convert form fields to strings for API calls
     */
    getApiSafeString(value, fieldName = '') {
      // Special handling for reference_solution - get directly from editor
      if (fieldName === 'reference_solution') {
        const editorValue = this.getEditorValue();
        const trimmedValue = editorValue.trim();
        console.log('getApiSafeString for reference_solution:');
        console.log('Raw editor value:', JSON.stringify(editorValue));
        console.log('Trimmed value:', JSON.stringify(trimmedValue));
        return trimmedValue;
      }
      
      if (typeof value === 'string') {
        return value.trim();
      }
      
      // Handle Vue reactivity proxies and objects
      if (value && typeof value === 'object') {
        // If it's a proxy or object, try to get the actual string value
        if (value.toString && typeof value.toString === 'function') {
          const stringified = value.toString();
          // Don't return "[object Object]" - that means toString() failed
          if (stringified !== '[object Object]') {
            return stringified.trim();
          }
        }
        
        // Try to access common string properties
        if (value.value && typeof value.value === 'string') {
          return value.value.trim();
        }
        
        // If it's an array, JSON stringify it
        if (Array.isArray(value)) {
          return JSON.stringify(value);
        }
        
        // Last resort: empty string for objects we can't convert
        return '';
      }
      
      return String(value || '').trim();
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

/* Test Cases - Simplified */

/* Actions Bar */
.test-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  border: 2px solid var(--color-bg-border);
}

.left-actions {
  display: flex;
  gap: var(--spacing-md);
}

/* Test Cases List */
.test-cases-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* Test Case Cards */
.test-case {
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  background: var(--color-bg-panel);
  transition: var(--transition-fast);
  overflow: hidden;
}

.test-case:hover {
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-colored);
}

.test-case.error {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.test-case.passed {
  border-color: var(--color-success);
  background: rgba(16, 185, 129, 0.05);
}

.test-case.failed {
  border-color: var(--color-error);
  background: rgba(239, 68, 68, 0.05);
}

/* Test Case Row */
.test-case-row {
  display: grid;
  grid-template-columns: 40px 1fr 1fr auto auto;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  align-items: stretch;
}

/* Smart Parameters Layout */
.smart-parameters {
  display: grid;
  grid-template-columns: repeat(var(--param-count, 1), 1fr);
  gap: var(--spacing-sm);
  align-items: start;
}

.smart-param-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.param-input-container,
.output-input-container {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.param-input,
.output-field {
  flex: 1;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
}

.param-input:focus,
.output-field:focus {
  border-color: var(--color-primary-gradient-start);
  outline: none;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.param-input.param-error,
.output-field.param-error {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.param-input::placeholder,
.output-field::placeholder {
  color: var(--color-text-muted);
  font-family: inherit;
}

/* Parameter Labels */
.param-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-xs);
  min-height: 18px;
}

.param-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.param-expected-type {
  color: var(--color-text-muted);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
}

/* Type Badges */
.param-type-badge {
  position: absolute;
  top: -8px;
  right: 8px;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
  z-index: 10;
  pointer-events: none;
  transform: scale(0.9);
  transform-origin: center;
}

.type-number {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #3b82f6;
}

.type-string {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #22c55e;
}

.type-boolean {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #f59e0b;
}

.type-collection {
  background: #ede9fe;
  color: #6b21a8;
  border: 1px solid #8b5cf6;
}

.type-none {
  background: var(--color-bg-muted);
  color: var(--color-text-muted);
  border: 1px solid var(--color-bg-border);
}

.type-any {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.type-invalid {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.type-error {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

/* Output Field Container */
.output-field-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.test-number {
  font-weight: 600;
  color: var(--color-text-primary);
  text-align: center;
  background: var(--color-bg-hover);
  border-radius: var(--radius-circle);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
}

/* Legacy Input Field (fallback) */
.inputs-field {
  padding: var(--spacing-sm);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
}

.inputs-field:focus {
  border-color: var(--color-primary-gradient-start);
  outline: none;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.inputs-field::placeholder {
  color: var(--color-text-muted);
  font-family: inherit;
}

/* Status Badge */
.status-badge {
  font-size: var(--font-size-sm);
  font-weight: bold;
  padding: var(--spacing-xs);
  border-radius: var(--radius-xs);
  text-align: center;
  min-width: 24px;
}

.status-badge.passed {
  color: var(--color-success);
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--color-success);
}

.status-badge.failed {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--color-error);
}

/* Remove Button */
.remove-btn {
  background: transparent;
  border: 1px solid var(--color-error);
  color: var(--color-error);
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  border-radius: var(--radius-circle);
  transition: var(--transition-fast);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-btn:hover {
  background: var(--color-error);
  color: var(--color-text-primary);
  transform: scale(1.1);
}

/* Error and Failure Messages */
.error-msg,
.failure-msg {
  padding: var(--spacing-sm) var(--spacing-md);
  margin: 0 var(--spacing-md) var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-sm);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
}

.error-msg {
  background: var(--color-error-bg);
  color: var(--color-error-text);
  border-left: 3px solid var(--color-error);
}

.failure-msg {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-error-text);
  border-left: 3px solid var(--color-error);
}


/* Editor Toolbar */
.editor-toolbar {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base) var(--radius-base) 0 0;
  border-bottom: none;
  margin-bottom: 0;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

/* Zoom Controls */
.zoom-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  background: var(--color-bg-panel);
  padding: var(--spacing-xs);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-bg-border);
}

.zoom-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-base);
  font-weight: 600;
  padding: 0;
}

.zoom-btn:hover:not(:disabled) {
  background: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  border-color: var(--color-primary-gradient-start);
  transform: scale(1.05);
}

.zoom-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.zoom-icon {
  line-height: 1;
  font-size: 18px;
}

.zoom-display {
  min-width: 50px;
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

/* Theme Selector */
.theme-selector {
  position: relative;
}

.theme-dropdown {
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  outline: none;
  min-width: 120px;
}

.theme-dropdown:hover {
  border-color: var(--color-primary-gradient-start);
}

.theme-dropdown:focus {
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}


/* Code Editor */
.code-editor {
  border: 2px solid var(--color-bg-border);
  border-radius: 0 0 var(--radius-base) var(--radius-base);
  overflow: hidden;
  transition: var(--transition-fast);
  border-top: none;
}

.code-editor:focus-within {
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* Override ACE editor default styles */
.code-editor :deep(.ace_editor) {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace !important;
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
  
  .test-actions {
    flex-direction: column;
    gap: var(--spacing-lg);
  }
  
  .left-actions {
    width: 100%;
    justify-content: center;
  }
  
  .test-case-row {
    grid-template-columns: 1fr;
    gap: var(--spacing-sm);
    text-align: left;
  }
  
  .test-number {
    justify-self: start;
  }
  
  .smart-parameters {
    grid-template-columns: 1fr;
    gap: var(--spacing-md);
  }
  
  .param-type-badge {
    position: static;
    transform: none;
    align-self: flex-start;
    margin-top: var(--spacing-xs);
  }
  
  .btn {
    width: 100%;
    justify-content: center;
  }
  
  /* Editor toolbar responsive */
  .editor-toolbar {
    flex-direction: column;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
  }
  
  .toolbar-left {
    width: 100%;
    justify-content: center;
  }
  
  .theme-dropdown {
    width: 100%;
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
