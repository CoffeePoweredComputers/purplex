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
            :problem-slug="problemSlug"
            :course-id="courseId"
            :problem-set-slug="problemSetSlug"
            :current-attempts="currentAttempts"
            @hint-used="onHintUsed"
          />
        </div>
        <Editor
          ref="entry"
          lang="python"
          mode="python"
          height="300px"
          width="500px"
          :value="solutionCode"
          @update:value="updateSolutionCode"
        />
      </div>

      <!-- Buttons to switch between problems -->
      <div class="buttons">
        <button @click="decrementProblem">
          Left
        </button>
        <div><b>Pick a problem</b></div>
        <button @click="incrementProblem">
          Right
        </button>
      </div>

      <!-- Submission interface -->
      <div class="promptentry">
        <Editor
          ref="prompt_entry"
          lang="text"
          mode="text"
          height="50px"
          :show-gutter="false"
          wrap="free"
        />
      </div>
      <div class="submit-button-container">
        <button
          id="submitButton"
          class="submit-button"
          @click="getResults"
        >
          <span
            v-if="!loading"
            class="button-text"
          >Submit</span>
          <div
            v-if="loading"
            class="bouncing-dots"
          >
            <span class="dot" />
            <span class="dot" />
            <span class="dot" />
          </div>
        </button>
      </div>
    </div>
    <Feedback
      :progress="promptCorrectness"
      :notches="6"
      :codes="codeResults"
      :test-results="testResults"
      :comprehension-results="comprehensionResults"
      title="Feedback"
    />
  </div>
</template>

<script lang="ts">

import { defineComponent, PropType } from 'vue'
import Editor from './components/Editor.vue'
import Feedback from "./components/Feedback.vue"
import HintButton from "./HintButton.vue"

export default defineComponent({
    components: {
        Editor,
        Feedback,
        HintButton
    },
    props: {
        solutionCode: {
            type: String as PropType<string>,
            default: ''
        },
        codeResults: {
            type: Array as PropType<any[]>,
            default: () => []
        },
        testResults: {
            type: Array as PropType<any[]>,
            default: () => []
        },
        promptCorrectness: {
            type: Number as PropType<number>,
            default: 0
        },
        comprehensionResults: {
            type: Array as PropType<any[]>,
            default: () => []
        },
        loading: {
            type: Boolean as PropType<boolean>,
            default: false
        },
        problemIndex: {
            type: Number as PropType<number>,
            default: 0
        },
        problemSlug: {
            type: String as PropType<string>,
            default: ''
        },
        courseId: {
            type: String as PropType<string>,
            default: ''
        },
        problemSetSlug: {
            type: String as PropType<string>,
            default: ''
        },
        currentAttempts: {
            type: Number as PropType<number>,
            default: 0
        }
    },
    methods: {
        updateSolutionCode(): void {
            this.$emit('update-solution-code');
        },
        incrementProblem(): void {
            this.$emit('increment-problem');
        },
        decrementProblem(): void {
            this.$emit('decrement-problem');
        },
        async getResults(): Promise<void> {
            this.$emit('get-results');
        },
        onHintUsed(hintData: any): void {
            this.$emit('hint-used', hintData);
        }
    }
})
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
