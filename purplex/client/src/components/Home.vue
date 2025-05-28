<template>
  <div class="home-container">
    <div class="gallery-section">
      <div class="gallery-header">
        <h2 class="gallery-title">
          <span class="title-icon">📚</span>
          Explain in Plain Language Questions
        </h2>
      </div>

      <div v-if="loading.codeComprehension" class="gallery-grid">
        <!-- Skeleton cards to prevent layout shift -->
        <div v-for="n in 3" :key="`skeleton-${n}`" class="problem-set-card skeleton">
          <div class="card-content">
            <div class="card-header">
              <div class="skeleton-title"></div>
            </div>
            <div class="progress-section">
              <div class="skeleton-progress-bar"></div>
              <div class="skeleton-progress-text"></div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="gallery-grid">
        <div 
                  class="problem-set-card" 
                  v-for="problemSet in problemsSets" 
                  :key="problemSet.slug" 
                  @click="handleClick(problemSet)"
                  >
                  <div class="card-content">
                    <div class="card-header">
                      <h3 class="card-title">{{ problemSet.title }}</h3>
                    </div>

                    <div class="progress-section">
                      <div class="progress-bar-container">
                        <div class="progress-bar-background">
                          <div 
                             class="progress-bar-fill" 
                             :style="{ width: getProgressPercentage(problemSet) + '%' }"
                             ></div>
                        </div>
                        <span class="progress-text">
                          <template v-if="getTotalProblems(problemSet) === 0">
                            No problems yet
                          </template>
                          <template v-else>
                            {{ getCompletedCount(problemSet) }} / {{ getTotalProblems(problemSet) }} completed
                          </template>
                        </span>
                      </div>
                    </div>
                    <div v-if="isCompleted(problemSet)" class="completion-badge">
                      <span class="badge-icon">✅</span>
                      <span class="badge-text">Completed</span>
                    </div>
                  </div>
                  <div class="card-hover-text">{{ isCompleted(problemSet) ? 'Review →' : 'Continue →' }}</div>
        </div>
      </div>
    </div>

    <div class="gallery-section coming-soon">
      <div class="gallery-header">
        <h2 class="gallery-title">
          <span class="title-icon">🔧</span>
          Function ReDefinition Questions
        </h2>
      </div>
      <div class="coming-soon-content">
        <div class="sparkle">✨</div>
        <h3>Coming Soon</h3>
        <p>New problem sets are being prepared for you!</p>
      </div>
    </div>

  </div>
</template>

<script>
  import axios from 'axios';

  export default {
    name: 'Gallery',
    components: {},
    data() {
      return {
        problemsSets: [],
        progressData: [], // Store progress data for all problem sets
        loading: {
          codeComprehension: true, // Start with loading state as true
        }
      };
    },
    computed: {
      isAdmin() {
        return this.$store.getters['auth/isAdmin'];
      }
    },
    methods: {
      handleClick(problemSet) {
        this.$router.push({ path: `/problem-set/${problemSet.slug}`});
      },
      // Progress tracking methods
      getTotalProblems(problemSet) {
        // Use problems_count from API if available, otherwise fallback to problems array length
        return problemSet.problems_count || (problemSet.problems ? problemSet.problems.length : 0);
      },
      getCompletedCount(problemSet) {
        // Find progress data for this problem set
        const progress = this.progressData.find(p => p.problem_set_slug === problemSet.slug);
        return progress ? progress.completed_problems : 0;
      },
      getProgressPercentage(problemSet) {
        const total = this.getTotalProblems(problemSet);
        const completed = this.getCompletedCount(problemSet);
        return total > 0 ? Math.round((completed / total) * 100) : 0;
      },
      isCompleted(problemSet) {
        return this.getProgressPercentage(problemSet) === 100;
      },
      loadProblemSets() {
        // Only load if user is authenticated
        if (!this.$store.state.auth.status.loggedIn) {
          console.log('Not loading problem sets - user not authenticated');
          this.loading.codeComprehension = false;
          return;
        }

        this.loading.codeComprehension = true;

        // Load both problem sets and progress data in parallel
        Promise.all([
          axios.get('/api/problem-sets/'),
          axios.get('/api/progress-summary/')
        ])
          .then(([problemSetsResponse, progressResponse]) => {
            console.log('Problem sets loaded:', problemSetsResponse.data);
            console.log('Progress data loaded:', progressResponse.data);

            this.problemsSets = problemSetsResponse.data;
            this.progressData = progressResponse.data.problem_sets || [];
            this.loading.codeComprehension = false;
          })
          .catch(error => {
            console.error('Error fetching data:', error);
            this.loading.codeComprehension = false;
          });
      }
    },

    async created() {
      // Always try to load problem sets when component is created
      // The loadProblemSets method has its own auth check
      this.loadProblemSets();
    },
    activated() {
      this.loadProblemSets();
    },

    // Watch for auth state changes - reload when user logs in
    watch: {
      '$store.state.auth.status.loggedIn': function(newVal, oldVal) {
        // Only reload if transitioning from not logged in to logged in
        if (newVal === true && oldVal === false) {
          console.log('Auth state changed to logged in, reloading problem sets');
          this.loadProblemSets();
        }
      }
    },
  };
</script>

<style scoped>
.home-container {
  padding: var(--spacing-lg);
  max-width: var(--max-width-content);
  margin: 0 auto;
}

.gallery-section {
  margin-bottom: calc(var(--spacing-xl) + 10px);
}

.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-input);
}

.gallery-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.title-icon {
  font-size: 32px;
}


/* Skeleton Loading State */
.problem-set-card.skeleton {
  pointer-events: none;
  animation: pulse 1.5s ease-in-out infinite;
}

    @keyframes pulse {
      0%, 100% {
        opacity: 1;
      }
      50% {
        opacity: 0.5;
      }
    }

    .skeleton-title {
      height: 20px;
      width: 70%;
      background: var(--color-bg-input);
      border-radius: var(--radius-xs);
    }

    .skeleton-progress-bar {
      height: 8px;
      width: 100%;
      background: var(--color-bg-input);
      border-radius: var(--radius-xs);
      margin-bottom: var(--spacing-sm);
    }

    .skeleton-progress-text {
      height: 13px;
      width: 40%;
      background: var(--color-bg-input);
      border-radius: var(--radius-xs);
      margin: 0 auto;
    }

    /* Gallery Grid */
    .gallery-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 25px;
    }

    /* Problem Set Card */
    .problem-set-card {
      background: var(--color-bg-panel);
      border-radius: var(--radius-lg);
      overflow: hidden;
      cursor: pointer;
      transition: var(--transition-base);
      box-shadow: var(--shadow-md);
      position: relative;
      min-height: 180px;
      display: flex;
      flex-direction: column;
      border: 2px solid transparent;
    }

    .problem-set-card:hover {
      transform: translateY(-5px);
      box-shadow: var(--shadow-lg);
      border-color: var(--color-primary-gradient-start);
    }

    .card-content {
      padding: var(--spacing-xl);
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .card-header {
      position: relative;
      margin-bottom: var(--spacing-lg);
    }

    .card-hover-text {
      position: absolute;
      bottom: var(--spacing-lg);
      right: var(--spacing-lg);
      color: var(--color-primary-gradient-start);
      font-weight: 600;
      font-size: var(--font-size-base);
      opacity: 0;
      transform: translateX(-10px);
      transition: var(--transition-base);
    }

    .problem-set-card:hover .card-hover-text {
      opacity: 1;
      transform: translateX(0);
    }

    .card-title {
      font-size: var(--font-size-base);
      color: var(--color-text-primary);
      margin: 0;
    }

    /* Completion Badge */
    .completion-badge {
      top: var(--spacing-sm);
      right: var(--spacing-sm);
      display: flex;
      align-items: center;
      gap: var(--spacing-xs);
      background: var(--color-success-bg);
      padding: var(--spacing-xs) var(--spacing-md);
      border-radius: var(--radius-xl);
      border: 1px solid var(--color-success);
      margin: auto;
    }

    .badge-icon {
      font-size: 14px;
    }

    .badge-text {
      font-size: var(--font-size-xs);
      font-weight: 600;
      color: var(--color-success);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    /* Progress Section */
    .progress-section {
      margin: var(--spacing-lg) 0;
    }

    .progress-bar-container {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-sm);
    }

    .progress-bar-background {
      width: 100%;
      height: 8px;
      background: var(--color-bg-hover);
      border-radius: var(--radius-xs);
      overflow: hidden;
      position: relative;
    }

    .progress-bar-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
      border-radius: var(--radius-xs);
      transition: width var(--transition-slow);
    }

    .progress-text {
      font-size: var(--font-size-sm);
      color: var(--color-text-muted);
      text-align: center;
    }


    /* Coming Soon Section */
    .coming-soon {
      opacity: 0.8;
    }

    .coming-soon-content {
      text-align: center;
      padding: calc(var(--spacing-xxl) + 30px) var(--spacing-lg);
      background: linear-gradient(135deg, var(--color-bg-panel) 0%, var(--color-bg-hover) 100%);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-md);
    }

    .sparkle {
      font-size: 48px;
      margin-bottom: var(--spacing-lg);
      animation: sparkle 2s ease-in-out infinite;
    }

    @keyframes sparkle {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(1.1); }
    }

    .coming-soon-content h3 {
      font-size: var(--font-size-xl);
      color: var(--color-text-primary);
      margin: 0 0 var(--spacing-sm) 0;
    }

    .coming-soon-content p {
      color: var(--color-text-muted);
      font-size: var(--font-size-base);
      margin: 0;
    }

    /* Modal Styles */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(4px);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1000;
      animation: fadeIn 0.2s ease-out;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .modal-content {
      background: var(--color-bg-panel);
      border-radius: var(--radius-lg);
      width: 90%;
      max-width: 540px;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: var(--shadow-lg);
      border: 2px solid var(--color-bg-input);
      animation: slideIn 0.3s ease-out;
    }

    @keyframes slideIn {
      from { 
        opacity: 0;
        transform: translateY(-20px) scale(0.95);
      }
      to { 
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: var(--spacing-xl) var(--spacing-xl) var(--spacing-lg) var(--spacing-xl);
      border-bottom: 1px solid var(--color-bg-input);
    }

    .modal-title {
      font-size: var(--font-size-lg);
      font-weight: 600;
      color: var(--color-text-primary);
      margin: 0;
    }

    .modal-close {
      background: var(--color-bg-hover);
      border: 1px solid var(--color-bg-border);
      color: var(--color-text-secondary);
      width: 32px;
      height: 32px;
      border-radius: var(--radius-circle);
      cursor: pointer;
      transition: var(--transition-fast);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .modal-close:hover {
      background: var(--color-bg-input);
      color: var(--color-text-primary);
      border-color: var(--color-primary-gradient-start);
    }

    .close-icon {
      font-size: 16px;
      font-weight: bold;
    }

    .modal-form {
      padding: var(--spacing-xl);
      display: flex;
      flex-direction: column;
      gap: var(--spacing-xl);
    }

    .form-field {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-sm);
    }

    .field-label {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-xs);
    }

    .label-text {
      font-size: var(--font-size-base);
      font-weight: 600;
      color: var(--color-text-primary);
      letter-spacing: -0.01em;
    }

    .label-subtitle {
      font-size: var(--font-size-sm);
      color: var(--color-text-muted);
      font-weight: 400;
    }

    .form-input {
      width: 100%;
      padding: calc(var(--spacing-md) + 2px) var(--spacing-md);
      background: var(--color-bg-input);
      border: 1px solid var(--color-bg-border);
      border-radius: var(--radius-base);
      color: var(--color-text-primary);
      font-size: var(--font-size-base);
      transition: var(--transition-fast);
      box-sizing: border-box;
    }

    .form-input:focus {
      outline: none;
      border-color: var(--color-primary-gradient-start);
      box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    .form-textarea {
      resize: vertical;
      min-height: 80px;
      font-family: inherit;
      line-height: 1.5;
    }

    .file-input-wrapper {
      position: relative;
    }

    .file-input-label {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      padding: calc(var(--spacing-md) + 2px) var(--spacing-md);
      background: var(--color-bg-input);
      border: 1px solid var(--color-bg-border);
      border-radius: var(--radius-base);
      color: var(--color-text-secondary);
      cursor: pointer;
      transition: var(--transition-fast);
    }

    .file-input-label:hover {
      background: var(--color-bg-hover);
      border-color: var(--color-primary-gradient-start);
      color: var(--color-text-primary);
    }

    .file-icon {
      font-size: 18px;
    }

    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: var(--spacing-md);
      padding-top: var(--spacing-lg);
      border-top: 1px solid var(--color-bg-input);
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: var(--spacing-sm);
      padding: var(--spacing-md) var(--spacing-lg);
      border-radius: var(--radius-base);
      font-size: var(--font-size-base);
      font-weight: 600;
      cursor: pointer;
      transition: var(--transition-base);
      border: none;
      text-decoration: none;
      box-sizing: border-box;
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
      color: var(--color-text-primary);
      box-shadow: var(--shadow-colored);
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }

    .btn-secondary {
      background: var(--color-bg-hover);
      color: var(--color-text-tertiary);
      border: 1px solid var(--color-bg-border);
    }

    .btn-secondary:hover {
      background: var(--color-bg-input);
      border-color: var(--color-primary-gradient-start);
      color: var(--color-text-primary);
    }

    .btn-icon {
      font-size: 16px;
    }

    /* Responsive Design */
    @media (max-width: 768px) {
      .modal-content {
        width: 95%;
        margin: var(--spacing-lg);
      }

      .modal-header,
      .modal-form {
        padding: var(--spacing-lg);
      }

      .modal-actions {
        flex-direction: column-reverse;
      }

      .btn {
        width: 100%;
        justify-content: center;
      }
    }

</style>
