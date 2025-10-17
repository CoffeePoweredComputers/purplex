<template>
  <div
    v-if="isLoading"
    class="loading-container"
    role="alert"
    aria-live="polite"
    aria-busy="true"
  >
    <div class="loading-message">
      Loading problem set...
    </div>
  </div>
  <div
    v-else-if="!problems || problems.length === 0"
    class="loading-container"
    role="status"
  >
    <div class="loading-message">
      No problems found in this set.
    </div>
  </div>
  <div
    v-else
    class="problem-set-container"
  >
    <!-- Skip Link for Accessibility -->
    <a href="#code-editor" class="skip-link">Skip to code editor</a>

    <!-- Navigation Progress Bar - Thin top indicator -->
    <div
      v-if="isNavigating"
      class="navigation-progress-bar"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div class="progress-bar-fill" />
    </div>

    <div class="problem-navigation">
      <div class="problem-selector">
        <button
          class="nav-button"
          :disabled="isNavigating"
          :class="{ 'is-loading': isNavigating }"
          aria-label="Previous problem"
          @click="prevProblem"
        >
          <span class="arrow-left" aria-hidden="true">‹</span>
        </button>
        <div class="problem-info">
          <div class="progress-summary">
            <span class="progress-stat completed">{{ completedCount }} completed</span>
            <span class="progress-stat in_progress">{{ inProgressCount }} in progress</span>
            <span class="progress-stat remaining">{{ remainingCount }} remaining</span>
          </div>
          <nav class="problem-progress" aria-label="Problem navigation">
            <button
              v-for="(problem, index) in problems"
              :key="`${problem.slug}-${getProblemStatus(problem.slug)}-${index}`"
              :class="['progress-bar',
                       { 'active': index === currentProblem },
                       { 'submitting': isCurrentProblemSubmitting(problem.slug) },
                       { 'completed': !isCurrentProblemSubmitting(problem.slug) && getProblemStatus(problem.slug) === 'completed' },
                       { 'in_progress': !isCurrentProblemSubmitting(problem.slug) && getProblemStatus(problem.slug) === 'in_progress' },
                       { 'not_started': !isCurrentProblemSubmitting(problem.slug) && getProblemStatus(problem.slug) === 'not_started' }
              ]"
              :aria-current="index === currentProblem ? 'true' : 'false'"
              :aria-label="getProblemTooltip(problem, index)"
              @click="setProblem(index)"
            />
          </nav>
        </div>
        <button
          class="nav-button"
          :disabled="isNavigating"
          :class="{ 'is-loading': isNavigating }"
          aria-label="Next problem"
          @click="nextProblem"
        >
          <span class="arrow-right" aria-hidden="true">›</span>
        </button>
      </div>
    </div>

    <!-- Main workspace -->
    <div id="main-workspace" class="workspace" :class="{ 'is-navigating': isNavigating }">
      <!-- Left panel: Code editor and submission -->
      <div class="left-panel" :class="{ 'is-navigating': isNavigating }">
        <!-- Code editor section -->
        <div id="code-editor" class="editor-section">
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
            :key="editorRenderKey"
            lang="python" 
            mode="python" 
            height="450px" 
            width="100%" 
            :value="displayedCode"
            :read-only="true"
            :show-gutter="showLineNumbers"
            :theme="currentTheme"
            @update:value="updateSolutionCode"
          />
          <div class="editor-toolbar">
            <div class="toolbar-options">
              <button
                class="toolbar-btn"
                :aria-label="codeCopied ? 'Code copied to clipboard' : 'Copy code to clipboard'"
                @click="copyCode"
              >
                <span aria-hidden="true">{{ codeCopied ? '✓' : '📋' }}</span>
                <span class="btn-text">{{ codeCopied ? 'Copied' : 'Copy' }}</span>
              </button>
              <button
                class="toolbar-btn"
                :aria-label="showLineNumbers ? 'Hide line numbers' : 'Show line numbers'"
                @click="toggleLineNumbers"
              >
                <span aria-hidden="true">{{ showLineNumbers ? '🔢' : '➖' }}</span>
                <span class="btn-text">{{ showLineNumbers ? 'Lines' : 'No Lines' }}</span>
              </button>
              <div class="theme-selector">
                <label for="editor-theme" class="visually-hidden">Editor theme</label>
                <select
                  id="editor-theme"
                  v-model="editorTheme"
                  class="theme-dropdown"
                  aria-label="Select editor theme"
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
                aria-label="Decrease font size"
                @click="decreaseFontSize"
              >
                <span class="zoom-icon" aria-hidden="true">−</span>
              </button>
              <span class="zoom-level" aria-live="polite">{{ Math.round((editorFontSize / 14) * 100) }}%</span>
              <button
                class="zoom-btn"
                :disabled="editorFontSize >= 35"
                aria-label="Increase font size"
                @click="increaseFontSize"
              >
                <span class="zoom-icon" aria-hidden="true">+</span>
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
            role="status"
            aria-live="polite"
          >✓ Draft saved</span>
          <div id="promptEditor" class="prompt-editor-wrapper" tabindex="-1">
            <Editor
              ref="prompt_entry"
              v-model:value="promptEditorValue"
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
            :disabled="isCurrentProblemSubmitting(getCurrentProblem().slug)"
            :aria-busy="isCurrentProblemSubmitting(getCurrentProblem().slug)"
            :aria-label="isCurrentProblemSubmitting(getCurrentProblem().slug) ? 'Submitting solution, please wait' : 'Submit Solution'"
            @click="submit"
          >
            <span
              v-if="!isCurrentProblemSubmitting(getCurrentProblem().slug)"
              class="button-text"
            >Submit Solution</span>
            <div
              v-if="isCurrentProblemSubmitting(getCurrentProblem().slug)"
              class="loading-content"
              role="status"
              aria-live="polite"
            >
              <div class="bouncing-dots" aria-hidden="true">
                <span class="dot" />
                <span class="dot" />
                <span class="dot" />
              </div>
              <span class="visually-hidden">Submitting solution, please wait</span>
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
          :segmentation-enabled="getCurrentProblem()?.segmentation_enabled === true"
          :is-loading="loading"
          :is-navigating="isNavigating"
          :submission-history="submissionHistory"
          title="Submission & Results"
          @load-attempt="loadSpecificAttempt"
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
import { submissionService } from '@/services/submissionService'
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
        // Note: We'll create individual SSE connections per submission instead of sharing one

        // Hint system setup
        const entry = ref(null);
        const originalSolutionCode = ref('');

        // Initialize hint system
        const {
            modifiedCode,
            hasActiveHints,
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
            // Hint system
            entry,
            originalSolutionCode,
            modifiedCode,
            hasActiveHints,
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
            isNavigating: false,  // Track navigation transitions
            navigationDebounceTimer: null,  // Debounce rapid navigation clicks

            /* Editor State */
            editorRenderKey: 0,
            promptEditorValue: '',  // Controlled value for prompt editor

            /* Submission State */
            loading: false,
            submittingProblems: new Set(), // Tracks all problem slugs currently being submitted
            submissionConnections: new Map(), // Tracks individual SSE connections per problem
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
            problemHintStates: {},

            /* Submission History */
            submissionHistory: []
        };
    },
    
    computed: {
        solutionCode() {
            return this.getCurrentProblem().reference_solution || '';
        },
        
        displayedCode() {
            const code = this.hasActiveHints ? this.modifiedCode : this.solutionCode;
            this.logger.debug('displayedCode computed:', {
                hasActiveHints: this.hasActiveHints,
                codeLength: code.length,
                lineCount: code.split('\n').length,
                firstFewChars: code.substring(0, 100),
                hasNewlines: code.includes('\n')
            });
            return code;
        },
        
        suggestedTraceOverlays() {
            return (this.activeOverlays || []).filter(
                overlay => overlay && overlay.component === 'SuggestedTraceOverlay'
            );
        },
        
        completedCount() {
            const count = Object.values(this.problemStatuses).filter(s => s && s.status === 'completed').length;
            return count;
        },

        inProgressCount() {
            const count = Object.values(this.problemStatuses).filter(s => s && s.status === 'in_progress').length;
            return count;
        },

        remainingCount() {
            const totalProblems = this.problems.length;
            const completed = this.completedCount;
            const inProgress = this.inProgressCount;
            const remaining = totalProblems - completed - inProgress;
            return remaining;
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

        // Clean up all active SSE connections
        for (const [problemSlug, connection] of this.submissionConnections) {
            this.logger.debug('Cleaning up SSE connection for problem', { problemSlug });
            connection.disconnect();
        }
        this.submissionConnections.clear();
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

            // Debounce rapid navigation clicks (200ms)
            if (this.navigationDebounceTimer) {
                clearTimeout(this.navigationDebounceTimer);
            }

            // Wait briefly to see if user is still clicking
            await new Promise(resolve => {
                this.navigationDebounceTimer = setTimeout(resolve, 50);
            });

            try {
                // Set navigating state to show loading indicator
                this.isNavigating = true;

                // Batch synchronous operations - no await needed
                const currentProblemSlug = this.getCurrentProblem().slug;

                // Save draft and hint state synchronously (local operations)
                this.saveDraft();
                if (currentProblemSlug) {
                    this.problemHintStates[currentProblemSlug] = this.saveHintState();
                }

                // Clear hints synchronously
                this.removeAllHints();

                // Get the problem we're navigating to
                const problem = this.problems[newIndex];

                // Check if this problem is currently submitting
                const isSubmitting = this.submittingProblems.has(problem.slug);

                let batchData = null;
                if (!isSubmitting) {
                    // Load ALL data in parallel for atomic update
                    batchData = await this.loadProblemDataBatch(problem.slug);
                }

                // ATOMIC STATE UPDATE - Everything changes at once
                // This prevents multiple re-renders with partial data
                this.currentProblem = newIndex;
                this.loading = isSubmitting;

                if (isSubmitting) {
                    // Clear feedback to show loading state
                    this.clearFeedbackData();
                    this.logger.info('Navigation: Problem is submitting, showing loading state', {
                        problemSlug: problem.slug
                    });
                } else if (batchData) {
                    // Apply all loaded data atomically
                    const { submissionHistory, submissionData, draftText } = batchData;

                    this.submissionHistory = submissionHistory;
                    this.codeResults = submissionData.variations || [];
                    this.testResults = submissionData.results || [];
                    this.promptCorrectness = submissionData.passing_variations || 0;
                    this.comprehensionResults = submissionData.feedback || '';
                    this.userPrompt = submissionData.user_prompt || '';

                    // Only set segmentation data if the problem has segmentation enabled
                    const currentProblem = this.getCurrentProblem();
                    if (currentProblem?.segmentation_enabled && submissionData.segmentation) {
                        this.segmentationData = submissionData.segmentation;
                    } else {
                        this.segmentationData = null;
                    }

                    // Update problem status with segmentation_passed if available
                    if (submissionData.has_submission && this.problemStatuses[problem.slug]) {
                        this.problemStatuses = {
                            ...this.problemStatuses,
                            [problem.slug]: {
                                ...this.problemStatuses[problem.slug],
                                segmentationPassed: submissionData.segmentation_passed
                            }
                        };
                    }

                    // Set prompt editor value (prioritize last submission over draft)
                    if (this.userPrompt) {
                        this.promptEditorValue = this.userPrompt;
                    } else if (draftText) {
                        this.promptEditorValue = draftText;
                    } else {
                        this.promptEditorValue = '';
                    }

                    this.logger.info('Navigation: Applied batched data atomically', {
                        problemSlug: problem.slug,
                        hasSubmission: submissionData.has_submission,
                        codeResults: this.codeResults.length,
                        testResults: this.testResults.length,
                        hasHistory: submissionHistory.length > 0
                    });
                }

                // Restore hints in next tick (batched with DOM updates)
                this.$nextTick(() => {
                    const newProblemSlug = this.getCurrentProblem().slug;
                    const savedState = newProblemSlug ? this.problemHintStates[newProblemSlug] : null;
                    this.restoreHintState(savedState);

                    // Clear navigating state after hints restored
                    this.isNavigating = false;
                });

            } catch (error) {
                this.logger.error('Navigation failed', error);
                this.notify.error('Navigation Error', 'Failed to load problem data');
                this.isNavigating = false; // Always clear loading state on error
            }
        },
        
        async loadProblemDataBatch(problemSlug) {
            /**
             * Batch load all problem data in parallel for atomic updates.
             * Optimized with early draft loading and true parallelism.
             */
            this.logger.debug('Batch loading problem data', { problemSlug });

            try {
                // Load draft immediately (synchronous - no await)
                const draftKey = `draft_${this.$route.params.slug}_${problemSlug}`;
                const draft = localStorage.getItem(draftKey);
                const timestamp = localStorage.getItem(`${draftKey}_timestamp`);

                let draftText = '';
                if (draft && timestamp) {
                    const age = Date.now() - parseInt(timestamp);
                    const maxAge = 24 * 60 * 60 * 1000; // 24 hours
                    if (age < maxAge) {
                        draftText = draft;
                    }
                }

                // Load network data in parallel (only async operations)
                const [historyResponse, submissionData] = await Promise.all([
                    // Load submission history
                    submissionService.getSubmissionHistory(
                        problemSlug,
                        this.$route.params.slug,
                        this.courseId,
                        50
                    ).catch(error => {
                        this.logger.error('Failed to load history in batch', error);
                        return { submissions: [], total_attempts: 0, best_score: 0 };
                    }),

                    // Load last submission data
                    this.loadSubmissionData(problemSlug).catch(error => {
                        this.logger.error('Failed to load submission in batch', error);
                        return {
                            has_submission: false,
                            variations: [],
                            results: [],
                            passing_variations: 0,
                            feedback: '',
                            user_prompt: '',
                            segmentation: null
                        };
                    })
                ]);

                this.logger.debug('Batch load complete', {
                    problemSlug,
                    hasHistory: historyResponse.submissions.length > 0,
                    hasSubmission: submissionData.has_submission,
                    hasDraft: !!draftText
                });

                return {
                    submissionHistory: historyResponse.submissions || [],
                    submissionData,
                    draftText
                };
            } catch (error) {
                this.logger.error('Batch load failed', error);
                throw error;
            }
        },

        async loadProblemData() {
            const problem = this.getCurrentProblem();
            if (!problem.slug) {return;}

            // Check if this problem is currently submitting
            if (this.submittingProblems.has(problem.slug)) {
                // Clear the feedback data to show loading state
                this.clearFeedbackData();
                this.logger.info('loadProblemData: Problem is submitting, showing loading state', {
                    problemSlug: problem.slug
                });
                return; // Don't load old submission
            }

            try {
                // Use batch loading for better performance
                const { submissionHistory, submissionData, draftText } =
                    await this.loadProblemDataBatch(problem.slug);

                // Apply all data atomically
                this.submissionHistory = submissionHistory;
                this.codeResults = submissionData.variations || [];
                this.testResults = submissionData.results || [];
                this.promptCorrectness = submissionData.passing_variations || 0;
                this.comprehensionResults = submissionData.feedback || '';
                this.userPrompt = submissionData.user_prompt || '';
                this.segmentationData = submissionData.segmentation || null;

                // Update problem status with segmentation_passed if available
                if (submissionData.has_submission && this.problemStatuses[problem.slug]) {
                    this.problemStatuses = {
                        ...this.problemStatuses,
                        [problem.slug]: {
                            ...this.problemStatuses[problem.slug],
                            segmentationPassed: submissionData.segmentation_passed
                        }
                    };
                }

                // Set draft text (prioritize last submission over draft)
                await this.$nextTick();
                if (this.userPrompt) {
                    this.promptEditorValue = this.userPrompt;
                } else if (draftText) {
                    this.promptEditorValue = draftText;
                } else {
                    this.promptEditorValue = '';
                }

                this.logger.info('Applied batched data to component', {
                    codeResults: this.codeResults.length,
                    testResults: this.testResults.length,
                    promptCorrectness: this.promptCorrectness,
                    hasSegmentation: !!this.segmentationData
                });

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
                // Include problem_set_slug and course_id in query params for proper context
                const params = {
                    problem_set_slug: this.$route.params.slug
                };
                if (this.courseId) {
                    params.course_id = this.courseId;
                }
                const response = await axios.get(`/api/last-submission/${problemSlug}/`, { params });
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
            // Note: We don't clear promptEditorValue here as it may contain draft text
        },

        async loadSubmissionHistory(problemSlug) {
            try {
                const historyResponse = await submissionService.getSubmissionHistory(
                    problemSlug,
                    this.$route.params.slug, // problem_set_slug
                    this.courseId,
                    50 // limit to last 50 attempts
                );

                this.submissionHistory = historyResponse.submissions || [];
                this.logger.info('Loaded submission history', {
                    problemSlug,
                    problemSetSlug: this.$route.params.slug,
                    totalAttempts: historyResponse.total_attempts,
                    bestScore: historyResponse.best_score,
                    submissions: this.submissionHistory
                });
            } catch (error) {
                this.logger.error('Error loading submission history', error);
                this.submissionHistory = [];
            }
        },

        async loadSpecificAttempt(attempt) {
            // Load data from specific attempt
            this.logger.info('Loading specific attempt', {
                attemptId: attempt.id,
                attemptNumber: attempt.attempt_number,
                score: attempt.score
            });

            // Apply the attempt data
            if (attempt.data) {
                const data = attempt.data;

                // Transform variations into code results
                if (data.variations && data.variations.length > 0) {
                    this.codeResults = data.variations.map(v => v.code);
                } else {
                    // For non-variation submissions, use processed_code
                    this.codeResults = [data.processed_code || data.raw_input];
                }

                // Transform test results into the format expected by Feedback
                const testResultsPerVariation = [];
                if (data.variations && data.variations.length > 0) {
                    // Create test results for each variation
                    data.variations.forEach(variation => {
                        // Use test_results from the variation itself
                        const testResultsArray = variation.test_results || [];
                        const varTestResults = {
                            success: variation.passed_all_tests,
                            testsPassed: variation.tests_passed,
                            totalTests: variation.total_tests,
                            results: testResultsArray.map(tr => ({
                                pass: tr.passed,
                                isSuccessful: tr.passed,
                                expected_output: tr.expected,
                                actual_output: tr.actual !== undefined && tr.actual !== null ? tr.actual : tr.error_message,
                                error: tr.error_message,
                                function_call: this.reconstructFunctionCall(tr),
                                inputs: tr.inputs
                            }))
                        };
                        testResultsPerVariation.push(varTestResults);
                    });
                } else if (data.test_results && data.test_results.length > 0) {
                    // For non-variation submissions, use top-level test_results
                    const varTestResults = {
                        success: attempt.passed_all_tests,
                        testsPassed: attempt.tests_passed,
                        totalTests: attempt.total_tests,
                        results: data.test_results.map(tr => ({
                            pass: tr.passed,
                            isSuccessful: tr.passed,
                            expected_output: tr.expected,
                            actual_output: tr.actual !== undefined && tr.actual !== null ? tr.actual : tr.error_message,
                            error: tr.error_message,
                            function_call: this.reconstructFunctionCall(tr),
                            inputs: tr.inputs
                        }))
                    };
                    testResultsPerVariation.push(varTestResults);
                }

                this.testResults = testResultsPerVariation;
                this.promptCorrectness = attempt.score;
                this.userPrompt = data.raw_input;
                this.comprehensionResults = '';
                // Apply segmentation data only if the problem has segmentation enabled
                const currentProblem = this.getCurrentProblem();
                if (currentProblem?.segmentation_enabled && attempt.segmentation) {
                    this.segmentationData = attempt.segmentation;
                } else {
                    this.segmentationData = null;
                }

                // Update UI to reflect loaded attempt
                this.logger.info('Applied attempt data to feedback', {
                    codeResults: this.codeResults.length,
                    testResults: this.testResults.length,
                    score: attempt.score
                });
            }
        },

        reconstructFunctionCall(testResult) {
            // Try to reconstruct function call from test data
            const problemSlug = this.currentProblemSlug;
            const problem = this.problems?.find(p => p.slug === problemSlug);
            const functionName = problem?.function_name || 'foo';

            // Format inputs for display
            if (testResult.inputs !== undefined && testResult.inputs !== null) {
                // If inputs is already a string representation, use it
                if (typeof testResult.inputs === 'string') {
                    return `${functionName}(${testResult.inputs})`;
                }
                // Otherwise format the value
                const formattedInput = this.formatTestValue(testResult.inputs);
                return `${functionName}(${formattedInput})`;
            }

            // Fallback to a generic representation
            return `${functionName}(...)`;
        },

        formatTestValue(value) {
            // Handle different types of values
            if (value === null) return 'None';
            if (value === undefined) return 'undefined';
            if (typeof value === 'string') return `"${value}"`;
            if (typeof value === 'boolean') return value ? 'True' : 'False';
            if (typeof value === 'number') return value.toString();
            if (Array.isArray(value)) {
                return '[' + value.map(v => this.formatTestValue(v)).join(', ') + ']';
            }
            if (typeof value === 'object') {
                return JSON.stringify(value);
            }
            return String(value);
        },

        getCurrentProblem() {
            if (!this.problems || this.problems.length === 0) {
                return { solution: '', slug: '', name: 'Loading...' };
            }
            const problem = this.problems[this.currentProblem] || this.problems[0];
            return problem;
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
            const currentProblemSlug = this.getCurrentProblem().slug;
            if (this.submittingProblems.has(currentProblemSlug)) {return;}

            // Constants matching backend validation
            const MIN_PROMPT_LENGTH = 10;
            const MAX_PROMPT_LENGTH = 1000;

            // Validate prompt before making any state changes
            const promptText = this.promptEditorValue;

            if (!promptText || promptText.trim() === '') {
                this.notify.warning('Missing Description', 'Please enter a description of what the function does.');
                return;
            }

            const trimmedPrompt = promptText.trim();

            // Check minimum length
            if (trimmedPrompt.length < MIN_PROMPT_LENGTH) {
                this.notify.warning(
                    'Description Too Short',
                    `Please enter at least ${MIN_PROMPT_LENGTH} characters. You have ${trimmedPrompt.length} character${trimmedPrompt.length === 1 ? '' : 's'}.`
                );
                return;
            }

            // Check maximum length
            if (trimmedPrompt.length > MAX_PROMPT_LENGTH) {
                this.notify.warning(
                    'Description Too Long',
                    `Please keep your description under ${MAX_PROMPT_LENGTH} characters. You have ${trimmedPrompt.length} characters.`
                );
                return;
            }

            // Validation passed - now we can proceed with submission
            this.addToSubmitting(currentProblemSlug);
            this.loading = true; // Track current problem's loading state for Feedback component

            // Declare rollback outside try block so it's accessible in catch block
            let rollback = null;

            try {
                // Clear cache for this problem to ensure fresh data on next load
                const cacheKey = `${this.$route.params.slug}_${currentProblemSlug}_${this.courseId || 'standalone'}`;
                this.submissionCache.delete(cacheKey);

                // Clear previous feedback only after validation passes
                this.clearFeedbackData();

                // Optimistic update
                rollback = this.updateProgress(currentProblemSlug, {
                    status: 'in_progress',
                    score: null,
                    attempts: (this.problemStatuses[currentProblemSlug]?.attempts || 0) + 1
                });

                // Get hints that were used for this problem
                const hintsUsed = this.getHintsUsed(
                    currentProblemSlug,
                    this.courseId,
                    this.$route.params.slug
                );

                // Transform hint tracking data to match backend expectations
                // Backend will look up hints by type, not ID
                const activatedHints = hintsUsed.map((hintType, index) => ({
                    hint_type: hintType,
                    trigger_type: 'manual'  // We can enhance this later to track actual trigger
                    // Note: Do not send hint_id - backend will look up by hint_type
                }));

                const submissionData = {
                    problem_slug: currentProblemSlug,
                    problem_set_slug: this.$route.params.slug,
                    user_prompt: trimmedPrompt,
                    activated_hints: activatedHints
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

                // Create a new SSE connection specifically for this submission
                const { connectToEiPLSubmission, disconnect } = useSSE();

                // Store the connection so we can clean it up later
                this.submissionConnections.set(currentProblemSlug, { disconnect });

                // Connect to SSE stream for real-time updates
                await connectToEiPLSubmission(
                    submissionResponse.request_id,
                    (variations, testResults, segmentation) => {
                        // Success callback - results are ready
                        this.logger.info('EiPL results received', { 
                            variations: variations.length,
                            testResults: testResults.length 
                        });

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

                        // Only update displayed feedback if this submission is for the currently viewed problem
                        if (currentProblemSlug === this.getCurrentProblem().slug) {
                            // Update feedback data for display
                            this.codeResults = variations;
                            this.testResults = testResults;
                            this.promptCorrectness = perfectVariations;
                            this.userPrompt = trimmedPrompt;
                            // Keep promptEditorValue in sync with successful submission
                            this.promptEditorValue = trimmedPrompt;

                            // Handle segmentation data from SSE response
                            // Only set segmentation data if the problem has segmentation enabled
                            const currentProblem = this.getCurrentProblem();

                            if (currentProblem?.segmentation_enabled && segmentation) {
                                this.segmentationData = segmentation;
                            } else {
                                this.segmentationData = null;
                            }
                        } else {
                            this.logger.info('SSE results received for different problem, not updating display', {
                                submittedProblem: currentProblemSlug,
                                currentProblem: this.getCurrentProblem().slug
                            });
                        }

                        // Calculate score based on total tests passed across all variations
                        const score = totalTestsRun > 0
                            ? Math.round((totalTestsPassed / totalTestsRun) * 100)
                            : 0;

                        // Update progress tracking with final status
                        // Determine if segmentation passed
                        const segmentationPassed = segmentation?.passed ?? null;

                        // Get the actual problem that was submitted (not the currently selected one)
                        const submittedProblem = this.problems.find(p => p.slug === currentProblemSlug);

                        // For EiPL problems with segmentation, check both conditions
                        let finalStatus = 'in_progress';
                        if (submittedProblem?.problem_type === 'eipl' && submittedProblem?.segmentation_enabled) {
                            // Requires both 100% score AND segmentation passed
                            finalStatus = (score >= 100 && segmentationPassed === true) ? 'completed' : 'in_progress';
                        } else {
                            // Non-EiPL or EiPL without segmentation: just check score
                            finalStatus = score >= 100 ? 'completed' : 'in_progress';
                        }

                        // Use Vue 3 reactive update by replacing entire object
                        this.problemStatuses = {
                            ...this.problemStatuses,
                            [currentProblemSlug]: {
                                status: finalStatus,
                                score: score,
                                attempts: (this.problemStatuses[currentProblemSlug]?.attempts || 0) + 1,
                                segmentationPassed: segmentationPassed
                            }
                        };

                        this.clearOptimistic(currentProblemSlug);

                        // Always update cache with new submission data for ALL problems
                        const cacheKey = `${this.$route.params.slug}_${currentProblemSlug}_${this.courseId || 'standalone'}`;
                        this.submissionCache.set(cacheKey, {
                            data: {
                                has_submission: true,
                                variations: variations,  // Use the actual data, not display variables
                                results: testResults,     // Use the actual data, not display variables
                                passing_variations: perfectVariations,  // Use calculated value
                                user_prompt: promptText,  // Use original prompt text
                                segmentation: segmentation  // Use actual segmentation data
                            },
                            timestamp: Date.now()
                        });

                        // Store successful submission
                        if (this.userSubmissions) {
                            this.userSubmissions[currentProblemSlug] = promptText;
                        }

                        // Get the problem index for clearer messaging (don't use title as it gives away the answer!)
                        const problemIndex = this.problems.findIndex(p => p.slug === currentProblemSlug);
                        const problemIdentifier = problemIndex >= 0 ? `Problem ${problemIndex + 1}` : 'Submission';

                        // Create detailed message with problem identifier
                        let message = `${problemIdentifier}: `;
                        let notificationType = 'info';

                        // Add high-level/low-level status if segmentation is enabled for this problem
                        if (submittedProblem?.problem_type === 'eipl' && submittedProblem?.segmentation_enabled && segmentation) {
                            // Report both variations (low-level) and segmentation (high-level)
                            const segmentCount = segmentation.segment_count || 0;
                            const threshold = submittedProblem.segmentation_config?.threshold || 2;
                            const highLevelText = segmentationPassed ? `✓ High-level (${segmentCount} segments)` : `✗ High-level (${segmentCount} segments, need ≤${threshold})`;
                            message += `Variations: ${perfectVariations}/${variations.length} passing, ${highLevelText}`;

                            // Determine notification type based on results
                            if (perfectVariations === variations.length && segmentationPassed) {
                                notificationType = 'success';  // Green - complete
                            } else {
                                notificationType = 'warning';  // Yellow - incomplete/partial
                            }
                        } else {
                            // Just report variations if segmentation is not enabled
                            message += `Variations: ${perfectVariations}/${variations.length} passing`;

                            // Determine notification type
                            if (perfectVariations === variations.length) {
                                notificationType = 'success';  // Green - all tests pass
                            } else {
                                notificationType = 'warning';  // Yellow - some tests fail
                            }
                        }

                        // Show notification with appropriate type
                        if (notificationType === 'success') {
                            this.notify.success(message);
                        } else {
                            this.notify.warning(message);
                        }
                        this.removeFromSubmitting(currentProblemSlug);
                        this.loading = this.submittingProblems.has(this.getCurrentProblem().slug);

                        // Clean up the SSE connection for this submission
                        const connection = this.submissionConnections.get(currentProblemSlug);
                        if (connection) {
                            connection.disconnect();
                            this.submissionConnections.delete(currentProblemSlug);
                        }

                        // Refresh submission history to include the new submission
                        this.loadSubmissionHistory(currentProblemSlug).then(() => {
                            // If this submission was for the currently viewed problem, also update the displayed history
                            if (currentProblemSlug === this.getCurrentProblem().slug) {
                                this.logger.info('Submission history refreshed for current problem');
                            }
                        }).catch(error => {
                            this.logger.error('Failed to refresh submission history', error);
                        });
                    },
                    {
                        // SSE options
                        onError: (error) => {
                            this.logger.error('SSE connection error', error);
                            this.notify.error(error.error || 'Failed to get results');
                            this.removeFromSubmitting(currentProblemSlug);
                            this.loading = this.submittingProblems.has(this.getCurrentProblem().slug);
                            if (rollback) {rollback();} // Rollback optimistic update on error

                            // Clean up the SSE connection for this submission
                            const connection = this.submissionConnections.get(currentProblemSlug);
                            if (connection) {
                                connection.disconnect();
                                this.submissionConnections.delete(currentProblemSlug);
                            }
                        },
                        onTimeout: () => {
                            this.logger.warn('SSE connection timeout');
                            this.notify.warning('Connection timeout. Please try again.');
                            this.removeFromSubmitting(currentProblemSlug);
                            this.loading = this.submittingProblems.has(this.getCurrentProblem().slug);
                            if (rollback) {rollback();}

                            // Clean up the SSE connection for this submission
                            const connection = this.submissionConnections.get(currentProblemSlug);
                            if (connection) {
                                connection.disconnect();
                                this.submissionConnections.delete(currentProblemSlug);
                            }
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
                this.removeFromSubmitting(currentProblemSlug);
                this.loading = this.submittingProblems.has(this.getCurrentProblem().slug);
                // Rollback optimistic update on error
                if (rollback) {rollback();}

                // Clean up any SSE connection if error occurred during submission
                const connection = this.submissionConnections.get(currentProblemSlug);
                if (connection) {
                    connection.disconnect();
                    this.submissionConnections.delete(currentProblemSlug);
                }
            } finally {
                // Loading state is managed in SSE callbacks
                // Don't reset it here as SSE is still processing
            }
        },
        
        async loadProblemSet() {
            const problemSetSlug = this.$route.params.slug;
            this.isLoading = true;

            // Clear submission cache for fresh data
            this.submissionCache.clear();

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

                // FIRST: Initialize ALL problems with default 'not_started' status
                this.problems.forEach(problem => {
                    newStatuses[problem.slug] = {
                        status: 'not_started',
                        score: 0,
                        attempts: 0,
                        segmentationPassed: null
                    };
                });

                // THEN: Overlay actual progress data from API
                progressData.forEach(progress => {
                    const mappedStatus = this.mapStatusFromAPI(progress.status, progress.best_score);

                    newStatuses[progress.problem_slug] = {
                        status: mappedStatus,
                        score: progress.best_score,
                        attempts: progress.attempts,
                        segmentationPassed: progress.segmentation_passed !== undefined ? progress.segmentation_passed : null
                    };
                });

                // Store problem set progress first
                if (response.data.problem_set) {
                    this.problemSetProgress = response.data.problem_set;
                }

                // Force Vue 3 reactivity by creating a completely new object
                this.problemStatuses = {};
                this.$nextTick(() => {
                    this.problemStatuses = { ...newStatuses };
                    // Another tick to ensure computed properties update
                    this.$nextTick(() => {
                        this.logger.debug('Counts recomputed after nextTick', {
                            completedCount: this.completedCount,
                            inProgressCount: this.inProgressCount,
                            remainingCount: this.remainingCount,
                            statuses: this.problemStatuses
                        });
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
            // For debugging, bypass optimistic updates temporarily
            const useOptimistic = false; // Toggle this to test
            const optimisticStatus = useOptimistic ? this.getProgress(problemSlug, actualStatus) : actualStatus;
            const finalStatus = optimisticStatus?.status || 'not_started';
            return finalStatus;
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

        isCurrentProblemSubmitting(problemSlug) {
            // Check if this specific problem is currently being submitted
            return this.submittingProblems.has(problemSlug);
        },

        // Helper methods for reactive Set updates
        addToSubmitting(problemSlug) {
            // Replace the entire Set to trigger Vue reactivity
            const newSet = new Set(this.submittingProblems);
            newSet.add(problemSlug);
            this.submittingProblems = newSet;
        },

        removeFromSubmitting(problemSlug) {
            // Replace the entire Set to trigger Vue reactivity
            const newSet = new Set(this.submittingProblems);
            newSet.delete(problemSlug);
            this.submittingProblems = newSet;
        },

        // Draft Management - Simplified
        saveDraft() {
            const promptText = this.promptEditorValue;
            if (promptText && promptText.trim()) {
                const draftKey = `draft_${this.$route.params.slug}_${this.getCurrentProblem().slug}`;
                localStorage.setItem(draftKey, promptText);
                localStorage.setItem(`${draftKey}_timestamp`, Date.now().toString());

                this.draftSaved = true;
                setTimeout(() => {
                    this.draftSaved = false;
                }, 2000);
            }
        },
        
        loadDraft() {
            // First priority: Load the last submission (userPrompt)
            if (this.userPrompt) {
                this.promptEditorValue = this.userPrompt;
                this.logger.debug('Loaded previous submission into prompt editor', {
                    promptLength: this.userPrompt.length
                });
                return;
            }

            // Second priority: Load draft from localStorage
            const draftKey = `draft_${this.$route.params.slug}_${this.getCurrentProblem().slug}`;
            const draft = localStorage.getItem(draftKey);
            const timestamp = localStorage.getItem(`${draftKey}_timestamp`);

            if (draft && timestamp) {
                const age = Date.now() - parseInt(timestamp);
                const maxAge = 24 * 60 * 60 * 1000; // 24 hours

                if (age < maxAge) {
                    this.promptEditorValue = draft;
                    this.logger.debug('Loaded draft into prompt editor', {
                        draftLength: draft.length,
                        ageMinutes: Math.round(age / 60000)
                    });
                } else {
                    localStorage.removeItem(draftKey);
                    localStorage.removeItem(`${draftKey}_timestamp`);
                    this.promptEditorValue = '';
                }
            } else {
                // Clear the editor if no submission and no draft
                this.promptEditorValue = '';
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

                        // Track hint usage for backend submission
                        this.onHintUsed({
                            problemSlug: this.getCurrentProblem().slug,
                            hintType: hintType,
                            timestamp: new Date().toISOString()
                        });

                        // Force complete re-render for subgoal hints to fix overlapping text
                        if (hintType === 'subgoal_highlight') {
                            this.editorRenderKey++;
                        }
                    } else {
                        this.logger.error('Failed to apply hint', { hintType });
                    }
                } else {
                    // Remove the hint using the composable
                    const success = await this.removeHint(hintType);
                    if (success) {
                        this.logger.info('Removed hint', { hintType });
                        // Force complete re-render when removing subgoal hints
                        if (hintType === 'subgoal_highlight') {
                            this.editorRenderKey++;
                        }
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
/* Navigation Progress Bar - Thin top indicator */
.navigation-progress-bar {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: rgba(255, 255, 255, 0.1);
    z-index: 1000;
    overflow: hidden;
}

.progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg,
        var(--color-primary-gradient-start) 0%,
        var(--color-primary-gradient-end) 100%);
    animation: progressSlide 1.5s ease-in-out infinite;
    transform-origin: left;
    box-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
}

@keyframes progressSlide {
    0% {
        transform: translateX(-100%) scaleX(0.3);
    }
    50% {
        transform: translateX(0%) scaleX(1);
    }
    100% {
        transform: translateX(100%) scaleX(0.3);
    }
}

/* No transitions - keep content completely static during navigation */
.editor-section,
.submission-section,
.right-panel,
.left-panel {
    /* All transitions removed for instant, stable navigation */
}

/* Workspace navigation transitions - removed all animations for static, stable UX */

/* Navigation button loading state */
.nav-button:active {
    transform: scale(0.95);
}

.nav-button.is-loading {
    opacity: 0.5;
    cursor: wait;
    pointer-events: none;
}

.nav-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
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
    width: 50px;
    height: 8px;
    border-radius: 4px;
    background: var(--color-bg-hover);
    cursor: pointer;
    transition: background 0.2s ease, box-shadow 0.2s ease;
    position: relative;
    /* Button resets */
    border: none;
    padding: 0;
    margin: 0;
    font-family: inherit;
    flex-shrink: 0;
}

/* Status styles */
.progress-bar.not_started {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.25);
}

.progress-bar.in_progress {
    background: var(--color-warning);  /* Yellow for incomplete/partial */
}

.progress-bar.completed {
    background: var(--color-success);
}

.progress-bar.submitting {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    position: relative;
    overflow: hidden;
}

/* Ripple Wave Animation */
.progress-bar.submitting::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg,
        transparent,
        rgba(255, 255, 255, 0.4),
        transparent
    );
    animation: rippleWave 1.5s linear infinite;
}

.progress-bar.submitting::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 100%;
    height: 200%;
    background: radial-gradient(circle,
        rgba(255, 255, 255, 0.3) 0%,
        transparent 70%
    );
    transform: translate(-50%, -50%) scale(0);
    animation: pulseCenter 2s ease-in-out infinite;
}

@keyframes rippleWave {
    0% {
        left: -100%;
    }
    100% {
        left: 200%;
    }
}

@keyframes pulseCenter {
    0%, 100% {
        transform: translate(-50%, -50%) scale(0);
        opacity: 0;
    }
    50% {
        transform: translate(-50%, -50%) scale(1);
        opacity: 1;
    }
}

/* Active state */
.progress-bar.active {
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px var(--color-primary-gradient-start);
}

.progress-bar.active.not_started {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.25);
}

.progress-bar.active.in_progress {
    background: var(--color-warning);  /* Yellow for incomplete/partial */
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px var(--color-warning);
}

.progress-bar.active.completed {
    background: var(--color-success);
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px var(--color-success);
}

.progress-bar.active.submitting {
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px #667eea;
}

/* Hover effects */
.progress-bar:hover {
    opacity: 0.8;
    transition: opacity 0.2s ease;
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
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--color-bg-hover);
    border-bottom: 1px solid var(--color-bg-input);
    margin-bottom: var(--spacing-sm);
}

.section-label {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-text-secondary);
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
    scroll-margin-top: 120px; /* Account for sticky navbar height */
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

/* Focus styles for keyboard navigation */
.nav-button:focus {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.nav-button:focus:not(:focus-visible) {
    outline: none;
}

.nav-button:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.progress-bar:focus {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.progress-bar:focus:not(:focus-visible) {
    outline: none;
}

.progress-bar:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.toolbar-btn:focus {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.toolbar-btn:focus:not(:focus-visible) {
    outline: none;
}

.toolbar-btn:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.zoom-btn:focus {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.zoom-btn:focus:not(:focus-visible) {
    outline: none;
}

.zoom-btn:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.submit-button:focus {
    outline: 2px solid var(--color-text-primary);
    outline-offset: 2px;
}

.submit-button:focus:not(:focus-visible) {
    outline: none;
}

.submit-button:focus-visible {
    outline: 2px solid var(--color-text-primary);
    outline-offset: 2px;
}

/* Visually hidden class for screen reader-only content */
.visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
}

/* Skip Link for Keyboard Navigation */
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--color-primary);
    color: var(--color-text-primary);
    padding: var(--spacing-sm) var(--spacing-md);
    text-decoration: none;
    border-radius: var(--radius-xs);
    z-index: 1000;
    font-weight: 600;
}

.skip-link:focus {
    top: var(--spacing-sm);
    left: var(--spacing-sm);
}

/* Button Text Labels */
.toolbar-btn {
    width: auto;
    padding: 0 var(--spacing-sm);
    gap: var(--spacing-xs);
}

.toolbar-btn .btn-text {
    font-size: var(--font-size-xs);
    font-weight: 500;
}

@media (max-width: 768px) {
    .toolbar-btn .btn-text {
        display: none;
    }

    .toolbar-btn {
        width: 32px;
        padding: 0;
    }
}
</style>
