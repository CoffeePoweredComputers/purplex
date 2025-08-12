<template>
  <div
    v-if="isLoading"
    class="loading-container"
  >
    <div class="loading-message">
      Loading problem set...
    </div>
  </div>
  <div
    v-else-if="!problems || problems.length === 0"
    class="loading-container"
  >
    <div class="loading-message">
      No problems found in this set.
    </div>
  </div>
  <div
    v-else
    class="problem-set-container"
  >
    <!-- Navigation Loading Overlay - Removed to prevent flashing -->
    <!-- Consider using a less intrusive loading indicator instead -->

    <div class="problem-navigation">
      <div class="problem-selector">
        <button 
          class="nav-button" 
          @click="prevProblem"
        >
          <span class="arrow-left">‹</span>
        </button>
        <div class="problem-info">
          <div class="progress-summary">
            <span class="progress-stat completed">{{ completedCount }} completed</span>
            <span class="progress-stat in_progress">{{ inProgressCount }} in progress</span>
            <span class="progress-stat remaining">{{ remainingCount }} remaining</span>
          </div>
          <div class="problem-progress">
            <div
              v-for="(problem, index) in problems"
              :key="problem.slug" 
              :class="['progress-bar', 
                       { 'active': index === currentProblem },
                       { 'completed': getProblemStatus(problem.slug) === 'completed' },
                       { 'in_progress': getProblemStatus(problem.slug) === 'in_progress' },
                       { 'not_started': getProblemStatus(problem.slug) === 'not_started' }
              ]" 
              :title="getProblemTooltip(problem, index)"
              @click="setProblem(index)"
            />
          </div>
        </div>
        <button 
          class="nav-button" 
          @click="nextProblem"
        >
          <span class="arrow-right">›</span>
        </button>
      </div>
    </div>

    <!-- Main workspace -->
    <div class="workspace">
      <!-- Left panel: Code editor and submission -->
      <div class="left-panel">
        <!-- Code editor section -->
        <div class="editor-section">
          <div class="section-header">
            <div class="section-label">
              Code Editor
            </div>
            <HintButton 
              :problem-slug="getCurrentProblem().slug"
              :course-id="courseId"
              :problem-set-slug="$route.params.slug"
              :current-attempts="getCurrentProblemAttempts()"
              @hint-used="onHintUsed"
              @hint-toggled="onHintToggled"
              @show-original="onShowOriginal"
              @remove-all-hints="onRemoveAllHints"
              @clear-all-hints="onClearAllHints"
            />
          </div>
          <Editor 
            ref="entry" 
            lang="python" 
            mode="python" 
            height="450px" 
            width="100%" 
            :value="displayedCode"
            :read-only="true"
            :show-gutter="showLineNumbers"
            :theme="currentTheme"
            :hint-markers="currentHintMarkers"
            @update:value="updateSolutionCode"
          />
          <div class="editor-toolbar">
            <div class="toolbar-options">
              <button
                class="toolbar-btn"
                title="Copy code"
                @click="copyCode"
              >
                <span v-if="!codeCopied">📋</span>
                <span v-else>✓</span>
              </button>
              <button
                class="toolbar-btn"
                :title="showLineNumbers ? 'Hide line numbers' : 'Show line numbers'"
                @click="toggleLineNumbers"
              >
                <span v-if="showLineNumbers">🔢</span>
                <span v-else>➖</span>
              </button>
              <div class="theme-selector">
                <select
                  v-model="editorTheme"
                  class="theme-dropdown"
                  @change="updateTheme"
                >
                  <option value="dark">
                    🌙 Dark
                  </option>
                  <option value="light">
                    ☀️ Light
                  </option>
                  <option value="monokai">
                    🎨 Monokai
                  </option>
                  <option value="github">
                    🐙 GitHub
                  </option>
                  <option value="solarized-dark">
                    🌅 Solarized Dark
                  </option>
                  <option value="solarized-light">
                    🌅 Solarized Light
                  </option>
                  <option value="dracula">
                    🧛 Dracula
                  </option>
                  <option value="tomorrow-night">
                    🌃 Tomorrow Night
                  </option>
                </select>
              </div>
            </div>
            <div class="zoom-controls">
              <button
                class="zoom-btn"
                :disabled="editorFontSize <= 12"
                title="Zoom out"
                @click="decreaseFontSize"
              >
                <span class="zoom-icon">−</span>
              </button>
              <span class="zoom-level">{{ Math.round((editorFontSize / 14) * 100) }}%</span>
              <button
                class="zoom-btn"
                :disabled="editorFontSize >= 35"
                title="Zoom in"
                @click="increaseFontSize"
              >
                <span class="zoom-icon">+</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Suggested Trace Hint Overlay -->
        <SuggestedTraceOverlay
          v-for="(overlay, index) in suggestedTraceOverlays"
          :key="`overlay-${index}`"
          v-bind="overlay.props"
          :solution-code="solutionCode"
          @open-pytutor="openPyTutor"
          @close="removeHint('suggested_trace')"
        />

        <!-- Submission section -->
        <div class="submission-section">
          <div class="section-header">
            <div class="section-label">
              Describe the code here
            </div>
          </div>
          <span
            v-if="draftSaved"
            class="draft-indicator"
          >✓ Draft saved</span>
          <div class="prompt-editor-wrapper">
            <Editor 
              ref="prompt_entry" 
              lang="text" 
              mode="text" 
              height="100px" 
              width="100%"
              :show-gutter="false" 
              :wrap="true"
              :theme="currentTheme"
            />
          </div>
          <button 
            id="submitButton" 
            class="submit-button" 
            :disabled="loading"
            @click="submit"
          >
            <span
              v-if="!loading"
              class="button-text"
            >Submit Solution</span>
            <div
              v-if="loading"
              class="loading-content"
            >
              <div class="bouncing-dots">
                <span class="dot" />
                <span class="dot" />
                <span class="dot" />
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- Right panel: Feedback -->
      <div class="right-panel">
        <Feedback 
          :progress="promptCorrectness" 
          :notches="6" 
          :code-results="codeResults" 
          :test-results="testResults"
          :comprehension-results="comprehensionResults" 
          :user-prompt="userPrompt"
          :segmentation="segmentationData"
          :reference-code="getCurrentProblem()?.reference_solution || ''"
          :problem-type="getCurrentProblem()?.problem_type || ''"
          :segmentation-enabled="getCurrentProblem()?.segmentation_enabled || false"
          :is-loading="loading"
          title="Feedback" 
        />
      </div>
    </div>

    <!-- PyTutor Modal -->
    <PyTutorModal 
      :is-visible="showPyTutorModal" 
      :python-tutor-url="pyTutorUrl" 
      @close="closePyTutor" 
    />
  </div>
</template>

<script>
import Editor from '@/features/editor/Editor.vue'
import Feedback from "@/components/Feedback.vue"
import HintButton from "@/components/HintButton.vue"
import SuggestedTraceOverlay from "@/components/hints/SuggestedTraceOverlay.vue"
import PyTutorModal from "@/modals/PyTutorModal.vue"
import axios from 'axios'
import { useNotification } from '@/composables/useNotification'
import { useLogger } from '@/composables/useLogger'
import { useOptimisticProgress } from '@/composables/useOptimisticProgress'
import { useHintTracking } from '@/composables/useHintTracking'
import { useEditorHints } from '@/composables/useEditorHints'
import { useSSE } from '@/composables/useSSE'
import submissionService from '@/services/submissionService'
import { computed, ref, watch } from 'vue'

export default {
    name: 'ProblemSet',
    components: {
        Editor,
        Feedback,
        HintButton,
        SuggestedTraceOverlay,
        PyTutorModal
    },
    props: {
        courseId: {
            type: String,
            default: null
        }
    },
    setup() {
        const { notify } = useNotification();
        const logger = useLogger();
        const { updateProgress, getProgress, clearOptimistic } = useOptimisticProgress();
        const { trackHintUsage, getHintsUsed } = useHintTracking();
        const { connectToEiPLSubmission, isConnected, error: sseError } = useSSE();
        
        // Hint system setup
        const entry = ref(null);
        const originalSolutionCode = ref('');
        
        // Initialize hint system
        const {
            modifiedCode,
            hasActiveHints,
            editorMarkers,
            activeOverlays,
            applyHint,
            removeHint,
            removeAllHints,
            restoreOriginal,
            isHintActive,
            getHintData,
            getStatus,
            saveState,
            restoreState
        } = useEditorHints(entry, originalSolutionCode);
        
        return { 
            notify, 
            logger,
            updateProgress, 
            getProgress, 
            clearOptimistic, 
            trackHintUsage, 
            getHintsUsed,
            // SSE connection
            connectToEiPLSubmission,
            isConnected,
            sseError,
            // Hint system
            entry,
            originalSolutionCode,
            modifiedCode,
            hasActiveHints,
            editorMarkers,
            activeOverlays,
            applyHint,
            removeHint,
            removeAllHints,
            restoreOriginal,
            isHintActive,
            getHintData,
            getHintStatus: getStatus,
            saveHintState: saveState,
            restoreHintState: restoreState
        };
    },
    data() {
        return {
            problemSet: {},
            problems: [],
            isLoading: true,
            
            /* Navigation State */
            currentProblem: 0,
            
            /* Submission State */
            loading: false,
            codeResults: [],
            testResults: [],
            promptCorrectness: 0,
            comprehensionResults: '',
            userPrompt: '',
            segmentationData: null,
            
            /* Problem Status Tracking */
            problemStatuses: {},
            problemSetProgress: null,
            
            /* Editor Settings */
            editorFontSize: 14,
            codeCopied: false,
            showLineNumbers: true,
            editorTheme: 'tomorrow-night',
            
            /* Draft Management */
            autoSaveInterval: null,
            draftSaved: false,
            
            /* Submission Data Cache - Simple 5min cache */
            submissionCache: new Map(),
            
            /* PyTutor Modal */
            showPyTutorModal: false,
            pyTutorUrl: '',
            
            /* Hint State Storage per Problem */
            problemHintStates: {}
        };
    },
    
    computed: {
        solutionCode() {
            return this.getCurrentProblem().reference_solution || '';
        },
        
        displayedCode() {
            return this.hasActiveHints ? this.modifiedCode : this.solutionCode;
        },
        
        currentHintMarkers() {
            const markers = this.editorMarkers || [];
            this.logger.debug('Current hint markers computed', { markers });
            return markers;
        },
        
        suggestedTraceOverlays() {
            return (this.activeOverlays || []).filter(
                overlay => overlay && overlay.component === 'SuggestedTraceOverlay'
            );
        },
        
        completedCount() {
            return Object.values(this.problemStatuses).filter(s => s.status === 'completed').length;
        },
        
        inProgressCount() {
            return Object.values(this.problemStatuses).filter(s => s.status === 'in_progress').length;
        },
        
        remainingCount() {
            return this.problems.length - this.completedCount - this.inProgressCount;
        },
        
        currentTheme() {
            const themeMap = {
                'dark': 'clouds_midnight',
                'light': 'chrome',
                'monokai': 'monokai',
                'github': 'github',
                'solarized-dark': 'solarized_dark',
                'solarized-light': 'solarized_light',
                'dracula': 'dracula',
                'tomorrow-night': 'tomorrow_night'
            };
            return themeMap[this.editorTheme] || 'clouds_midnight';
        }
    },
    
    watch: {
        '$route.params.slug': function(newSlug) {
            if (newSlug) {
                this.loadProblemSet();
            }
        },
        solutionCode: {
            handler(newCode) {
                // Update the originalSolutionCode ref when solution changes
                this.originalSolutionCode = newCode;
            },
            immediate: true
        },
        problemStatuses: {
            handler(newVal) {
                this.logger.debug('Problem statuses changed', {
                    statuses: newVal,
                    keys: Object.keys(newVal),
                    completedProblems: Object.values(newVal).filter(s => s.status === 'completed')
                });
            },
            deep: true
        },
        editorTheme: {
            handler() {
                this.$nextTick(() => {
                    this.updateTheme();
                });
            }
        }
    },
    
    async mounted() {
        await this.loadProblemSet();
        if (this.problems.length > 0) {
            await this.loadProblemData();
            this.startAutoSave();
            this.$nextTick(() => {
                if (this.$refs.entry && this.$refs.entry.editor) {
                    this.$refs.entry.editor.setFontSize(this.editorFontSize);
                }
                // Set theme for prompt editor
                if (this.$refs.prompt_entry && this.$refs.prompt_entry.editor) {
                    this.$refs.prompt_entry.editor.setTheme(`ace/theme/${this.currentTheme}`);
                }
            });
        }
    },
    
    beforeUnmount() {
        this.stopAutoSave();
        this.saveDraft(); // Save draft before leaving
    },
    
    methods: {
        async nextProblem() {
            await this.navigateToProblem((this.currentProblem + 1) % this.problems.length);
        },
        
        async prevProblem() {
            await this.navigateToProblem((this.currentProblem - 1 + this.problems.length) % this.problems.length);
        },
        
        async setProblem(index) {
            await this.navigateToProblem(index);
        },
        
        async navigateToProblem(newIndex) {
            if (newIndex === this.currentProblem) {return;}
            
            try {
                // Save current draft and hint state before switching
                this.saveDraft();
                const currentProblemSlug = this.getCurrentProblem().slug;
                if (currentProblemSlug) {
                    this.problemHintStates[currentProblemSlug] = this.saveHintState();
                }
                
                // Clear all hints and overlays before switching
                await this.removeAllHints();
                
                // Pre-fetch data to reduce loading time
                const problem = this.problems[newIndex];
                const submissionDataPromise = this.loadSubmissionData(problem.slug);
                
                // Update current problem index
                this.currentProblem = newIndex;
                
                // Wait for data and update UI smoothly
                const submissionData = await submissionDataPromise;
                
                // Apply submission data without clearing first
                this.codeResults = submissionData.variations || [];
                this.testResults = submissionData.results || [];
                this.promptCorrectness = submissionData.passing_variations || 0;
                this.comprehensionResults = submissionData.feedback || '';
                this.userPrompt = submissionData.user_prompt || '';
                this.segmentationData = submissionData.segmentation || null;
                
                // Load draft after data is ready
                await this.$nextTick();
                this.loadDraft();
                
                // Restore hint state for the new problem (this will clear if no state exists)
                const newProblemSlug = this.getCurrentProblem().slug;
                const savedState = newProblemSlug ? this.problemHintStates[newProblemSlug] : null;
                await this.restoreHintState(savedState);
                
            } catch (error) {
                this.logger.error('Navigation failed', error);
                this.notify.error('Navigation Error', 'Failed to load problem data');
            }
        },
        
        async loadProblemData() {
            const problem = this.getCurrentProblem();
            if (!problem.slug) {return;}
            
            try {
                // Load submission data with caching
                const submissionData = await this.loadSubmissionData(problem.slug);
                
                // Apply submission data
                this.codeResults = submissionData.variations || [];
                this.testResults = submissionData.results || [];
                this.promptCorrectness = submissionData.passing_variations || 0;
                this.comprehensionResults = submissionData.feedback || '';
                this.userPrompt = submissionData.user_prompt || '';
                this.segmentationData = submissionData.segmentation || null;
                
                // Load draft for this problem
                await this.$nextTick();
                this.loadDraft();
                
            } catch (error) {
                this.logger.error('Error loading problem data', error);
                // Clear on error
                this.clearFeedbackData();
            }
        },
        
        async loadSubmissionData(problemSlug) {
            const cacheKey = `${this.$route.params.slug}_${problemSlug}_${this.courseId || 'standalone'}`;
            
            // Check cache (5 minute expiry)
            if (this.submissionCache.has(cacheKey)) {
                const cached = this.submissionCache.get(cacheKey);
                if (Date.now() - cached.timestamp < 5 * 60 * 1000) {
                    return cached.data;
                }
            }
            
            try {
                // Include course_id in query params if available
                const params = this.courseId ? { course_id: this.courseId } : {};
                const response = await axios.get(`/api/user/last-submission/${problemSlug}/`, { params });
                const data = response.data;
                
                // Cache the response
                this.submissionCache.set(cacheKey, {
                    data,
                    timestamp: Date.now()
                });
                
                return data;
            } catch (error) {
                this.logger.error('Error loading submission', error);
                return {
                    has_submission: false,
                    variations: [],
                    results: [],
                    passing_variations: 0,
                    feedback: '',
                    user_prompt: '',
                    segmentation: null
                };
            }
        },
        
        clearFeedbackData() {
            this.codeResults = [];
            this.testResults = [];
            this.promptCorrectness = 0;
            this.comprehensionResults = '';
            this.userPrompt = '';
            this.segmentationData = null;
        },
        
        getCurrentProblem() {
            if (!this.problems || this.problems.length === 0) {
                return { solution: '', slug: '', name: 'Loading...' };
            }
            return this.problems[this.currentProblem] || this.problems[0];
        },
        
        getProblem() {
            return this.getCurrentProblem();
        },
        
        updateSolutionCode() {
            // Solution code is handled by computed property
        },
        
        increaseFontSize() {
            if (this.editorFontSize < 35) {
                this.editorFontSize += 2;
                this.updateEditorFontSize();
            }
        },
        
        decreaseFontSize() {
            if (this.editorFontSize > 12) {
                this.editorFontSize -= 2;
                this.updateEditorFontSize();
            }
        },
        
        updateEditorFontSize() {
            if (this.$refs.entry && this.$refs.entry.editor) {
                this.$refs.entry.editor.setFontSize(this.editorFontSize);
            }
        },
        
        copyCode() {
            const code = this.solutionCode;
            navigator.clipboard.writeText(code).then(() => {
                this.codeCopied = true;
                setTimeout(() => {
                    this.codeCopied = false;
                }, 2000);
            }).catch(err => {
                this.logger.error('Failed to copy code', err);
            });
        },
        
        toggleLineNumbers() {
            this.showLineNumbers = !this.showLineNumbers;
            if (this.$refs.entry && this.$refs.entry.editor) {
                this.$refs.entry.editor.renderer.setShowGutter(this.showLineNumbers);
            }
        },
        
        updateTheme() {
            if (this.$refs.entry && this.$refs.entry.editor) {
                this.$refs.entry.editor.setTheme(`ace/theme/${this.currentTheme}`);
            }
            // Also update theme for prompt editor
            if (this.$refs.prompt_entry && this.$refs.prompt_entry.editor) {
                this.$refs.prompt_entry.editor.setTheme(`ace/theme/${this.currentTheme}`);
            }
        },
        
        async submit() {
            if (this.loading) return;
            
            this.loading = true;
            const currentProblemSlug = this.getCurrentProblem().slug;
            
            try {
                // Add defensive checks for editor availability
                if (!this.$refs.prompt_entry || !this.$refs.prompt_entry.editor) {
                    this.notify.error('Editor not available. Please refresh the page.');
                    this.loading = false;
                    return;
                }
                
                const promptText = this.$refs.prompt_entry.editor.getValue();
                
                if (!promptText || promptText.trim() === '') {
                    this.notify.warning('Please enter a description of what the function does.');
                    this.loading = false;
                    return;
                }
                
                // Clear previous feedback
                this.clearFeedbackData();
                
                // Optimistic update
                let rollback = null;
                rollback = this.updateProgress(currentProblemSlug, {
                    status: 'in_progress',
                    score: null,
                    attempts: (this.problemStatuses[currentProblemSlug]?.attempts || 0) + 1
                });

                const submissionData = {
                    problem_slug: currentProblemSlug,
                    problem_set_slug: this.$route.params.slug,
                    user_prompt: promptText
                };
                
                // Include course_id if we're in a course context
                if (this.courseId) {
                    submissionData.course_id = this.courseId;
                }
                
                this.logger.info('Submitting EiPL solution', { problemSlug: currentProblemSlug });
                
                // Submit to async endpoint
                const submissionResponse = await submissionService.submitEiPL(submissionData);
                
                if (!submissionResponse.request_id) {
                    throw new Error('No request ID received from server');
                }
                
                this.logger.info('EiPL submission accepted, connecting to SSE stream', { 
                    requestId: submissionResponse.request_id 
                });
                
                // Connect to SSE stream for real-time updates
                await this.connectToEiPLSubmission(
                    submissionResponse.request_id,
                    (variations, testResults) => {
                        // Success callback - results are ready
                        this.logger.info('EiPL results received', { 
                            variations: variations.length,
                            testResults: testResults.length 
                        });

                        console.log('Test Results:', testResults);
                        console.log('Sample test result structure:', testResults[0]);
                        
                        // Update feedback data
                        this.codeResults = variations;
                        this.testResults = testResults;
                        
                        // Calculate test results across all variations
                        let totalTestsPassed = 0;
                        let totalTestsRun = 0;
                        let perfectVariations = 0;
                        
                        testResults.forEach(r => {
                            const passed = r.testsPassed || 0;
                            const total = r.totalTests || 0;
                            totalTestsPassed += passed;
                            totalTestsRun += total;
                            if (r.success) {
                                perfectVariations++;
                            }
                        });
                        
                        // Store perfect variations count for compatibility
                        this.promptCorrectness = perfectVariations;
                        this.userPrompt = promptText;
                        
                        // TODO: Handle segmentation data when available
                        this.segmentationData = null;
                        
                        // Calculate score based on total tests passed across all variations
                        const score = totalTestsRun > 0 
                            ? Math.round((totalTestsPassed / totalTestsRun) * 100)
                            : 0;
                        
                        // Update progress tracking with final status
                        this.problemStatuses[currentProblemSlug] = {
                            status: score >= 100 ? 'completed' : 'in_progress',
                            score: score,
                            attempts: (this.problemStatuses[currentProblemSlug]?.attempts || 0) + 1
                        };
                        
                        this.clearOptimistic(currentProblemSlug);
                        
                        // Update cache with new submission data
                        const cacheKey = `${this.$route.params.slug}_${currentProblemSlug}_${this.courseId || 'standalone'}`;
                        this.submissionCache.set(cacheKey, {
                            data: {
                                has_submission: true,
                                variations: this.codeResults,
                                results: this.testResults,
                                passing_variations: this.promptCorrectness,
                                user_prompt: this.userPrompt,
                                segmentation: this.segmentationData
                            },
                            timestamp: Date.now()
                        });
                        
                        // Store successful submission
                        if (this.userSubmissions) {
                            this.userSubmissions[currentProblemSlug] = promptText;
                        }
                        
                        // Create detailed success message
                        let message = `Solution submitted successfully! Score: ${score}%`;
                        if (totalTestsRun > 0) {
                            message += ` (${totalTestsPassed}/${totalTestsRun} tests passed across ${variations.length} variations)`;
                        }
                        this.notify.success(message);
                        this.loading = false;
                    },
                    {
                        // SSE options
                        onError: (error) => {
                            this.logger.error('SSE connection error', error);
                            this.notify.error(error.error || 'Failed to get results');
                            this.loading = false;
                            if (rollback) rollback(); // Rollback optimistic update on error
                        },
                        onTimeout: () => {
                            this.logger.warn('SSE connection timeout');
                            this.notify.warning('Connection timeout. Please try again.');
                            this.loading = false;
                            if (rollback) rollback();
                        },
                        reconnectAttempts: 3,
                        reconnectDelay: 2000
                    }
                );

            } catch (error) {
                this.logger.error('Error submitting code', error);
                
                // Clear feedback on error
                this.clearFeedbackData();
                
                // Handle errors
                if (error.response) {
                    if (error.response.status === 500) {
                        this.notify.error('Server Error', 'The AI service might be unavailable.');
                    } else if (error.response.status === 401) {
                        this.notify.error('Authentication Error', 'Please log in again.');
                    } else if (error.response.status === 400) {
                        this.notify.warning('Invalid Request', error.response.data.error || 'Please check your input.');
                    } else {
                        this.notify.error('Error', error.response.data.error || 'An unknown error occurred.');
                    }
                } else if (error.request) {
                    this.notify.error('Network Error', 'Unable to reach the server.');
                } else {
                    this.notify.error('Error', error.message);
                }
                // Reset loading state on error during initial submission
                this.loading = false;
                // Rollback optimistic update on error
                if (rollback) rollback();
            } finally {
                // Loading state is managed in SSE callbacks
                // Don't reset it here as SSE is still processing
            }
        },
        
        async loadProblemSet() {
            const problemSetSlug = this.$route.params.slug;
            this.isLoading = true;
            
            try {
                const response = await axios.get(`/api/problem-sets/${problemSetSlug}`);
                this.problemSet = response.data;
                
                if (response.data.problems_detail && Array.isArray(response.data.problems_detail)) {
                    this.problems = response.data.problems_detail.map(pd => pd.problem);
                } else if (response.data.problems && Array.isArray(response.data.problems)) {
                    this.problems = response.data.problems;
                } else {
                    this.problems = [];
                }
                
                await this.loadProblemStatuses();
                
            } catch (error) {
                this.logger.error('Error fetching problem set', error);
                this.notify.error('Load Error', 'Failed to load problem set.');
            } finally {
                this.isLoading = false;
            }
        },
        
        async loadProblemStatuses() {
            const problemSetSlug = this.$route.params.slug;
            
            try {
                // Include course_id in query params if available
                const params = this.courseId ? { course_id: this.courseId } : {};
                this.logger.debug('Loading problem statuses', { problemSetSlug, params });
                
                const response = await axios.get(`/api/problem-sets/${problemSetSlug}/progress/`, { params });
                const progressData = response.data.problems_progress || [];
                
                this.logger.debug('Progress data received', { progressData, problemSetProgress: response.data.problem_set });
                
                // Create new object for Vue reactivity
                const newStatuses = {};
                
                progressData.forEach(progress => {
                    newStatuses[progress.problem_slug] = {
                        status: this.mapStatusFromAPI(progress.status, progress.best_score),
                        score: progress.best_score,
                        attempts: progress.attempts
                    };
                });
                
                // Replace entire object to trigger reactivity
                this.problemStatuses = newStatuses;
                
                this.logger.debug('Problem statuses loaded', {
                    statuses: this.problemStatuses,
                    completedCount: this.completedCount,
                    inProgressCount: this.inProgressCount,
                    remainingCount: this.remainingCount
                });
                
                if (response.data.problem_set) {
                    this.problemSetProgress = response.data.problem_set;
                }
                
                // Force Vue to update the computed properties
                this.$nextTick(() => {
                    this.logger.debug('Counts recomputed after nextTick', {
                        completedCount: this.completedCount,
                        inProgressCount: this.inProgressCount,
                        remainingCount: this.remainingCount
                    });
                });
                
            } catch (error) {
                this.logger.error('Error loading progress data', {
                    error,
                    response: error.response?.data
                });
            }
        },
        
        mapStatusFromAPI(apiStatus, score) {
            // Direct pass-through - backend status is source of truth
            return apiStatus;
        },
        
        getProblemStatus(problemSlug) {
            const actualStatus = this.problemStatuses[problemSlug];
            const optimisticStatus = this.getProgress(problemSlug, actualStatus);
            return optimisticStatus?.status || 'not_started';
        },
        
        getProblemTooltip(problem, index) {
            const status = this.problemStatuses[problem.slug];
            const problemName = problem.title || `Problem ${index + 1}`;
            
            if (!status || status.status === 'not_started') {
                return `${problemName} - Not attempted`;
            } else if (status.status === 'in_progress') {
                return `${problemName} - In Progress (Score: ${status.score}%)`;
            } else if (status.status === 'completed') {
                return `${problemName} - Completed (Score: ${status.score}%)`;
            }
            return problemName;
        },
        
        // Draft Management - Simplified
        saveDraft() {
            // Add defensive checks to prevent accessing destroyed editor
            try {
                if (!this.$refs.prompt_entry || !this.$refs.prompt_entry.editor) {
                    return;
                }
                
                // Additional safety check for editor availability
                if (typeof this.$refs.prompt_entry.editor.getValue !== 'function') {
                    return;
                }
                
                const promptText = this.$refs.prompt_entry.editor.getValue();
                if (promptText && promptText.trim()) {
                    const draftKey = `draft_${this.$route.params.slug}_${this.getCurrentProblem().slug}`;
                    localStorage.setItem(draftKey, promptText);
                    localStorage.setItem(`${draftKey}_timestamp`, Date.now().toString());
                    
                    this.draftSaved = true;
                    setTimeout(() => {
                        this.draftSaved = false;
                    }, 2000);
                }
            } catch (error) {
                // Silently fail if editor is not available during navigation
                this.logger.debug('Draft save skipped during navigation', error);
            }
        },
        
        loadDraft() {
            try {
                if (!this.$refs.prompt_entry || !this.$refs.prompt_entry.editor) {
                    return;
                }
                
                // Additional safety check for editor availability
                if (typeof this.$refs.prompt_entry.editor.setValue !== 'function') {
                    return;
                }
                
                const draftKey = `draft_${this.$route.params.slug}_${this.getCurrentProblem().slug}`;
                const draft = localStorage.getItem(draftKey);
                const timestamp = localStorage.getItem(`${draftKey}_timestamp`);
                
                if (draft && timestamp) {
                    const age = Date.now() - parseInt(timestamp);
                    const maxAge = 24 * 60 * 60 * 1000; // 24 hours
                    
                    if (age < maxAge) {
                        this.$refs.prompt_entry.editor.setValue(draft);
                    } else {
                        localStorage.removeItem(draftKey);
                        localStorage.removeItem(`${draftKey}_timestamp`);
                    }
                }
            } catch (error) {
                this.logger.debug('Draft load skipped during navigation', error);
            }
        },
        
        clearDraft() {
            const draftKey = `draft_${this.$route.params.slug}_${this.getCurrentProblem().slug}`;
            localStorage.removeItem(draftKey);
            localStorage.removeItem(`${draftKey}_timestamp`);
        },
        
        startAutoSave() {
            this.autoSaveInterval = setInterval(() => {
                this.saveDraft();
            }, 30000); // 30 seconds
        },
        
        stopAutoSave() {
            if (this.autoSaveInterval) {
                clearInterval(this.autoSaveInterval);
                this.autoSaveInterval = null;
            }
        },
        
        // Hint Management
        getCurrentProblemAttempts() {
            const problemSlug = this.getCurrentProblem().slug;
            const status = this.problemStatuses[problemSlug];
            return status?.attempts || 0;
        },
        
        onHintUsed(hintData) {
            // Log hint usage for research data
            this.logger.info('Hint used', hintData);
            
            // Track hint usage with the composable
            this.trackHintUsage(
                hintData.problemSlug, 
                hintData.hintType,
                {
                    courseId: this.courseId,
                    problemSetSlug: this.$route.params.slug,
                    attemptNumber: this.getCurrentProblemAttempts(),
                    timestamp: hintData.timestamp
                }
            );
            
            // Emit event for analytics if needed
            this.$emit('hint-used', hintData);
        },
        
        async onHintToggled(event) {
            try {
                const { hintType, isActive, hintData } = event;
                
                if (isActive) {
                    // Apply the hint using the composable
                    const success = await this.applyHint(hintType, hintData);
                    if (success) {
                        this.logger.info('Applied hint', { hintType });
                    } else {
                        this.logger.error('Failed to apply hint', { hintType });
                    }
                } else {
                    // Remove the hint using the composable
                    const success = await this.removeHint(hintType);
                    if (success) {
                        this.logger.info('Removed hint', { hintType });
                    } else {
                        this.logger.error('Failed to remove hint', { hintType });
                    }
                }
            } catch (error) {
                this.logger.error('Error toggling hint', error);
            }
        },
        
        async onShowOriginal() {
            try {
                await this.restoreOriginal();
                this.logger.info('Restored original code');
            } catch (error) {
                this.logger.error('Error restoring original code', error);
            }
        },
        
        async onRemoveAllHints() {
            try {
                await this.removeAllHints();
                this.logger.info('Removed all hints');
            } catch (error) {
                this.logger.error('Error removing all hints', error);
            }
        },
        
        async onClearAllHints() {
            // Called when HintButton clears state during navigation
            try {
                await this.removeAllHints();
                // Note: removeAllHints already clears overlays internally
                this.logger.info('Cleared all hints for navigation');
            } catch (error) {
                this.logger.error('Error clearing hints on navigation', error);
            }
        },
        
        // PyTutor Modal Methods
        openPyTutor(url) {
            this.pyTutorUrl = url;
            this.showPyTutorModal = true;
        },
        
        closePyTutor() {
            this.showPyTutorModal = false;
            this.pyTutorUrl = '';
        }
    }
};
</script>

<style scoped>
/* Smooth transitions for content changes */
.editor-section,
.submission-section {
    transition: opacity 0.2s ease;
}

/* Optional: Add a subtle loading indicator on buttons during navigation */
.nav-button:active {
    transform: scale(0.95);
}

.loading-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 400px;
    width: 100%;
}

.loading-message {
    font-size: var(--font-size-md);
    padding: var(--spacing-xl);
    background: var(--color-bg-panel);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    color: var(--color-text-muted);
}

.problem-set-container {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    width: 100%;
    max-width: 100vw;
    box-sizing: border-box;
}

/* Problem Navigation Header */
.problem-navigation {
    background: var(--color-bg-panel);
    padding: var(--spacing-md) var(--spacing-xl);
    border-bottom: 1px solid var(--color-bg-input);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.problem-selector {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-xl);
}

.nav-button {
    background: var(--color-bg-hover);
    border: 1px solid var(--color-bg-border);
    color: var(--color-text-secondary);
    width: 32px;
    height: 32px;
    border-radius: var(--radius-circle);
    cursor: pointer;
    font-size: 18px;
    font-weight: 600;
    transition: var(--transition-base);
    display: flex;
    align-items: center;
    justify-content: center;
}

.nav-button:hover:not(:disabled) {
    background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
    color: var(--color-text-primary);
    border-color: var(--color-primary-gradient-start);
    transform: translateY(-1px);
}

.arrow-left, .arrow-right {
    display: block;
}

.problem-info {
    text-align: center;
    min-width: 300px;
}

.progress-summary {
    display: flex;
    justify-content: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-sm);
}

.progress-stat {
    font-size: var(--font-size-xs);
    font-weight: 600;
    padding: 2px var(--spacing-sm);
    border-radius: var(--radius-xl);
    background: var(--color-bg-hover);
    border: 1px solid var(--color-bg-border);
}

.progress-stat.completed {
    color: var(--color-success);
    background: var(--color-success-bg);
    border-color: var(--color-success);
}

.progress-stat.in_progress {
    color: var(--color-warning);
    background: var(--color-warning-bg);
    border-color: var(--color-warning);
}

.progress-stat.remaining {
    color: var(--color-text-muted);
}

.problem-progress {
    display: flex;
    justify-content: center;
    gap: var(--spacing-sm);
}

.progress-bar {
    width: 40px;
    height: 6px;
    border-radius: 3px;
    background: var(--color-bg-hover);
    cursor: pointer;
    transition: background 0.2s ease, box-shadow 0.2s ease;
    position: relative;
}

/* Status styles */
.progress-bar.not_started {
    background: var(--color-bg-hover);
}

.progress-bar.in_progress {
    background: var(--color-warning);
}

.progress-bar.completed {
    background: var(--color-success);
}

/* Active state */
.progress-bar.active {
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px var(--color-primary-gradient-start);
}

.progress-bar.active.not_started {
    background: linear-gradient(90deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
}

.progress-bar.active.in_progress {
    background: var(--color-warning);
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px var(--color-warning);
}

.progress-bar.active.completed {
    background: var(--color-success);
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px var(--color-success);
}

/* Hover effects */
.progress-bar:hover {
    opacity: 0.8;
    transform: translateY(-1px);
    transition: all 0.2s ease;
}

/* Main Workspace */
.workspace {
    display: flex;
    flex: 1;
    gap: var(--spacing-xl);
    padding: var(--spacing-xl);
    background: var(--color-bg-main);
    min-height: 0;
    box-sizing: border-box;
}

.left-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xl);
    min-height: 0;
    min-width: 0;
    box-sizing: border-box;
}

.right-panel {
    flex: 0 0 520px;
    min-height: 0;
    overflow-y: auto;
    box-sizing: border-box;
}

/* Section Header and Label Styling */
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) var(--spacing-lg);
    background: var(--color-bg-hover);
    border-bottom: 1px solid var(--color-bg-input);
    margin-bottom: var(--spacing-sm);
}

.section-label {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-text-muted);
}

/* Editor Section */
.editor-section {
    background: var(--color-bg-panel);
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: var(--shadow-md);
    border: 2px solid transparent;
    transition: var(--transition-base);
    display: flex;
    flex-direction: column;
    flex: 0 0 auto;
    min-height: 0;
}

.editor-section:hover {
    border-color: var(--color-bg-input);
}

.editor-toolbar {
    background: var(--color-bg-hover);
    border-top: 1px solid var(--color-bg-input);
    padding: var(--spacing-sm) var(--spacing-xl);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
    min-height: 40px;
}

.zoom-controls {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.zoom-btn {
    width: 24px;
    height: 24px;
    padding: 0;
    background: var(--color-bg-panel);
    border: 1px solid var(--color-bg-border);
    color: var(--color-text-secondary);
    font-size: 16px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: var(--transition-fast);
    border-radius: var(--radius-xs);
}

.zoom-btn:hover:not(:disabled) {
    background: var(--color-bg-input);
    color: var(--color-text-primary);
    border-color: var(--color-primary-gradient-start);
}

.zoom-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.zoom-icon {
    line-height: 1;
}

.zoom-level {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    min-width: 45px;
    text-align: center;
    font-weight: 600;
}

.toolbar-btn {
    width: 32px;
    height: 24px;
    padding: 0;
    background: var(--color-bg-panel);
    border: 1px solid var(--color-bg-border);
    color: var(--color-text-secondary);
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: var(--transition-fast);
    border-radius: var(--radius-xs);
}

.toolbar-btn:hover {
    background: var(--color-bg-input);
    color: var(--color-text-primary);
    border-color: var(--color-primary-gradient-start);
}

.toolbar-options {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.theme-selector {
    display: flex;
    align-items: center;
}

.theme-dropdown {
    height: 24px;
    padding: 0 var(--spacing-sm);
    background: var(--color-bg-panel);
    border: 1px solid var(--color-bg-border);
    color: var(--color-text-secondary);
    font-size: var(--font-size-sm);
    border-radius: var(--radius-xs);
    cursor: pointer;
    transition: var(--transition-fast);
    min-width: 120px;
}

.theme-dropdown:hover {
    background: var(--color-bg-input);
    color: var(--color-text-primary);
    border-color: var(--color-primary-gradient-start);
}

.theme-dropdown:focus {
    outline: none;
    border-color: var(--color-primary-gradient-start);
    box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.theme-dropdown option {
    background: var(--color-bg-panel);
    color: var(--color-text-primary);
    padding: var(--spacing-xs);
}

/* Submission Section */
.submission-section {
    background: var(--color-bg-panel);
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: var(--shadow-md);
    border: 2px solid transparent;
    transition: var(--transition-base);
    display: flex;
    flex-direction: column;
    min-height: 250px;
    position: relative;
}

.submission-section:hover {
    border-color: var(--color-bg-input);
}

.draft-indicator {
    position: absolute;
    top: var(--spacing-sm);
    right: var(--spacing-lg);
    color: var(--color-success);
    font-size: var(--font-size-xs);
    font-weight: 600;
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(-5px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.prompt-editor-wrapper {
    padding: 0;
    background: var(--color-bg-input);
    border: 2px solid var(--color-bg-border);
    margin: var(--spacing-md) var(--spacing-xl);
    margin-bottom: 0;
    border-radius: var(--radius-base);
    overflow: hidden;
    transition: var(--transition-base);
}

.prompt-editor-wrapper:hover {
    border-color: var(--color-primary-gradient-start);
}

.submission-section .submit-button {
    margin: var(--spacing-md) var(--spacing-xl) var(--spacing-sm);
    width: calc(100% - calc(var(--spacing-xl) * 2));
    flex-shrink: 0;
}

.submit-button {
    width: 100%;
    padding: var(--spacing-md) var(--spacing-xl);
    background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
    color: var(--color-text-primary);
    border: none;
    border-radius: var(--radius-base);
    font-size: var(--font-size-base);
    font-weight: 600;
    cursor: pointer;
    transition: var(--transition-base);
    box-shadow: var(--shadow-colored);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-sm);
}

.submit-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.submit-button:disabled {
    background: var(--color-bg-disabled);
    cursor: not-allowed;
    opacity: 0.7;
}

/* Loading Animation */
.loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-xs);
}

.bouncing-dots {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: var(--spacing-sm);
}

.status-message {
    font-size: var(--font-size-sm);
    color: var(--color-text-primary);
    opacity: 0.9;
    margin-top: var(--spacing-xs);
    text-align: center;
    animation: fadeIn 0.3s ease-in;
}

.progress-percentage {
    font-weight: 600;
    color: var(--color-text-primary);
    margin-left: var(--spacing-xs);
}

.dot {
    width: 10px;
    height: 10px;
    background: var(--color-text-primary);
    border-radius: var(--radius-circle);
    animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
    animation-delay: -0.32s;
}

.dot:nth-child(2) {
    animation-delay: -0.16s;
}

@keyframes bounce {
    0%, 80%, 100% {
        transform: scale(0);
        opacity: 0.5;
    }
    40% {
        transform: scale(1);
        opacity: 1;
    }
}

/* Responsive Design */
@media (max-width: 1200px) {
    .workspace {
        flex-direction: column;
        padding: var(--spacing-lg);
        gap: var(--spacing-lg);
        overflow-y: auto;
    }
    
    .left-panel {
        flex: none;
        max-width: 100%;
        padding-right: 0;
        gap: var(--spacing-lg);
    }
    
    .right-panel {
        flex: none;
        max-width: 100%;
        flex-basis: auto;
        min-height: 400px;
    }
    
    .editor-section {
        min-height: 500px;
        flex: none;
    }
    
    .submission-section {
        min-height: 250px;
        flex: none;
    }
}

@media (max-width: 768px) {
    .problem-set-container {
        min-height: auto;
    }
    
    .problem-navigation {
        padding: var(--spacing-md) var(--spacing-lg);
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .problem-selector {
        gap: var(--spacing-sm);
        flex-wrap: wrap;
    }
    
    .problem-info {
        min-width: 250px;
        order: -1;
        width: 100%;
        margin-bottom: var(--spacing-sm);
    }
    
    .nav-button {
        width: 36px;
        height: 36px;
        font-size: 18px;
    }
    
    .workspace {
        padding: var(--spacing-md);
        gap: var(--spacing-md);
        flex-direction: column;
        overflow-y: visible;
    }
    
    .left-panel,
    .right-panel {
        flex: none;
        width: 100%;
    }
    
    .editor-section {
        min-height: 400px;
    }
    
    .submission-section {
        min-height: 200px;
    }
    
    .section-header {
        padding: var(--spacing-md) var(--spacing-lg);
    }
    
    .editor-toolbar {
        padding: var(--spacing-sm) var(--spacing-lg);
        flex-wrap: wrap;
        gap: var(--spacing-sm);
        justify-content: center;
    }
    
    .toolbar-options {
        gap: var(--spacing-xs);
        order: 2;
    }
    
    .zoom-controls {
        gap: var(--spacing-sm);
        order: 1;
    }
    
    .theme-dropdown {
        min-width: 90px;
        font-size: var(--font-size-xs);
    }
    
    .zoom-btn {
        width: 24px;
        height: 24px;
        font-size: 14px;
    }
    
    .zoom-level {
        font-size: var(--font-size-xs);
        min-width: 40px;
    }
    
    .submit-button {
        position: sticky;
        bottom: var(--spacing-md);
        margin-bottom: var(--spacing-md);
        z-index: 5;
        box-shadow: var(--shadow-lg);
    }
}
</style>
