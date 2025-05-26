<template>
  <div class="about-page">
    <!-- Introduction Section -->
    <div class="intro-section">
      <div class="intro-content">
        <h2 class="section-title">Our Mission</h2>
        <p class="intro-text">
          Purplex is a cutting-edge research project designed to support the development and evaluation of natural language programming activities. 
          Our goal is to equip students with the essential skills needed for successful Human-AI collaborative coding in an increasingly AI-driven world.
        </p>
        
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">🤖</div>
            <h3>AI-Powered Learning</h3>
            <p>Leverage advanced AI to understand and practice code comprehension</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">📝</div>
            <h3>Natural Language</h3>
            <p>Explain code functionality in plain English to develop clear communication skills</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <h3>Adaptive Practice</h3>
            <p>Personalized problem sets that adapt to your learning pace</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Research Section -->
    <div class="research-section">
      <h2 class="section-title">Research Publications</h2>
      <p class="section-subtitle">
        Explore the academic research behind Purplex and its impact on CS education
      </p>
      
      <div class="carousel-container">
        <button @click="prevSlide" class="carousel-button prev" :disabled="currentSlide === 0">
          <span class="carousel-arrow">‹</span>
        </button>
        
        <div class="publications-carousel">
          <div class="carousel-track" :style="{ transform: `translateX(-${currentSlide * 100}%)` }">
            <div v-for="(slide, slideIndex) in publicationSlides" :key="slideIndex" class="carousel-slide">
              <article v-for="paper in slide" :key="paper.title" class="publication-card">
                <div class="publication-header">
                  <h3 class="publication-title">{{ paper.title }}</h3>
                </div>
                
                <div class="publication-authors">{{ paper.authors }}</div>
                <div class="publication-venue-wrapper">
                  <span class="publication-venue">{{ paper.venue }}</span>
                  <span class="publication-year">{{ paper.year }}</span>
                </div>
                
                <div class="publication-actions">
                  <a v-if="paper.url" :href="paper.url" target="_blank" class="action-button primary">
                    <span class="button-icon">📄</span>
                    View Paper
                  </a>
                  <button @click="copyBibTeX(paper.bibtex, publications.indexOf(paper))" class="action-button secondary">
                    <span class="button-icon">📋</span>
                    {{ paper.showCopied ? 'Copied!' : 'Copy BibTeX' }}
                  </button>
                </div>
              </article>
            </div>
          </div>
        </div>
        
        <button @click="nextSlide" class="carousel-button next" :disabled="currentSlide === publicationSlides.length - 1">
          <span class="carousel-arrow">›</span>
        </button>
      </div>
      
      <div class="carousel-dots">
        <button 
          v-for="(slide, index) in publicationSlides" 
          :key="index"
          @click="currentSlide = index"
          :class="['dot', { active: currentSlide === index }]"
        ></button>
      </div>
    </div>

    <!-- Developer Banner -->
    <div class="developer-banner">
      <div class="developer-content">
        <span class="created-by">Created by</span>
        <span class="developer-name">David H. Smith IV</span>
        <span class="separator">•</span>
        <span class="developer-role">Lead Researcher & Developer</span>
        <span class="separator">•</span>
        <a href="https://scholar.google.com/citations?user=hpe-z9YAAAAJ" target="_blank" class="scholar-link">
          View Google Scholar →
        </a>
      </div>
    </div>
  </div>
</template>

<script>
import { reactive } from 'vue';

export default {
  name: 'About',
  data() {
    return {
      currentSlide: 0
    };
  },
  setup() {
    const publications = reactive([
      {
        title: "Code Generation Based Grading: Evaluating an Auto-grading Mechanism for 'Explain-in-Plain-English' Questions",
        authors: "DH Smith IV and C Zilles",
        venue: "ACM ITiCSE",
        year: 2024,
        url: "https://dl.acm.org/doi/abs/10.1145/3649217.3653582",
        showCopied: false,
        bibtex: `@incollection{smith2024code,
  title={Code Generation Based Grading: Evaluating an Auto-grading Mechanism for" Explain-in-Plain-English" Questions},
  author={Smith IV, David H and Zilles, Craig},
  booktitle={Proceedings of the 2024 on Innovation and Technology in Computer Science Education V. 1},
  pages={171--177},
  year={2024}
}`
      },
      {
        title: "Prompting for Comprehension: Exploring the Intersection of Explain in Plain English Questions and Prompt Writing",
        authors: "DH Smith IV, P Denny, M Fowler, and C Zilles",
        venue: "ACM Learning@Scale",
        year: 2024,
        url: "https://dl.acm.org/doi/pdf/10.1145/3657604.3662039",
        showCopied: false,
        bibtex: `@inproceedings{smith2024prompting,
  title={Prompting for comprehension: Exploring the intersection of explain in plain english questions and prompt writing},
  author={Smith IV, David H and Denny, Paul and Fowler, Max},
  booktitle={Proceedings of the Eleventh ACM Conference on Learning@ Scale},
  pages={39--50},
  year={2024}
}`
      },
      {
        title: "Integrating Natural Language Prompting Tasks in Introductory Programming Courses",
        authors: "C Kerslake, P Denny, DH Smith IV, J Prather, J Leinonen, A Luxton-Reilly, S MacNeil",
        venue: "ACM SIGCSE Virtual",
        year: 2024,
        url: "https://dl.acm.org/doi/pdf/10.1145/3657604.3662039",
        showCopied: false,
        bibtex: `@inproceedings{smith2024prompting,
  title={Prompting for comprehension: Exploring the intersection of explain in plain english questions and prompt writing},
  author={Smith IV, David H and Denny, Paul and Fowler, Max},
  booktitle={Proceedings of the Eleventh ACM Conference on Learning@ Scale},
  pages={39--50},
  year={2024}
}`
      },
      {
        title: "Explain in Plain Language Questions with Indic Languages: Drawbacks, Affordances, and Opportunities",
        authors: "DH Smith IV, V Kumar, P Denny",
        venue: "ACM India: COMPUTE 2024",
        year: 2024,
        url: "https://arxiv.org/pdf/2409.20297",
        showCopied: false,
        bibtex: `@article{smith2024explain,
  title={Explain in Plain Language Questions with Indic Languages: Drawbacks, Affordances, and Opportunities},
  author={Smith IV, David H and Kumar, Viraj and Denny, Paul},
  journal={arXiv preprint arXiv:2409.20297},
  year={2024}
}`
      }
    ]);

    const copyBibTeX = (bibtex, index) => {
      navigator.clipboard.writeText(bibtex);
      
      // Reset all copied messages
      publications.forEach(paper => {
        paper.showCopied = false;
      });
      
      // Show copied message for this paper
      publications[index].showCopied = true;
      setTimeout(() => {
        publications[index].showCopied = false;
      }, 2000);
    };

    return {
      publications,
      copyBibTeX
    };
  },
  computed: {
    publicationSlides() {
      const slides = [];
      const itemsPerSlide = 2;
      
      for (let i = 0; i < this.publications.length; i += itemsPerSlide) {
        slides.push(this.publications.slice(i, i + itemsPerSlide));
      }
      
      return slides;
    }
  },
  methods: {
    nextSlide() {
      if (this.currentSlide < this.publicationSlides.length - 1) {
        this.currentSlide++;
      }
    },
    prevSlide() {
      if (this.currentSlide > 0) {
        this.currentSlide--;
      }
    }
  }
};
</script>

<style scoped>
.about-page {
  width: 100%;
  margin: 0;
  padding: 0;
}

/* Section Titles */
.section-title {
  font-size: var(--font-size-xxl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-lg) 0;
  text-align: center;
}

.section-subtitle {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-md);
  margin-bottom: calc(var(--spacing-xl) + 10px);
}

/* Introduction Section */
.intro-section {
  padding: 0 0 60px;
}

.intro-content {
  text-align: center;
}

.intro-text {
  font-size: var(--font-size-md);
  line-height: 1.8;
  color: var(--color-text-tertiary);
  max-width: 800px;
  margin: 0 auto var(--spacing-xxl);
}

/* Features Grid */
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-xl);
  margin-top: var(--spacing-xxl);
}

.feature-card {
  background: var(--color-bg-panel);
  padding: calc(var(--spacing-xl) + 10px) var(--spacing-xl);
  border-radius: calc(var(--radius-lg) + 4px);
  text-align: center;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  border: 2px solid transparent;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-colored);
  border-color: var(--color-primary-gradient-start);
}

.feature-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-lg);
}

.feature-card h3 {
  font-size: calc(var(--font-size-lg) + 0.5px);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-base) 0;
}

.feature-card p {
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  line-height: 1.6;
  margin: 0;
}

/* Developer Banner */
.developer-banner {
  background: var(--color-bg-dark);
  border-top: 1px solid var(--color-bg-input);
  padding: var(--spacing-lg) calc(var(--spacing-xl) + 10px);
  margin-top: calc(var(--spacing-xxl) + 10px);
  margin-bottom: calc(var(--spacing-xl) + 10px);
}

.developer-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
  font-size: var(--font-size-base);
}

.created-by {
  color: var(--color-text-muted);
}

.developer-name {
  color: var(--color-text-primary);
  font-weight: 600;
}

.separator {
  color: var(--color-bg-border);
}

.developer-role {
  color: var(--color-text-muted);
}

.scholar-link {
  color: var(--color-primary-gradient-start);
  text-decoration: none;
  transition: color var(--transition-base);
  font-weight: 500;
}

.scholar-link:hover {
  color: var(--color-primary-gradient-end);
}

/* Research Section */
.research-section {
  padding: calc(var(--spacing-xxl) + 10px) calc(var(--spacing-xl) + 10px);
}

/* Carousel Container */
.carousel-container {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.publications-carousel {
  overflow: hidden;
  flex: 1;
}

.carousel-track {
  display: flex;
  transition: transform 0.5s ease;
}

.carousel-slide {
  min-width: 100%;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-xl);
}

/* Carousel Buttons */
.carousel-button {
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-border);
  color: var(--color-text-primary);
  width: 50px;
  height: 50px;
  border-radius: var(--radius-circle);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: var(--transition-base);
  flex-shrink: 0;
}

.carousel-button:hover:not(:disabled) {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  transform: scale(1.1);
}

.carousel-button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.carousel-arrow {
  font-size: 24px;
  font-weight: bold;
}

/* Carousel Dots */
.carousel-dots {
  display: flex;
  justify-content: center;
  gap: var(--spacing-sm);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-circle);
  background: var(--color-bg-border);
  border: none;
  cursor: pointer;
  transition: var(--transition-base);
}

.dot:hover {
  background: var(--color-bg-disabled);
}

.dot.active {
  background: var(--color-primary-gradient-start);
  transform: scale(1.3);
}

.publication-card {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  border: 2px solid transparent;
}

.publication-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-bg-input);
}

.publication-header {
  margin-bottom: var(--spacing-base);
}

.publication-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.4;
  margin: 0;
}

.publication-authors {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-sm);
}

.publication-venue-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.publication-venue {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-style: italic;
}

.publication-year {
  background: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-sm);
  font-weight: 600;
  flex-shrink: 0;
}

.publication-actions {
  display: flex;
  gap: var(--spacing-md);
  margin-top: var(--spacing-lg);
  justify-content: center;
}

.action-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) calc(var(--spacing-base) + 1px);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: 500;
  text-decoration: none;
  transition: var(--transition-base);
  cursor: pointer;
  border: none;
  font-family: inherit;
}

.action-button.primary {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
}

.action-button.primary:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-colored);
}

.action-button.secondary {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.action-button.secondary:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.button-icon {
  font-size: 16px;
}

/* Responsive Design */
@media (max-width: 768px) {
  .developer-banner {
    padding: var(--spacing-base) var(--spacing-lg);
  }
  
  .developer-content {
    font-size: var(--font-size-sm);
    gap: var(--spacing-sm);
  }
  
  .separator {
    display: none;
  }
  
  .carousel-slide {
    grid-template-columns: 1fr;
  }
  
  .carousel-button {
    width: 40px;
    height: 40px;
  }
  
  .carousel-arrow {
    font-size: 20px;
  }
  
  .publication-actions {
    flex-direction: column;
  }
  
  .action-button {
    width: 100%;
    justify-content: center;
  }
}
</style>
