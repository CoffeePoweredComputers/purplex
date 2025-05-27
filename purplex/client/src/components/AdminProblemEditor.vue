<template>
  <div class="admin-problem-editor">
    <div class="header">
      <h2>{{ isEditing ? 'Edit Problem' : 'Create New Problem' }}</h2>
      <div class="actions">
        <button @click="testProblem" :disabled="testing" class="btn btn-secondary">
          {{ testing ? 'Testing...' : 'Test Solution' }}
        </button>
        <button @click="saveProblem" :disabled="saving" class="btn btn-primary">
          {{ saving ? 'Saving...' : 'Save Problem' }}
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
            v-model="problem.title"
            type="text"
            required
            placeholder="e.g., Anagram Checker"
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="difficulty">Difficulty</label>
            <select id="difficulty" v-model="problem.difficulty">
              <option value="easy">Easy</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          <div class="form-group">
            <label for="estimated_time">Estimated Time (minutes)</label>
            <input
              id="estimated_time"
              v-model.number="problem.estimated_time"
              type="number"
              min="5"
              max="120"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="categories">Categories</label>
          <div class="category-selector">
            <div
              v-for="category in categories"
              :key="category.id"
              class="category-option"
              :class="{ active: problem.category_ids.includes(category.id) }"
              @click="toggleCategory(category.id)"
            >
              <span class="category-color" :style="{ backgroundColor: category.color }"></span>
              {{ category.name }}
            </div>
          </div>
        </div>

        <div class="form-group">
          <label for="tags">Tags (comma-separated)</label>
          <input
            id="tags"
            v-model="tagsString"
            type="text"
            placeholder="e.g., strings, sorting, hash-map"
          />
        </div>
      </div>

      <!-- Problem Description -->
      <div class="form-section">
        <h3>Problem Description</h3>
        <div class="editor-container">
          <div class="editor-tabs">
            <button
              type="button"
              :class="{ active: activeTab === 'edit' }"
              @click="activeTab = 'edit'"
            >
              Edit
            </button>
            <button
              type="button"
              :class="{ active: activeTab === 'preview' }"
              @click="activeTab = 'preview'"
            >
              Preview
            </button>
          </div>
          
          <textarea
            v-if="activeTab === 'edit'"
            v-model="problem.description"
            class="description-editor"
            placeholder="Write your problem description in Markdown..."
            rows="10"
          ></textarea>
          
          <div
            v-if="activeTab === 'preview'"
            class="description-preview"
            v-html="markdownPreview"
          ></div>
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
              v-model="problem.function_name"
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
            v-model="problem.function_signature"
            type="text"
            placeholder="e.g., def is_anagram(str1: str, str2: str) -> bool:"
          />
        </div>

        <div class="form-group">
          <label for="reference_solution">Reference Solution *</label>
          <div class="code-editor">
            <textarea
              id="reference_solution"
              v-model="problem.reference_solution"
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
            v-model="problem.hints"
            rows="3"
            placeholder="Provide helpful hints for students..."
          ></textarea>
        </div>
      </div>

      <!-- Test Cases -->
      <div class="form-section">
        <h3>Test Cases</h3>
        <div class="test-cases-header">
          <button type="button" @click="addTestCase" class="btn btn-secondary">
            Add Test Case
          </button>
          <button
            type="button"
            @click="generateTestCases"
            :disabled="generating"
            class="btn btn-secondary"
          >
            {{ generating ? 'Generating...' : 'Generate with AI' }}
          </button>
        </div>

        <div class="test-cases-list">
          <div
            v-for="(testCase, index) in problem.test_cases"
            :key="index"
            class="test-case"
            :class="{ 'test-case-error': testCase.error }"
          >
            <div class="test-case-header">
              <span class="test-case-number">Test {{ index + 1 }}</span>
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
                  v-model="testCase.inputsString"
                  @input="parseTestCaseInputs(testCase, $event.target.value)"
                  type="text"
                  placeholder='["arg1", "arg2"]'
                />
              </div>

              <div class="form-group">
                <label>Expected Output (JSON)</label>
                <input
                  v-model="testCase.expectedString"
                  @input="parseTestCaseOutput(testCase, $event.target.value)"
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
            </div>
          </div>
        </div>
      </div>

      <!-- Test Results -->
      <div v-if="testResults" class="form-section test-results">
        <h3>Test Results</h3>
        <div class="results-summary">
          <span class="score" :class="testResults.score === 100 ? 'perfect' : 'partial'">
            {{ testResults.passed }}/{{ testResults.total }} tests passed
            ({{ testResults.score.toFixed(1) }}%)
          </span>
        </div>

        <div class="test-result-list">
          <div
            v-for="result in testResults.results"
            :key="result.test_number"
            class="test-result"
            :class="{ passed: result.passed, failed: !result.passed }"
          >
            <div class="result-header">
              <span class="test-number">Test {{ result.test_number }}</span>
              <span class="result-status">{{ result.passed ? 'PASS' : 'FAIL' }}</span>
            </div>
            
            <div v-if="!result.passed" class="result-details">
              <div><strong>Input:</strong> {{ JSON.stringify(result.inputs) }}</div>
              <div><strong>Expected:</strong> {{ JSON.stringify(result.expected_output) }}</div>
              <div><strong>Actual:</strong> {{ JSON.stringify(result.actual_output) }}</div>
              <div v-if="result.error" class="error-message">
                <strong>Error:</strong> {{ result.error }}
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
            <label for="time_limit">Time Limit (seconds)</label>
            <input
              id="time_limit"
              v-model.number="problem.time_limit"
              type="number"
              min="1"
              max="300"
            />
          </div>

          <div class="form-group">
            <label for="memory_limit">Memory Limit (MB)</label>
            <input
              id="memory_limit"
              v-model.number="problem.memory_limit"
              type="number"
              min="32"
              max="1024"
            />
          </div>

          <div class="form-group">
            <label>
              <input type="checkbox" v-model="problem.is_active" />
              Active (visible to students)
            </label>
          </div>
        </div>
      </div>
    </form>
  </div>
</template>

<script>
import { marked } from 'marked'
import axios from 'axios'

export default {
  name: 'AdminProblemEditor',
  props: {
    problemSlug: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      problem: {
        title: '',
        description: '',
        difficulty: 'beginner',
        categories: [],
        category_ids: [],
        function_name: '',
        function_signature: '',
        reference_solution: '',
        hints: '',
        time_limit: 30,
        memory_limit: 128,
        estimated_time: 15,
        tags: [],
        is_active: true,
        test_cases: []
      },
      categories: [],
      activeTab: 'edit',
      testing: false,
      saving: false,
      generating: false,
      testResults: null,
      tagsString: ''
    }
  },
  computed: {
    isEditing() {
      return Boolean(this.problemSlug)
    },
    markdownPreview() {
      return marked(this.problem.description || '')
    }
  },
  watch: {
    tagsString(newVal) {
      this.problem.tags = newVal.split(',').map(tag => tag.trim()).filter(tag => tag)
    },
    'problem.tags'(newVal) {
      this.tagsString = newVal.join(', ')
    }
  },
  async mounted() {
    await this.loadCategories()
    if (this.isEditing) {
      await this.loadProblem()
    } else {
      this.addTestCase()
    }
  },
  methods: {
    async loadCategories() {
      try {
        const response = await axios.get('/api/admin/categories/')
        this.categories = response.data
      } catch (error) {
        console.error('Failed to load categories:', error)
      }
    },
    
    async loadProblem() {
      try {
        const response = await axios.get(`/api/admin/problems/${this.problemSlug}/`)
        this.problem = { ...response.data }
        
        // Convert test cases to editable format
        this.problem.test_cases = this.problem.test_cases.map(tc => ({
          ...tc,
          inputsString: JSON.stringify(tc.inputs),
          expectedString: JSON.stringify(tc.expected_output)
        }))
        
        // Set tags string
        this.tagsString = this.problem.tags.join(', ')
      } catch (error) {
        console.error('Failed to load problem:', error)
        this.$emit('error', 'Failed to load problem')
      }
    },
    
    toggleCategory(categoryId) {
      const index = this.problem.category_ids.indexOf(categoryId)
      if (index > -1) {
        this.problem.category_ids.splice(index, 1)
      } else {
        this.problem.category_ids.push(categoryId)
      }
    },
    
    addTestCase() {
      this.problem.test_cases.push({
        inputs: [],
        expected_output: null,
        inputsString: '[]',
        expectedString: '',
        description: '',
        is_hidden: false,
        is_sample: false,
        order: this.problem.test_cases.length,
        error: null
      })
    },
    
    removeTestCase(index) {
      this.problem.test_cases.splice(index, 1)
    },
    
    parseTestCaseInputs(testCase, value) {
      try {
        testCase.inputs = JSON.parse(value)
        testCase.error = null
      } catch (error) {
        testCase.error = `Invalid inputs JSON: ${error.message}`
      }
    },
    
    parseTestCaseOutput(testCase, value) {
      try {
        testCase.expected_output = JSON.parse(value)
        testCase.error = null
      } catch (error) {
        testCase.error = `Invalid expected output JSON: ${error.message}`
      }
    },
    
    async testProblem() {
      this.testing = true
      this.testResults = null
      
      try {
        // Prepare test data
        const testData = {
          title: this.problem.title,
          description: this.problem.description,
          function_name: this.problem.function_name,
          reference_solution: this.problem.reference_solution,
          test_cases: this.problem.test_cases.map(tc => ({
            inputs: tc.inputs,
            expected_output: tc.expected_output,
            description: tc.description
          }))
        }
        
        const response = await axios.post('/api/admin/test-problem/', testData)
        this.testResults = response.data
      } catch (error) {
        console.error('Test failed:', error)
        this.$emit('error', 'Failed to test problem')
      } finally {
        this.testing = false
      }
    },
    
    async generateTestCases() {
      if (!this.problem.function_name || !this.problem.reference_solution) {
        this.$emit('error', 'Function name and reference solution are required for AI generation')
        return
      }
      
      this.generating = true
      
      try {
        const response = await axios.post('/api/admin/generate-test-cases/', {
          description: this.problem.description,
          function_name: this.problem.function_name,
          function_signature: this.problem.function_signature,
          reference_solution: this.problem.reference_solution
        })
        
        const generatedCases = response.data.test_cases || []
        generatedCases.forEach(tc => {
          this.problem.test_cases.push({
            ...tc,
            inputsString: JSON.stringify(tc.inputs),
            expectedString: JSON.stringify(tc.expected_output),
            is_hidden: false,
            is_sample: false,
            order: this.problem.test_cases.length,
            error: null
          })
        })
        
        this.$emit('success', `Generated ${generatedCases.length} test cases`)
      } catch (error) {
        console.error('Generation failed:', error)
        this.$emit('error', 'Failed to generate test cases')
      } finally {
        this.generating = false
      }
    },
    
    async saveProblem() {
      // Validate form
      if (!this.problem.title || !this.problem.function_name || !this.problem.reference_solution) {
        this.$emit('error', 'Title, function name, and reference solution are required')
        return
      }
      
      if (this.problem.test_cases.length === 0) {
        this.$emit('error', 'At least one test case is required')
        return
      }
      
      // Check for test case errors
      const hasErrors = this.problem.test_cases.some(tc => tc.error)
      if (hasErrors) {
        this.$emit('error', 'Please fix test case errors before saving')
        return
      }
      
      this.saving = true
      
      try {
        const problemData = {
          ...this.problem,
          test_cases: this.problem.test_cases.map(tc => ({
            inputs: tc.inputs,
            expected_output: tc.expected_output,
            description: tc.description,
            is_hidden: tc.is_hidden,
            is_sample: tc.is_sample,
            order: tc.order
          }))
        }
        
        let response
        if (this.isEditing) {
          response = await axios.put(`/api/admin/problems/${this.problemSlug}/`, problemData)
        } else {
          response = await axios.post('/api/admin/problems/', problemData)
        }
        
        this.$emit('success', `Problem ${this.isEditing ? 'updated' : 'created'} successfully`)
        
        if (!this.isEditing) {
          // Redirect to edit mode for the new problem
          this.$router.push(`/admin/problems/${response.data.slug}/edit`)
        }
      } catch (error) {
        console.error('Save failed:', error)
        this.$emit('error', `Failed to ${this.isEditing ? 'update' : 'create'} problem`)
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<style scoped>
.admin-problem-editor {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.actions {
  display: flex;
  gap: 10px;
}

.btn {
  padding: 8px 16px;
  border: 1px solid;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-secondary {
  background: white;
  color: #374151;
  border-color: #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background: #f9fafb;
}

.form-section {
  margin-bottom: 40px;
  padding: 20px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.form-section h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #111827;
}

.form-group {
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #374151;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.category-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.category-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.category-option:hover {
  border-color: #3b82f6;
}

.category-option.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.category-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.editor-container {
  border: 1px solid #d1d5db;
  border-radius: 4px;
  overflow: hidden;
}

.editor-tabs {
  display: flex;
  background: #f9fafb;
  border-bottom: 1px solid #d1d5db;
}

.editor-tabs button {
  padding: 10px 20px;
  border: none;
  background: none;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.editor-tabs button.active {
  background: white;
  border-bottom-color: #3b82f6;
}

.description-editor {
  width: 100%;
  border: none;
  padding: 15px;
  resize: vertical;
  font-family: 'Courier New', monospace;
}

.description-preview {
  padding: 15px;
  min-height: 200px;
  background: white;
}

.code-editor {
  border: 1px solid #d1d5db;
  border-radius: 4px;
  overflow: hidden;
}

.code-textarea {
  width: 100%;
  border: none;
  padding: 15px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  background: #f8f9fa;
  resize: vertical;
}

.test-cases-header {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.test-case {
  border: 1px solid #d1d5db;
  border-radius: 4px;
  margin-bottom: 15px;
  overflow: hidden;
}

.test-case-error {
  border-color: #ef4444;
}

.test-case-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: #f9fafb;
  border-bottom: 1px solid #d1d5db;
}

.test-case-number {
  font-weight: 500;
}

.test-case-options {
  display: flex;
  align-items: center;
  gap: 15px;
}

.test-case-options label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
}

.btn-remove {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  font-size: 18px;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.test-case-content {
  padding: 15px;
}

.test-case-error-message {
  color: #ef4444;
  font-size: 12px;
  margin-top: 5px;
}

.test-results {
  background: #f9fafb;
}

.results-summary {
  margin-bottom: 20px;
}

.score {
  font-size: 18px;
  font-weight: 600;
  padding: 10px 15px;
  border-radius: 4px;
}

.score.perfect {
  background: #d1fae5;
  color: #065f46;
}

.score.partial {
  background: #fef3c7;
  color: #92400e;
}

.test-result {
  border: 1px solid #d1d5db;
  border-radius: 4px;
  margin-bottom: 10px;
  overflow: hidden;
}

.test-result.passed {
  border-color: #10b981;
}

.test-result.failed {
  border-color: #ef4444;
}

.result-header {
  display: flex;
  justify-content: space-between;
  padding: 10px 15px;
  background: white;
}

.result-status {
  font-weight: 600;
}

.test-result.passed .result-status {
  color: #10b981;
}

.test-result.failed .result-status {
  color: #ef4444;
}

.result-details {
  padding: 15px;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.result-details > div {
  margin-bottom: 5px;
}

.error-message {
  color: #ef4444;
  margin-top: 10px;
}
</style>