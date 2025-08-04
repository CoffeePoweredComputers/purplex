<template>
  <div>
    <AdminNavBar />
    <div class="admin-problem-sets container">
      <h1 class="page-title">
        Problem Sets Management
      </h1>
      
      <div class="status-container">
        <div
          v-if="loading"
          class="loading-indicator"
        >
          Loading problem sets...
        </div>
        
        <div
          v-if="error"
          class="error-message"
        >
          {{ error }}
        </div>
      </div>
      
      <div
        v-if="!loading && !error"
        class="controls-container"
      >
        <button
          class="action-button add-button"
          @click="showAddModal = true"
        >
          Add New Problem Set
        </button>
      </div>
      
      <div
        v-if="!loading && !error"
        class="table-responsive"
      >
        <table class="problem-sets-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Description</th>
              <th>Problems</th>
              <th>Visibility</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="set in problemSets"
              :key="set.slug"
            >
              <td>{{ set.title }}</td>
              <td>{{ set.description || 'No description' }}</td>
              <td>{{ set.problems_count || 0 }}</td>
              <td>
                <span :class="['visibility-badge', set.is_public ? 'public' : 'private']">
                  {{ set.is_public ? 'Public' : 'Private' }}
                </span>
              </td>
              <td class="actions-cell">
                <button
                  class="action-button edit-button"
                  @click="editProblemSet(set)"
                >
                  Edit
                </button>
                <button
                  class="action-button delete-button"
                  @click="confirmDelete(set)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        
        <p
          v-if="problemSets.length === 0"
          class="no-data"
        >
          No problem sets found. Create your first one!
        </p>
      </div>
    </div>

    <!-- Add Problem Set Modal -->
    <AddEditProblemSetModal
      v-if="showAddModal"
      :problems="problems"
      @close="showAddModal = false"
      @problem-set-added="handleProblemSetAdded"
      @error="handleError"
    />
    
    <!-- Edit Problem Set Modal -->
    <AddEditProblemSetModal 
      v-if="showEditModal"
      :edit-mode="true"
      :problem-set-data="selectedProblemSet"
      :problems="problems"
      @close="showEditModal = false"
      @problem-set-updated="handleProblemSetUpdated"
      @error="handleError"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { mapGetters } from 'vuex';
import axios, { AxiosError } from 'axios';
import AdminNavBar from './AdminNavBar.vue';
import AddEditProblemSetModal from '../modals/AddEditProblemSetModal.vue';
import { log } from '@/utils/logger';
import type { ProblemSet, ProblemDetailed } from '@/types';

interface ComponentData {
  problemSets: ProblemSet[];
  problems: ProblemDetailed[];
  loading: boolean;
  error: string | null;
  showAddModal: boolean;
  showEditModal: boolean;
  selectedProblemSet: ProblemSet | null;
}

export default defineComponent({
  name: 'AdminProblemSets',
  components: {
    AdminNavBar,
    AddEditProblemSetModal
  },
  data(): ComponentData {
    return {
      problemSets: [],
      problems: [],
      loading: true,
      error: null,
      showAddModal: false,
      showEditModal: false,
      selectedProblemSet: null
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
    
    this.fetchData();
  },
  methods: {
    async fetchData(): Promise<void> {
      try {
        this.loading = true;
        this.error = null;
        
        const [setsResponse, problemsResponse] = await Promise.all([
          axios.get('/api/admin/problem-sets/'),
          axios.get('/api/admin/problems/')
        ]);
        
        this.problemSets = setsResponse.data;
        this.problems = problemsResponse.data;
      } catch (error) {
        const axiosError = error as AxiosError;
        this.error = 'Failed to load data. Please try again.';
        log.error('Error fetching data', axiosError);
      } finally {
        this.loading = false;
      }
    },
    
    editProblemSet(set: ProblemSet): void {
      this.selectedProblemSet = set;
      this.showEditModal = true;
    },
    
    confirmDelete(set: ProblemSet): void {
      if (confirm(`Are you sure you want to delete the problem set "${set.title}"? This action cannot be undone.`)) {
        this.deleteProblemSet(set);
      }
    },
    
    async deleteProblemSet(set: ProblemSet): Promise<void> {
      try {
        await axios.delete(`/api/admin/problem-sets/${set.slug}/`);
        // Remove the problem set from the array
        this.problemSets = this.problemSets.filter(s => s.slug !== set.slug);
      } catch (error) {
        const axiosError = error as AxiosError;
        this.error = 'Failed to delete problem set. Please try again.';
        log.error('Error deleting problem set', axiosError);
      }
    },
    
    // Modal event handlers
    handleProblemSetAdded(newProblemSet: ProblemSet): void {
      this.problemSets.push(newProblemSet);
      this.showAddModal = false;
    },
    
    handleProblemSetUpdated(updatedProblemSet: ProblemSet): void {
      const index = this.problemSets.findIndex(s => s.slug === updatedProblemSet.slug);
      if (index !== -1) {
        this.problemSets[index] = updatedProblemSet;
      }
      this.showEditModal = false;
      this.selectedProblemSet = null;
    },
    
    handleError(errorMessage: string): void {
      this.error = errorMessage;
      // Clear error after 5 seconds
      setTimeout(() => {
        this.error = null;
      }, 5000);
    }
  }
});
</script>

<style scoped>
.admin-problem-sets {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: var(--spacing-lg);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xl) 0;
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-input);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.status-container {
  margin-bottom: var(--spacing-xl);
}

.controls-container {
  display: flex;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.loading-indicator {
  padding: var(--spacing-xl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
  text-align: center;
  box-shadow: var(--shadow-md);
}

.error-message {
  padding: var(--spacing-xl);
  background: var(--color-error-bg);
  border-radius: var(--radius-lg);
  color: var(--color-error-text);
  text-align: center;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-error);
}

.action-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-base);
}

.add-button {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  box-shadow: var(--shadow-colored);
}

.add-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.add-button::before {
  content: "+";
  font-size: 18px;
  font-weight: bold;
}

.table-responsive {
  overflow-x: auto;
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 2px solid transparent;
  transition: var(--transition-base);
}

.table-responsive:hover {
  border-color: var(--color-bg-input);
}

.problem-sets-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.problem-sets-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-lg) var(--spacing-xl);
  font-weight: 600;
  font-size: var(--font-size-base);
  border-bottom: 2px solid var(--color-bg-input);
}

.problem-sets-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.problem-sets-table tr:hover {
  background: var(--color-bg-hover);
}

.problem-sets-table tr:last-child td {
  border-bottom: none;
}

.visibility-badge {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-weight: 600;
  font-size: var(--font-size-xs);
  display: inline-block;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.visibility-badge.public {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.visibility-badge.private {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.actions-cell {
  display: flex;
  gap: var(--spacing-md);
}

.edit-button {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.edit-button:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.delete-button {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.delete-button:hover {
  background: var(--color-error);
  color: var(--color-text-primary);
  transform: translateY(-1px);
}

.no-data {
  text-align: center;
  padding: var(--spacing-xxl);
  color: var(--color-text-muted);
  font-size: var(--font-size-md);
}

/* Responsive Design */
@media (max-width: 768px) {
  .controls-container {
    flex-direction: column;
  }
  
  .action-button {
    width: 100%;
    justify-content: center;
  }
  
  .problem-sets-table {
    font-size: var(--font-size-sm);
  }
  
  .problem-sets-table th,
  .problem-sets-table td {
    padding: var(--spacing-md);
  }
  
  .actions-cell {
    flex-direction: column;
  }
}
</style>