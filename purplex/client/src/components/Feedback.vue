<template>
  <div class="feedback-container">

    <div class="title">{{ title }}</div>

    <!-- The Thermometer -->
    <div class="therm-container">
      <div class="thermometer">
        <div class="bar">
          <div class="progress" :style="{ width: ((100 / (notches - 1)) * progress) + '%' }"></div>
        </div>
        <div class="notches">
          <div v-for="notch in notches" :key="notch" class="notch"></div>
        </div>
      </div>
    </div>
    <div v-if="slides.length > 0">
      <div class="carousel">
        <Editor @update:value="updateSolutionCode" :value="currentSlideContents" height="150px" width="500px"
          :highlightMarkers="currentComprehensionResult" />
      </div>

      <!-- Test Case Results Accordion -->
      <div class="accordion">
        <div v-if="slides.length > 0">
          <div v-for="(test, i) in slides[currentSlide].tests" :key="test.expected_output" class="accordion-item">
            <div class="accordion-header" @click="toggleAccordion(i)">
              <div>
                <span v-if="test.pass" :style="{ color: 'red', textAlign: 'left', paddingRight: '5px' }">✅</span>
                <span v-else :style="{ color: 'red', textAlign: 'left', paddingRight: '5px' }">❌</span>
                <b>Test Case {{ i + 1 }} : <code>{{ test.function_call }} == {{ test.expected_output }}</code></b>
              </div>
              <div class="accordion-icon" :class="{ 'accordion-icon-rotate': activeAccordion === i }">
                <i class="chevron-down"></i>
              </div>
            </div>
            <div v-show="activeAccordion === i" class="accordion-body">
              <table>
              <tr>
                <td><b>Function Call</b></td>
                <td>{{ test.function_call }}</td>
              </tr>
              <tr>
                <td><b>Expected Result</b></td>
                <td>{{ test.expected_output }}</td>
              </tr>
              <tr>
                <td><b>Actual Result</b></td>
                <td>{{ test.actual_output }}</td>
              </tr>
              </table>

              <button class="pytutor-btn" @click="openPyTutor(test)">Open in Python Tutor</button>
              <PyTutorModal :isVisible="showModal" :pythonTutorUrl="pythonTutorUrl" @close="showModal = false" />

            </div>
          </div>
        </div>
      </div>

      <!-- The Dots Clickthrough Thing -->
      <div class="progress-bar">
        <button @click="prevSlide" class="prev-btn">Prev</button>
        <div v-for="segment in slides.length" :key="segment" class="segment" :style="{
          backgroundColor: (slides[segment - 1].correct ? 'purple' : 'white'),
          borderRadius: (currentSlide === segment - 1 ? '0' : '50%'),
          border: (currentSlide === segment - 1 ? '2px solid black' : '2px solid #191919'),
          transition: 'border-radius 0.75s ease',
        }">
        </div>
        <button @click="nextSlide" class="next-btn">Next</button>
      </div>
    </div>

    <!-- If There Be No Feedback to Be Had -->
    <div v-else>
      <div class="collapse-container">
        <div class="p-text">Submit a prompt in order to start getting feedback!</div>
      </div>
    </div>
  </div>

</template>

<script>
import Editor from '@/features/editor/Editor.vue';
import PyTutorModal from '../modals/PyTutorModal.vue'; 

export default {
  components: { 
    Editor,
    PyTutorModal
  },
  props: {
    progress: {
      type: Number,
      default: 0,
    },
    notches: {
      type: Number,
      default: 10,
    },
    title: {
      type: String,
      default: '',
    },
    feedback: {
      type: String,
      default: '',
    },
    codeResults: {
      type: Array,
      default: () => [],
    },
    testResults: {
      type: Array,
      default: () => [],
    },
    solutionCode: {
      type: String,
      default: '',
    },
    comprehensionResults: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      showModal: false,
      collapsed: true,
      collapseHeight: 0,
      currentSlide: 0,
      currentSlideContents: "",
      currentComprehensionResult: 0,
      currentComprehensionResultContent: [],
      activeAccordion: -1,
    };
  },
  mounted() {
    this.updateSolutionCode();
  },
  watch: {
    slides: {
      handler() {
        this.updateSolutionCode();
      },
      deep: true,
    },
  },
  computed: {
    slides() {
      var slideResults = this.codeResults.map((code, index) => {
        const tests = this.testResults[index];
        const passing = tests.every(test => test.pass);
        return {
          content: code,
          correct: passing,
          tests: tests
        };
      });
      console.log("SLIDES", slideResults);
      return slideResults;
    },
    progress() {
      if (this.slides.length === 0) {
        return 0;
      }
      var allPass = this.slides.filter(slide => 
        slide.tests.every(test => test.pass)
      ).length;

      return allPass;
    },
  },
  methods: {
    toggleCollapse() {
      this.collapsed = !this.collapsed;
    },
    updateSolutionCode() {
      console.log("UPDATING SOLUTION CODE")
      console.log(this.currentSlide);
      if (this.slides.length === 0) {
        this.currentSlideContents = "";
        //this.currentComprehensionResultContent = [];
      } else {
        this.currentSlideContents = this.slides[this.currentSlide].content;
        //this.currentComprehensionResult = this.comprehensionResults[0];
        console.log(this.currentComprehensionResult);
      }
    },
    nextSlide() {
      this.currentSlide = (this.currentSlide + 1) % this.slides.length;
      this.updateSolutionCode();
    },
    prevSlide() {
      this.currentSlide = this.currentSlide === 0 ? this.slides.length - 1 : this.currentSlide - 1;
      this.updateSolutionCode();
    },
    toggleAccordion(index) {
      this.activeAccordion = this.activeAccordion === index ? -1 : index;
    },
    openPyTutor(testCase) {
      const code = this.slides[this.currentSlide].content + '\n' + testCase.function_call;
      const url = `https://pythontutor.com/render.html#code=${encodeURIComponent(code)}&cumulative=false&curInstr=0&heapPrimitives=nevernest&mode=display&origin=opt-frontend.js&py=3&rawInputLstJSON=%5B%5D&textReferences=false`;
      this.pythonTutorUrl = url;
      this.showModal = true;
    },
  },
};
</script>

<style>
/*
* Thermometer Component Styles
*/
.thermometer {
  width: 100%;
  height: 20px;
  display: flex;
  flex-direction: column;
  margin-top: 5px;
}

.bar {
  width: 100%;
  height: 5px;
  background-color: #ddd;
  position: relative;
}

.progress {
  height: 100%;
  background-color: #800080;
  transition: 1.5s;
}

.notches {
  display: flex;
  justify-content: space-between;
}

.notch {
  height: 10px;
  width: 2px;
  margin-top: 2px;
  background-color: #888;
}

.feedback-container {
  display: flex;
  flex-direction: column;
  border-radius: 5px;
  width: 500px;
}

.collapse-container {
  background-color: dark grey;
  transform-origin: top;
  overflow: hidden;
  border-bottom-left-radius: 5px;
  border-bottom-right-radius: 5px;
  white-space: pre-wrap;
  text-align: left;
}

.title {
  font-weight: bold;
  background-color: #1f1f1f;
  padding: 0.5rem;
}

.p-text {
  background-color: #1f1f1f;
  padding: 0.5rem;
}


.therm-container {
  display: flex;
  gap: 1rem;
  padding-right: 1rem;
  padding-left: 1rem;
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
  background-color: #191919;
}


/*
* Feedback Component Styles
*/
.feedback-pane {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-top: 20px;
}

.carousel-wrapper {
  display: flex;
  height: 200px;
}

.slide {
  flex-shrink: 0;
}

.hide {
  display: none;
}

.prev-btn,
.next-btn {
  color: white;
  border: none;
  cursor: pointer;
  position: relative;
}

.progress-bar {
  position: relative;
  display: flex;
  justify-content: center;
  margin-top: 10px;
  margin-bottom: 0px;
}

.segment {
  position: relative;
  width: 10px;
  height: 10px;
  margin-top: 15px;
  margin-right: 10px;
  margin-left: 10px;
  border-radius: 50%;
}

.test-cases {
  display: flex;
  flex-direction: column;
  margin-left: 2px;
}

.test-title {
  padding: 5px;
  font-weight: bold;
  background-color: #191919;
}

.test-cases {
  display: flex;
  flex-direction: column;
  margin-top: 10px;
}

.accordion {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.accordion-icon {
  display: flex;
  justify-content: center;
  align-items: center;
  transition: 0.5s ease-in-out;
  color: white;
}

.fa-chevron-down {
  font-size: 1rem;
}

.fas {
  font-size: 1rem;
}

.accordion-icon-rotate {
  transform: rotate(180deg);
}

.accordion-item {
  border-radius: 5px;
}

.accordion-header {
  display: flex;
  background-color: #191919;
  justify-content: space-between;
  padding: 10px;
  cursor: pointer;
}

.accordion-body {
  padding: 10px;
}

.accordion-body div {
  margin-top: 5px;
  transition: 0.5 ease-in-out;
}

.accordion-body div:first-child {
  margin-top: 0;
}

code {
  font: optional;
}

table {
  width: 100%;
}

td {
  border-bottom: 1px solid #191919;
  text-align: left;
}

.pytutor-btn {
  background-color: #191919;
  color: white;
  border: none;
  padding: 5px;
  cursor: pointer;
  width: 100%;
}

.chevron-down {
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 5px solid white;
}

</style>
