<template>
    <div class="workspace">
        <div class="entryspace">
            <!-- Editor for the solution code -->
            <div class="entry">
                <Editor 
                    ref="entry" 
                    lang="python" 
                    mode="python" 
                    height="300px" 
                    width="500px" 
                    :value="solutionCode"
                    @update:value="updateSolutionCode" 
                />
                <div class="progress-bar">
                    <div v-for="(problem, index) in problems" :key="problem.qid" 
                        :class="['segment', { 'segment-active': index === currentProblem }]" 
                        :style="{ width: `${100 / problems.length}%` }"
                        @click="setProblem(index)">
                        <span class="segment-index"> Problem {{ index + 1 }}</span>
                    </div>
                </div>
            </div>

            <!-- Buttons to switch between problems -->
            <div class="buttons">
                <button @click="prevProblem">Prev</button>
                <div><b>Pick a problem</b></div>
                <button @click="nextProblem">Next</button>
            </div>

            <!-- Submission interface -->
            <div class="promptentry">
                <Editor ref="prompt_entry" lang="text" mode="text" height="50px" v-bind:showGutter=false wrap="free" />
            </div>
            <div class="submit-button-container">
                <button id="submitButton" class="submit-button" @click="submit">
                    <span class="button-text" v-if="!loading">Submit</span>
                    <div class="bouncing-dots" v-if="loading">
                        <span class="dot"></span>
                        <span class="dot"></span>
                        <span class="dot"></span>
                    </div>
                </button>
            </div>
        </div>
        <Feedback :progress="promptCorrectness" :notches=6 :codeResults="codeResults" :testResults="testResults"
            :comprehensionResults="comprehensionResults" title="Feedback" />
    </div>
</template>

<script>
import Editor from '@/features/editor/Editor.vue'
import Feedback from "@/components/Feedback.vue"

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
            return this.problems[this.currentProblem];
        },
        updateSolutionCode() {
            this.solutionCode = this.getProblem().solution;
            this.codeResults = [];
            this.testResults = [];
            this.promptCorrectness = 0;
        },
        async submit() {
            this.loading = true;

            try {

                /* Generating the five code snippets */
                const response = await fetch('http://localhost:8000/api/generate/', { // Update the URL to match your Django view
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        prompt: this.$refs.prompt_entry.editor.getValue()
                    })
                });

                const result = await response.json();
                this.codeResults = result.code;


                /* Testing each o fthe code snippets */
                const newTestResults = [];
                for (let i = 0; i < this.codeResults.length; i++) {
                    const generated_code = this.codeResults[i];//.code;
                    const response = await fetch('http://localhost:8000/api/test/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            generated_code: generated_code,
                            qid: this.getProblem().qid,
                        })
                    });

                    const testResult = await response.json();
                    console.log("Test result:", testResult);
                    newTestResults.push(testResult.test_results);
                }
                this.testResults = newTestResults;

            } catch (error) {
                console.error('Error submitting code:', error);
            } finally {
                this.loading = false;
            }
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
                const allPass = tests.every(test => test.pass);
                count += allPass ? 1 : 0;
            }
            return count;
        },
        solutionCode() {
            if (this.problems.length === 0) {
                return '';
            }
            return this.problems[this.currentProblem].solution;
        },
    },
    data() {
        return {
            problemSet: {},
            problems: [],

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
        const problemSetName = this.$route.params.name;
        fetch(`http://localhost:8000/api/problem-set/${problemSetName}`)
            .then(response => response.json())
            .then(data => {
                this.problemSet = data;
                this.problems = data.problems;
            });
    },
};
</script>
<style scoped>
.workspace {
    display: flex;
    justify-content: space-between;
    gap: 20px;
}

.entryspace {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.entry {
    display: flex;
    flex-direction: column;
    gap: 0px; /* Removed the gap between editor and progress bar */
}

.progress-bar {
    display: flex;
    margin: 0px;
}

.segment {
    height: 20px;
    border-radius: 5px;
    background-color: #333;
    margin: 0px;
    box-sizing: border-box;
    border: 2px solid transparent;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.3s, border-color 0.3s;
}

.segment:hover {
    background-color: #3333;
    cursor: pointer;
}

.segment-active {
    background-color: grey;
    border-color: grey;
}

.segment-passed {
    background-color: green;
}

.segment-label {
    position: absolute;
    top: -20px;
    font-size: 12px;
    color: white;
    font-weight: bold;
}

.segment-index {
    color: white;
    font-size: 16px;
}
</style>
