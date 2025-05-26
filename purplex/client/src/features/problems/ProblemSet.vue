<template>
    <div v-if="isLoading" class="loading-container">
        <div class="loading-message">Loading problem set...</div>
    </div>
    <div v-else-if="!problems || problems.length === 0" class="loading-container">
        <div class="loading-message">No problems found in this set.</div>
    </div>
    <div v-else class="problem-set-container">
        <!-- Problem navigation header -->
        <div class="problem-navigation">
            <div class="problem-selector">
                <button class="nav-button" @click="prevProblem">
                    <span class="arrow-left">‹</span>
                </button>
                <div class="problem-info">
                    <h3>{{ currentProblemData.name || `Problem ${currentProblem + 1}` }}</h3>
                    <div class="problem-progress">
                        <div v-for="(problem, index) in problems" :key="problem.qid" 
                            :class="['progress-dot', { 'active': index === currentProblem }]" 
                            @click="setProblem(index)"
                            :title="`Problem ${index + 1}`">
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
                    />
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
        getProblem() {
            if (!this.problems || this.problems.length === 0) {
                return { solution: '', qid: '' };
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

                /* Generating the five code snippets */
                const response = await axios.post('/api/generate/', {
                    prompt: this.$refs.prompt_entry.editor.getValue()
                });

                this.codeResults = response.data.code;


                /* Testing each o fthe code snippets */
                const newTestResults = [];
                for (let i = 0; i < this.codeResults.length; i++) {
                    const generated_code = this.codeResults[i];//.code;
                    const response = await axios.post('/api/test/', {
                        generated_code: generated_code,
                        qid: this.getProblem().qid,
                    });

                    const testResult = response.data;
                    console.log("Test result:", testResult);
                    newTestResults.push(testResult.test_results);
                }
                this.testResults = newTestResults;

            } catch (error) {
                console.error('Error submitting code:', error);
            } finally {
                this.loading = false;
            }
        },
        loadProblemSet() {
            const problemSetName = this.$route.params.name;
            this.isLoading = true;
            
            console.log(`Loading problem set: ${problemSetName}`);
            axios.get(`/api/problem-set/${problemSetName}`)
                .then(response => {
                    this.problemSet = response.data;
                    this.problems = response.data.problems || [];
                    console.log("Problems loaded:", this.problems);
                    
                    // If problems exist, update solution code
                    if (this.problems.length > 0) {
                        this.updateSolutionCode();
                    }
                    
                    this.isLoading = false;
                })
                .catch(error => {
                    console.error('Error fetching problem set:', error);
                    this.isLoading = false;
                });
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
            comprehensionResults: ''
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
        '$route.params.name': function(newName) {
            if (newName) {
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
    padding: var(--spacing-lg);
    background-color: var(--color-bg-input);
    border-radius: var(--radius-base);
    box-shadow: var(--shadow-sm);
}

.problem-set-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-height: 100vh;
    overflow: hidden;
}

/* Problem Navigation Header */
.problem-navigation {
    background-color: var(--color-bg-dark);
    padding: var(--spacing-base) var(--spacing-lg);
    border-bottom: 1px solid var(--color-bg-input);
}

.problem-selector {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-lg);
}

.nav-button {
    background-color: var(--color-bg-input);
    border: none;
    color: var(--color-text-primary);
    padding: var(--spacing-sm) calc(var(--spacing-base) + 1px);
    border-radius: var(--radius-xs);
    cursor: pointer;
    font-size: var(--spacing-lg);
    transition: background-color var(--transition-fast);
}

.nav-button:hover {
    background-color: var(--color-bg-border);
}

.arrow-left, .arrow-right {
    display: block;
}

.problem-info {
    text-align: center;
    min-width: 300px;
}

.problem-info h3 {
    margin: 0 0 var(--spacing-sm) 0;
    color: var(--color-text-primary);
}

.problem-progress {
    display: flex;
    justify-content: center;
    gap: var(--spacing-sm);
}

.progress-dot {
    width: 10px;
    height: 10px;
    border-radius: var(--radius-circle);
    background-color: var(--color-bg-disabled);
    cursor: pointer;
    transition: var(--transition-base);
}

.progress-dot:hover {
    background-color: var(--color-text-muted);
    transform: scale(1.2);
}

.progress-dot.active {
    background-color: var(--color-primary);
    transform: scale(1.3);
}

/* Main Workspace */
.workspace {
    display: flex;
    flex: 1;
    gap: var(--spacing-lg);
    padding: var(--spacing-lg);
    overflow: hidden;
}

.left-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
    overflow-y: auto;
    padding-right: var(--spacing-sm);
}

.right-panel {
    flex: 0 0 520px;
    overflow-y: auto;
}

/* Editor Section */
.editor-section {
    background-color: var(--color-bg-panel-light);
    border-radius: var(--radius-base);
    overflow: hidden;
}

.section-header {
    padding: var(--spacing-base) var(--spacing-lg);
    background-color: var(--color-bg-dark);
    border-bottom: 1px solid var(--color-bg-input);
}

.section-header h4 {
    margin: 0;
    color: var(--color-text-primary);
    font-size: var(--font-size-base);
}

.editor-hint {
    margin: var(--spacing-xs) 0 0 0;
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
}

/* Submission Section */
.submission-section {
    background-color: var(--color-bg-panel-light);
    border-radius: var(--radius-base);
    overflow: hidden;
}

.submission-section .section-header {
    background-color: var(--color-bg-dark);
    padding: var(--spacing-base) var(--spacing-lg);
    border-bottom: 1px solid var(--color-bg-input);
}

.submission-section .section-header h4 {
    margin: 0 0 var(--spacing-xs) 0;
    color: var(--color-text-primary);
    font-size: var(--font-size-base);
}

.prompt-hint {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
}

.prompt-editor-wrapper {
    padding: 0;
    background-color: var(--color-bg-hover);
    border: 1px solid var(--color-bg-input);
    margin: var(--spacing-lg);
    margin-bottom: 0;
    border-radius: var(--radius-xs);
    overflow: hidden;
}

.submission-section .submit-button {
    margin: var(--spacing-lg);
    margin-top: 0;
    width: calc(100% - calc(var(--spacing-lg) * 2));
}

.submit-button {
    width: 100%;
    margin-top: var(--spacing-base);
    padding: var(--spacing-md) calc(var(--spacing-lg) + 4px);
    background-color: var(--color-primary);
    color: var(--color-text-primary);
    border: none;
    border-radius: var(--radius-xs);
    font-size: var(--font-size-base);
    font-weight: 500;
    cursor: pointer;
    transition: background-color var(--transition-base);
}

.submit-button:hover {
    background-color: var(--color-primary-hover);
}

.submit-button:disabled {
    background-color: var(--color-bg-disabled);
    cursor: not-allowed;
}

/* Loading Animation */
.bouncing-dots {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: var(--spacing-xs);
}

.dot {
    width: 8px;
    height: 8px;
    background-color: var(--color-text-primary);
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
    }
    40% {
        transform: scale(1);
    }
}

/* Responsive Design */
@media (max-width: 1200px) {
    .workspace {
        flex-direction: column;
    }
    
    .right-panel {
        flex: 1;
        max-width: 100%;
    }
}
</style>
