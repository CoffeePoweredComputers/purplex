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
import authHeader from '../services/auth-header';
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
        const response = await axios.get('/api/admin/problems/', { headers: authHeader() });
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
        const response = await axios.get('/api/admin/problem-sets/', { headers: authHeader() });
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
        await axios.delete(`/api/admin/problem/${problemId}/`, { headers: authHeader() });
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
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
  background-color: #1e1e1e;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.page-title {
  font-size: 28px;
  color: #e0e0e0;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #444;
}

.status-container {
  margin-bottom: 20px;
}

.controls-container {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.loading-indicator {
  padding: 15px;
  background-color: #333;
  border-radius: 6px;
  color: #ddd;
}

.error-message {
  padding: 15px;
  background-color: #442a2a;
  border-radius: 6px;
  color: #ffadb9;
}

.table-responsive {
  overflow-x: auto;
  background-color: #272727;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.problems-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.problems-table th {
  background-color: #333;
  color: #ddd;
  padding: 12px 15px;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.9rem;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #444;
}

.problems-table td {
  padding: 12px 15px;
  border-bottom: 1px solid #333;
  color: #e0e0e0;
  vertical-align: middle;
}

.problems-table tr:hover {
  background-color: #2a2a2a;
}

.problems-table tr:last-child td {
  border-bottom: none;
}

.badge {
  padding: 6px 12px;
  border-radius: 30px;
  font-weight: 500;
  font-size: 0.8rem;
  display: inline-block;
  text-align: center;
}

.easy-badge {
  background-color: #2d4d3a;
  color: #a3e9c1;
}

.medium-badge {
  background-color: #4d4c2d;
  color: #e9e4a3;
}

.hard-badge {
  background-color: #4d2d2d;
  color: #e9a3a3;
}

.default-badge {
  background-color: #2d3a4d;
  color: #a3c9e9;
}

.actions-cell {
  display: flex;
  gap: 10px;
}

.action-button {
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  font-weight: 500;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.85rem;
}

.add-button {
  background-color: #2d4d3a;
}

.add-button:hover {
  background-color: #3a6349;
}

.manage-sets-button {
  background-color: #2d3a4d;
}

.manage-sets-button:hover {
  background-color: #3a4a63;
}

.edit-button {
  background-color: #4d4c2d;
}

.edit-button:hover {
  background-color: #636149;
}

.delete-button {
  background-color: #4d2d2d;
}

.delete-button:hover {
  background-color: #633a3a;
}
</style>