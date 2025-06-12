<template>
    <div v-if="isLoading" class="loading-container">
        <div class="loading-message">Loading problem set...</div>
    </div>
    <div v-else-if="!problems || problems.length === 0" class="loading-container">
        <div class="loading-message">No problems found in this set.</div>
    </div>
    <div v-else class="problem-set-container">
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
                        <span class="progress-stat partially-complete">{{ partiallyCompleteCount }} partially complete</span>
                        <span class="progress-stat remaining">{{ remainingCount }} remaining</span>
                    </div>
                    <div class="problem-progress">
                        <div v-for="(problem, index) in problems" :key="problem.slug" 
                            :class="['progress-bar', 
                                { 'active': index === currentProblem },
                                { 'completed': getProblemStatus(problem.slug) === 'completed' },
                                { 'partially-complete': getProblemStatus(problem.slug) === 'partially_complete' },
                                { 'not-tried': getProblemStatus(problem.slug) === 'not-tried' }
                            ]" 
                            @click="setProblem(index)"
                            :title="getProblemTooltip(problem, index)">
                        </div>
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
                    <div class="section-label">Code Editor</div>
                    <Editor 
                        ref="entry" 
                        lang="python" 
                        mode="python" 
                        height="450px" 
                        width="100%" 
                        :value="solutionCode"
                        @update:value="updateSolutionCode"
                        :readOnly="true"
                        :showGutter="showLineNumbers"
                        :theme="currentTheme"
                        :key="`editor-${currentProblem}`"
                    />
                    <div class="editor-toolbar">
                        <div class="toolbar-options">
                            <button class="toolbar-btn" @click="copyCode" title="Copy code">
                                <span v-if="!codeCopied">📋</span>
                                <span v-else>✓</span>
                            </button>
                            <button class="toolbar-btn" @click="toggleLineNumbers" :title="showLineNumbers ? 'Hide line numbers' : 'Show line numbers'">
                                <span v-if="showLineNumbers">🔢</span>
                                <span v-else>➖</span>
                            </button>
                            <div class="theme-selector">
                                <select v-model="editorTheme" @change="updateTheme" class="theme-dropdown">
                                    <option value="dark">🌙 Dark</option>
                                    <option value="light">☀️ Light</option>
                                    <option value="monokai">🎨 Monokai</option>
                                    <option value="github">🐙 GitHub</option>
                                    <option value="solarized-dark">🌅 Solarized Dark</option>
                                    <option value="solarized-light">🌅 Solarized Light</option>
                                    <option value="dracula">🧛 Dracula</option>
                                    <option value="tomorrow-night">🌃 Tomorrow Night</option>
                                </select>
                            </div>
                        </div>
                        <div class="zoom-controls">
                            <button class="zoom-btn" @click="decreaseFontSize" :disabled="editorFontSize <= 12" title="Zoom out">
                                <span class="zoom-icon">−</span>
                            </button>
                            <span class="zoom-level">{{ Math.round((editorFontSize / 14) * 100) }}%</span>
                            <button class="zoom-btn" @click="increaseFontSize" :disabled="editorFontSize >= 24" title="Zoom in">
                                <span class="zoom-icon">+</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Submission section -->
                <div class="submission-section">
                    <div class="section-label">Describe the code here</div>
                    <span v-if="draftSaved" class="draft-indicator">✓ Draft saved</span>
                    <div class="prompt-editor-wrapper">
                        <Editor 
                            ref="prompt_entry" 
                            lang="text" 
                            mode="text" 
                            height="100px" 
                            width="100%"
                            v-bind:showGutter=false 
                            wrap="free" 
                        />
                    </div>
                    <button 
                        id="submitButton" 
                        class="submit-button" 
                        @click="submit"
                        :disabled="loading"
                    >
                        <span class="button-text" v-if="!loading">Submit Solution</span>
                        <div class="bouncing-dots" v-if="loading">
                            <span class="dot"></span>
                            <span class="dot"></span>
                            <span class="dot"></span>
                        </div>
                    </button>
                </div>
            </div>

            <!-- Right panel: Feedback -->
            <div class="right-panel">
                <Feedback 
                    :progress="promptCorrectness" 
                    :notches="6" 
                    :codeResults="codeResults" 
                    :testResults="testResults"
                    :comprehensionResults="comprehensionResults" 
                    :userPrompt="userPrompt"
                    title="Feedback" 
                />
            </div>
        </div>
    </div>
</template>

<script>
import Editor from '@/features/editor/Editor.vue'
import Feedback from "@/components/Feedback.vue"
import axios from 'axios'
import { useNotification } from '@/composables/useNotification'
import { useOptimisticProgress } from '@/composables/useOptimisticProgress'

export default {
    name: 'ProblemSet',
    components: {
        Editor,
        Feedback
    },
    props: {
        courseId: {
            type: String,
            default: null
        }
    },
    setup() {
        const { notify } = useNotification();
        const { updateProgress, getProgress, clearOptimistic } = useOptimisticProgress();
        return { notify, updateProgress, getProgress, clearOptimistic };
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
            
            /* Problem Status Tracking */
            problemStatuses: {},
            problemSetProgress: null,
            
            /* Editor Settings */
            editorFontSize: 14,
            codeCopied: false,
            showLineNumbers: true,
            editorTheme: 'dark',
            
            /* Draft Management */
            autoSaveInterval: null,
            draftSaved: false,
            
            /* Submission Data Cache - Simple 5min cache */
            submissionCache: new Map()
        };
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
            if (newIndex === this.currentProblem) return;
            
            try {
                // Save current draft before switching
                this.saveDraft();
                
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
                
                // Load draft after data is ready
                await this.$nextTick();
                this.loadDraft();
                
            } catch (error) {
                console.error('Navigation failed:', error);
                this.notify.error('Navigation Error', 'Failed to load problem data');
            }
        },
        
        async loadProblemData() {
            const problem = this.getCurrentProblem();
            if (!problem.slug) return;
            
            try {
                // Load submission data with caching
                const submissionData = await this.loadSubmissionData(problem.slug);
                
                // Apply submission data
                this.codeResults = submissionData.variations || [];
                this.testResults = submissionData.results || [];
                this.promptCorrectness = submissionData.passing_variations || 0;
                this.comprehensionResults = submissionData.feedback || '';
                this.userPrompt = submissionData.user_prompt || '';
                
                // Load draft for this problem
                await this.$nextTick();
                this.loadDraft();
                
            } catch (error) {
                console.error('Error loading problem data:', error);
                // Clear on error
                this.clearFeedbackData();
            }
        },
        
        async loadSubmissionData(problemSlug) {
            const cacheKey = `${this.$route.params.slug}_${problemSlug}`;
            
            // Check cache (5 minute expiry)
            if (this.submissionCache.has(cacheKey)) {
                const cached = this.submissionCache.get(cacheKey);
                if (Date.now() - cached.timestamp < 5 * 60 * 1000) {
                    return cached.data;
                }
            }
            
            try {
                const response = await axios.get(`/api/user/last-submission/${problemSlug}/`);
                const data = response.data;
                
                // Cache the response
                this.submissionCache.set(cacheKey, {
                    data,
                    timestamp: Date.now()
                });
                
                return data;
            } catch (error) {
                console.error('Error loading submission:', error);
                return {
                    has_submission: false,
                    variations: [],
                    results: [],
                    passing_variations: 0,
                    feedback: '',
                    user_prompt: ''
                };
            }
        },
        
        clearFeedbackData() {
            this.codeResults = [];
            this.testResults = [];
            this.promptCorrectness = 0;
            this.comprehensionResults = '';
            this.userPrompt = '';
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
            if (this.editorFontSize < 24) {
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
                console.error('Failed to copy code:', err);
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
        },
        
        async submit() {
            if (this.loading) return;
            
            this.loading = true;
            const currentProblemSlug = this.getCurrentProblem().slug;
            
            try {
                const promptText = this.$refs.prompt_entry.editor.getValue();
                
                if (!promptText || promptText.trim() === '') {
                    this.notify.warning('Please enter a description of what the function does.');
                    this.loading = false;
                    return;
                }
                
                // Optimistic update
                const rollback = this.updateProgress(currentProblemSlug, {
                    status: 'partially_complete',
                    score: null,
                    attempts: (this.problemStatuses[currentProblemSlug]?.attempts || 0) + 1
                });

                const submissionData = {
                    problem_slug: currentProblemSlug,
                    problem_set_slug: this.$route.params.slug,
                    prompt: promptText
                };
                
                // Include course_id if we're in a course context
                if (this.courseId) {
                    submissionData.course_id = this.courseId;
                }
                
                const response = await axios.post('/api/submit-eipl/', submissionData);

                const data = response.data;
                
                // Update feedback data
                this.codeResults = data.code_variations || data.variations || [];
                this.testResults = data.test_results || data.results || [];
                this.promptCorrectness = data.passing_variations || 0;
                this.userPrompt = promptText;
                
                // Update progress tracking
                this.problemStatuses[currentProblemSlug] = {
                    status: data.progress.is_completed ? 'completed' : 'partially_complete',
                    score: data.score,
                    attempts: data.progress.attempts
                };
                
                this.clearOptimistic(currentProblemSlug);
                
                // Update cache with new submission data including prompt
                const cacheKey = `${this.$route.params.slug}_${currentProblemSlug}`;
                this.submissionCache.set(cacheKey, {
                    data: {
                        has_submission: true,
                        variations: this.codeResults,
                        results: this.testResults,
                        passing_variations: this.promptCorrectness,
                        feedback: this.comprehensionResults,
                        user_prompt: promptText
                    },
                    timestamp: Date.now()
                });
                
                // Clear draft on success
                this.clearDraft();
                
                this.notify.success('Solution submitted successfully!', `Score: ${data.score}%`);

            } catch (error) {
                console.error('Error submitting code:', error);
                
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
            } finally {
                this.loading = false;
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
                console.error('Error fetching problem set:', error);
                this.notify.error('Load Error', 'Failed to load problem set.');
            } finally {
                this.isLoading = false;
            }
        },
        
        async loadProblemStatuses() {
            const problemSetSlug = this.$route.params.slug;
            
            try {
                const response = await axios.get(`/api/problem-sets/${problemSetSlug}/progress/`);
                const progressData = response.data.problems_progress || [];
                
                progressData.forEach(progress => {
                    this.problemStatuses[progress.problem_slug] = {
                        status: this.mapStatusFromAPI(progress.status, progress.best_score),
                        score: progress.best_score,
                        attempts: progress.attempts
                    };
                });
                
                if (response.data.problem_set) {
                    this.problemSetProgress = response.data.problem_set;
                }
                
            } catch (error) {
                console.error('Error loading progress data:', error);
            }
        },
        
        mapStatusFromAPI(apiStatus, score) {
            if (apiStatus === 'completed' || apiStatus === 'mastered') {
                return 'completed';
            } else if (apiStatus === 'not_started') {
                return 'not-tried';
            } else if (score > 0) {
                return 'partially_complete';
            } else {
                return 'not-tried';
            }
        },
        
        getProblemStatus(problemSlug) {
            const actualStatus = this.problemStatuses[problemSlug];
            const optimisticStatus = this.getProgress(problemSlug, actualStatus);
            return optimisticStatus?.status || 'not-tried';
        },
        
        getProblemTooltip(problem, index) {
            const status = this.problemStatuses[problem.slug];
            const problemName = problem.name || `Problem ${index + 1}`;
            
            if (!status || status.status === 'not-tried') {
                return `${problemName} - Not attempted`;
            } else if (status.status === 'partially_complete') {
                return `${problemName} - Partially Complete (Score: ${status.score}%)`;
            } else if (status.status === 'completed') {
                return `${problemName} - Completed (Score: ${status.score}%)`;
            }
            return problemName;
        },
        
        // Draft Management - Simplified
        saveDraft() {
            if (!this.$refs.prompt_entry || !this.$refs.prompt_entry.editor) return;
            
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
        },
        
        loadDraft() {
            if (!this.$refs.prompt_entry || !this.$refs.prompt_entry.editor) return;
            
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
        }
    },
    
    computed: {
        solutionCode() {
            return this.getCurrentProblem().solution || '';
        },
        
        completedCount() {
            return Object.values(this.problemStatuses).filter(s => s.status === 'completed').length;
        },
        
        partiallyCompleteCount() {
            return Object.values(this.problemStatuses).filter(s => s.status === 'partially_complete').length;
        },
        
        remainingCount() {
            return this.problems.length - this.completedCount - this.partiallyCompleteCount;
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

.progress-stat.partially-complete {
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
.progress-bar.not-tried {
    background: var(--color-bg-hover);
}

.progress-bar.partially-complete {
    background: var(--color-warning);
}

.progress-bar.completed {
    background: var(--color-success);
}

/* Active state */
.progress-bar.active {
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px var(--color-primary-gradient-start);
}

.progress-bar.active.not-tried {
    background: linear-gradient(90deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
}

.progress-bar.active.partially-complete {
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

/* Section Label Styling */
.section-label {
    text-align: center;
    padding: var(--spacing-sm) var(--spacing-lg);
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-text-muted);
    background: var(--color-bg-hover);
    border-bottom: 1px solid var(--color-bg-input);
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
    min-height: 300px;
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
    margin: var(--spacing-xl);
    margin-bottom: 0;
    border-radius: var(--radius-base);
    overflow: hidden;
    transition: var(--transition-base);
}

.prompt-editor-wrapper:hover {
    border-color: var(--color-primary-gradient-start);
}

.submission-section .submit-button {
    margin: var(--spacing-xl);
    margin-top: var(--spacing-lg);
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
.bouncing-dots {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: var(--spacing-sm);
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
