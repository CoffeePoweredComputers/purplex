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
        <Editor @update:value="updateSolutionCode" :value="currentSlideContents" height="150px" width="100%"
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
        // Handle case where tests might be undefined
        if (!tests || !Array.isArray(tests)) {
          return {
            content: code,
            correct: false,
            tests: []
          };
        }
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

<style scoped>
/* Main Container */
.feedback-container {
  display: flex;
  flex-direction: column;
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 520px;
  box-shadow: var(--shadow-md);
  border: 2px solid transparent;
  transition: var(--transition-base);
  overflow: hidden;
}

.feedback-container:hover {
  border-color: var(--color-bg-input);
}

/* Title Section */
.title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 2px solid var(--color-bg-input);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}


/* Thermometer Component */
.therm-container {
  display: flex;
  gap: var(--spacing-base);
  padding: var(--spacing-lg) var(--spacing-xl);
  background: var(--color-bg-panel);
}

.thermometer {
  width: 100%;
  height: 20px;
  display: flex;
  flex-direction: column;
}

.bar {
  width: 100%;
  height: 8px;
  background: var(--color-bg-hover);
  position: relative;
  border-radius: var(--radius-xs);
  overflow: hidden;
}

.progress {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  transition: width 1.5s ease;
  border-radius: var(--radius-xs);
}

.notches {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-xs);
}

.notch {
  height: 12px;
  width: 2px;
  background: var(--color-bg-border);
}

/* Carousel Section */
.carousel {
  padding: var(--spacing-lg);
  background: var(--color-bg-panel);
  border-bottom: 1px solid var(--color-bg-input);
}

/* Progress Bar */
.progress-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
}

.prev-btn,
.next-btn {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  border: none;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-base);
  cursor: pointer;
  font-weight: 600;
  transition: var(--transition-base);
}

.prev-btn:hover,
.next-btn:hover {
  background: var(--color-bg-border);
  transform: translateY(-1px);
}

.segment {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-circle);
  transition: var(--transition-base);
  cursor: pointer;
}

/* Accordion Styles */
.accordion {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
}

.accordion-item {
  border-radius: var(--radius-base);
  overflow: hidden;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  transition: var(--transition-base);
}

.accordion-item:hover {
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-sm);
}

.accordion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer;
  background: var(--color-bg-input);
  transition: var(--transition-base);
}

.accordion-header:hover {
  background: var(--color-bg-border);
}

.accordion-icon {
  display: flex;
  justify-content: center;
  align-items: center;
  transition: transform 0.3s ease;
  color: var(--color-text-primary);
}

.accordion-icon-rotate {
  transform: rotate(180deg);
}

.chevron-down {
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid var(--color-text-primary);
}

.accordion-body {
  padding: var(--spacing-lg);
  background: var(--color-bg-panel);
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Table Styles */
table {
  width: 100%;
  margin-bottom: var(--spacing-lg);
}

td {
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
}

td:first-child {
  font-weight: 600;
  color: var(--color-text-primary);
  width: 140px;
}

/* Code Styles */
code {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--font-size-sm);
  background: var(--color-bg-input);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  color: var(--color-primary-gradient-start);
}

/* PyTutor Button */
.pytutor-btn {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: none;
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-base);
  cursor: pointer;
  width: 100%;
  font-weight: 600;
  transition: var(--transition-base);
  box-shadow: var(--shadow-colored);
}

.pytutor-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.pytutor-btn::before {
  content: "🔍 ";
}

/* Empty State */
.collapse-container {
  background: var(--color-bg-panel);
  padding: var(--spacing-xxl);
  text-align: center;
}

.p-text {
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  padding: var(--spacing-xl);
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

/* Responsive Design */
@media (max-width: 768px) {
  .feedback-container {
    max-width: 100%;
  }
  
  .title {
    font-size: var(--font-size-base);
    padding: var(--spacing-md) var(--spacing-lg);
  }
  
  .accordion-header {
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: var(--font-size-sm);
  }
}
</style>
