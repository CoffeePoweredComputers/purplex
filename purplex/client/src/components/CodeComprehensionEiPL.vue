<!-- EiPLInterface.vue -->
<template>
    <div class="workspace">
        <div class="entryspace">
            <!-- Editor for the solution code -->
            <div class="entry">
                <div class="editor-header">
                    <h3>Code Editor</h3>
                    <HintButton 
                        v-if="problemSlug"
                        :problemSlug="problemSlug"
                        :courseId="courseId"
                        :problemSetSlug="problemSetSlug"
                        :currentAttempts="currentAttempts"
                        @hint-used="onHintUsed"
                    />
                </div>
                <Editor ref="entry" lang="python" mode="python" height="300px" width="500px" :value="solutionCode"
                    @update:value="updateSolutionCode" />
            </div>

            <!-- Buttons to switch between problems -->
            <div class="buttons">
                <button @click="decrementProblem">Left</button>
                <div><b>Pick a problem</b></div>
                <button @click="incrementProblem">Right</button>
            </div>

            <!-- Submission interface -->
            <div class="promptentry">
                <Editor ref="prompt_entry" lang="text" mode="text" height="50px" v-bind:showGutter=false wrap="free" />
            </div>
            <div class="submit-button-container">
                <button id="submitButton" class="submit-button" @click="getResults">
                    <span class="button-text" v-if="!loading">Submit</span>
                    <div class="bouncing-dots" v-if="loading">
                        <span class="dot"></span>
                        <span class="dot"></span>
                        <span class="dot"></span>
                    </div>
                </button>
            </div>
        </div>
        <Feedback :progress="promptCorrectness" :notches=6 :codes="codeResults" :testResults="testResults"
            :comprehensionResults="comprehensionResults" title="Feedback" />
    </div>
</template>

<script>

import Editor from './components/Editor.vue'
import Feedback from "./components/Feedback.vue"
import HintButton from "./HintButton.vue"

export default {
    components: {
        Editor,
        Feedback,
        HintButton
    },
    props: {
        solutionCode: String,
        codeResults: Array,
        testResults: Array,
        promptCorrectness: Number,
        comprehensionResults: Array,
        loading: Boolean,
        problemIndex: Number,
        problemSlug: String,
        courseId: String,
        problemSetSlug: String,
        currentAttempts: {
            type: Number,
            default: 0
        }
    },
    methods: {
        updateSolutionCode: function () {
            this.$emit('update-solution-code');
        },
        incrementProblem: function () {
            this.$emit('increment-problem');
        },
        decrementProblem: function () {
            this.$emit('decrement-problem');
        },
        getResults: async function () {
            this.$emit('get-results');
        },
        onHintUsed: function (hintData) {
            this.$emit('hint-used', hintData);
        }
    }
}
</script>

<style scoped>
.editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px;
    background: #f5f5f5;
    border-bottom: 1px solid #ddd;
}

.editor-header h3 {
    margin: 0;
    font-size: 16px;
    color: #333;
}
</style>
