<template>
  <div class="home-container">
    <div class="gallery-section">
      <div class="gallery-header">
        <h2 class="gallery-title">
          <span class="title-icon">📚</span>
          Explain in Plain Language Questions
        </h2>
        <button v-if="isAdmin" @click="showAddProblemSetModal = true" class="add-btn">
          <span class="plus-icon">+</span>
          Add Problem Set
        </button>
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
          :key="problemSet.name" 
          @click="handleClick(problemSet)"
        >
          <div class="card-content">
            <div class="card-header">
              <h3 class="card-title">{{ problemSet.title }}</h3>
              <div v-if="isCompleted(problemSet)" class="completion-badge">
                <span class="badge-icon">✅</span>
                <span class="badge-text">Completed</span>
              </div>
            </div>
            
            <div class="progress-section">
              <div class="progress-bar-container">
                <div class="progress-bar-background">
                  <div 
                    class="progress-bar-fill" 
                    :style="{ width: getProgressPercentage(problemSet) + '%' }"
                  ></div>
                </div>
                <span class="progress-text">{{ getCompletedCount(problemSet) }} / {{ getTotalProblems(problemSet) }} completed</span>
              </div>
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

    <!-- Add Problem Set Modal -->
    <div v-if="showAddProblemSetModal" class="modal-backdrop">
      <div class="modal-content">
        <h2>Add New Problem Set</h2>
        <form @submit.prevent="createProblemSet">
          <div class="form-group">
            <label for="title">Title:</label>
            <input type="text" id="title" v-model="newProblemSet.title" required>
          </div>
          <div class="form-group">
            <label for="sid">Set ID (unique identifier):</label>
            <input type="text" id="sid" v-model="newProblemSet.sid" required>
          </div>
          <div class="form-group">
            <label for="description">Description:</label>
            <textarea id="description" v-model="newProblemSet.description" rows="3"></textarea>
          </div>
          <div class="form-group">
            <label for="icon">Icon:</label>
            <input type="file" id="icon" @change="handleFileUpload" accept="image/*">
          </div>
          <div class="modal-actions">
            <button type="button" @click="showAddProblemSetModal = false" class="cancel-btn">Cancel</button>
            <button type="submit" class="submit-btn">Create Problem Set</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
  import axios from 'axios';

  export default {
    name: 'Gallery',
    data() {
      return {
        problemsSets: [],
        loading: {
          codeComprehension: true, // Start with loading state as true
        },
        showAddProblemSetModal: false,
        newProblemSet: {
          title: '',
          sid: '',
          description: '',
          icon: null
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
        this.$router.push({ path: `/problem-set/${problemSet.sid}`});
      },
      handleFileUpload(event) {
        this.newProblemSet.icon = event.target.files[0];
      },
      // Placeholder methods for progress tracking
      getTotalProblems(problemSet) {
        return problemSet.problems ? problemSet.problems.length : 10; // Default to 10 for demo
      },
      getCompletedCount(problemSet) {
        // Placeholder: return a fixed number for demo
        return 3; // Just return 3 completed for all sets as placeholder
      },
      getProgressPercentage(problemSet) {
        const total = this.getTotalProblems(problemSet);
        const completed = this.getCompletedCount(problemSet);
        return total > 0 ? Math.round((completed / total) * 100) : 0;
      },
      isCompleted(problemSet) {
        return this.getProgressPercentage(problemSet) === 100;
      },
      createProblemSet() {
        // Create FormData object to send form including the file
        const formData = new FormData();
        formData.append('title', this.newProblemSet.title);
        formData.append('sid', this.newProblemSet.sid);
        // Empty problems array as required by the serializer
        formData.append('problems', JSON.stringify([]));
        if (this.newProblemSet.icon) {
          formData.append('icon', this.newProblemSet.icon);
        }

        console.log('Creating problem set with:', {
          title: this.newProblemSet.title,
          sid: this.newProblemSet.sid,
          problems: [],
          icon: this.newProblemSet.icon ? this.newProblemSet.icon.name : 'No icon uploaded'
        });

        axios.post('/api/admin/problem-sets/', formData)
          .then(response => {
            return response.data;
          })
          .then(data => {
            console.log('Problem set created successfully:', data);
            this.problemsSets.push(data);
            this.resetForm();
            this.showAddProblemSetModal = false;
          })
          .catch(error => {
            console.error('Error creating problem set:', error);
            alert(`Failed to create problem set: ${error.message}`);
          });
      },
      resetForm() {
        this.newProblemSet = {
          title: '',
          sid: '',
          description: '',
          icon: null
        };
      },
      loadProblemSets() {
        // Only load if user is authenticated
        if (!this.$store.state.auth.status.loggedIn) {
          console.log('Not loading problem sets - user not authenticated');
          this.loading.codeComprehension = false;
          return;
        }
        
        this.loading.codeComprehension = true;
        axios.get('/api/problem-sets/')
          .then(response => {
            console.log('Problem sets loaded:', response.data);
            this.problemsSets = response.data;
            this.loading.codeComprehension = false;
          })
          .catch(error => {
            console.error('Error fetching problem sets:', error);
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

.add-btn {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-base);
  padding: var(--spacing-sm) var(--spacing-lg);
  cursor: pointer;
  font-weight: 600;
  font-size: var(--font-size-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  transition: var(--transition-base);
  box-shadow: var(--shadow-colored);
}

.add-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.plus-icon {
  font-size: 18px;
  font-weight: bold;
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
  position: absolute;
  top: var(--spacing-sm);
  right: var(--spacing-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  background: var(--color-success-bg);
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-success);
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

/* Modal styles */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
}

.modal-content {
  background-color: var(--color-bg-hover);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
  width: 90%;
  max-width: 500px;
  box-shadow: var(--shadow-sm);
}

.form-group {
  margin-bottom: var(--spacing-base);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-weight: bold;
  text-align: left;
}

.form-group input, 
.form-group textarea {
  width: 100%;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  background-color: var(--color-bg-input);
  color: var(--color-text-primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-lg);
}

.cancel-btn {
  background-color: var(--color-bg-disabled);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-xs);
  padding: var(--spacing-sm) calc(var(--spacing-base) + 1px);
  cursor: pointer;
}

.submit-btn {
  background-color: var(--color-success);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-xs);
  padding: var(--spacing-sm) calc(var(--spacing-base) + 1px);
  cursor: pointer;
}

.cancel-btn:hover {
  background-color: var(--color-bg-border);
}

.submit-btn:hover {
  background-color: #45a049;
}

</style>
