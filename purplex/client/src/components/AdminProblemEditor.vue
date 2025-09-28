<template>
  <div class="admin-problem-editor">
    <!-- Breadcrumb navigation -->
    <nav class="breadcrumb border-default">
      <router-link
        to="/admin/problems"
        class="breadcrumb-link transition-fast"
      >
        ← Back to Problems
      </router-link>
    </nav>
    
    <div class="header rounded-lg border-default">
      <h2>{{ isEditing ? 'Edit Problem' : 'Create New Problem' }}</h2>
      <div class="actions">
        <button
          :disabled="!canSave || ui.loading"
          class="btn btn-primary rounded-base"
          @click="saveProblem"
        >
          {{ ui.loading ? 'Saving...' : 'Save Problem' }}
        </button>
      </div>
    </div>

    <form
      class="problem-form"
      @submit.prevent="saveProblem"
    >
      <!-- Basic Information -->
      <div class="form-section rounded-lg border-default transition-fast">
        <h3>Basic Information</h3>
        <div class="form-group">
          <label for="title">Title *</label>
          <input
            id="title"
            v-model="form.title"
            type="text"
            required
            placeholder="e.g., Anagram Checker"
          >
        </div>

        <div class="form-group">
          <label for="difficulty">Difficulty</label>
          <select
            id="difficulty"
            v-model="form.difficulty"
          >
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
          <label for="categories">Categories</label>
          <div class="category-selector">
            <div
              v-for="category in categories"
              :key="category.id"
              class="category-option hover-primary hover-lift transition-fast"
              :class="{ active: form.category_ids && form.category_ids.includes(category.id) }"
              @click="toggleCategory(category.id)"
            >
              <span
                class="category-color"
                :style="{ backgroundColor: category.color }"
              />
              {{ category.name }}
            </div>
            
            <!-- Morphing Category Bean -->
            <div 
              ref="categoryShell"
              class="category-shell hover-primary hover-lift transition-fast" 
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
                  >
                </div>
                  
                <!-- Color Segment -->
                <div class="form-segment color-segment">
                  <div 
                    ref="colorTrigger"
                    class="color-preview-btn"
                    :style="{ backgroundColor: newCategory.color }"
                    @click="toggleColorPicker"
                  />
                </div>
                  
                <!-- Action Segment -->
                <div class="form-segment action-segment">
                  <button 
                    :disabled="!newCategory.name.trim() || creatingCategory"
                    class="bean-submit-btn"
                    :class="{ loading: creatingCategory, disabled: !newCategory.name.trim() }"
                    :title="creatingCategory ? 'Creating...' : 'Create Category'"
                    @click="createCategory"
                  >
                    {{ creatingCategory ? '⋯' : '✓' }}
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Error message -->
            <transition name="error-slide">
              <div
                v-if="categoryError"
                class="bean-error"
              >
                {{ categoryError }}
              </div>
            </transition>
          </div>
        </div>


        <div class="form-group">
          <label for="tags">Tags (comma-separated)</label>
          <input
            id="tags"
            :value="tagsDisplay"
            type="text"
            placeholder="e.g., strings, sorting, hash-map"
            @input="updateTags"
          >
        </div>
      </div>

      <!-- Code Solution -->
      <div class="form-section rounded-lg border-default transition-fast">
        <h3>Code Solution</h3>

        <div class="form-group">
          <label for="function_signature">Function Signature (with type hints) *</label>
          <input
            id="function_signature"
            v-model="form.function_signature"
            type="text"
            required
            placeholder="e.g., def is_anagram(str1: str, str2: str) -> bool:"
            @input="parseFunctionSignature"
          >
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
                  :disabled="editorFontSize <= 12"
                  class="zoom-btn"
                  title="Decrease font size"
                  @click="decreaseFontSize"
                >
                  <span class="zoom-icon">−</span>
                </button>
                <span class="zoom-display">{{ Math.round((editorFontSize / 14) * 100) }}%</span>
                <button
                  type="button"
                  :disabled="editorFontSize >= 24"
                  class="zoom-btn"
                  title="Increase font size"
                  @click="increaseFontSize"
                >
                  <span class="zoom-icon">+</span>
                </button>
              </div>

              <!-- Theme selector -->
              <div class="theme-selector">
                <select
                  v-model="editorTheme"
                  class="theme-dropdown"
                >
                  <option value="monokai">
                    Monokai
                  </option>
                  <option value="github">
                    GitHub
                  </option>
                  <option value="clouds_midnight">
                    Clouds Midnight
                  </option>
                  <option value="chrome">
                    Chrome
                  </option>
                  <option value="solarized_dark">
                    Solarized Dark
                  </option>
                  <option value="solarized_light">
                    Solarized Light
                  </option>
                  <option value="dracula">
                    Dracula
                  </option>
                  <option value="tomorrow_night">
                    Tomorrow Night
                  </option>
                </select>
              </div>
            </div>
          </div>

          <!-- Editor component -->
          <div class="code-editor">
            <Editor
              ref="editor"
              :value="String(form.reference_solution || '')"
              :height="'300px'"
              :width="'100%'"
              :theme="editorTheme"
              :show-gutter="true"
              :mode="'python'"
              :lang="'python'"
              @update:value="updateReferenceSolution($event)"
            />
          </div>
        </div>
      </div>

      <!-- Test Cases -->
      <div
        class="form-section rounded-lg border-default transition-fast"
        style="position: relative;"
      >
        <h3>Test Cases</h3>
        
        <!-- Loading overlay for test section -->
        <div
          v-if="ui.loading"
          class="test-loading-overlay"
        >
          <div class="loading-spinner">
            <div class="spinner" />
            <div class="loading-text">
              Running tests...
            </div>
          </div>
        </div>
        
        <!-- Simplified Actions Bar -->
        <div class="test-actions">
          <div class="left-actions">
            <button
              type="button"
              class="btn-secondary rounded-base transition-fast"
              @click="addTestCase"
            >
              + Add Test
            </button>
          </div>
          
          <button 
            :disabled="!canTest || ui.loading" 
            class="btn-primary rounded-base transition-fast" 
            :title="canTestReason || 'Test your reference solution against all test cases'"
            @click="testProblem"
          >
            {{ ui.loading ? 'Testing...' : 'Test All Cases' }}
          </button>
        </div>

        <!-- Simplified Test Cases List -->
        <div class="test-cases-list">
          <div
            v-for="(testCase, index) in form.test_cases"
            :key="index"
            class="test-case hover-primary transition-fast"
            :class="{ 
              error: testCase.error, 
              passed: isTestPassed(index), 
              failed: isTestFailed(index) 
            }"
          >
            <!-- Single row with everything -->
            <div
              class="test-case-row"
              :style="{ '--param-count': getParameterCount() }"
            >
              <span class="test-number">{{ index + 1 }}</span>
              
              <!-- Dynamic parameter fields based on function signature -->
              <div
                v-if="functionParameters.length > 0"
                class="smart-parameters"
              >
                <div 
                  v-for="(param, paramIndex) in functionParameters" 
                  :key="paramIndex" 
                  class="smart-param-field"
                >
                  <div class="param-input-container">
                    <input 
                      :value="getParameterDisplayValue(testCase, paramIndex)"
                      :placeholder="getParameterPlaceholder(param.type)"
                      class="param-input" 
                      :class="{ 'param-error': getParameterValidationError(testCase, paramIndex) }" 
                      @input="updateParameterValue(testCase, paramIndex, $event.target.value)"
                    >
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
              
              <!-- No parameters message -->
              <div
                v-else
                class="no-params-message"
              >
                No parameters
              </div>
              
              <!-- Expected output field -->
              <div class="output-field-container">
                <div class="output-input-container">
                  <input 
                    :value="getTestCaseExpectedDisplay(testCase)"
                    :placeholder="getOutputPlaceholder()"
                    class="param-input" 
                    :class="{ 'param-error': getOutputValidationError(testCase) }" 
                    @input="updateTestCaseExpected(testCase, $event.target.value)"
                  >
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
              
              <!-- Actions -->
              <div class="test-case-actions">
                <button 
                  class="remove-btn" 
                  @click="removeTestCase(index)"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                  >
                    <circle
                      cx="8"
                      cy="8"
                      r="7"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.5"
                    />
                    <line
                      x1="5"
                      y1="8"
                      x2="11"
                      y2="8"
                      stroke="currentColor"
                      stroke-width="1.5"
                    />
                  </svg>
                </button>
                <!-- Status badge positioned under remove button -->
                <div
                  v-if="ui.testResults"
                  class="status-badge"
                  :class="getStatusClass(index)"
                >
                  <div class="status-icon">
                    {{ getStatusText(index) }}
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Error message directly below if exists -->
            <div
              v-if="testCase.error"
              class="error-msg"
            >
              {{ testCase.error }}
            </div>
            
            <!-- Failure details directly below if failed -->
            <div
              v-if="isTestFailed(index)"
              class="failure-msg"
            >
              Expected: {{ JSON.stringify(ui.testResults.results[index].expected_output) }} | 
              Got: {{ JSON.stringify(ui.testResults.results[index].actual_output) }}
              <span v-if="ui.testResults.results[index].error"> | Error: {{ ui.testResults.results[index].error }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Hints Configuration -->
      <div class="form-section rounded-lg border-default transition-fast">
        <h3>Hints Configuration</h3>
        
        <!-- Hint Type Tabs -->
        <div class="hint-tabs">
          <button 
            type="button"
            class="hint-tab-button"
            :class="{ active: hintsTab === 'variable_fade' }"
            @click="hintsTab = 'variable_fade'"
          >
            Variable Fade
          </button>
          <button 
            type="button"
            class="hint-tab-button"
            :class="{ active: hintsTab === 'subgoal_highlight' }"
            @click="hintsTab = 'subgoal_highlight'"
          >
            Subgoal Highlighting
          </button>
          <button 
            type="button"
            class="hint-tab-button"
            :class="{ active: hintsTab === 'suggested_trace' }"
            @click="hintsTab = 'suggested_trace'"
          >
            Suggested Trace
          </button>
        </div>
        
        <!-- Variable Fade Configuration -->
        <div
          v-if="hintsTab === 'variable_fade'"
          class="hint-config-panel"
        >
          <div class="hint-toggle">
            <label class="toggle-label">
              <input 
                v-model="hints.variable_fade.is_enabled" 
                type="checkbox"
                class="toggle-checkbox"
              >
              <span class="toggle-text">Enable Variable Fade Hints</span>
            </label>
            <div
              v-if="hints.variable_fade.is_enabled"
              class="attempts-config"
            >
              <label>Min Attempts Required:</label>
              <input 
                v-model.number="hints.variable_fade.min_attempts" 
                type="number"
                min="0"
                max="10"
                class="attempts-input"
              >
            </div>
          </div>
          
          <div
            v-if="hints.variable_fade.is_enabled"
            class="mappings-section"
          >
            <h4>Variable Mappings</h4>
            <div class="mappings-list">
              <div 
                v-for="(mapping, index) in hints.variable_fade.content.mappings" 
                :key="index"
                class="mapping-item"
              >
                <input 
                  v-model="mapping.from"
                  placeholder="Original variable"
                  class="mapping-input"
                  @input="validateVariableName(mapping, 'from')"
                >
                <span class="mapping-arrow">→</span>
                <input 
                  v-model="mapping.to"
                  placeholder="Replacement"
                  class="mapping-input"
                  @input="validateVariableName(mapping, 'to')"
                >
                <button 
                  type="button"
                  class="remove-btn"
                  @click="removeVariableMapping(index)"
                >
                  ×
                </button>
              </div>
            </div>
            <div class="add-mapping">
              <input 
                v-model="newVariableMapping.from"
                placeholder="Original variable"
                class="mapping-input"
                @keyup.enter="addVariableMapping"
              >
              <span class="mapping-arrow">→</span>
              <input 
                v-model="newVariableMapping.to"
                placeholder="Replacement"
                class="mapping-input"
                @keyup.enter="addVariableMapping"
              >
              <button 
                type="button"
                class="btn-secondary"
                :disabled="!newVariableMapping.from || !newVariableMapping.to"
                @click="addVariableMapping"
              >
                Add Mapping
              </button>
            </div>
          </div>
        </div>
        
        <!-- Subgoal Highlighting Configuration -->
        <div
          v-if="hintsTab === 'subgoal_highlight'"
          class="hint-config-panel"
        >
          <div class="hint-toggle">
            <label class="toggle-label">
              <input 
                v-model="hints.subgoal_highlight.is_enabled" 
                type="checkbox"
                class="toggle-checkbox"
              >
              <span class="toggle-text">Enable Subgoal Highlighting</span>
            </label>
            <div
              v-if="hints.subgoal_highlight.is_enabled"
              class="attempts-config"
            >
              <label>Min Attempts Required:</label>
              <input 
                v-model.number="hints.subgoal_highlight.min_attempts" 
                type="number"
                min="0"
                max="10"
                class="attempts-input"
              >
            </div>
          </div>
          
          <div
            v-if="hints.subgoal_highlight.is_enabled"
            class="subgoals-section"
          >
            <h4>Subgoals</h4>
            <div class="subgoals-list">
              <div 
                v-for="(subgoal, index) in hints.subgoal_highlight.content.subgoals" 
                :key="index"
                class="subgoal-item"
              >
                <div class="subgoal-header">
                  <input 
                    v-model="subgoal.title"
                    placeholder="Subgoal title"
                    class="subgoal-title-input"
                  >
                  <button 
                    type="button"
                    class="remove-btn"
                    @click="removeSubgoal(index)"
                  >
                    ×
                  </button>
                </div>
                <div class="subgoal-lines">
                  <label>Lines:</label>
                  <input 
                    v-model.number="subgoal.line_start"
                    type="number"
                    min="1"
                    placeholder="Start"
                    class="line-input"
                  >
                  <span>to</span>
                  <input 
                    v-model.number="subgoal.line_end"
                    type="number"
                    :min="subgoal.line_start"
                    placeholder="End"
                    class="line-input"
                  >
                </div>
                <textarea 
                  v-model="subgoal.explanation"
                  placeholder="Explanation of this subgoal"
                  rows="2"
                  class="subgoal-explanation"
                />
              </div>
            </div>
            <div class="add-subgoal">
              <h5>Add New Subgoal</h5>
              <input 
                v-model="newSubgoal.title"
                placeholder="Subgoal title"
                class="subgoal-title-input"
              >
              <div class="subgoal-lines">
                <label>Lines:</label>
                <input 
                  v-model.number="newSubgoal.line_start"
                  type="number"
                  min="1"
                  placeholder="Start"
                  class="line-input"
                >
                <span>to</span>
                <input 
                  v-model.number="newSubgoal.line_end"
                  type="number"
                  :min="newSubgoal.line_start"
                  placeholder="End"
                  class="line-input"
                >
              </div>
              <textarea 
                v-model="newSubgoal.explanation"
                placeholder="Explanation of this subgoal"
                rows="2"
                class="subgoal-explanation"
              />
              <button 
                type="button"
                class="btn-secondary"
                :disabled="!newSubgoal.title || !newSubgoal.explanation"
                @click="addSubgoal"
              >
                Add Subgoal
              </button>
            </div>
          </div>
        </div>
        
        <!-- Suggested Trace Configuration -->
        <div
          v-if="hintsTab === 'suggested_trace'"
          class="hint-config-panel"
        >
          <div class="hint-toggle">
            <label class="toggle-label">
              <input 
                v-model="hints.suggested_trace.is_enabled" 
                type="checkbox"
                class="toggle-checkbox"
              >
              <span class="toggle-text">Enable Suggested Trace</span>
            </label>
            <div
              v-if="hints.suggested_trace.is_enabled"
              class="attempts-config"
            >
              <label>Min Attempts Required:</label>
              <input 
                v-model.number="hints.suggested_trace.min_attempts" 
                type="number"
                min="0"
                max="10"
                class="attempts-input"
              >
            </div>
          </div>
          
          <div
            v-if="hints.suggested_trace.is_enabled"
            class="suggested-trace-section"
          >
            <h4>Configure Suggested Trace</h4>
            <p class="hint-description">
              Provide a function call that students can trace through Python Tutor to better understand the problem. 
              This hint will be shown after {{ hints.suggested_trace.min_attempts }} failed attempts.
            </p>
            
            <div class="form-group">
              <label class="form-label">
                <span class="label-text">Suggested Function Call</span>
                <span class="label-required">*</span>
              </label>
              <div class="input-with-preview">
                <input 
                  v-model="hints.suggested_trace.content.suggested_call"
                  type="text"
                  placeholder="e.g., function_name([1, 2, 3], 'example')"
                  class="form-input suggested-call-input"
                  @input="validateFunctionCall"
                >
                <div
                  v-if="functionCallError"
                  class="input-error"
                >
                  {{ functionCallError }}
                </div>
              </div>
              <!-- Trace Preview (matches student view) -->
              <div
                v-if="hints.suggested_trace.content.suggested_call && !functionCallError"
                class="trace-preview-section"
              >
                <div class="preview-label">
                  Preview (as students will see it):
                </div>
                <div class="suggested-trace">
                  <div class="trace-content">
                    <span class="trace-label">💡 Try tracing:</span>
                    <code class="trace-function">{{ hints.suggested_trace.content.suggested_call }}</code>
                    <button 
                      v-if="form.reference_solution"
                      type="button"
                      class="trace-btn"
                      @click="previewInPyTutor"
                    >
                      <span>🔍</span> Trace
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Segmentation Configuration (EiPL only) -->
      <div 
        v-if="form.problem_type === 'eipl'"
        class="form-section rounded-lg border-default transition-fast"
      >
        <h3>Prompt Segmentation Configuration</h3>
        
        <div class="segmentation-toggle">
          <label class="toggle-label">
            <input 
              v-model="segmentation.enabled" 
              type="checkbox"
              class="toggle-checkbox"
            >
            <span class="toggle-text">Enable Prompt Segmentation Analysis</span>
          </label>
          <p class="hint-description">
            Analyzes student explanations to classify their code comprehension level based on the number of segments in their response.
          </p>
        </div>

        <div
          v-if="segmentation.enabled"
          class="segmentation-config-panel"
        >
          <!-- Custom Segmentation Examples -->
          <div class="segmentation-examples-section">
            <h4>Segmentation Training Examples</h4>
            <p class="section-description">
              Provide examples to train the AI how to segment student responses for this specific problem.
            </p>

            <!-- Binary Threshold Setting -->
            <div class="threshold-setting">
              <label class="form-label">Comprehension Threshold</label>
              <div class="threshold-control">
                <input 
                  v-model.number="segmentation.threshold" 
                  type="number" 
                  min="1" 
                  max="5"
                  class="threshold-input"
                >
                <span class="threshold-help">
                  ≤ {{ segmentation.threshold }} segments = Good (Relational)<br>
                  > {{ segmentation.threshold }} segments = Needs Work (Multi-structural)
                </span>
              </div>
            </div>

            <!-- Relational Example -->
            <div class="example-block relational">
              <h5>
                <span class="example-icon">✅</span>
                Good Example (Relational)
              </h5>
              <p class="example-help">
                Show how a high-level description should look
              </p>
              
              <div class="form-group">
                <label>Student Description</label>
                <textarea 
                  v-model="segmentation.examples.relational.prompt"
                  placeholder="Example: The function checks if a word is a palindrome by comparing it with its reverse"
                  rows="3"
                />
              </div>
              
              <div class="segments-editor">
                <label>Expected Segments ({{ relationalSegments.length }})</label>
                <div 
                  v-for="(seg, idx) in relationalSegments" 
                  :key="`rel-${idx}`"
                  class="segment-item"
                >
                  <div class="segment-row">
                    <input 
                      v-model="seg.text" 
                      placeholder="Segment text"
                      class="segment-input"
                    >
                    <button 
                      type="button"
                      class="btn-icon"
                      @click="removeRelationalSegment(idx)"
                    >
                      ×
                    </button>
                  </div>
                  <div class="code-lines-row">
                    <label class="lines-label">Code lines:</label>
                    <input 
                      v-model="seg.lines"
                      placeholder="e.g., 1-3 or 1,2,3"
                      class="lines-input"
                      @input="validateLineRange(seg)"
                    >
                    <span class="lines-help">{{ getLineRangeHelp(seg) }}</span>
                  </div>
                </div>
                <button 
                  type="button"
                  class="btn-secondary btn-sm"
                  @click="addRelationalSegment"
                >
                  + Add Segment
                </button>
              </div>
            </div>

            <!-- Multi-structural Example -->
            <div class="example-block multi-structural">
              <h5>
                <span class="example-icon">❌</span>
                Needs Work Example (Multi-structural)
              </h5>
              <p class="example-help">
                Show how a line-by-line description looks
              </p>
              
              <div class="form-group">
                <label>Student Description</label>
                <textarea 
                  v-model="segmentation.examples.multi_structural.prompt"
                  placeholder="Example: It takes the input. Converts each character. Creates empty string. Loops through..."
                  rows="3"
                />
              </div>
              
              <div class="segments-editor">
                <label>Expected Segments ({{ multiStructuralSegments.length }})</label>
                <div 
                  v-for="(seg, idx) in multiStructuralSegments" 
                  :key="`multi-${idx}`"
                  class="segment-item"
                >
                  <div class="segment-row">
                    <input 
                      v-model="seg.text" 
                      placeholder="Segment text"
                      class="segment-input"
                    >
                    <button 
                      type="button"
                      class="btn-icon"
                      @click="removeMultiSegment(idx)"
                    >
                      ×
                    </button>
                  </div>
                  <div class="code-lines-row">
                    <label class="lines-label">Code lines:</label>
                    <input 
                      v-model="seg.lines"
                      placeholder="e.g., 1-3 or 1,2,3"
                      class="lines-input"
                      @input="validateLineRange(seg)"
                    >
                    <span class="lines-help">{{ getLineRangeHelp(seg) }}</span>
                  </div>
                </div>
                <button 
                  type="button"
                  class="btn-secondary btn-sm"
                  @click="addMultiSegment"
                >
                  + Add Segment
                </button>
              </div>
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
                :title="color.name"
                @click="selectColor(color.value)"
              />
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Notification toast integration -->
    <NotificationToast />
    
    <!-- Python Tutor Modal -->
    <PyTutorModal 
      :is-visible="showPyTutorModal" 
      :python-tutor-url="pyTutorUrl" 
      @close="closePyTutor" 
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue'
import NotificationToast from './NotificationToast.vue'
import Editor from '@/features/editor/Editor.vue'
import PyTutorModal from '@/modals/PyTutorModal.vue'
import { problemService } from '../services/problemService'
import { marked } from 'marked'
import { PythonTutorService } from '@/services/pythonTutor.service'
import { log } from '@/utils/logger'
import { useNotification } from '@/composables/useNotification'
import axios from 'axios'
import { 
  autoDetectAndConvert,
  autoDetectTypeFromInput,
  formatTypeSpec,
  formatValueForInput,
  getPlaceholderForType,
  parseTypeAnnotation,
  validateValueAgainstType
} from '@/utils/typeSystem'
import type { 
  DifficultyLevel, 
  HintConfig, 
  ProblemCategory,
  ProblemDetailed,
  ProblemType,
  SubgoalHighlightHint,
  SuggestedTraceHint,
  TestCaseInput,
  TestExecutionResult,
  TestResult,
  VariableFadeHint
} from '@/types'

// Type definitions
interface FunctionParameter {
  name: string
  type: string
  typeSpec: any // TODO: Define proper type spec interface
}

interface CategoryForm {
  name: string
  color: string
  description: string
}

interface PopupPosition {
  top: string
  left: string
}

interface SegmentationExample {
  prompt: string
  segments: Array<{
    text: string
    code_lines: number[]
  }>
}

interface SegmentationConfig {
  enabled: boolean
  threshold: number
  examples: {
    relational: SegmentationExample
    multi_structural: SegmentationExample
  }
}

interface FormState {
  title: string
  difficulty: DifficultyLevel
  problem_type: ProblemType
  category_ids: number[]
  function_signature: string
  reference_solution: string
  tags: string[]
  test_cases: TestCaseInput[]
}

interface UIState {
  loading: boolean
  error: string | null
  testResults: TestExecutionResult | null
}

interface HintsState {
  variable_fade: VariableFadeHint
  subgoal_highlight: SubgoalHighlightHint
  suggested_trace: SuggestedTraceHint
}

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

export default defineComponent({
  name: 'AdminProblemEditor',
  components: {
    NotificationToast,
    Editor,
    PyTutorModal
  },
  // Static options
  colorOptions: COLOR_OPTIONS,
  props: {
    problemSlug: {
      type: String,
      default: null
    }
  },
  data(): {
    form: FormState
    ui: UIState
    categories: ProblemCategory[]
    functionParameters: FunctionParameter[]
    returnType: string
    returnTypeSpec: any
    showAddCategory: boolean
    isTransitioning: boolean
    creatingCategory: boolean
    categoryError: string | null
    newCategory: CategoryForm
    showColorPicker: boolean
    popupPosition: PopupPosition
    popupDirection: string
    clickOutsideHandler: ((event: MouseEvent) => void) | null
    editorFontSize: number
    editorTheme: string
    hintsTab: string
    hints: HintsState
    newVariableMapping: { from: string; to: string }
    newSubgoal: { line_start: number; line_end: number; title: string; explanation: string }
    functionCallError: string | null
    showPyTutorModal: boolean
    pyTutorUrl: string
    segmentation: SegmentationConfig
    notify: any
  } {
    return {
      // Single form state
      form: {
        title: '',
        difficulty: 'beginner',
        problem_type: 'eipl',
        category_ids: [],
        function_signature: '',
        reference_solution: '',
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
      returnTypeSpec: { type: 'Any' },
      
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
      editorTheme: 'monokai',
      
      // Hints configuration
      hintsTab: 'variable_fade',
      hints: {
        variable_fade: {
          type: 'variable_fade',
          is_enabled: false,
          min_attempts: 0,
          content: {
            mappings: []
          }
        },
        subgoal_highlight: {
          type: 'subgoal_highlight',
          is_enabled: false,
          min_attempts: 0,
          content: {
            subgoals: []
          }
        },
        suggested_trace: {
          type: 'suggested_trace',
          is_enabled: false,
          min_attempts: 0,
          content: {
            suggested_call: ''
          }
        }
      },
      newVariableMapping: { from: '', to: '' },
      newSubgoal: { line_start: 1, line_end: 1, title: '', explanation: '' },
      functionCallError: null,
      
      // Python Tutor Modal
      showPyTutorModal: false,
      pyTutorUrl: '',
      
      // Segmentation configuration
      segmentation: {
        enabled: false,
        examples: {
          relational: {
            prompt: '',
            segments: []
          },
          multi_structural: {
            prompt: '',
            segments: []
          }
        }
      },
      
      // Notification handler (set in created hook)
      notify: null
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
    canSave() {
      if (this.ui.loading) {return false;}
      
      const title = (this.form.title || '').toString().trim();
      const functionSignature = (this.form.function_signature || '').toString().trim();
      const referenceSolution = (this.form.reference_solution || '').toString().trim();

      // Check for validation errors
      if (!title || !functionSignature || !referenceSolution) {return false;}
      if (this.form.test_cases.length === 0) {return false;}
      if (this.form.test_cases.some(tc => tc.error)) {return false;}
      
      return true;
    },
    canTest() {
      const functionSignature = (this.form.function_signature || '').toString().trim();
      const referenceSolution = (this.form.reference_solution || '').toString().trim();

      return !this.ui.loading &&
             functionSignature.length > 0 &&
             referenceSolution.length > 0 &&
             this.form.test_cases.length > 0 &&
             this.form.test_cases.every(tc => !tc.error);
    },
    canTestReason() {
      const functionSignature = (this.form.function_signature || '').toString().trim();
      const referenceSolution = (this.form.reference_solution || '').toString().trim();

      if (this.ui.loading) {return "Currently loading...";}
      if (!functionSignature) {return "Function signature required";}
      if (!referenceSolution) {return "Reference solution required";}
      if (this.form.test_cases.length === 0) {return "Add at least one test case";}
      if (this.form.test_cases.some(tc => tc.error)) {return "Fix test case errors first";}
      return null; // Can test
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
    
    // Computed properties for segmentation segments
    relationalSegments() {
      // Ensure segmentation structure exists
      if (!this.segmentation) {
        return [];
      }
      if (!this.segmentation.examples) {
        this.$set(this.segmentation, 'examples', {
          relational: { prompt: '', segments: [] },
          multi_structural: { prompt: '', segments: [] }
        });
      }
      if (!this.segmentation.examples.relational) {
        this.$set(this.segmentation.examples, 'relational', { prompt: '', segments: [] });
      }
      if (!this.segmentation.examples.relational.segments) {
        this.$set(this.segmentation.examples.relational, 'segments', []);
      }
      return this.segmentation.examples.relational.segments;
    },
    
    multiStructuralSegments() {
      // Ensure segmentation structure exists
      if (!this.segmentation) {
        return [];
      }
      if (!this.segmentation.examples) {
        this.$set(this.segmentation, 'examples', {
          relational: { prompt: '', segments: [] },
          multi_structural: { prompt: '', segments: [] }
        });
      }
      if (!this.segmentation.examples.multi_structural) {
        this.$set(this.segmentation.examples, 'multi_structural', { prompt: '', segments: [] });
      }
      if (!this.segmentation.examples.multi_structural.segments) {
        this.$set(this.segmentation.examples.multi_structural, 'segments', []);
      }
      return this.segmentation.examples.multi_structural.segments;
    },
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
      async handler(newSlug: string | null, oldSlug: string | null): Promise<void> {
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
    },
    
    // Debug: Watch test results changes
    'ui.testResults': {
      deep: true,
      handler(newVal, oldVal) {
        log.debug('Test results changed', {
          old: oldVal,
          new: newVal,
          hasResults: !!newVal,
          resultsLength: newVal?.results?.length
        });
      }
    },
    
    // Debug: Watch loading state
    'ui.loading'(newVal, oldVal) {
      log.debug('Loading state changed', {
        old: oldVal,
        new: newVal
      });
    }
  },
  created() {
    // Set up notification
    const { notify } = useNotification();
    this.notify = notify;
  },
  async mounted(): Promise<void> {
    // Configure ACE editor base path
    if (window.ace) {
      window.ace.config.set('basePath', 'https://cdn.jsdelivr.net/npm/ace-builds@1.15.0/src-noconflict/');
    }
    
    try {
      await Promise.all([
        this.loadCategories()
        // Don't call loadProblem here as the watcher will handle it
        // Removed automatic test case creation for new problems
      ]);
      
      // Parse function signature if available
      this.parseFunctionSignature();
    } catch (error) {
      this.notify.error('Failed to load data');
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
    /**
     * Extract function name from reference solution
     */
    extractFunctionName() {
      if (!this.form.reference_solution) {return '';}

      const functionNameRegex = /def\s+(\w+)\s*\(/;
      const match = this.form.reference_solution.match(functionNameRegex);
      return match ? match[1] : '';
    },

    /**
     * Extract function signature from reference solution
     */
    extractFunctionSignature() {
      if (!this.form.reference_solution) {return '';}

      // Match the full function definition line including type hints
      const signatureRegex = /def\s+\w+\s*\([^)]*\)(?:\s*->\s*[^:]+)?:/;
      const match = this.form.reference_solution.match(signatureRegex);
      return match ? match[0] : '';
    },

    async executeAction(actionName: string, actionFn: () => Promise<any>, successMsg: string | null = null): Promise<void> {
      log.debug('Execute action started', {
        actionName,
        currentLoading: this.ui.loading,
        hasNotify: !!this.notify
      });
      
      if (this.ui.loading) {
        log.debug('Already loading, skipping action');
        return;
      }
      
      this.ui.loading = true;
      this.ui.error = null;
      log.debug('Set loading to true');
      
      try {
        log.debug('Running action', { actionName });
        const result = await actionFn();
        log.info('Action completed successfully', { actionName, result });
        
        if (successMsg) {
          log.debug('Showing success toast', { successMsg });
          this.notify.success(successMsg);
        }
        return result;
      } catch (error) {
        log.error('Action failed', { actionName, error });
        
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
        log.info('Showing error toast', { errorMsg });
        this.notify.error(errorMsg);
        throw error;
      } finally {
        this.ui.loading = false;
        log.debug('Set loading to false');
        // Force UI update to ensure loading state change is reflected
        this.$nextTick(() => {
          log.debug('Force update after loading state change');
          this.$forceUpdate();
        });
      }
    },

    /**
     * Normalize problem data to ensure proper types
     */
    normalizeProblemData(problemData: ProblemDetailed): void {
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
      
      // Ensure reference_solution is always a string
      if (problemData.reference_solution && typeof problemData.reference_solution !== 'string') {
        problemData.reference_solution = String(problemData.reference_solution);
      }
      
      // Convert test cases to string format for editing
      if (problemData.test_cases) {
        problemData.test_cases = this.convertTestCasesFromBackend(problemData.test_cases);
      }
      
      return problemData;
    },

    async loadCategories(): Promise<void> {
      await this.executeAction('load categories', async () => {
        this.categories = await problemService.loadCategories();
      });
    },
    
    async loadProblem(): Promise<void> {
      if (!this.currentProblemSlug) {
        return;
      }
      
      await this.executeAction('load problem', async () => {
        const loadedProblem = await problemService.loadProblem(this.currentProblemSlug);
        this.form = this.normalizeProblemData(loadedProblem);
        
        // Parse function signature first to get parameter info
        this.parseFunctionSignature();
        
        // Load hints for the problem
        await this.loadHints();
        
        // Load segmentation config if it exists
        if (loadedProblem.segmentation_config && Object.keys(loadedProblem.segmentation_config).length > 0) {
          const config = loadedProblem.segmentation_config;
          this.segmentation.enabled = config.enabled !== undefined ? config.enabled : true;
          this.segmentation.threshold = config.threshold || 2;
          
          // Load examples with proper format
          if (config.examples) {
            if (config.examples.relational) {
              this.segmentation.examples.relational = {
                prompt: config.examples.relational.prompt || '',
                segments: (config.examples.relational.segments || []).map((s, index) => {
                  // Handle both string segments and object segments
                  if (typeof s === 'string') {
                    // Check if we have corresponding code_lines data
                    const codeLines = config.examples.relational.code_lines && config.examples.relational.code_lines[index];
                    const linesStr = codeLines && Array.isArray(codeLines) ? this.formatLineRangeFromArray(codeLines) : '';
                    return { text: s, lines: linesStr };
                  } else {
                    return { 
                      text: s.text || '', 
                      lines: s.lines || ''
                    };
                  }
                })
              };
            }
            if (config.examples.multi_structural) {
              this.segmentation.examples.multi_structural = {
                prompt: config.examples.multi_structural.prompt || '',
                segments: (config.examples.multi_structural.segments || []).map((s, index) => {
                  // Handle both string segments and object segments
                  if (typeof s === 'string') {
                    // Check if we have corresponding code_lines data
                    const codeLines = config.examples.multi_structural.code_lines && config.examples.multi_structural.code_lines[index];
                    const linesStr = codeLines && Array.isArray(codeLines) ? this.formatLineRangeFromArray(codeLines) : '';
                    return { text: s, lines: linesStr };
                  } else {
                    return { 
                      text: s.text || '', 
                      lines: s.lines || ''
                    };
                  }
                })
              };
            }
          }
        }
      });
    },
    
    toggleCategory(categoryId: number): void {
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
      if (this.isTransitioning) {return;}
      
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
      if (this.isTransitioning) {return;}
      
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
    
    selectColor(colorValue: string): void {
      this.newCategory.color = colorValue;
      this.showColorPicker = false; // Auto-close after selection
    },
    
    async createCategory(): Promise<void> {
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
    
    addTestCase(): void {
      const newTestCase = {
        inputs: new Array(this.functionParameters.length).fill(''),
        expected_output: '',
        description: '',
        order: this.form.test_cases.length,
        error: null
      };
      
      this.form.test_cases.push(newTestCase);
    },
    
    removeTestCase(index: number): void {
      this.form.test_cases.splice(index, 1)
    },
    
    getTestCaseExpectedDisplay(testCase) {
      return testCase.expected_output ?? '';
    },
    
    updateTestCaseExpected(testCase, value) {
      // Store exactly what user typed (raw string)
      testCase.expected_output = value;
    },
    
    
    async testProblem(): Promise<void> {
      log.debug('testProblem() called', {
        canTest: this.canTest,
        canTestReason: this.canTestReason,
        testCasesCount: this.form.test_cases.length,
        loading: this.ui.loading,
        testCases: this.form.test_cases
      });

      if (!this.canTest) {
        // Show specific reason instead of generic warning
        const reason = this.canTestReason || 'Cannot test problem in current state';
        log.info('Cannot test', { reason });
        this.notify.warning(reason);
        return;
      }
      
      // Validate test cases for errors
      for (let i = 0; i < this.form.test_cases.length; i++) {
        if (this.form.test_cases[i].error) {
          log.warn(`Test case ${i + 1} has error`, { error: this.form.test_cases[i].error });
          this.notify.error(`Please fix errors in test case ${i + 1}`);
          return;
        }
      }
      
      // Clear previous results
      this.ui.testResults = null;
      log.debug('Cleared previous test results');
      
      // Show immediate feedback
      this.notify.info('Running tests...');
      
      await this.executeAction('test problem', async () => {
        log.info('Starting test execution');
        
        // Convert string test cases to backend format
        const validTestCases = this.form.test_cases.filter(tc => !tc.error);
        log.debug('Valid test cases', { count: validTestCases.length });
        
        const convertedTestCases = this.convertTestCasesForBackend(validTestCases);
        log.debug('Converted test cases', { testCases: convertedTestCases });
        
        const testData = {
          title: this.form.title,
          function_name: this.extractFunctionName(),
          function_signature: this.form.function_signature,
          reference_solution: this.getApiSafeString(this.form.reference_solution),
          test_cases: convertedTestCases
        };
        
        log.debug('Test data being sent', {
          ...testData,
          reference_solution: testData.reference_solution.substring(0, 50) + '...'
        });
        
        // Check if we have any test cases to test
        if (!testData.test_cases || testData.test_cases.length === 0) {
          log.error('No valid test cases found');
          throw new Error('No valid test cases found. Please add test cases with inputs and expected outputs.');
        }
        
        log.debug('Calling problemService.testProblem()');
        const startTime = Date.now();
        
        try {
          this.ui.testResults = await problemService.testProblem(testData);
          const elapsed = Date.now() - startTime;
          log.info(`Test results received in ${elapsed}ms`, { results: this.ui.testResults });
          
          // Debug: Log the full response structure
          log.debug('Full test results structure', {
            success: this.ui.testResults.success,
            testsPassed: this.ui.testResults.testsPassed,
            totalTests: this.ui.testResults.totalTests,
            results: this.ui.testResults.results,
            resultsType: typeof this.ui.testResults.results,
            resultsLength: this.ui.testResults.results?.length,
            firstResult: this.ui.testResults.results?.[0]
          });
          
          // Temporary fix: If results array is empty but we have test counts,
          // create placeholder results to show visual feedback
          if ((!this.ui.testResults.results || this.ui.testResults.results.length === 0) && this.ui.testResults.total > 0) {
            log.warn('Backend returned empty results array, creating placeholders');
            
            // Extract function name from solution
            const functionNameInSolution = this.extractFunctionName();

            let errorMessage = 'Test execution failed - no detailed results from backend';

            if (!functionNameInSolution) {
              errorMessage = 'No function found in reference solution';
              log.error(errorMessage);
            }
            
            this.ui.testResults.results = [];
            for (let i = 0; i < this.ui.testResults.total; i++) {
              this.ui.testResults.results.push({
                passed: false,
                test_number: i + 1,
                inputs: testData.test_cases[i]?.inputs || [],
                expected_output: testData.test_cases[i]?.expected_output,
                actual_output: null,
                error: errorMessage
              });
            }
          }
        } catch (error) {
          log.error('API call failed', error);
          throw error;
        }
        
        // Force UI update
        this.$forceUpdate();
        
        const passed = this.ui.testResults.testsPassed || 0;
        const total = this.ui.testResults.totalTests || 0;
        
        log.info(`Test results: ${passed}/${total} passed`);
        
        if (this.ui.testResults.success && passed === total) {
          return 'All tests passed! ✓';
        } else {
          return `${passed}/${total} tests passed`;
        }
      });
    },
    
    
    async saveProblem(): Promise<void> {
      if (!this.canSave) {
        this.notify.error('Please fix validation errors before saving');
        return;
      }
      
      await this.executeAction('save problem', async () => {
        // Convert string test cases to backend format
        const validTestCases = this.form.test_cases.filter(tc => {
          // Filter out test cases with errors or missing required fields
          if (tc.error) {return false;}
          if (!Array.isArray(tc.inputs)) {return false;}
          const hasValidInput = tc.inputs.some(input => input && String(input).trim());
          const hasValidOutput = tc.expected_output != null && String(tc.expected_output).trim();
          return hasValidInput || hasValidOutput;
        });
        
        const convertedTestCases = this.convertTestCasesForBackend(validTestCases);
        
        const problemData = {
          title: this.getApiSafeString(this.form.title),
          difficulty: this.form.difficulty,
          problem_type: this.form.problem_type,
          category_ids: Array.isArray(this.form.category_ids) ? this.form.category_ids : [],
          function_name: this.extractFunctionName() || '',
          function_signature: this.form.function_signature || '',
          reference_solution: this.getApiSafeString(this.form.reference_solution),
          tags: Array.isArray(this.form.tags) ? this.form.tags : [],
          test_cases: convertedTestCases,
          // Add segmentation config and requires_highlevel_comprehension for EiPL problems
          ...(this.form.problem_type === 'eipl' && {
            segmentation_config: this.formatSegmentationConfig(),
            requires_highlevel_comprehension: this.segmentation.enabled === true
          })
        };
        
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
        
        // Re-parse function signature to rebuild functionParameters
        this.parseFunctionSignature();
        
        // Save hints after problem is saved successfully
        if (this.isEditing && savedProblem) {
          await this.saveHints();
        }
        
        return this.isEditing ? 'Problem updated successfully' : 'Problem created successfully';
      });
    },
    
    /**
     * Save hints configuration
     */
    async saveHints(): Promise<void> {
      try {
        const hintsArray = Object.values(this.hints);
        await problemService.updateHints(this.currentProblemSlug, hintsArray);
      } catch (error) {
        log.error('Failed to save hints', error);
        // Don't throw - hints are optional functionality
      }
    },
    
    /**
     * Load hints configuration for existing problem
     */
    async loadHints(): Promise<void> {
      if (!this.currentProblemSlug) {return;}
      
      try {
        const hintsData = await problemService.getProblemHints(this.currentProblemSlug);
        
        // Update local hints data - add defensive check
        if (hintsData && Array.isArray(hintsData)) {
          hintsData.forEach(hint => {
            if (this.hints[hint.type]) {
              this.hints[hint.type] = hint;
            }
          });
        }
      } catch (error) {
        log.error('Failed to load hints', error);
        // Don't throw - hints are optional functionality
      }
    },
    
    /**
     * Add variable mapping
     */
    addVariableMapping() {
      if (!this.newVariableMapping.from || !this.newVariableMapping.to) {return;}
      
      this.hints.variable_fade.content.mappings.push({
        from: this.newVariableMapping.from,
        to: this.newVariableMapping.to
      });
      
      this.newVariableMapping = { from: '', to: '' };
    },
    
    
    /**
     * Format value for preview display
     */
    formatPreviewValue(value) {
      if (value === null || value === undefined) {return 'None';}
      if (typeof value === 'string') {
        // Truncate long strings
        const truncated = value.length > 20 ? value.substring(0, 17) + '...' : value;
        return `"${truncated}"`;
      }
      if (Array.isArray(value)) {
        if (value.length === 0) {return '[]';}
        if (value.length > 3) {return `[${value.slice(0, 3).map(v => this.formatPreviewValue(v)).join(', ')}, ...]`;}
        return `[${value.map(v => this.formatPreviewValue(v)).join(', ')}]`;
      }
      if (typeof value === 'object') {
        const keys = Object.keys(value);
        if (keys.length === 0) {return '{}';}
        if (keys.length > 2) {return `{${keys.slice(0, 2).join(', ')}, ...}`;}
        return JSON.stringify(value);
      }
      return String(value);
    },
    
    /**
     * Remove variable mapping
     */
    removeVariableMapping(index: number): void {
      this.hints.variable_fade.content.mappings.splice(index, 1);
    },
    
    /**
     * Validate variable name
     */
    validateVariableName(mapping, field) {
      const value = mapping[field];
      const isValid = /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(value);
      
      if (!isValid && value) {
        this.notify.warning(`Invalid variable name: ${value}. Must start with letter or underscore.`);
      }
    },
    
    /**
     * Add subgoal
     */
    addSubgoal() {
      if (!this.newSubgoal.title || !this.newSubgoal.explanation) {return;}
      
      this.hints.subgoal_highlight.content.subgoals.push({
        line_start: this.newSubgoal.line_start,
        line_end: this.newSubgoal.line_end,
        title: this.newSubgoal.title,
        explanation: this.newSubgoal.explanation
      });
      
      this.newSubgoal = { line_start: 1, line_end: 1, title: '', explanation: '' };
    },
    
    validateFunctionCall() {
      const call = this.hints.suggested_trace.content.suggested_call;
      
      if (!call) {
        this.functionCallError = null;
        return;
      }
      
      // Basic validation: check if it looks like a function call
      const functionCallPattern = /^[a-zA-Z_][a-zA-Z0-9_]*\s*\(/;
      if (!functionCallPattern.test(call.trim())) {
        this.functionCallError = 'Must start with a valid function name followed by parentheses';
        return;
      }
      
      // Check for balanced parentheses
      let parenCount = 0;
      let inString = false;
      let stringChar = null;
      let escaped = false;
      
      for (let i = 0; i < call.length; i++) {
        const char = call[i];
        
        if (escaped) {
          escaped = false;
          continue;
        }
        
        if (char === '\\') {
          escaped = true;
          continue;
        }
        
        if ((char === '"' || char === "'") && !inString) {
          inString = true;
          stringChar = char;
        } else if (char === stringChar && inString) {
          inString = false;
          stringChar = null;
        }
        
        if (!inString) {
          if (char === '(') {parenCount++;}
          if (char === ')') {parenCount--;}
          if (parenCount < 0) {
            this.functionCallError = 'Unmatched closing parenthesis';
            return;
          }
        }
      }
      
      if (parenCount !== 0) {
        this.functionCallError = 'Unmatched parentheses';
        return;
      }
      
      if (inString) {
        this.functionCallError = 'Unterminated string';
        return;
      }
      
      // Validate it matches the function name from reference solution
      const expectedFunctionName = this.extractFunctionName();
      if (expectedFunctionName) {
        const functionName = call.trim().split('(')[0].trim();
        if (functionName !== expectedFunctionName) {
          this.functionCallError = `Function name doesn't match problem function: ${expectedFunctionName}`;
          return;
        }
      }
      
      this.functionCallError = null;
    },
    
    // Python Tutor preview methods
    previewInPyTutor() {
      if (!this.form.reference_solution || !this.hints.suggested_trace.content.suggested_call) {
        this.notify.warning('Please provide both a reference solution and a suggested call');
        return;
      }
      
      // Create the test code with the suggested call
      const testCode = `# Suggested trace\nprint(${this.hints.suggested_trace.content.suggested_call})`;
      const formattedCode = `${this.form.reference_solution}\n\n${testCode}`;
      
      // Generate Python Tutor URL
      this.pyTutorUrl = PythonTutorService.generateEmbedUrl(formattedCode);
      this.showPyTutorModal = true;
    },
    
    closePyTutor() {
      this.showPyTutorModal = false;
      this.pyTutorUrl = '';
    },
    
    
    /**
     * Remove subgoal
     */
    removeSubgoal(index: number): void {
      this.hints.subgoal_highlight.content.subgoals.splice(index, 1);
    },
    
    // Segmentation management methods
    addRelationalSegment() {
      if (!this.segmentation.examples.relational.segments) {
        this.$set(this.segmentation.examples.relational, 'segments', []);
      }
      this.segmentation.examples.relational.segments.push({ text: '', lines: '' });
    },
    
    removeRelationalSegment(index) {
      this.segmentation.examples.relational.segments.splice(index, 1);
    },
    
    addMultiSegment() {
      if (!this.segmentation.examples.multi_structural.segments) {
        this.$set(this.segmentation.examples.multi_structural, 'segments', []);
      }
      this.segmentation.examples.multi_structural.segments.push({ text: '', lines: '' });
    },
    
    removeMultiSegment(index) {
      this.segmentation.examples.multi_structural.segments.splice(index, 1);
    },
    
    validateLineRange(segment) {
      // Validate the line range input
      const lines = segment.lines;
      if (!lines) {
        segment.parsedLines = [];
        return;
      }
      
      try {
        segment.parsedLines = this.parseLineRange(lines);
      } catch (e) {
        segment.parsedLines = [];
      }
    },
    
    parseLineRange(input) {
      // Parse line ranges like "1-3" or "1,2,3" or "1-3,5,7-9"
      if (!input || typeof input !== 'string') {return [];}
      
      const lines = [];
      const parts = input.split(',');
      
      for (const part of parts) {
        const trimmed = part.trim();
        if (trimmed.includes('-')) {
          // Range like "1-3"
          const [start, end] = trimmed.split('-').map(n => parseInt(n.trim()));
          if (!isNaN(start) && !isNaN(end) && start <= end) {
            for (let i = start; i <= end; i++) {
              lines.push(i);
            }
          }
        } else {
          // Single number
          const num = parseInt(trimmed);
          if (!isNaN(num)) {
            lines.push(num);
          }
        }
      }
      
      // Remove duplicates and sort
      return [...new Set(lines)].sort((a, b) => a - b);
    },
    
    getLineRangeHelp(segment) {
      if (!segment.lines) {return '';}
      const parsed = this.parseLineRange(segment.lines);
      if (parsed.length === 0) {return '';}
      return `Lines: ${parsed.join(', ')}`;
    },

    formatLineRangeFromArray(lineNumbers) {
      // Convert array of line numbers back to compact string format
      if (!Array.isArray(lineNumbers) || lineNumbers.length === 0) {return '';}
      
      // Sort the numbers
      const sorted = [...lineNumbers].sort((a, b) => a - b);
      const ranges = [];
      let start = sorted[0];
      let end = sorted[0];
      
      for (let i = 1; i < sorted.length; i++) {
        if (sorted[i] === end + 1) {
          // Consecutive number, extend the range
          end = sorted[i];
        } else {
          // Gap found, close current range and start new one
          if (start === end) {
            ranges.push(start.toString());
          } else {
            ranges.push(`${start}-${end}`);
          }
          start = sorted[i];
          end = sorted[i];
        }
      }
      
      // Add the final range
      if (start === end) {
        ranges.push(start.toString());
      } else {
        ranges.push(`${start}-${end}`);
      }
      
      return ranges.join(', ');
    },
    
    formatSegmentationConfig() {
      // Format segmentation config for the API
      const config = {
        enabled: this.segmentation.enabled,
        threshold: this.segmentation.threshold,
        examples: {}
      };
      
      // Only include examples if they have both prompt and segments
      const rel = this.segmentation.examples.relational;
      if (rel.prompt && rel.segments && rel.segments.length > 0) {
        const validSegments = rel.segments.filter(s => s.text);
        if (validSegments.length > 0) {
          config.examples.relational = {
            prompt: rel.prompt,
            segments: validSegments.map(s => s.text),
            code_lines: validSegments.map(s => this.parseLineRange(s.lines || ''))
          };
        }
      }
      
      const multi = this.segmentation.examples.multi_structural;
      if (multi.prompt && multi.segments && multi.segments.length > 0) {
        const validSegments = multi.segments.filter(s => s.text);
        if (validSegments.length > 0) {
          config.examples.multi_structural = {
            prompt: multi.prompt,
            segments: validSegments.map(s => s.text),
            code_lines: validSegments.map(s => this.parseLineRange(s.lines || ''))
          };
        }
      }
      
      return config;
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
     * Check if test case passed
     */
    isTestPassed(index) {
      return this.ui.testResults && 
             this.ui.testResults.results && 
             this.ui.testResults.results[index] && 
             this.ui.testResults.results[index].isSuccessful;
    },
    
    /**
     * Check if test case failed
     */
    isTestFailed(index) {
      return this.ui.testResults && 
             this.ui.testResults.results && 
             this.ui.testResults.results[index] && 
             !this.ui.testResults.results[index].isSuccessful;
    },
    
    /**
     * Get status class for test case
     */
    getStatusClass(index) {
      if (this.isTestPassed(index)) {return 'passed';}
      if (this.isTestFailed(index)) {return 'failed';}
      return '';
    },
    
    /**
     * Get status text for test case
     */
    getStatusText(index) {
      if (this.isTestPassed(index)) {return '✓';}
      if (this.isTestFailed(index)) {return '✗';}
      return '';
    },
    
    // === Function Signature Parsing ===
    
    /**
     * Parse function signature to extract parameters and return type
     */
    parseFunctionSignature() {
      const signature = this.form.function_signature;
      if (!signature) {
        this.functionParameters = [];
        this.returnType = 'Any';
        this.returnTypeSpec = { type: 'Any' };
        return;
      }
      
      // Parse function signature pattern: def func_name(param1: type1, param2: type2) -> return_type:
      const regex = /def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*(.+?))?:/;
      const match = signature.match(regex);
      
      if (!match) {
        this.functionParameters = [];
        this.returnType = 'Any';
        this.returnTypeSpec = { type: 'Any' };
        return;
      }
      
      const [_, functionName, paramsStr, returnTypeStr] = match;
      
      // Parse parameters with enhanced type specs
      this.functionParameters = this.parseParameters(paramsStr || '');
      this.returnType = returnTypeStr?.trim() || 'Any';
      this.returnTypeSpec = parseTypeAnnotation(this.returnType);
    },
    
    /**
     * Parse parameter string into parameter objects
     */
    parseParameters(paramsStr) {
      if (!paramsStr.trim()) {return [];}
      
      const params = [];
      
      // Handle typed parameters: param: type
      const paramRegex = /(\w+)\s*:\s*([^,]+)/g;
      let match;
      
      while ((match = paramRegex.exec(paramsStr)) !== null) {
        const typeStr = match[2].trim();
        params.push({
          name: match[1],
          type: typeStr,
          simplifiedType: typeStr.toLowerCase().split('[')[0],
          typeSpec: parseTypeAnnotation(typeStr)
        });
      }
      
      // Handle untyped parameters if no typed ones found
      if (params.length === 0) {
        const simpleParams = paramsStr.split(',').map(p => p.trim()).filter(p => p);
        simpleParams.forEach(param => {
          params.push({
            name: param,
            type: 'Any',
            simplifiedType: 'Any',
            typeSpec: { type: 'Any' }
          });
        });
      }
      
      return params;
    },
    
    
    // === Parameter Input Methods ===
    
    /**
     * Get parameter count for grid layout
     */
    getParameterCount() {
      return this.functionParameters.length || 1;
    },
    
    /**
     * Get parameter value for display in input field (raw string)
     */
    getParameterDisplayValue(testCase, paramIndex) {
      if (!testCase.inputs || paramIndex >= testCase.inputs.length) {
        return '';
      }
      return testCase.inputs[paramIndex] ?? '';
    },
    
    /**
     * Update parameter value (store raw string)
     */
    updateParameterValue(testCase, paramIndex, stringValue) {
      // Ensure inputs array exists and is long enough
      if (!testCase.inputs) {
        testCase.inputs = [];
      }
      while (testCase.inputs.length <= paramIndex) {
        testCase.inputs.push('');
      }
      
      // Store exactly what user typed (raw string)
      testCase.inputs[paramIndex] = stringValue;
    },
    
    
    /**
     * Get validation error for a parameter (computed on-demand)
     */
    getParameterValidationError(testCase, paramIndex) {
      if (!testCase.inputs || paramIndex >= testCase.inputs.length) {
        return null;
      }
      
      const rawString = String(testCase.inputs[paramIndex] || '');
      const expectedType = this.functionParameters[paramIndex]?.type;
      
      if (!expectedType || expectedType === 'Any' || !rawString.trim()) {
        return null;
      }
      
      try {
        // Convert raw string to value for validation
        const convertedValue = autoDetectAndConvert(rawString);
        const typeSpec = parseTypeAnnotation(expectedType);
        const validationResult = validateValueAgainstType(convertedValue, typeSpec);
        return validationResult.valid ? null : validationResult.error;
      } catch (error) {
        return 'Invalid input format';
      }
    },
    
    /**
     * Get detected type for a parameter (computed on-demand)
     */
    getParameterDetectedType(testCase, paramIndex) {
      if (!testCase.inputs || paramIndex >= testCase.inputs.length) {
        return 'Any';
      }
      
      const rawString = String(testCase.inputs[paramIndex] || '');
      if (!rawString.trim()) {
        return 'Any';
      }
      
      // Auto-detect type from raw string input
      const typeInfo = autoDetectTypeFromInput(rawString);
      return typeInfo.annotation;
    },
    
    /**
     * Get CSS class for type badge
     */
    getTypeClass(detectedType, hasError = false) {
      if (hasError) {return 'type-error';}
      
      // Extract base type from complex annotations like "Dict[int, List[str]]"
      const baseType = detectedType.toLowerCase().split('[')[0];
      
      if (['int', 'float'].includes(baseType)) {return 'type-number';}
      if (baseType === 'str') {return 'type-string';}
      if (baseType === 'bool') {return 'type-boolean';}
      if (['list', 'dict', 'tuple', 'set'].includes(baseType)) {return 'type-collection';}
      if (baseType === 'none') {return 'type-none';}
      if (baseType === 'invalid') {return 'type-invalid';}
      if (baseType === 'optional') {return 'type-optional';}
      
      return 'type-any';
    },
    
    /**
     * Get CSS class for parameter type badge
     */
    getParameterTypeClass(testCase, paramIndex) {
      const detectedType = this.getParameterDetectedType(testCase, paramIndex);
      const hasError = this.getParameterValidationError(testCase, paramIndex);
      return this.getTypeClass(detectedType, hasError);
    },
    
    
    /**
     * Get type info tooltip
     */
    getParameterTypeInfo(testCase, paramIndex) {
      const detectedType = this.getParameterDetectedType(testCase, paramIndex);
      const expectedType = this.functionParameters[paramIndex]?.type || 'Any';
      const error = this.getParameterValidationError(testCase, paramIndex);
      
      if (error) {return error;}
      return `Detected: ${detectedType} | Expected: ${expectedType}`;
    },
    
    /**
     * Get placeholder for parameter input
     */
    getParameterPlaceholder(type) {
      return getPlaceholderForType(type);
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
     * Get detected type for output (computed on-demand)
     */
    getOutputDetectedType(testCase) {
      const rawString = String(testCase.expected_output || '');
      if (!rawString.trim()) {
        return 'Any';
      }
      
      // Auto-detect type from raw string input
      const typeInfo = autoDetectTypeFromInput(rawString);
      return typeInfo.annotation;
    },
    
    /**
     * Get CSS class for output type badge
     */
    getOutputTypeClass(testCase) {
      const detectedType = this.getOutputDetectedType(testCase);
      const hasError = this.getOutputValidationError(testCase);
      return this.getTypeClass(detectedType, hasError);
    },
    
    /**
     * Get validation error for output (computed on-demand)
     */
    getOutputValidationError(testCase) {
      const rawString = String(testCase.expected_output || '');
      const expectedType = this.getReturnType();
      
      if (!expectedType || expectedType === 'Any' || !rawString.trim()) {
        return null;
      }
      
      try {
        // Convert raw string to value for validation
        const convertedValue = autoDetectAndConvert(rawString);
        const typeSpec = parseTypeAnnotation(expectedType);
        const validationResult = validateValueAgainstType(convertedValue, typeSpec);
        return validationResult.valid ? null : validationResult.error;
      } catch (error) {
        return 'Invalid input format';
      }
    },

    /**
     * Get type info tooltip for output
     */
    getOutputTypeInfo(testCase) {
      const detectedType = this.getOutputDetectedType(testCase);
      const expectedType = this.getReturnType();
      const error = this.getOutputValidationError(testCase);
      
      if (error) {return error;}
      return `Detected: ${detectedType} | Expected: ${expectedType}`;
    },
    
    /**
     * Update reference solution ensuring it's always a string
     */
    updateReferenceSolution(value) {
      this.form.reference_solution = value;
    },
    
    
    /**
     * Convert test cases from string format to backend format
     */
    convertTestCasesForBackend(testCases) {
      return testCases.map(tc => {
        const convertedInputs = tc.inputs.map(rawValue => {
          if (rawValue == null || !String(rawValue).trim()) {
            return null;
          }
          try {
            // If it's already a proper type (from AI), use it directly
            // If it's a string (from user input), try to convert it
            if (typeof rawValue === 'string') {
              return autoDetectAndConvert(rawValue);
            } else {
              return rawValue; // Use the typed value directly
            }
          } catch {
            return rawValue; // Keep original value if conversion fails
          }
        });

        let convertedOutput;
        const rawOutput = tc.expected_output;
        if (rawOutput == null || !String(rawOutput).trim()) {
          convertedOutput = null;
        } else {
          try {
            // If it's already a proper type (from AI), use it directly
            // If it's a string (from user input), try to convert it
            if (typeof rawOutput === 'string') {
              convertedOutput = autoDetectAndConvert(rawOutput);
            } else {
              convertedOutput = rawOutput; // Use the typed value directly
            }
          } catch {
            convertedOutput = rawOutput; // Keep original value if conversion fails
          }
        }

        return {
          inputs: convertedInputs,
          expected_output: convertedOutput,
          description: tc.description || '',
          order: Number(tc.order) || 0
        };
      });
    },

    /**
     * Convert backend test cases to string format for editing
     */
    convertTestCasesFromBackend(testCases) {
      if (!Array.isArray(testCases)) {
        return [];
      }
      return testCases.map(tc => ({
        ...tc,
        inputs: (tc.inputs || []).map(value => formatValueForInput(value)),
        expected_output: formatValueForInput(tc.expected_output),
        error: null
      }));
    },

    /**
     * Helper method to safely convert form fields to strings for API calls
     */
    getApiSafeString(value) {
      if (Array.isArray(value)) {
        return JSON.stringify(value);
      }
      return String(value || '').trim();
    }
  }
})
</script>

<style scoped>
/* Common Utilities */
.transition-fast {
  transition: var(--transition-fast);
}

.rounded-base {
  border-radius: var(--radius-base);
}

.rounded-lg {
  border-radius: var(--radius-lg);
}

.border-default {
  border: 2px solid var(--color-bg-border);
}

.hover-lift:hover {
  transform: translateY(-1px);
}

.hover-primary:hover {
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

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
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-xs);
}

.breadcrumb-link:hover {
  background: var(--color-bg-hover);
}

/*/* Header Section */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xxl);
  padding: var(--spacing-xl);
  background: var(--color-bg-panel);
  box-shadow: var(--shadow-base);
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
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-base);
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

/* Markdown Tabs */
.markdown-tabs {
  display: flex;
  border-bottom: 2px solid var(--color-bg-border);
  margin-bottom: 0;
  margin-top: var(--spacing-sm);
}

.tab-button {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-bg-hover);
  border: none;
  border-bottom: 3px solid transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: 500;
  transition: var(--transition-fast);
  border-radius: var(--radius-xs) var(--radius-xs) 0 0;
}

.tab-button:hover {
  background: var(--color-bg-panel);
  color: var(--color-text-primary);
}

.tab-button.active {
  background: var(--color-bg-panel);
  color: var(--color-primary-gradient-start);
  border-bottom-color: var(--color-primary-gradient-start);
  font-weight: 600;
}

.markdown-content {
  border: 2px solid var(--color-bg-border);
  border-top: none;
  border-radius: 0 0 var(--radius-base) var(--radius-base);
  overflow: hidden;
}

.markdown-textarea {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
  font-size: var(--font-size-sm);
  resize: vertical;
  min-height: 200px;
  transition: var(--transition-base);
  line-height: 1.5;
  caret-color: var(--color-text-primary);
}

.markdown-textarea:focus {
  outline: none;
  background: var(--color-bg-panel);
}

.markdown-textarea::placeholder {
  color: var(--color-text-muted);
}

.markdown-preview {
  text-align: left !important;
  padding: var(--spacing-lg);
  background: var(--color-bg-panel);
  color: var(--color-text-primary);
  min-height: 300px;
  line-height: 1.6;
  font-size: var(--font-size-base);
  overflow-y: auto;
  max-height: 500px;
}

/* Markdown content styling */
.markdown-preview h1,
.markdown-preview h2,
.markdown-preview h3,
.markdown-preview h4,
.markdown-preview h5,
.markdown-preview h6 {
  color: var(--color-text-primary);
  margin-top: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
  font-weight: 600;
}

.markdown-preview h1 {
  font-size: var(--font-size-xl);
  border-bottom: 2px solid var(--color-bg-border);
  padding-bottom: var(--spacing-sm);
}

.markdown-preview h2 {
  font-size: var(--font-size-lg);
  border-bottom: 1px solid var(--color-bg-border);
  padding-bottom: var(--spacing-xs);
}

.markdown-preview h3 {
  font-size: var(--font-size-md);
}

.markdown-preview p {
  margin-bottom: var(--spacing-md);
  line-height: 1.7;
}

.markdown-preview code {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
  font-size: 0.9em;
}

.markdown-preview pre {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-md);
  overflow-x: auto;
  margin: var(--spacing-md) 0;
}

.markdown-preview pre code {
  background: none;
  padding: 0;
  border-radius: 0;
}

.markdown-preview blockquote {
  border-left: 4px solid var(--color-primary-gradient-start);
  padding-left: var(--spacing-md);
  margin: var(--spacing-md) 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

.markdown-preview ul,
.markdown-preview ol {
  margin: var(--spacing-md) 0;
  padding-left: var(--spacing-xl);
}

.markdown-preview li {
  margin-bottom: var(--spacing-sm);
}

.markdown-preview table {
  border-collapse: collapse;
  width: 100%;
  margin: var(--spacing-md) 0;
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  overflow: hidden;
}

.markdown-preview th,
.markdown-preview td {
  padding: var(--spacing-sm) var(--spacing-md);
  text-align: left;
  border-bottom: 1px solid var(--color-bg-border);
}

.markdown-preview th {
  background: var(--color-bg-hover);
  font-weight: 600;
}

.markdown-preview .no-content,
.markdown-preview .error {
  color: var(--color-text-muted);
  font-style: italic;
  text-align: center;
  padding: var(--spacing-xl);
}

.markdown-preview .error {
  color: var(--color-error-text);
  background: var(--color-error-bg);
  border-radius: var(--radius-base);
}

.form-group input,
.form-group textarea:not(.markdown-textarea),
.form-group select {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.form-group input:focus,
.form-group textarea:not(.markdown-textarea):focus,
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

/* Test Actions Bar */
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
  grid-template-columns: 40px 1fr 1fr auto;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  align-items: stretch;
}

/* No parameters message */
.no-params-message {
  display: flex;
  align-items: center;
  color: var(--color-text-muted);
  font-style: italic;
  font-size: var(--font-size-sm);
  padding: var(--spacing-sm);
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

.param-input {
  flex: 1;
  padding: var(--spacing-md);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
}

.param-input:focus {
  border-color: var(--color-primary-gradient-start);
  outline: none;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.param-input.param-error {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.param-input::placeholder {
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

.type-optional {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #f59e0b;
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

/* Test Case Actions Container */
.test-case-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
}

/* Status Badge - Improved Design */
.status-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-circle);
  transition: var(--transition-fast);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.status-badge.passed {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.status-badge.failed {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
}

.status-icon {
  font-size: 14px;
  font-weight: bold;
  line-height: 1;
}

/* Remove Button */
.remove-btn {
  background: var(--color-bg-hover);
  border: 1.5px solid var(--color-bg-border);
  color: var(--color-text-muted);
  cursor: pointer;
  border-radius: var(--radius-circle);
  transition: var(--transition-fast);
  width: 32px;
  height: 32px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.remove-btn:hover {
  background: var(--color-error-bg);
  border-color: var(--color-error);
  color: var(--color-error);
  transform: scale(1.05);
}

.remove-btn svg {
  width: 16px;
  height: 16px;
  transition: var(--transition-fast);
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

/* Loading Overlay */
.test-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  border-radius: var(--radius-lg);
}

.loading-spinner {
  text-align: center;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: var(--color-primary-gradient-start);
  border-radius: 50%;
  animation: spin 1s ease-in-out infinite;
  margin: 0 auto var(--spacing-md);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
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

/* Hints Configuration Styles */
.hint-tabs {
  display: flex;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-lg);
  border-bottom: 2px solid var(--color-bg-border);
}

.hint-tab-button {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: 500;
  transition: var(--transition-fast);
  border-bottom: 3px solid transparent;
  border-radius: var(--radius-xs) var(--radius-xs) 0 0;
}

.hint-tab-button:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.hint-tab-button.active {
  color: var(--color-primary-gradient-start);
  border-bottom-color: var(--color-primary-gradient-start);
  font-weight: 600;
}

.hint-config-panel {
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

.hint-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.toggle-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.toggle-checkbox {
  width: 20px;
  height: 20px;
  margin-right: var(--spacing-sm);
  cursor: pointer;
}

.toggle-text {
  color: var(--color-text-primary);
  font-weight: 500;
}

.attempts-config {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.attempts-config label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  margin: 0;
}

.attempts-input {
  width: 60px;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  text-align: center;
}

/* Variable Fade Styles */
.mappings-section h4,
.subgoals-section h4,
.suggested-trace-section h4 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: 600;
}

.mappings-list,
.subgoals-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
}

.mapping-item,
.add-mapping {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.mapping-input {
  flex: 1;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
}

.mapping-arrow {
  color: var(--color-text-secondary);
  font-weight: 600;
  flex-shrink: 0;
}

.remove-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-error);
  color: white;
  border: none;
  border-radius: var(--radius-xs);
  cursor: pointer;
  font-size: var(--font-size-lg);
  line-height: 1;
  transition: var(--transition-fast);
}

.remove-btn:hover {
  background: var(--color-error-dark);
  transform: scale(1.1);
}

/* Subgoal Styles */
.subgoal-item {
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
}

.subgoal-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.subgoal-title-input {
  flex: 1;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  font-weight: 500;
}

.subgoal-lines {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.subgoal-lines label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  margin: 0;
}

.line-input {
  width: 80px;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  text-align: center;
}

.subgoal-explanation {
  width: 100%;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  resize: vertical;
  min-height: 60px;
}

.add-subgoal {
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border: 2px dashed var(--color-bg-border);
  border-radius: var(--radius-base);
}

.add-subgoal h5 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

/* Suggested Trace Styles */
.suggested-trace-section {
  animation: fadeIn 0.3s ease-out;
}

.suggested-trace-section h4 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.hint-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--spacing-lg) 0;
  line-height: 1.6;
  background: var(--color-bg-panel);
  padding: var(--spacing-md);
  border-radius: var(--radius-base);
  border-left: 3px solid var(--color-primary-gradient-start);
}

.form-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.label-required {
  color: var(--color-error);
  font-size: var(--font-size-base);
}

.label-optional {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: normal;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-family: inherit;
  transition: var(--transition-fast);
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 100px;
}

.input-error {
  color: var(--color-error);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.input-error::before {
  content: '⚠';
  font-size: var(--font-size-sm);
}

.input-hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

/* Trace Preview Section (matches student view) */
.trace-preview-section {
  margin-top: var(--spacing-lg);
}

.trace-preview-section .preview-label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Student view styles */
.suggested-trace {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-md) var(--spacing-lg);
  transition: var(--transition-base);
}

.suggested-trace:hover {
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-sm);
}

.trace-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.trace-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.trace-function {
  font-family: var(--font-mono, 'SF Mono', 'Monaco', 'Inconsolata', monospace);
  font-size: var(--font-size-sm);
  background: var(--color-bg-code, var(--color-bg-hover));
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-sm, 4px);
  padding: var(--spacing-xs) var(--spacing-sm);
  color: var(--color-text-primary);
  flex: 1;
  min-width: 200px;
  overflow-x: auto;
}

.trace-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-primary-gradient-start);
  color: white;
  border: none;
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: var(--transition-base);
  font-size: var(--font-size-sm);
  font-weight: 500;
  white-space: nowrap;
}

.trace-btn:hover:not(:disabled) {
  background: var(--color-primary-gradient-end);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.trace-btn:disabled {
  background: var(--color-bg-disabled);
  color: var(--color-text-muted);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}


.test-case-selector {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  max-height: 300px;
  overflow-y: auto;
  padding: var(--spacing-sm);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
}

.test-case-option {
  padding: var(--spacing-sm);
  border-radius: var(--radius-xs);
  transition: var(--transition-fast);
}

.test-case-option:hover {
  background: var(--color-bg-hover);
}

.test-case-option.selected {
  background: rgba(102, 126, 234, 0.1);
  border-left: 3px solid var(--color-primary-gradient-start);
  padding-left: calc(var(--spacing-sm) - 3px);
}

.test-case-option label {
  display: flex;
  align-items: center;
  cursor: pointer;
  margin: 0;
}

.test-case-option input[type="checkbox"] {
  margin-right: var(--spacing-sm);
}

.test-case-preview {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.instructions-section {
  margin-top: var(--spacing-lg);
}

.instructions-section label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
}

.instructions-section textarea {
  width: 100%;
  padding: var(--spacing-sm);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  resize: vertical;
}

/* Segmentation Configuration Styles */
.segmentation-toggle {
  margin-bottom: var(--spacing-lg);
}

.segmentation-toggle .hint-description {
  margin-top: var(--spacing-sm);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.segmentation-config-panel {
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

.threshold-section {
  margin-bottom: var(--spacing-xl);
}

.threshold-section:last-child {
  margin-bottom: 0;
}

.section-description {
  margin: var(--spacing-sm) 0 var(--spacing-lg);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: 1.5;
}

.threshold-control {
  background: var(--color-bg-secondary);
  padding: var(--spacing-lg);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-bg-border);
}

.threshold-slider-container {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  margin: var(--spacing-md) 0;
}

.threshold-slider {
  flex: 1;
  -webkit-appearance: none;
  height: 6px;
  background: var(--color-bg-border);
  border-radius: 3px;
  outline: none;
}

.threshold-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: var(--color-primary-gradient-start);
  cursor: pointer;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s;
}

.threshold-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.threshold-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: var(--color-primary-gradient-start);
  cursor: pointer;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  border: none;
}

.threshold-value {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-primary-gradient-start);
  min-width: 30px;
  text-align: center;
}

.threshold-labels {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md);
  margin-top: var(--spacing-lg);
}

.threshold-label {
  padding: var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  text-align: center;
  transition: all 0.3s ease;
  opacity: 0.6;
}

.threshold-label.active {
  opacity: 1;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-hover);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.threshold-label .label-icon {
  font-size: var(--font-size-xl);
  display: block;
  margin-bottom: var(--spacing-xs);
}

.threshold-label .label-name {
  font-weight: 600;
  color: var(--color-text-primary);
  display: block;
  margin-bottom: var(--spacing-xs);
}

.threshold-label .label-range {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

/* Segmentation Configuration Styles */

.segment-item {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) 0;
  font-size: var(--font-size-sm);
}

.segment-number {
  font-weight: 600;
  color: var(--color-primary-gradient-start);
  min-width: 20px;
}

.segment-text {
  flex: 1;
  color: var(--color-text-primary);
}

.segment-lines {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}


/* New Segmentation Examples Styles */
.segmentation-examples-section {
  background: var(--color-bg-hover);
  padding: var(--spacing-lg);
  border-radius: var(--radius-base);
}

.threshold-setting {
  margin-bottom: var(--spacing-xl);
}

.threshold-control {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.threshold-input {
  width: 80px;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
  font-size: var(--font-size-base);
  text-align: center;
}

.threshold-help {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-left: var(--spacing-md);
}

.example-block {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-lg);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-base);
  background: var(--color-bg-secondary);
}

.example-block.relational {
  border-color: var(--color-success);
}

.example-block.multi-structural {
  border-color: var(--color-error);
}

.example-block h5 {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-base);
  font-weight: 600;
}

.example-icon {
  font-size: 1.2em;
}

.example-help {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--spacing-lg);
}

.segments-editor {
  margin-top: var(--spacing-md);
}

.segments-editor label {
  display: block;
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.segment-item {
  background: var(--color-bg-secondary);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-md);
  border: 1px solid var(--color-bg-border);
}

.segment-row {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.segment-input {
  flex: 1;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-primary);
  font-size: var(--font-size-sm);
}

.code-lines-row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.code-lines-row .lines-label {
  font-weight: 600;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  min-width: 80px;
  margin-bottom: 0;
}

.code-lines-row input {
  flex: 1;
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-primary);
  font-size: var(--font-size-xs);
  font-family: var(--font-family-mono);
}

.btn-icon {
  width: 32px;
  height: 32px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 1.2em;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: var(--transition-base);
}

.btn-icon:hover {
  background: var(--color-error-bg);
  color: var(--color-error);
  border-color: var(--color-error);
}

.btn-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
}
</style>
