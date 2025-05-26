<template>
  <div>
    <AdminNavBar />
    <div class="admin-problems container">
      <h1 class="page-title">Problems Management</h1>
      
      <div class="status-container">
        <div class="loading-indicator" v-if="loading">
          Loading problems...
        </div>
        
        <div class="error-message" v-if="error">
          {{ error }}
        </div>
      </div>
      
      <div class="controls-container" v-if="!loading && !error">
        <button class="action-button add-button" @click="showAddProblemModal = true">
          Add New Problem
        </button>
        
        <button class="action-button manage-sets-button" @click="showProblemSetsModal = true">
          Manage Problem Sets
        </button>
      </div>
      
      <div class="table-responsive" v-if="!loading && !error">
        <table class="problems-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Difficulty</th>
              <th>Category</th>
              <th>Problem Sets</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="problem in problems" :key="problem.id">
              <td>{{ problem.name }}</td>
              <td>
                <span class="badge" :class="difficultyClass(problem.difficulty)">
                  {{ problem.difficulty }}
                </span>
              </td>
              <td>{{ problem.category }}</td>
              <td>{{ getProblemSets(problem) }}</td>
              <td class="actions-cell">
                <button class="action-button edit-button" @click="editProblem(problem.id)">
                  Edit
                </button>
                <button class="action-button delete-button" @click="confirmDelete(problem.id)">
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import axios from 'axios';
import AdminNavBar from './AdminNavBar.vue';

export default {
  name: 'AdminProblems',
  components: {
    AdminNavBar
  },
  data() {
    return {
      problems: [],
      problemSets: [],
      loading: true,
      error: null,
      showAddProblemModal: false,
      showProblemSetsModal: false,
      selectedProblemId: null
    };
  },
  computed: {
    ...mapGetters('auth', ['isAdmin'])
  },
  created() {
    // Redirect non-admin users
    if (!this.isAdmin) {
      this.$router.push('/');
      return;
    }
    
    this.fetchProblems();
    this.fetchProblemSets();
  },
  methods: {
    async fetchProblems() {
      try {
        this.loading = true;
        const response = await axios.get('/api/admin/problems/');
        this.problems = response.data;
        this.loading = false;
      } catch (error) {
        this.error = 'Failed to load problems. Please try again.';
        this.loading = false;
        console.error('Error fetching problems:', error);
      }
    },
    
    async fetchProblemSets() {
      try {
        const response = await axios.get('/api/admin/problem-sets/');
        this.problemSets = response.data;
      } catch (error) {
        console.error('Error fetching problem sets:', error);
      }
    },
    
    getProblemSets(problem) {
      // Extract and format problem sets this problem belongs to
      if (!problem.problem_sets || problem.problem_sets.length === 0) {
        return 'None';
      }
      
      return problem.problem_sets.map(psId => {
        const problemSet = this.problemSets.find(ps => ps.id === psId);
        return problemSet ? problemSet.name : 'Unknown';
      }).join(', ');
    },
    
    difficultyClass(difficulty) {
      switch(difficulty.toLowerCase()) {
        case 'easy':
          return 'easy-badge';
        case 'medium':
          return 'medium-badge';
        case 'hard':
          return 'hard-badge';
        default:
          return 'default-badge';
      }
    },
    
    editProblem(problemId) {
      this.selectedProblemId = problemId;
      // Implementation for editing problem
    },
    
    confirmDelete(problemId) {
      if (confirm('Are you sure you want to delete this problem? This action cannot be undone.')) {
        this.deleteProblem(problemId);
      }
    },
    
    async deleteProblem(problemId) {
      try {
        await axios.delete(`/api/admin/problem/${problemId}/`);
        // Remove the problem from the array
        this.problems = this.problems.filter(problem => problem.id !== problemId);
      } catch (error) {
        this.error = 'Failed to delete problem. Please try again.';
        console.error('Error deleting problem:', error);
      }
    }
  }
}
</script>

<style scoped>
.admin-problems {
  max-width: var(--max-width-panel);
  margin: 0 auto;
  padding: var(--spacing-lg);
  background-color: var(--color-bg-panel);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-base);
}

.page-title {
  font-size: var(--font-size-xl);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-sm);
  border-bottom: 2px solid var(--color-bg-border);
}

.status-container {
  margin-bottom: var(--spacing-lg);
}

.controls-container {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.loading-indicator {
  padding: var(--spacing-base);
  background-color: var(--color-bg-input);
  border-radius: calc(var(--radius-sm) + 1px);
  color: var(--color-text-tertiary);
}

.error-message {
  padding: var(--spacing-base);
  background-color: var(--color-error-bg);
  border-radius: calc(var(--radius-sm) + 1px);
  color: var(--color-error-text);
}

.table-responsive {
  overflow-x: auto;
  background-color: var(--color-bg-table);
  border-radius: calc(var(--radius-sm) + 1px);
  box-shadow: var(--shadow-sm);
}

.problems-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.problems-table th {
  background-color: var(--color-bg-input);
  color: var(--color-text-tertiary);
  padding: var(--spacing-md) var(--spacing-base);
  font-weight: 600;
  text-transform: uppercase;
  font-size: calc(var(--font-size-sm) + 0.05rem);
  letter-spacing: 0.5px;
  border-bottom: 2px solid var(--color-bg-border);
}

.problems-table td {
  padding: var(--spacing-md) var(--spacing-base);
  border-bottom: 1px solid var(--color-bg-input);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.problems-table tr:hover {
  background-color: var(--color-bg-hover);
}

.problems-table tr:last-child td {
  border-bottom: none;
}

.badge {
  padding: calc(var(--spacing-xs) + 2px) var(--spacing-md);
  border-radius: var(--radius-round);
  font-weight: 500;
  font-size: calc(var(--font-size-xs) + 0.05rem);
  display: inline-block;
  text-align: center;
}

.easy-badge {
  background-color: var(--color-success-bg);
  color: var(--color-success-text);
}

.medium-badge {
  background-color: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.hard-badge {
  background-color: var(--color-error-bg);
  color: var(--color-error-text);
}

.default-badge {
  background-color: var(--color-info-bg);
  color: var(--color-info-text);
}

.actions-cell {
  display: flex;
  gap: var(--spacing-sm);
}

.action-button {
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
  border-radius: var(--radius-xs);
  font-weight: 500;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-sm);
}

.add-button {
  background-color: var(--color-success-bg);
}

.add-button:hover {
  background-color: #3a6349;
}

.manage-sets-button {
  background-color: var(--color-info-bg);
}

.manage-sets-button:hover {
  background-color: #3a4a63;
}

.edit-button {
  background-color: var(--color-warning-bg);
}

.edit-button:hover {
  background-color: #636149;
}

.delete-button {
  background-color: var(--color-error-bg);
}

.delete-button:hover {
  background-color: #633a3a;
}
</style>