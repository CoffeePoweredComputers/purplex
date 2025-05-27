<template>
    <div v-if="isLoading" class="loading-container">
        <div class="loading-message">Loading problem set...</div>
    </div>
    <div v-else-if="!problems || problems.length === 0" class="loading-container">
        <div class="loading-message">No problems found in this set.</div>
    </div>
    <div v-else class="problem-set-container">
        <div class="problem-navigation">
            <div class="problem-selector">
                <button class="nav-button" @click="prevProblem">
                    <span class="arrow-left">‹</span>
                </button>
                <div class="problem-info">
                    <div class="progress-summary">
                        <span class="progress-stat completed">{{ completedCount }} completed</span>
                        <span class="progress-stat attempted">{{ attemptedCount }} attempted</span>
                        <span class="progress-stat remaining">{{ remainingCount }} remaining</span>
                    </div>
                    <div class="problem-progress">
                        <div v-for="(problem, index) in problems" :key="problem.slug" 
                            :class="['progress-bar', 
                                { 'active': index === currentProblem },
                                { 'completed': getProblemStatus(problem.slug) === 'completed' },
                                { 'attempted': getProblemStatus(problem.slug) === 'attempted' },
                                { 'not-tried': getProblemStatus(problem.slug) === 'not-tried' }
                            ]" 
                            @click="setProblem(index)"
                            :title="getProblemTooltip(problem, index)">
                        </div>
                    </div>
                </div>
                <button class="nav-button" @click="nextProblem">
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
                        <h4>Code Editor</h4>
                        <p class="editor-hint">Analyze the code and understand what it does</p>
                    </div>
                    <Editor 
                        ref="entry" 
                        lang="python" 
                        mode="python" 
                        height="450px" 
                        width="100%" 
                        :value="solutionCode"
                        @update:value="updateSolutionCode"
                        :readOnly="true"
                        :key="editorKey"
                        :showGutter="showLineNumbers"
                        :theme="currentTheme"
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
                    <div class="section-header">
                        <h4>Describe what this function does</h4>
                        <p class="prompt-hint">Enter your understanding of the problem in the text area below</p>
                    </div>
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
                    <button id="submitButton" class="submit-button" @click="submit">
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
                    title="Test Results" 
                />
            </div>
        </div>
    </div>
</template>

<script>
import Editor from '@/features/editor/Editor.vue'
import Feedback from "@/components/Feedback.vue"
import axios from 'axios'

export default {
    name: 'ProblemSet',
    components: {
        Editor,
        Feedback
    },
    methods: {
        nextProblem() {
            this.currentProblem = (this.currentProblem + 1) % this.problems.length;
            this.updateSolutionCode();
        },
        prevProblem() {
            this.currentProblem = (this.currentProblem - 1 + this.problems.length) % this.problems.length;
            this.updateSolutionCode();
        },
        setProblem(index) {
            this.currentProblem = index;
            this.updateSolutionCode();
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
            // Force editor to update by changing key
            this.editorKey += 1;
            // Apply font size after editor re-renders
            this.$nextTick(() => {
                if (this.$refs.entry && this.$refs.entry.editor) {
                    this.$refs.entry.editor.setFontSize(this.editorFontSize);
                }
            });
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
            this.editorKey += 1; // Force re-render
        },
        updateTheme() {
            this.editorKey += 1; // Force re-render with new theme
        },
        getProblem() {
            if (!this.problems || this.problems.length === 0) {
                return { solution: '', slug: '' };
            }
            return this.problems[this.currentProblem];
        },
        updateSolutionCode() {
            if (this.problems && this.problems.length > 0) {
                this.solutionCode = this.getProblem().solution;
                this.codeResults = [];
                this.testResults = [];
                this.promptCorrectness = 0;
            }
        },
        async submit() {
            this.loading = true;

            try {
                const promptText = this.$refs.prompt_entry.editor.getValue();
                
                // Check if prompt is empty
                if (!promptText || promptText.trim() === '') {
                    alert('Please enter a description of what the function does.');
                    this.loading = false;
                    return;
                }

                /* Generating the five code snippets */
                const response = await axios.post('/api/generate/', {
                    prompt: promptText
                });

                this.codeResults = response.data.code;


                /* Testing each of the code snippets */
                const newTestResults = [];
                for (let i = 0; i < this.codeResults.length; i++) {
                    const generated_code = this.codeResults[i];
                    const response = await axios.post('/api/test-solution/', {
                        user_code: generated_code,
                        problem_slug: this.getProblem().slug,
                    });

                    const testResult = response.data;
                    console.log("Test result:", testResult);
                    newTestResults.push(testResult.test_results);
                }
                this.testResults = newTestResults;
                
                // Update problem status after submission
                const currentProblemSlug = this.getProblem().slug;
                const score = this.calculateScore(newTestResults);
                this.problemStatuses[currentProblemSlug] = {
                    status: score === 100 ? 'completed' : 'attempted',
                    score: score
                };

            } catch (error) {
                console.error('Error submitting code:', error);
                
                // Show more detailed error message
                if (error.response) {
                    // Server responded with error
                    if (error.response.status === 500) {
                        alert('Server error: The AI service might be unavailable or the OpenAI API key might be missing. Please contact the administrator.');
                    } else if (error.response.status === 401) {
                        alert('Authentication error: Please log in again.');
                    } else if (error.response.status === 400) {
                        alert('Invalid request: ' + (error.response.data.error || 'Please check your input.'));
                    } else {
                        alert('Error: ' + (error.response.data.error || 'An unknown error occurred.'));
                    }
                } else if (error.request) {
                    // Request made but no response
                    alert('Network error: Unable to reach the server. Please check your connection.');
                } else {
                    // Something else happened
                    alert('Error: ' + error.message);
                }
            } finally {
                this.loading = false;
            }
        },
        
        calculateScore(testResults) {
            // Calculate percentage score based on test results
            if (!testResults || testResults.length === 0) return 0;
            
            let totalTests = 0;
            let passedTests = 0;
            
            testResults.forEach(result => {
                if (result && Array.isArray(result)) {
                    totalTests += result.length;
                    passedTests += result.filter(test => test.pass).length;
                }
            });
            
            return totalTests > 0 ? Math.round((passedTests / totalTests) * 100) : 0;
        },
        loadProblemSet() {
            const problemSetSlug = this.$route.params.slug;
            this.isLoading = true;
            
            console.log(`Loading problem set: ${problemSetSlug}`);
            axios.get(`/api/problem-sets/${problemSetSlug}`)
                .then(response => {
                    this.problemSet = response.data;
                    
                    // Extract problems from problems_detail array
                    if (response.data.problems_detail && Array.isArray(response.data.problems_detail)) {
                        // problems_detail contains objects with { problem: {...}, order: n }
                        this.problems = response.data.problems_detail.map(pd => pd.problem);
                    } else if (response.data.problems && Array.isArray(response.data.problems)) {
                        // Fallback to direct problems array if it exists
                        this.problems = response.data.problems;
                    } else {
                        this.problems = [];
                    }
                    
                    console.log("Problems loaded:", this.problems);
                    
                    // Load user's submission history for these problems
                    this.loadProblemStatuses();
                    
                    // If problems exist, update solution code
                    if (this.problems.length > 0) {
                        this.updateSolutionCode();
                        // Set initial font size
                        this.$nextTick(() => {
                            if (this.$refs.entry && this.$refs.entry.editor) {
                                this.$refs.entry.editor.setFontSize(this.editorFontSize);
                            }
                        });
                    }
                    
                    this.isLoading = false;
                })
                .catch(error => {
                    console.error('Error fetching problem set:', error);
                    this.isLoading = false;
                });
        },
        
        loadProblemStatuses() {
            // TODO: Replace with actual API call to get user's submission history
            // Example: axios.get('/api/user/submissions/')
            // For now, using mock data to demonstrate the UI
            
            // Mock data - remove when API is available
            this.problems.forEach((problem, index) => {
                // Simulate different statuses for demo
                if (index === 0) {
                    this.problemStatuses[problem.slug] = { status: 'completed', score: 100 };
                } else if (index === 1) {
                    this.problemStatuses[problem.slug] = { status: 'attempted', score: 75 };
                } else {
                    this.problemStatuses[problem.slug] = { status: 'not-tried', score: 0 };
                }
            });
        },
        
        getProblemStatus(problemSlug) {
            return this.problemStatuses[problemSlug]?.status || 'not-tried';
        },
        
        getProblemTooltip(problem, index) {
            const status = this.problemStatuses[problem.slug];
            const problemName = problem.name || `Problem ${index + 1}`;
            
            if (!status || status.status === 'not-tried') {
                return `${problemName} - Not attempted`;
            } else if (status.status === 'attempted') {
                return `${problemName} - Attempted (Score: ${status.score}%)`;
            } else if (status.status === 'completed') {
                return `${problemName} - Completed (Score: ${status.score}%)`;
            }
            return problemName;
        }

    },
    computed: {
        numPassed() {
            if (this.testResults.length == 0) {
                return 0;
            }
            let count = 0;
            for (let i = 0; i < this.testResults.length; i++) {
                const tests = this.testResults[i];
                console.log("THESE ARE THE TESTS:", tests);
                const allPass = tests && tests.every(test => test.pass);
                count += allPass ? 1 : 0;
            }
            return count;
        },
        solutionCode() {
            if (!this.problems || this.problems.length === 0) {
                return '';
            }
            return this.problems[this.currentProblem].solution;
        },
        currentProblemData() {
            if (!this.problems || this.problems.length === 0) {
                return {};
            }
            return this.problems[this.currentProblem];
        },
        
        completedCount() {
            return Object.values(this.problemStatuses).filter(s => s.status === 'completed').length;
        },
        
        attemptedCount() {
            return Object.values(this.problemStatuses).filter(s => s.status === 'attempted').length;
        },
        
        remainingCount() {
            return this.problems.length - this.completedCount - this.attemptedCount;
        },
        currentTheme() {
            // Map our theme names to ACE editor theme names
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
    data() {
        return {
            problemSet: {},
            problems: [],
            isLoading: true, // Loading state for the initial data fetch

            /* State Management */
            currentProblem: 0,
            loading: false,

            /* Feedback */
            codeResults: [],
            testResults: [],

            /* Comprehension Results */
            comprehensionResults: '',
            
            /* Problem Status Tracking */
            problemStatuses: {}, // Will store { problemId: { status: 'completed'|'attempted'|'not-tried', score: number } }
            
            /* Editor Settings */
            editorFontSize: 14,
            editorKey: 0,
            codeCopied: false,
            showLineNumbers: true,
            editorTheme: 'dark'
        };
    },
    created() {
        this.loadProblemSet();
    },
    
    // When this component is activated (user navigates back to it)
    activated() {
        this.loadProblemSet();
    },
    
    // Watch for route changes in case user navigates between different problem sets
    watch: {
        '$route.params.slug': function(newSlug) {
            if (newSlug) {
                this.loadProblemSet();
            }
        }
    },
};
</script>
<style scoped>
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
    font-weight: 500;
    transition: var(--transition-base);
    display: flex;
    align-items: center;
    justify-content: center;
}

.nav-button:hover {
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
    font-weight: 500;
    padding: 2px var(--spacing-sm);
    border-radius: var(--radius-xl);
    background: var(--color-bg-hover);
    border: 1px solid var(--color-bg-border);
}

.progress-stat.completed {
    color: #10b981;
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.3);
}

.progress-stat.attempted {
    color: #ff9f43;
    background: rgba(255, 159, 67, 0.1);
    border-color: rgba(255, 159, 67, 0.3);
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

.progress-bar.attempted {
    background: #ff9f43;
}

.progress-bar.completed {
    background: #10b981;
}

/* Active state - using outline instead of height change */
.progress-bar.active {
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px var(--color-primary-gradient-start);
}

.progress-bar.active.not-tried {
    background: linear-gradient(90deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
}

.progress-bar.active.attempted {
    background: linear-gradient(90deg, #ff9f43 0%, #ff7a00 100%);
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px #ff7a00;
}

.progress-bar.active.completed {
    background: linear-gradient(90deg, #10b981 0%, #059669 100%);
    box-shadow: 0 0 0 2px var(--color-bg-panel), 0 0 0 4px #059669;
}

/* Hover effects - only change opacity/brightness */
.progress-bar:hover {
    opacity: 0.8;
}

.progress-bar.not-tried:hover {
    background: var(--color-bg-input);
}

.progress-bar.attempted:hover {
    opacity: 0.8;
}

.progress-bar.completed:hover {
    opacity: 0.8;
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
    flex: 1;
    min-height: 0;
}

.editor-section:hover {
    border-color: var(--color-bg-input);
}

.section-header {
    padding: var(--spacing-lg) var(--spacing-xl);
    background: var(--color-bg-hover);
    border-bottom: 2px solid var(--color-bg-input);
    flex-shrink: 0;
}

.section-header h4 {
    margin: 0;
    color: var(--color-text-primary);
    font-size: var(--font-size-md);
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
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
    font-weight: 500;
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


.editor-hint {
    margin: var(--spacing-xs) 0 0 0;
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
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
}

.submission-section:hover {
    border-color: var(--color-bg-input);
}

.submission-section .section-header {
    background: var(--color-bg-hover);
    padding: var(--spacing-lg) var(--spacing-xl);
    border-bottom: 2px solid var(--color-bg-input);
}

.submission-section .section-header h4 {
    margin: 0 0 var(--spacing-xs) 0;
    color: var(--color-text-primary);
    font-size: var(--font-size-md);
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}


.prompt-hint {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
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
