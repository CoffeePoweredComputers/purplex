<template>
  <div
    v-if="isLoading"
    class="loading-container"
    role="alert"
    aria-live="polite"
    aria-busy="true"
  >
    <div class="loading-message">
      {{ $t('problems.problemSet.loading') }}
    </div>
  </div>
  <div
    v-else-if="!problems || problems.length === 0"
    class="loading-container"
    role="status"
  >
    <div class="loading-message">
      {{ $t('problems.problemSet.noProblems') }}
    </div>
  </div>
  <div
    v-else
    class="problem-set-container"
  >
    <!-- Skip Link for Accessibility -->
    <a
      href="#code-editor"
      class="skip-link"
    >{{ $t('problems.problemSet.skipToEditor') }}</a>

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
          :aria-label="$t('problems.problemSet.aria.previousProblem')"
          @click="prevProblem"
        >
          <span
            class="arrow-left"
            aria-hidden="true"
          >‹</span>
        </button>
        <div class="problem-info">
          <div class="progress-summary">
            <span class="progress-stat completed">{{ $t('problems.problemSet.completedCount', { count: completedCount }) }}</span>
            <span class="progress-stat in_progress">{{ $t('problems.problemSet.inProgressCount', { count: inProgressCount }) }}</span>
            <span class="progress-stat remaining">{{ $t('problems.problemSet.remainingCount', { count: remainingCount }) }}</span>
          </div>
          <nav
            class="problem-progress"
            :aria-label="$t('problems.problemSet.aria.problemNav')"
          >
            <button
              v-for="(problem, index) in problems"
              :key="problem.slug"
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
          :aria-label="$t('problems.problemSet.aria.nextProblem')"
          @click="nextProblem"
        >
          <span
            class="arrow-right"
            aria-hidden="true"
          >›</span>
        </button>
      </div>
    </div>

    <!-- Deadline Banner -->
    <div
      v-if="deadline"
      class="deadline-banner"
      :class="{
        'deadline-locked': deadline.is_locked,
        'deadline-past': deadline.is_past_due && !deadline.is_locked,
        'deadline-urgent': !deadline.is_past_due && isDeadlineUrgent,
        'deadline-soft': deadline.deadline_type === 'soft' && deadline.is_past_due
      }"
      role="alert"
    >
      <span class="deadline-icon">{{ deadline.is_locked ? '🔒' : deadline.is_past_due ? '⚠️' : '⏰' }}</span>
      <span class="deadline-text">
        <template v-if="deadline.is_locked">
          <strong>{{ $t('problems.problemSet.deadline.submissionsClosed') }}</strong> — {{ $t('problems.problemSet.deadline.closedOn', { date: formatDeadline(deadline.due_date) }) }}
        </template>
        <template v-else-if="deadline.is_past_due && deadline.deadline_type === 'soft'">
          <strong>{{ $t('problems.problemSet.deadline.lateSubmission') }}</strong> — {{ $t('problems.problemSet.deadline.dueDateWas', { date: formatDeadline(deadline.due_date) }) }}
        </template>
        <template v-else>
          <strong>{{ $t('problems.problemSet.deadline.due', { date: formatDeadline(deadline.due_date) }) }}</strong>
          <span v-if="isDeadlineUrgent" class="urgency-note">— {{ $t('problems.problemSet.deadline.submitSoon') }}</span>
        </template>
      </span>
    </div>

    <!-- Main workspace -->
    <div
      id="main-workspace"
      class="workspace"
      :class="{ 'is-navigating': isNavigating }"
    >
      <!-- Left panel: Code editor/image and submission -->
      <div
        class="left-panel"
        :class="{ 'is-navigating': isNavigating }"
      >
        <!-- Image section for prompt problems (when display_config.show_image is true) -->
        <div
          v-if="getCurrentProblem()?.display_config?.show_image"
          id="problem-image"
          class="image-section"
        >
          <div class="section-header">
            <div class="section-label">
              {{ $t('problems.problemSet.problemImage') }}
            </div>
          </div>
          <div class="problem-image-wrapper">
            <img
              v-if="getCurrentProblem()?.display_config?.image_url"
              :src="getCurrentProblem()?.display_config?.image_url"
              :alt="getCurrentProblem()?.display_config?.image_alt_text || $t('problems.problemSet.problemImageAlt')"
              class="problem-image"
              loading="lazy"
            >
            <div
              v-else
              class="problem-image-placeholder"
            >
              {{ $t('problems.problemSet.noImageConfigured') }}
            </div>
          </div>
        </div>

        <!-- Problem description section (for non-code problems that aren't MCQ) -->
        <!-- MCQ problems display their question_text via McqInput component -->
        <div
          v-else-if="getCurrentProblem()?.display_config?.show_reference_code === false && getCurrentProblem()?.problem_type !== 'mcq'"
          id="problem-description"
          class="description-section"
        >
          <div class="section-header">
            <div class="section-label">
              {{ getCurrentProblem()?.title || $t('problems.problemSet.question') }}
            </div>
          </div>
          <div class="problem-description-content">
            <div
              v-if="getCurrentProblem()?.description"
              class="problem-description-markdown"
              v-html="renderMarkdown(getCurrentProblem()?.description)"
            />
            <div
              v-else
              class="problem-description-missing"
            >
              {{ $t('problems.problemSet.noQuestionText') }}
            </div>
          </div>
        </div>

        <!-- Code editor section (for EiPL and other code-based problems) -->
        <div
          v-else
          id="code-editor"
          class="editor-section"
        >
          <div class="section-header">
            <div class="section-label">
              {{ $t('problems.problemSet.codeEditor') }}
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
            height="auto"
            width="100%"
            :min-lines="10"
            :max-lines="35"
            :extra-lines="2"
            :value="displayedCode"
            :markers="subgoalMarkers"
            :read-only="true"
            :show-gutter="showLineNumbers"
            :theme="currentTheme"
            @update:value="updateSolutionCode"
          />
          <div class="editor-toolbar">
            <div class="toolbar-options">
              <button
                class="toolbar-btn"
                :aria-label="codeCopied ? $t('problems.problemSet.aria.codeCopied') : $t('problems.problemSet.aria.copyCode')"
                @click="copyCode"
              >
                <span aria-hidden="true">{{ codeCopied ? '✓' : '📋' }}</span>
                <span class="btn-text">{{ codeCopied ? $t('problems.editor.copied') : $t('problems.editor.copy') }}</span>
              </button>
              <button
                class="toolbar-btn"
                :aria-label="showLineNumbers ? $t('problems.problemSet.aria.hideLineNumbers') : $t('problems.problemSet.aria.showLineNumbers')"
                @click="toggleLineNumbers"
              >
                <span aria-hidden="true">{{ showLineNumbers ? '🔢' : '➖' }}</span>
                <span class="btn-text">{{ showLineNumbers ? $t('problems.editor.lines') : $t('problems.editor.noLines') }}</span>
              </button>
              <div class="theme-selector">
                <label
                  for="editor-theme"
                  class="visually-hidden"
                >{{ $t('problems.problemSet.editorThemeLabel') }}</label>
                <select
                  id="editor-theme"
                  v-model="editorTheme"
                  class="theme-dropdown"
                  :aria-label="$t('problems.problemSet.selectEditorTheme')"
                  @change="updateTheme"
                >
                  <option value="dark">
                    {{ $t('problems.problemSet.theme.dark') }}
                  </option>
                  <option value="light">
                    {{ $t('problems.problemSet.theme.light') }}
                  </option>
                  <option value="monokai">
                    {{ $t('problems.problemSet.theme.monokai') }}
                  </option>
                  <option value="github">
                    {{ $t('problems.problemSet.theme.github') }}
                  </option>
                  <option value="solarized-dark">
                    {{ $t('problems.problemSet.theme.solarizedDark') }}
                  </option>
                  <option value="solarized-light">
                    {{ $t('problems.problemSet.theme.solarizedLight') }}
                  </option>
                  <option value="dracula">
                    {{ $t('problems.problemSet.theme.dracula') }}
                  </option>
                  <option value="tomorrow-night">
                    {{ $t('problems.problemSet.theme.tomorrowNight') }}
                  </option>
                </select>
              </div>
            </div>
            <div class="zoom-controls">
              <button
                class="zoom-btn"
                :disabled="editorFontSize <= 12"
                :aria-label="$t('problems.problemSet.aria.decreaseFont')"
                @click="decreaseFontSize"
              >
                <span
                  class="zoom-icon"
                  aria-hidden="true"
                >−</span>
              </button>
              <span
                class="zoom-level"
                aria-live="polite"
              >{{ Math.round((editorFontSize / 14) * 100) }}%</span>
              <button
                class="zoom-btn"
                :disabled="editorFontSize >= 35"
                :aria-label="$t('problems.problemSet.aria.increaseFont')"
                @click="increaseFontSize"
              >
                <span
                  class="zoom-icon"
                  aria-hidden="true"
                >+</span>
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
          <InputSelector
            v-model="promptEditorValue"
            :activity-type="getCurrentProblem()?.problem_type || 'eipl'"
            :problem="getCurrentProblem()"
            :disabled="isCurrentProblemSubmitting(getCurrentProblem()?.slug)"
            :theme="currentTheme"
            :draft-saved="draftSaved"
            @submit="submit"
          />
        </div>
      </div>

      <!-- Right panel: Feedback -->
      <div class="right-panel">
        <FeedbackSelector
          :activity-type="getCurrentProblem()?.problem_type || 'eipl'"
          :progress="feedback.promptCorrectness"
          :notches="6"
          :code-results="feedback.codeResults"
          :test-results="feedback.testResults"
          :comprehension-results="feedback.comprehensionResults"
          :user-prompt="feedback.userPrompt"
          :segmentation="feedback.segmentationData"
          :mcq-result="feedback.mcqResult"
          :reference-code="getCurrentProblem()?.reference_solution || ''"
          :segmentation-enabled="getCurrentProblem()?.feedback_config?.show_segmentation === true"
          :is-loading="loading"
          :is-navigating="isNavigating"
          :submission-history="submissionHistory"
          :title="$t('problems.problemSet.submissionResults')"
          @load-attempt="loadSpecificAttempt"
          @next-problem="nextProblem"
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
import HintButton from "@/components/HintButton.vue"
import SuggestedTraceOverlay from "@/components/hints/SuggestedTraceOverlay.vue"
import PyTutorModal from "@/modals/PyTutorModal.vue"
import InputSelector from "@/components/activities/InputSelector.vue"
import FeedbackSelector from "@/components/activities/FeedbackSelector.vue"
import axios from 'axios'
import { marked } from 'marked'
import { useNotification } from '@/composables/useNotification'
import { useLogger } from '@/composables/useLogger'
import { useOptimisticProgress } from '@/composables/useOptimisticProgress'
import { useHintTracking } from '@/composables/useHintTracking'
import { useEditorHints } from '@/composables/useEditorHints'
import { useFeedbackState } from '@/composables/useFeedbackState'
import { useSubmissionCache } from '@/composables/useSubmissionCache'
import { useSubmissionTracking } from '@/composables/useSubmissionTracking'
import { parseProblemQueryParam } from './problemNavigation'
import { sseService } from '@/services/sseService'
import { submissionService } from '@/services/submissionService'
import { computed, ref, watch } from 'vue'

export default {
    name: 'ProblemSet',
    components: {
        Editor,
        HintButton,
        SuggestedTraceOverlay,
        PyTutorModal,
        InputSelector,
        FeedbackSelector
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
        // Feedback state management - atomic updates for all feedback properties
        const { feedback, clear: clearFeedback, set: setFeedback, hasContent: hasFeedbackContent } = useFeedbackState();

        // Submission cache management - 5min TTL cache for submission data
        const submissionCache = useSubmissionCache();

        // Submission tracking - multi-problem submission state
        const submissionTracking = useSubmissionTracking();

        // Hint system setup
        const entry = ref(null);
        const originalSolutionCode = ref('');

        // Initialize hint system
        const {
            modifiedCode,
            subgoalMarkers,
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
            // Feedback state management
            feedback,
            clearFeedback,
            setFeedback,
            hasFeedbackContent,
            // Submission cache management
            submissionCache,
            // Submission tracking (multi-problem submissions)
            submissionTracking,
            // Hint system
            entry,
            originalSolutionCode,
            modifiedCode,
            subgoalMarkers,
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
            // Note: submittingProblems and submissionConnections are now managed
            // by useSubmissionTracking composable. Access via this.submissionTracking.*
            // Note: codeResults, testResults, promptCorrectness, comprehensionResults,
            // userPrompt, and segmentationData are now managed by useFeedbackState composable
            // Access via this.feedback.* and update via this.setFeedback()

            /* Problem Status Tracking */
            problemStatuses: {},
            problemSetProgress: null,

            /* Deadline Info */
            deadline: null,

            /* Editor Settings */
            editorFontSize: 14,
            codeCopied: false,
            showLineNumbers: true,
            editorTheme: 'tomorrow-night',

            /* Draft Management */
            autoSaveInterval: null,
            draftSaved: false,

            // Note: submissionCache is now managed by useSubmissionCache composable
            // Access via this.submissionCache.get/set/invalidate/invalidateAll

            /* PyTutor Modal */
            showPyTutorModal: false,
            pyTutorUrl: '',

            /* Hint State Storage per Problem */
            problemHintStates: {},

            /* Current Attempt Hint Tracking - NEW: Two-level tracking system */
            currentAttemptHints: new Set(),  // Tracks hints used in current attempt only

            /* Submission History - keyed by problem slug for isolation */
            submissionHistoryMap: {}
        };
    },

    computed: {
        /**
         * Current problem's submission history.
         * Uses keyed map pattern to prevent cross-problem contamination
         * when async callbacks complete after navigation.
         */
        submissionHistory() {
            const currentSlug = this.getCurrentProblem()?.slug;
            return currentSlug ? (this.submissionHistoryMap[currentSlug] || []) : [];
        },

        solutionCode() {
            return this.getCurrentProblem().reference_solution || '';
        },

        displayedCode() {
            return this.hasActiveHints ? this.modifiedCode : this.solutionCode;
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

        isDeadlineUrgent() {
            if (!this.deadline || this.deadline.is_past_due) {
                return false;
            }
            const dueDate = new Date(this.deadline.due_date);
            const now = new Date();
            const diffMs = dueDate.getTime() - now.getTime();
            const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
            return diffDays <= 2;
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
        // Note: submissionTracking.cancelAll() is called automatically on unmount
        // but we call it explicitly here to ensure cleanup order
        this.submissionTracking.cancelAll();
    },

    methods: {
        renderMarkdown(text) {
            if (!text) {return '';}
            return marked(text, { breaks: true });
        },

        formatDeadline(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = date.getTime() - now.getTime();
            const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

            // Format date with time
            const dateOptions = { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' };
            const formatted = date.toLocaleDateString('en-US', dateOptions);

            // Add relative indicator for upcoming deadlines
            if (diffDays > 0 && diffDays <= 7) {
                if (diffDays === 1) {
                    return this.$t('problems.problemSet.deadline.tomorrow', { date: formatted });
                }
                return this.$t('problems.problemSet.deadline.inDays', { days: diffDays, date: formatted });
            }

            return formatted;
        },

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

                // Clear current attempt hints when navigating away
                this.currentAttemptHints = new Set();

                // Clear hints synchronously
                this.removeAllHints();

                // Get the problem we're navigating to
                const problem = this.problems[newIndex];

                // Check if this problem is currently submitting
                const isSubmitting = this.submissionTracking.isSubmitting(problem.slug);

                let batchData = null;
                if (!isSubmitting) {
                    // Load ALL data in parallel for atomic update
                    batchData = await this.loadProblemDataBatch(problem.slug);
                }

                // ATOMIC STATE UPDATE - Everything changes at once
                // This prevents multiple re-renders with partial data
                this.currentProblem = newIndex;
                this.loading = isSubmitting;

                // Update URL to persist problem position across refresh
                this.$router.replace({
                    query: { ...this.$route.query, p: newIndex }
                });

                if (isSubmitting) {
                    // Clear feedback to show loading state
                    this.clearFeedbackData();
                    this.logger.info('Navigation: Problem is submitting, showing loading state', {
                        problemSlug: problem.slug
                    });
                } else if (batchData) {
                    // Apply all loaded data atomically
                    const { submissionHistory, submissionData, draftText } = batchData;

                    this.submissionHistoryMap[problem.slug] = submissionHistory;

                    // Only set segmentation data if the problem has segmentation enabled (use handler config)
                    const currentProblem = this.getCurrentProblem();
                    const problemType = currentProblem?.problem_type || 'eipl';
                    const segData = currentProblem?.feedback_config?.show_segmentation && submissionData.segmentation
                        ? submissionData.segmentation
                        : null;

                    // Handle different data formats based on problem type
                    let codeResults = [];
                    let testResults = [];

                    if (problemType === 'probeable_code') {
                        // Probeable code stores student_code instead of variations
                        if (submissionData.student_code) {
                            codeResults = [{ code: submissionData.student_code }];
                        }
                        testResults = submissionData.results || submissionData.test_results || [];
                    } else {
                        // EiPL and other types use variations
                        codeResults = submissionData.variations || [];
                        testResults = submissionData.results || [];
                    }

                    // Update feedback state atomically
                    this.setFeedback({
                        codeResults: codeResults,
                        testResults: testResults,
                        promptCorrectness: submissionData.passing_variations || 0,
                        comprehensionResults: submissionData.feedback || '',
                        userPrompt: submissionData.user_prompt || '',
                        segmentationData: segData,
                        mcqResult: submissionData.mcq_result || null
                    });

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
                    if (this.feedback.userPrompt) {
                        this.promptEditorValue = this.feedback.userPrompt;
                    } else if (draftText) {
                        this.promptEditorValue = draftText;
                    } else {
                        this.promptEditorValue = '';
                    }

                    this.logger.info('Navigation: Applied batched data atomically', {
                        problemSlug: problem.slug,
                        hasSubmission: submissionData.has_submission,
                        codeResults: this.feedback.codeResults.length,
                        testResults: this.feedback.testResults.length,
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
            if (this.submissionTracking.isSubmitting(problem.slug)) {
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
                this.submissionHistoryMap[problem.slug] = submissionHistory;
                this.setFeedback({
                    codeResults: submissionData.variations || [],
                    testResults: submissionData.results || [],
                    promptCorrectness: submissionData.passing_variations || 0,
                    comprehensionResults: submissionData.feedback || '',
                    userPrompt: submissionData.user_prompt || '',
                    segmentationData: submissionData.segmentation || null
                });

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
                if (this.feedback.userPrompt) {
                    this.promptEditorValue = this.feedback.userPrompt;
                } else if (draftText) {
                    this.promptEditorValue = draftText;
                } else {
                    this.promptEditorValue = '';
                }

                this.logger.info('Applied batched data to component', {
                    codeResults: this.feedback.codeResults.length,
                    testResults: this.feedback.testResults.length,
                    promptCorrectness: this.feedback.promptCorrectness,
                    hasSegmentation: !!this.feedback.segmentationData
                });

            } catch (error) {
                this.logger.error('Error loading problem data', error);
                // Clear on error
                this.clearFeedbackData();
            }
        },

        async loadSubmissionData(problemSlug) {
            const cacheKey = this.submissionCache.buildKey(
                this.$route.params.slug,
                problemSlug,
                this.courseId
            );

            // Check cache (TTL handled internally by composable)
            const cached = this.submissionCache.get(cacheKey);
            if (cached) {
                return cached;
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

                // Cache the response (timestamp handled by composable)
                this.submissionCache.set(cacheKey, data);

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
            // Use composable's clear() for atomic reset of all feedback state
            this.clearFeedback();
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

                this.submissionHistoryMap[problemSlug] = historyResponse.submissions || [];
                this.logger.info('Loaded submission history', {
                    problemSlug,
                    problemSetSlug: this.$route.params.slug,
                    totalAttempts: historyResponse.total_attempts,
                    bestScore: historyResponse.best_score,
                    submissions: this.submissionHistoryMap[problemSlug]
                });
            } catch (error) {
                this.logger.error('Error loading submission history', error);
                this.submissionHistoryMap[problemSlug] = [];
            }
        },

        async loadSpecificAttempt(attempt) {
            // Load data from specific attempt
            this.logger.info('Loading specific attempt', {
                attemptId: attempt.id,
                attemptNumber: attempt.attempt_number,
                score: attempt.score
            });

            // Validate attempt data exists
            if (!attempt || !attempt.data) {
                this.logger.error('Cannot load attempt: missing data', { attempt });
                this.notify.error('Failed to load attempt', 'Submission data is missing or corrupted');
                this.clearFeedbackData();
                return;
            }

            // Apply the attempt data
            const data = attempt.data;

            // Validate required fields in data
            if (!data.raw_input && !data.processed_code && (!data.variations || data.variations.length === 0)) {
                this.logger.error('Cannot load attempt: data is empty', { data });
                this.notify.error('Failed to load attempt', 'Submission data is incomplete');
                this.clearFeedbackData();
                return;
            }

            // Transform variations into code results
            let codeResults;
            if (data.variations && data.variations.length > 0) {
                codeResults = data.variations.map(v => v.code);
            } else {
                // For non-variation submissions, use processed_code
                codeResults = [data.processed_code || data.raw_input];
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

            // Apply segmentation data only if the problem has segmentation enabled (use handler config)
            const currentProblem = this.getCurrentProblem();
            const segData = currentProblem?.feedback_config?.show_segmentation && attempt.segmentation
                ? attempt.segmentation
                : null;

            // Update all feedback state atomically
            this.setFeedback({
                codeResults,
                testResults: testResultsPerVariation,
                promptCorrectness: attempt.score,
                userPrompt: data.raw_input,
                comprehensionResults: '',
                segmentationData: segData
            });

            // Update UI to reflect loaded attempt
            this.logger.info('Applied attempt data to feedback', {
                codeResults: this.feedback.codeResults.length,
                testResults: this.feedback.testResults.length,
                score: attempt.score
            });
        },

        reconstructFunctionCall(testResult) {
            // Try to reconstruct function call from test data
            const currentProblem = this.getCurrentProblem();
            const functionName = currentProblem?.function_name || 'foo';

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
            if (value === null) {return 'None';}
            if (value === undefined) {return 'undefined';}
            if (typeof value === 'string') {return `"${value}"`;}
            if (typeof value === 'boolean') {return value ? 'True' : 'False';}
            if (typeof value === 'number') {return value.toString();}
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
            if (this.submissionTracking.isSubmitting(currentProblemSlug)) {return;}

            // Get the input value (validation is handled by the input component)
            const rawInput = this.promptEditorValue?.trim() || '';

            // Proceed with submission
            this.submissionTracking.addSubmission(currentProblemSlug);
            this.loading = true; // Track current problem's loading state for Feedback component

            // Declare rollback outside try block so it's accessible in catch block
            let rollback = null;

            try {
                // Clear cache for this problem to ensure fresh data on next load
                const cacheKey = this.submissionCache.buildKey(
                    this.$route.params.slug,
                    currentProblemSlug,
                    this.courseId
                );
                this.submissionCache.invalidate(cacheKey);

                // Clear previous feedback only after validation passes
                this.clearFeedbackData();

                // Optimistic update
                rollback = this.updateProgress(currentProblemSlug, {
                    status: 'in_progress',
                    score: null,
                    attempts: (this.problemStatuses[currentProblemSlug]?.attempts || 0) + 1
                });

                // Get hints that were used for THIS ATTEMPT only (not cumulative)
                const hintsUsed = Array.from(this.currentAttemptHints);

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
                    raw_input: rawInput,
                    activated_hints: activatedHints,
                    course_id: this.courseId || undefined
                };

                this.logger.info('Submitting activity solution', { problemSlug: currentProblemSlug });

                // Submit to generic activity endpoint
                const submissionResponse = await submissionService.submitActivity(submissionData);

                // Check if this is a synchronous (immediate) response
                if (submissionResponse.status === 'complete') {
                    // Synchronous submission (e.g., MCQ) - result is already available
                    this.logger.info('Sync submission complete', {
                        submissionId: submissionResponse.submission_id,
                        score: submissionResponse.score
                    });

                    // Process the immediate result
                    this.handleSyncSubmissionResult(submissionResponse, currentProblemSlug, rawInput);
                    return;
                }

                // Asynchronous submission - need to connect to SSE
                if (!submissionResponse.task_id) {
                    throw new Error('No task ID received from server');
                }

                this.logger.info('Async submission accepted, connecting to SSE stream', {
                    taskId: submissionResponse.task_id
                });

                // Connect to unified SSE stream for real-time updates
                // sseService returns a disconnect function - store it for cleanup
                const disconnect = await sseService.connectToSubmission(
                    submissionResponse.task_id,
                    (unifiedResult) => {
                        // Success callback - results are ready
                        // Defensive: Get problem type from result, fall back to current problem
                        const currentProblem = this.getCurrentProblem();
                        const problemType = unifiedResult.problem_type
                            || currentProblem?.problem_type
                            || 'eipl';

                        this.logger.info('Submission results received', {
                            problem_type: problemType,
                            is_correct: unifiedResult.is_correct,
                            score: unifiedResult.score,
                            has_result_field: !!unifiedResult.result
                        });

                        // Store the unified result
                        this.setFeedback({ unifiedResult });

                        // Get the problem index for clearer messaging
                        const problemIndex = this.problems.findIndex(p => p.slug === currentProblemSlug);
                        const problemIdentifier = problemIndex >= 0 ? `Problem ${problemIndex + 1}` : 'Submission';

                        // Process based on problem type
                        if (problemType === 'mcq') {
                            // MCQ processing - use result field with fallback to legacy fields
                            const resultData = unifiedResult.result;
                            const mcqResult = resultData || {
                                selected_option: unifiedResult.selected_option || { id: '', text: '' },
                                correct_option: unifiedResult.correct_option || { id: '', text: '' },
                                selected_options: unifiedResult.selected_options,
                                correct_options: unifiedResult.correct_options,
                                is_correct: unifiedResult.is_correct ?? false
                            };

                            // Only update displayed feedback if this submission is for the currently viewed problem
                            if (currentProblemSlug === this.getCurrentProblem().slug) {
                                this.setFeedback({
                                    mcqResult: {
                                        is_correct: mcqResult.is_correct,
                                        score: unifiedResult.score ?? 0,
                                        submission_id: unifiedResult.submission_id,
                                        selected_option: mcqResult.selected_option,
                                        correct_option: mcqResult.correct_option,
                                        selected_options: mcqResult.selected_options,
                                        correct_options: mcqResult.correct_options,
                                        completion_status: unifiedResult.completion_status
                                    },
                                    promptCorrectness: unifiedResult.score ?? 0,
                                    userPrompt: unifiedResult.user_input ?? rawInput,
                                    // Clear EiPL-specific fields
                                    codeResults: [],
                                    testResults: [],
                                    comprehensionResults: '',
                                    segmentationData: null
                                });
                                this.promptEditorValue = unifiedResult.user_input ?? rawInput;
                            }

                            // Update problem status
                            const finalStatus = mcqResult.is_correct ? 'completed' : 'in_progress';
                            this.problemStatuses = {
                                ...this.problemStatuses,
                                [currentProblemSlug]: {
                                    status: finalStatus,
                                    score: unifiedResult.score,
                                    attempts: (this.problemStatuses[currentProblemSlug]?.attempts || 0) + 1
                                }
                            };

                            // Update cache
                            const cacheKey = this.submissionCache.buildKey(
                                this.$route.params.slug,
                                currentProblemSlug,
                                this.courseId
                            );
                            this.submissionCache.set(cacheKey, {
                                has_submission: true,
                                mcq_result: mcqResult,
                                user_prompt: unifiedResult.user_input
                            });

                            // Show notification
                            const message = `${problemIdentifier}: ${mcqResult.is_correct ? 'Correct!' : 'Incorrect'}`;
                            if (mcqResult.is_correct) {
                                this.notify.success(message);
                            } else {
                                this.notify.warning(message);
                            }
                        } else if (problemType === 'probeable_code') {
                            // Probeable code processing - extracts student_code and test_results
                            const probeableResult = unifiedResult.result || {};
                            const studentCode = probeableResult.student_code || '';
                            const testResults = probeableResult.test_results || [];

                            // Calculate test statistics
                            let totalTestsPassed = 0;
                            let totalTestsRun = 0;

                            (testResults || []).forEach(r => {
                                const passed = r.testsPassed || 0;
                                const total = r.totalTests || 0;
                                totalTestsPassed += passed;
                                totalTestsRun += total;
                            });

                            // Only update displayed feedback if this submission is for the currently viewed problem
                            if (currentProblemSlug === this.getCurrentProblem().slug) {
                                this.setFeedback({
                                    codeResults: [{ code: studentCode }],
                                    testResults: testResults,
                                    promptCorrectness: unifiedResult.score ?? 0,
                                    userPrompt: unifiedResult.user_input ?? rawInput,
                                    comprehensionResults: '',
                                    segmentationData: null,
                                    mcqResult: null
                                });
                                this.promptEditorValue = unifiedResult.user_input ?? rawInput;
                            }

                            // Calculate score and determine status
                            const score = totalTestsRun > 0
                                ? Math.round((totalTestsPassed / totalTestsRun) * 100)
                                : (unifiedResult.score ?? 0);
                            const finalStatus = score >= 100 ? 'completed' : 'in_progress';

                            // Update problem status
                            this.problemStatuses = {
                                ...this.problemStatuses,
                                [currentProblemSlug]: {
                                    status: finalStatus,
                                    score: score,
                                    attempts: (this.problemStatuses[currentProblemSlug]?.attempts || 0) + 1
                                }
                            };

                            // Update cache
                            const cacheKey = this.submissionCache.buildKey(
                                this.$route.params.slug,
                                currentProblemSlug,
                                this.courseId
                            );
                            this.submissionCache.set(cacheKey, {
                                has_submission: true,
                                student_code: studentCode,
                                results: testResults,
                                user_prompt: unifiedResult.user_input
                            });

                            // Show notification
                            const allPassed = totalTestsRun > 0 && totalTestsPassed === totalTestsRun;
                            const message = `${problemIdentifier}: ${totalTestsPassed}/${totalTestsRun} tests passed`;
                            if (allPassed) {
                                this.notify.success(message);
                            } else {
                                this.notify.warning(message);
                            }
                        } else {
                            // EiPL and other types processing - use result field with fallback to legacy fields
                            const eiplResult = unifiedResult.result;

                            // Defensive extraction with legacy fallbacks
                            const variations = eiplResult?.variations?.map(v => v.code)
                                ?? unifiedResult.variations
                                ?? [];
                            const testResults = eiplResult?.test_results
                                ?? unifiedResult.test_results
                                ?? [];
                            const segmentation = eiplResult?.segmentation
                                ?? unifiedResult.segmentation;

                            // Calculate test results across all variations
                            let totalTestsPassed = 0;
                            let totalTestsRun = 0;
                            let perfectVariations = 0;

                            (testResults || []).forEach(r => {
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
                                const segData = currentProblem?.feedback_config?.show_segmentation && segmentation
                                    ? segmentation
                                    : null;

                                this.setFeedback({
                                    codeResults: variations,
                                    testResults: testResults,
                                    promptCorrectness: perfectVariations,
                                    userPrompt: unifiedResult.user_input ?? rawInput,
                                    comprehensionResults: '',
                                    segmentationData: segData,
                                    mcqResult: null
                                });
                                this.promptEditorValue = unifiedResult.user_input ?? rawInput;
                            }

                            // Calculate score and determine status
                            const score = totalTestsRun > 0
                                ? Math.round((totalTestsPassed / totalTestsRun) * 100)
                                : 0;
                            const segmentationPassed = segmentation?.passed ?? null;
                            const submittedProblem = this.problems.find(p => p.slug === currentProblemSlug);

                            // Determine completion status using handler config instead of hardcoded type checks
                            // feedback_config.show_segmentation comes from ActivityHandler.get_problem_config()
                            let finalStatus = 'in_progress';
                            if (submittedProblem?.feedback_config?.show_segmentation) {
                                finalStatus = (score >= 100 && segmentationPassed === true) ? 'completed' : 'in_progress';
                            } else {
                                finalStatus = score >= 100 ? 'completed' : 'in_progress';
                            }

                            // Update problem status
                            this.problemStatuses = {
                                ...this.problemStatuses,
                                [currentProblemSlug]: {
                                    status: finalStatus,
                                    score: score,
                                    attempts: (this.problemStatuses[currentProblemSlug]?.attempts || 0) + 1,
                                    segmentationPassed: segmentationPassed
                                }
                            };

                            // Update cache
                            const cacheKey = this.submissionCache.buildKey(
                                this.$route.params.slug,
                                currentProblemSlug,
                                this.courseId
                            );
                            this.submissionCache.set(cacheKey, {
                                has_submission: true,
                                variations: variations,
                                results: testResults,
                                passing_variations: perfectVariations,
                                user_prompt: unifiedResult.user_input,
                                segmentation: segmentation
                            });

                            // Build notification message
                            let message = `${problemIdentifier}: `;
                            let notificationType = 'info';

                            // Use handler config instead of hardcoded type checks
                            // feedback_config.show_segmentation comes from ActivityHandler.get_problem_config()
                            if (submittedProblem?.feedback_config?.show_segmentation && segmentation) {
                                const segmentCount = segmentation.segment_count || 0;
                                // Read threshold from segmentation result (backend uses DB field as single source of truth)
                                const threshold = segmentation.threshold ?? 2;
                                const thresholdText = threshold === 1 ? 'need 1' : `need ≤${threshold}`;
                                const highLevelText = segmentationPassed
                                    ? `✓ High-level (${segmentCount} segment${segmentCount !== 1 ? 's' : ''})`
                                    : `✗ High-level (${segmentCount} segments, ${thresholdText})`;
                                message += `Variations: ${perfectVariations}/${variations.length} passing, ${highLevelText}`;
                                notificationType = (perfectVariations === variations.length && segmentationPassed) ? 'success' : 'warning';
                            } else {
                                message += `Variations: ${perfectVariations}/${variations.length} passing`;
                                notificationType = (perfectVariations === variations.length) ? 'success' : 'warning';
                            }

                            if (notificationType === 'success') {
                                this.notify.success(message);
                            } else {
                                this.notify.warning(message);
                            }
                        }

                        // Common cleanup
                        this.clearOptimistic(currentProblemSlug);
                        this.submissionTracking.removeSubmission(currentProblemSlug);
                        this.loading = this.submissionTracking.isSubmitting(this.getCurrentProblem().slug);

                        const connection = this.submissionTracking.getAndRemoveConnection(currentProblemSlug);
                        connection?.disconnect();

                        this.currentAttemptHints = new Set();

                        // Refresh submission history (uses keyed map - safe even if user navigated away)
                        this.loadSubmissionHistory(currentProblemSlug).then(() => {
                            this.logger.info('Submission history refreshed');
                        }).catch(error => {
                            this.logger.error('Failed to refresh submission history', error);
                        });
                    },
                    {
                        onError: (error) => {
                            this.logger.error('SSE connection error', error);
                            this.notify.error(error.error || 'Failed to get results');
                            this.submissionTracking.removeSubmission(currentProblemSlug);
                            this.loading = this.submissionTracking.isSubmitting(this.getCurrentProblem().slug);
                            if (rollback) { rollback(); }

                            const connection = this.submissionTracking.getAndRemoveConnection(currentProblemSlug);
                            connection?.disconnect();

                            this.currentAttemptHints = new Set();
                        },
                        onTimeout: () => {
                            this.logger.warn('SSE connection timeout');
                            this.notify.warning('Connection timeout. Please try again.');
                            this.submissionTracking.removeSubmission(currentProblemSlug);
                            this.loading = this.submissionTracking.isSubmitting(this.getCurrentProblem().slug);
                            if (rollback) { rollback(); }

                            const connection = this.submissionTracking.getAndRemoveConnection(currentProblemSlug);
                            connection?.disconnect();

                            this.currentAttemptHints = new Set();
                        },
                        reconnectAttempts: 3,
                        reconnectDelay: 2000
                    }
                );

                // Store the disconnect function for cleanup
                this.submissionTracking.setConnection(currentProblemSlug, { disconnect });

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
                this.submissionTracking.removeSubmission(currentProblemSlug);
                this.loading = this.submissionTracking.isSubmitting(this.getCurrentProblem().slug);
                // Rollback optimistic update on error
                if (rollback) {rollback();}

                // Clean up any SSE connection if error occurred during submission
                const connection = this.submissionTracking.getAndRemoveConnection(currentProblemSlug);
                connection?.disconnect();

                // Clear current attempt hints after error
                this.currentAttemptHints = new Set();
            } finally {
                // Loading state is managed in SSE callbacks
                // Don't reset it here as SSE is still processing
            }
        },

        handleSyncSubmissionResult(response, problemSlug, rawInput) {
            /**
             * Handle synchronous submission result (e.g., MCQ).
             * MCQ submissions return immediately with complete results.
             */
            const problemType = response.problem_type || 'mcq';
            const problemIndex = this.problems.findIndex(p => p.slug === problemSlug);
            const problemIdentifier = problemIndex >= 0 ? `Problem ${problemIndex + 1}` : 'Submission';

            // Build MCQ result from response
            const mcqResult = {
                is_correct: response.is_correct ?? false,
                score: response.score ?? 0,
                submission_id: response.submission_id,
                selected_option: response.selected_option || { id: '', text: '' },
                correct_option: response.correct_option || { id: '', text: '', explanation: '' },
                selected_options: response.selected_options,
                correct_options: response.correct_options,
                completion_status: response.completion_status
            };

            // Only update displayed feedback if this submission is for the currently viewed problem
            if (problemSlug === this.getCurrentProblem().slug) {
                this.setFeedback({
                    mcqResult: mcqResult,
                    promptCorrectness: response.score ?? 0,
                    userPrompt: response.user_input ?? rawInput,
                    // Clear EiPL-specific fields
                    codeResults: [],
                    testResults: [],
                    comprehensionResults: '',
                    segmentationData: null
                });
                this.promptEditorValue = response.user_input ?? rawInput;
            }

            // Update problem status
            const finalStatus = mcqResult.is_correct ? 'completed' : 'in_progress';
            this.problemStatuses = {
                ...this.problemStatuses,
                [problemSlug]: {
                    status: finalStatus,
                    score: response.score,
                    attempts: (this.problemStatuses[problemSlug]?.attempts || 0) + 1
                }
            };

            // Update cache
            const cacheKey = this.submissionCache.buildKey(
                this.$route.params.slug,
                problemSlug,
                this.courseId
            );
            this.submissionCache.set(cacheKey, {
                has_submission: true,
                mcq_result: mcqResult,
                user_prompt: response.user_input
            });

            // Show notification
            const message = `${problemIdentifier}: ${mcqResult.is_correct ? 'Correct!' : 'Incorrect'}`;
            if (mcqResult.is_correct) {
                this.notify.success(message);
            } else {
                this.notify.warning(message);
            }

            // Clean up submission tracking state
            this.clearOptimistic(problemSlug);
            this.submissionTracking.removeSubmission(problemSlug);
            this.loading = this.submissionTracking.isSubmitting(this.getCurrentProblem().slug);

            // Clear current attempt hints
            this.currentAttemptHints = new Set();

            // Refresh submission history (uses keyed map - safe even if user navigated away)
            this.loadSubmissionHistory(problemSlug).then(() => {
                this.logger.info('Submission history refreshed after sync submission');
            }).catch(error => {
                this.logger.error('Failed to refresh submission history', error);
            });

            this.logger.info('Sync submission processed', {
                problemSlug,
                problemType,
                isCorrect: mcqResult.is_correct,
                score: response.score
            });
        },

        async loadProblemSet() {
            const problemSetSlug = this.$route.params.slug;
            this.isLoading = true;

            // Clear submission cache for fresh data
            this.submissionCache.invalidateAll();

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

                // Restore problem position from URL query param
                const initialIndex = parseProblemQueryParam(this.$route.query, this.problems.length);
                if (initialIndex > 0) {
                    this.currentProblem = initialIndex;
                }

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

                // Store deadline info if provided
                if (response.data.deadline) {
                    this.deadline = response.data.deadline;
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
                return this.$t('problems.problemSet.tooltip.notAttempted', { name: problemName });
            } else if (status.status === 'in_progress') {
                return this.$t('problems.problemSet.tooltip.inProgress', { name: problemName, score: status.score });
            } else if (status.status === 'completed') {
                return this.$t('problems.problemSet.tooltip.completed', { name: problemName, score: status.score });
            }
            return problemName;
        },

        isCurrentProblemSubmitting(problemSlug) {
            // Check if this specific problem is currently being submitted
            // Delegates to submissionTracking composable
            return this.submissionTracking.isSubmitting(problemSlug);
        },

        // Note: addToSubmitting and removeFromSubmitting have been moved to
        // useSubmissionTracking composable. Use this.submissionTracking.addSubmission()
        // and this.submissionTracking.removeSubmission() instead.

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
            if (this.feedback.userPrompt) {
                this.promptEditorValue = this.feedback.userPrompt;
                this.logger.debug('Loaded previous submission into prompt editor', {
                    promptLength: this.feedback.userPrompt.length
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

            // Track for current attempt (submission) - Vue 3 reactive Set update
            const newSet = new Set(this.currentAttemptHints);
            newSet.add(hintData.hintType);
            this.currentAttemptHints = newSet;

            // Track hint usage with the composable (research data - cumulative)
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

/* Deadline Banner */
.deadline-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1.25rem;
    margin: 0 1rem 1rem 1rem;
    border-radius: 8px;
    font-size: 0.9rem;
    background: var(--color-surface-elevated, #2a2d3a);
    border: 1px solid var(--color-border, #3a3d4a);
}

.deadline-banner .deadline-icon {
    font-size: 1.1rem;
}

.deadline-banner .deadline-text {
    flex: 1;
}

.deadline-banner .urgency-note {
    color: var(--color-warning, #f5a623);
    font-weight: 500;
}

.deadline-banner.deadline-locked {
    background: rgba(220, 53, 69, 0.15);
    border-color: rgba(220, 53, 69, 0.4);
    color: #ff6b6b;
}

.deadline-banner.deadline-past,
.deadline-banner.deadline-soft {
    background: rgba(245, 166, 35, 0.15);
    border-color: rgba(245, 166, 35, 0.4);
    color: #f5a623;
}

.deadline-banner.deadline-urgent {
    background: rgba(245, 166, 35, 0.1);
    border-color: rgba(245, 166, 35, 0.3);
}

/* No transitions - keep content completely static during navigation */
.editor-section,
.description-section,
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
    margin-bottom: 0px !important;
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

/* Image Section (for prompt problems) */
.image-section {
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
    scroll-margin-top: 120px;
}

.image-section:hover {
    border-color: var(--color-bg-input);
}

.problem-image-wrapper {
    padding: var(--spacing-lg);
    display: flex;
    justify-content: center;
    align-items: center;
}

.problem-image {
    max-width: 100%;
    max-height: 500px;
    object-fit: contain;
    border-radius: var(--radius-base);
    border: 4px solid var(--color-text-muted);
    box-shadow: var(--shadow-md);
}

.problem-image-placeholder {
    color: var(--color-text-muted);
    font-style: italic;
    text-align: center;
    padding: var(--spacing-xl);
}

/* Description Section (for MCQ and other non-code problems) */
.description-section {
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
    scroll-margin-top: 120px;
}

.description-section:hover {
    border-color: var(--color-bg-input);
}

.problem-description-content {
    padding: var(--spacing-xl);
}

.problem-description-markdown {
    font-size: var(--font-size-base);
    color: var(--color-text-primary);
    line-height: 1.7;
}

.problem-description-markdown :deep(p) {
    margin: 0 0 var(--spacing-md) 0;
}

.problem-description-markdown :deep(p:last-child) {
    margin-bottom: 0;
}

.problem-description-markdown :deep(code) {
    background: var(--color-bg-hover);
    padding: 2px 6px;
    border-radius: var(--radius-xs);
    font-family: 'Fira Code', 'Monaco', monospace;
    font-size: 0.9em;
    color: var(--color-text-code);
}

.problem-description-markdown :deep(pre) {
    background: var(--color-bg-input);
    padding: var(--spacing-md);
    border-radius: var(--radius-base);
    overflow-x: auto;
    margin: var(--spacing-md) 0;
}

.problem-description-markdown :deep(pre code) {
    background: none;
    padding: 0;
    font-size: var(--font-size-sm);
}

.problem-description-markdown :deep(ul),
.problem-description-markdown :deep(ol) {
    margin: var(--spacing-md) 0;
    padding-left: var(--spacing-xl);
}

.problem-description-markdown :deep(li) {
    margin-bottom: var(--spacing-xs);
}

.problem-description-markdown :deep(strong) {
    font-weight: 600;
    color: var(--color-text-primary);
}

.problem-description-markdown :deep(em) {
    font-style: italic;
}

.problem-description-missing {
    font-size: var(--font-size-base);
    color: var(--color-warning);
    font-style: italic;
    padding: var(--spacing-md);
    background: var(--color-warning-bg);
    border-radius: var(--radius-base);
    border: 1px dashed var(--color-warning);
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
    position: relative;
}

.submission-section:hover {
    border-color: var(--color-bg-input);
}

/* Input-specific styles moved to EiplInput.vue */

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

    .editor-section,
    .description-section {
        flex: none;
    }

    .submission-section {
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

    .editor-section,
    .description-section {
        min-height: 400px;
    }

    .submission-section {
        /* Content determines height */
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
